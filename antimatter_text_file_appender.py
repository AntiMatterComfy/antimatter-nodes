import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path


_FILE_LOCK = threading.Lock()


def _default_output_dir() -> str:
    try:
        import folder_paths

        return folder_paths.get_output_directory()
    except Exception:
        return str(Path.cwd() / "output")


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(_as_text(item) for item in value)
    return str(value)


def _resolve_path(directory: str, filename: str, file_format: str) -> Path:
    directory = _as_text(directory).strip()
    filename = _as_text(filename).strip()

    if not filename:
        raise ValueError("filename cannot be empty")

    file_path = Path(filename).expanduser()
    if not file_path.is_absolute():
        if not directory:
            directory = _default_output_dir()
        file_path = Path(directory).expanduser() / file_path

    wanted_suffix = f".{file_format.lower()}"
    if file_path.suffix.lower() != wanted_suffix:
        file_path = file_path.with_suffix(wanted_suffix)

    return file_path


def _index_regex_from_template(prefix_template: str):
    if "{index}" not in prefix_template and "{counter}" not in prefix_template:
        return None

    token = "__BM_TEXT_FILE_APPENDER_INDEX__"
    template = prefix_template.replace("{index}", token).replace("{counter}", token)
    pattern = re.escape(template)
    pattern = pattern.replace(re.escape(token), r"(\d+)")

    for placeholder in ("{date}", "{time}", "{datetime}"):
        pattern = pattern.replace(re.escape(placeholder), r".+?")

    return re.compile(pattern)


def _next_text_index(file_path: Path, prefix_template: str, index_start: int) -> int:
    regex = _index_regex_from_template(prefix_template)
    if regex is None or not file_path.exists():
        return index_start

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return index_start

    numbers = []
    for match in regex.finditer(content):
        try:
            numbers.append(int(match.group(1)))
        except (IndexError, ValueError):
            pass

    return max(numbers) + 1 if numbers else index_start


def _load_json_records(file_path: Path):
    if not file_path.exists() or file_path.stat().st_size == 0:
        return []

    with file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError("Existing JSON file must contain a JSON array.")

    return data


def _next_json_index(file_path: Path, index_start: int) -> int:
    try:
        records = _load_json_records(file_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return index_start

    indexes = [
        record.get("index")
        for record in records
        if isinstance(record, dict) and isinstance(record.get("index"), int)
    ]
    return max(indexes) + 1 if indexes else index_start + len(records)


def _format_prefix(prefix_template: str, index: int, index_padding: int) -> str:
    now = datetime.now()
    padded_index = str(index).zfill(max(0, int(index_padding)))

    return (
        _as_text(prefix_template)
        .replace("{index}", padded_index)
        .replace("{counter}", padded_index)
        .replace("{date}", now.strftime("%Y-%m-%d"))
        .replace("{time}", now.strftime("%H-%M-%S"))
        .replace("{datetime}", now.strftime("%Y-%m-%d_%H-%M-%S"))
    )


def _append_txt(file_path: Path, saved_text: str, blank_lines_between_entries: int) -> None:
    has_existing_text = file_path.exists() and file_path.stat().st_size > 0
    separator = "\n" * (max(0, int(blank_lines_between_entries)) + 1)
    entry = saved_text.rstrip("\r\n")

    with file_path.open("a", encoding="utf-8", newline="\n") as handle:
        if has_existing_text:
            handle.write(separator)
        handle.write(entry)


def _write_json_records(file_path: Path, records: list, json_indent: int) -> None:
    tmp_path = file_path.with_name(f"{file_path.name}.tmp")
    indent = None if int(json_indent) <= 0 else int(json_indent)

    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=indent)
        handle.write("\n")

    os.replace(tmp_path, file_path)


def _append_json(file_path: Path, record: dict, json_indent: int) -> None:
    records = _load_json_records(file_path)
    records.append(record)
    _write_json_records(file_path, records, json_indent)


def _scene_number(scene_name: str):
    match = re.search(r"(\d+)", _as_text(scene_name))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _normalize_scene_name(scene_name: str) -> str:
    scene_name = _as_text(scene_name).strip().lower()
    number = _scene_number(scene_name)
    if number is not None:
        return f"scene-{number:03d}"
    return re.sub(r"[^a-z0-9]+", "-", scene_name).strip("-")


def _record_matches_scene(record: dict, scene_name: str) -> bool:
    if not isinstance(record, dict):
        return False

    normalized_scene = _normalize_scene_name(scene_name)
    scene_number = _scene_number(scene_name)
    for key in ("scene_name", "scene", "scene_id", "id", "name", "title"):
        value = record.get(key)
        if value is not None and _normalize_scene_name(value) == normalized_scene:
            return True

    if scene_number is not None:
        try:
            return int(record.get("index")) == scene_number
        except (TypeError, ValueError):
            return False
    return False


def _upsert_json_by_scene(file_path: Path, record: dict, scene_name: str, json_indent: int) -> bool:
    records = _load_json_records(file_path)
    scene_number = _scene_number(scene_name)

    replace_index = None
    for i, existing_record in enumerate(records):
        if _record_matches_scene(existing_record, scene_name):
            replace_index = i
            break

    if replace_index is None and scene_number is not None and 1 <= scene_number <= len(records):
        replace_index = scene_number - 1

    if replace_index is None:
        records.append(record)
        replaced = False
    else:
        records[replace_index] = record
        replaced = True

    _write_json_records(file_path, records, json_indent)
    return replaced


def _entry_matches_scene(entry: str, scene_name: str) -> bool:
    normalized_scene = _normalize_scene_name(scene_name)
    normalized_entry = re.sub(r"[^a-z0-9]+", "-", _as_text(entry).lower()).strip("-")
    if normalized_scene and normalized_scene in normalized_entry:
        return True

    scene_number = _scene_number(scene_name)
    if scene_number is None:
        return False

    patterns = (
        rf"\bscene[\s_-]*0*{scene_number}\b",
        rf"\bсцена[\s_-]*0*{scene_number}\b",
    )
    return any(re.search(pattern, entry, flags=re.IGNORECASE) for pattern in patterns)


def _replace_txt_by_scene(
    file_path: Path,
    saved_text: str,
    scene_name: str,
    blank_lines_between_entries: int,
) -> bool:
    if not file_path.exists() or file_path.stat().st_size == 0:
        _append_txt(file_path, saved_text, blank_lines_between_entries)
        return False

    content = file_path.read_text(encoding="utf-8", errors="ignore")
    parts = re.split(r"(\r?\n(?:[ \t]*\r?\n)+)", content)
    entry_indexes = [i for i in range(0, len(parts), 2) if parts[i].strip()]

    replace_part_index = None
    for part_index in entry_indexes:
        if _entry_matches_scene(parts[part_index], scene_name):
            replace_part_index = part_index
            break

    scene_number = _scene_number(scene_name)
    if replace_part_index is None and scene_number is not None and 1 <= scene_number <= len(entry_indexes):
        replace_part_index = entry_indexes[scene_number - 1]

    if replace_part_index is None:
        _append_txt(file_path, saved_text, blank_lines_between_entries)
        return False

    parts[replace_part_index] = saved_text.rstrip("\r\n")
    tmp_path = file_path.with_name(f"{file_path.name}.tmp")
    tmp_path.write_text("".join(parts), encoding="utf-8", newline="\n")
    os.replace(tmp_path, file_path)
    return True


class AntimatterTextFileAppender:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "directory": ("STRING", {"multiline": False, "default": _default_output_dir()}),
                "filename": ("STRING", {"multiline": False, "default": "saved_text"}),
                "file_format": (["txt", "json"], {"default": "txt"}),
                "prefix": ("STRING", {"multiline": False, "default": ""}),
                "blank_lines_between_entries": (
                    "INT",
                    {"default": 1, "min": 0, "max": 20, "step": 1},
                ),
                "index_start": ("INT", {"default": 1, "min": 0, "max": 10**9, "step": 1}),
                "index_padding": ("INT", {"default": 0, "min": 0, "max": 12, "step": 1}),
                "json_indent": ("INT", {"default": 2, "min": 0, "max": 8, "step": 1}),
            },
            "optional": {
                "text_input": ("STRING", {"forceInput": True}),
                "scene_name": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("saved_text", "file_path")
    FUNCTION = "save"
    CATEGORY = "AntiMatter/Text"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def save(
        self,
        text,
        directory,
        filename,
        file_format,
        prefix,
        blank_lines_between_entries,
        index_start,
        index_padding,
        json_indent,
        text_input=None,
        scene_name=None,
    ):
        file_path = _resolve_path(directory, filename, file_format)
        raw_text = _as_text(text_input if text_input is not None else text)
        scene_name_text = _as_text(scene_name).strip()

        with _FILE_LOCK:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            scene_index = _scene_number(scene_name_text) if scene_name_text else None

            if scene_index is not None:
                index = scene_index
            elif file_format == "json":
                index = _next_json_index(file_path, int(index_start))
            else:
                index = _next_text_index(file_path, prefix, int(index_start))

            rendered_prefix = _format_prefix(prefix, index, int(index_padding))
            saved_text = f"{rendered_prefix}{raw_text}"

            if file_format == "json":
                record = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "index": index,
                    "prefix": rendered_prefix,
                    "text": raw_text,
                    "saved_text": saved_text,
                }
                if scene_name_text:
                    record["scene_name"] = _normalize_scene_name(scene_name_text)
                    _upsert_json_by_scene(file_path, record, scene_name_text, int(json_indent))
                else:
                    _append_json(file_path, record, int(json_indent))
            else:
                if scene_name_text:
                    _replace_txt_by_scene(file_path, saved_text, scene_name_text, int(blank_lines_between_entries))
                else:
                    _append_txt(file_path, saved_text, int(blank_lines_between_entries))

        return (saved_text, str(file_path))


NODE_CLASS_MAPPINGS = {
    "Antimatter_TextFileAppender": AntimatterTextFileAppender,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Antimatter_TextFileAppender": "Antimatter Text File Appender",
}
