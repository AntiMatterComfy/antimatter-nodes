import hashlib
import json
import os
import random
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import folder_paths
import numpy as np
import torch
from PIL import Image, ImageOps

try:
    from aiohttp import web
    from server import PromptServer
except Exception:
    web = None
    PromptServer = None

_STATE: Dict[str, Dict[str, Any]] = {}
_JSON_STATE: Dict[str, Dict[str, Any]] = {}
_JSON_IMAGE_STATE: Dict[str, Dict[str, Any]] = {}
_NONE_FILE = "none"
_STYLE_SLOT_COUNT = 10
_COMMENT_PREFIXES = ("#", "//")
_JSON_PROMPT_KEYS = ("prompt", "image_prompt", "positive", "text", "description")
_JSON_SCENE_ID_KEYS = ("scene", "scene_id", "id", "name", "title", "row", "row_id", "row_number", "index")
_JSON_SCENE_LIST_KEYS = ("scenes", "scene_prompts", "items", "data")
_JSON_FILE_EXTS = (".json",)
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")
_SCENE_RE = re.compile(r"(?:^|[^0-9a-z])scene[\s_-]*(\d+)(?=$|[^0-9])", re.IGNORECASE)
_DIGIT_RE = re.compile(r"(\d+)")

_MODE_MAP = {
    "sequential": "sequential",
    "random": "random",
    "from_end": "from_end",
    "from end": "from_end",
    "fromend": "from_end",
}

_JSON_SCENE_MODE_MAP = {
    "sequential": "sequential",
    "manual": "manual",
    "row": "row",
}

_JSON_IMAGE_SCENE_MODE_MAP = {
    **_JSON_SCENE_MODE_MAP,
    "interval": "interval",
}

_JSON_AFTER_LAST_MAP = {
    "stop_empty": "stop_empty",
    "loop": "loop",
}


class AnyType(str):
    """ComfyUI socket type that can receive STRING, JSON, or dict/list payloads."""

    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")


def _custom_nodes_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _default_styles_root() -> str:
    custom_nodes = _custom_nodes_dir()
    preferred = os.path.join(custom_nodes, "Style_evo", "styles")
    if os.path.isdir(preferred):
        return preferred
    return os.path.join(custom_nodes, "styles")


def _style_root(root_path: str = "") -> str:
    root = str(root_path or "").strip().strip('"').strip("'")
    if not root:
        return os.path.abspath(_default_styles_root())
    if os.path.isabs(root):
        return os.path.abspath(root)
    return os.path.abspath(os.path.join(folder_paths.base_path, root))


def _style_root_for_display(root_path: str = "") -> str:
    return _display_path(_style_root(root_path))


def _display_path(path: str) -> str:
    try:
        rel = os.path.relpath(path, folder_paths.base_path)
    except ValueError:
        rel = path
    return rel.replace(os.sep, "/")


def _available_txt_files(root_path: str = "") -> List[str]:
    files: List[str] = []
    seen = set()
    root = _style_root(root_path)
    if not os.path.isdir(root):
        return [_NONE_FILE]

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.lower().endswith(".txt"):
                continue
            path = os.path.abspath(os.path.join(dirpath, filename))
            key = os.path.normcase(path)
            if key in seen:
                continue
            seen.add(key)
            files.append(_display_path(path))
    files.sort(key=str.lower)
    return [_NONE_FILE] + files


if PromptServer is not None and web is not None:
    @PromptServer.instance.routes.get("/lineprompt_masterload/styles")
    async def get_lineprompt_styles(request):
        root_path = request.rel_url.query.get("root", "")
        return web.json_response(
            {
                "root": _style_root_for_display(root_path),
                "files": _available_txt_files(root_path),
            }
        )


def _clamp_int(value: Any, lo: int, hi: int) -> int:
    try:
        v = int(value)
    except Exception:
        v = lo
    return max(lo, min(hi, v))


def _parse_lines(text: str) -> List[str]:
    if not text:
        return []

    out: List[str] = []
    for raw in str(text).splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith(_COMMENT_PREFIXES):
            continue
        out.append(s)
    return out


def _normalize_txt_path(path: str) -> str:
    if not path:
        return ""
    p = str(path).strip().strip('"').strip("'")
    if not p or p == _NONE_FILE:
        return ""
    if os.path.isabs(p):
        return p
    return os.path.join(folder_paths.base_path, p)


def _read_text_from_file(path: str) -> Tuple[str, Optional[str]]:
    p = _normalize_txt_path(path)
    if not p:
        return "", "no_file_path"
    if not os.path.exists(p):
        return "", f"file_not_found: {p}"

    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        return "", f"read_error: {type(e).__name__}"

    return text, None


def _source_key_from_text(text: str) -> str:
    b = str(text).encode("utf-8", errors="ignore")
    return "text:" + hashlib.sha256(b).hexdigest()


def _source_key_from_file(path: str) -> str:
    p = _normalize_txt_path(path)
    if not p:
        return "file:missing_path"
    try:
        st = os.stat(p)
        return f"file:{os.path.abspath(p)}:{int(st.st_mtime)}:{st.st_size}"
    except Exception:
        return f"file:missing:{os.path.abspath(p)}"


def _resolve_json_file_path(path: str) -> Tuple[str, Optional[str]]:
    p = _normalize_txt_path(path)
    if not p:
        return "", "no_file_path"
    if not os.path.exists(p):
        return p, None
    if not os.path.isdir(p):
        return p, None

    try:
        json_files = [
            os.path.join(p, filename)
            for filename in os.listdir(p)
            if os.path.splitext(filename)[1].lower() in _JSON_FILE_EXTS
            and os.path.isfile(os.path.join(p, filename))
        ]
    except Exception as e:
        return p, f"read_error: {type(e).__name__}"

    json_files.sort(key=lambda item: item.lower())
    if not json_files:
        return p, f"no_json_files_in_folder: {p}"
    if len(json_files) > 1:
        names = ", ".join(os.path.basename(item) for item in json_files[:5])
        if len(json_files) > 5:
            names += ", ..."
        return p, f"multiple_json_files_in_folder: {p} ({names})"
    return json_files[0], None


def _stable_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return repr(value)


def _source_key_from_json_value(value: Any) -> str:
    b = _stable_json_text(value).encode("utf-8", errors="ignore")
    return "json:" + hashlib.sha256(b).hexdigest()


def _has_json_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _parse_json_value(value: Any) -> Tuple[Any, Optional[str]]:
    if isinstance(value, tuple) and len(value) == 1:
        value = value[0]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None, "empty_json"
        try:
            return json.loads(text), None
        except Exception as e:
            return None, f"json_parse_error: {type(e).__name__}"
    return value, None


def _prompt_from_dict(data: Dict[str, Any]) -> Optional[str]:
    for key in _JSON_PROMPT_KEYS:
        if key in data and data[key] is not None:
            prompt = str(data[key]).strip()
            if prompt:
                return prompt
    return None


def _scene_id_from_dict(data: Dict[str, Any], fallback: str) -> str:
    for key in _JSON_SCENE_ID_KEYS:
        if key in data and data[key] is not None:
            scene_id = str(data[key]).strip()
            if scene_id:
                return scene_id
    return fallback


def _append_scene(scenes: List[Tuple[str, str]], scene_id: Any, prompt: Any) -> None:
    prompt_s = str(prompt or "").strip()
    if not prompt_s:
        return
    scene_id_s = str(scene_id or "").strip() or f"scene-{len(scenes) + 1:03d}"
    scenes.append((scene_id_s, prompt_s))


def _scene_from_json_row(row: Any) -> Optional[Tuple[Any, str]]:
    if not isinstance(row, (list, tuple)) or len(row) < 2:
        return None

    scene_id = row[0]
    prompt_value = row[1]
    if isinstance(prompt_value, dict):
        prompt = _prompt_from_dict(prompt_value)
    elif isinstance(prompt_value, (list, tuple)):
        prompt = None
    else:
        prompt = str(prompt_value).strip()

    if not prompt:
        return None
    return scene_id, prompt


def _extract_scenes_from_json(data: Any) -> List[Tuple[str, str]]:
    scenes: List[Tuple[str, str]] = []

    if isinstance(data, dict):
        direct_prompt = _prompt_from_dict(data)
        if direct_prompt:
            _append_scene(scenes, _scene_id_from_dict(data, f"scene-{len(scenes) + 1:03d}"), direct_prompt)
            return scenes

        for key in _JSON_SCENE_LIST_KEYS:
            value = data.get(key)
            if isinstance(value, (list, tuple, dict)):
                nested = _extract_scenes_from_json(value)
                if nested:
                    return nested

        if data and all(not isinstance(v, (list, tuple, dict)) for v in data.values()):
            for key, value in data.items():
                _append_scene(scenes, key, value)
            return scenes

        for key, value in data.items():
            if isinstance(value, dict):
                nested = _extract_scenes_from_json(value)
                for scene_id, prompt in nested:
                    if scene_id.startswith("scene-") and scene_id[6:].isdigit():
                        scene_id = str(key)
                    _append_scene(scenes, scene_id, prompt)
            elif isinstance(value, (list, tuple)) and str(key).lower() in _JSON_SCENE_LIST_KEYS:
                scenes.extend(_extract_scenes_from_json(value))
        return scenes

    if isinstance(data, (list, tuple)):
        for item in data:
            if isinstance(item, dict):
                scenes.extend(_extract_scenes_from_json(item))
            elif isinstance(item, (list, tuple)):
                row_scene = _scene_from_json_row(item)
                if row_scene is None:
                    scenes.extend(_extract_scenes_from_json(item))
                    continue
                scene_id, prompt = row_scene
                _append_scene(scenes, scene_id, prompt)
            elif isinstance(item, str):
                _append_scene(scenes, f"scene-{len(scenes) + 1:03d}", item)
        return scenes

    if isinstance(data, str):
        _append_scene(scenes, f"scene-{len(scenes) + 1:03d}", data)
    return scenes


def _resolve_json_source(json_input: Any, json_file: str, json_text: str) -> Tuple[List[Tuple[str, str]], str, Optional[str]]:
    if _has_json_value(json_input):
        data, error = _parse_json_value(json_input)
        if error:
            return [], _source_key_from_json_value(json_input), error
        return _extract_scenes_from_json(data), _source_key_from_json_value(data), None

    file_path = str(json_file or "").strip().strip('"').strip("'")
    if file_path:
        resolved_file_path, path_error = _resolve_json_file_path(file_path)
        if path_error:
            return [], _source_key_from_file(resolved_file_path or file_path), path_error
        text, error = _read_text_from_file(resolved_file_path)
        if error:
            return [], _source_key_from_file(resolved_file_path), error
        data, parse_error = _parse_json_value(text)
        if parse_error:
            return [], _source_key_from_file(resolved_file_path), parse_error
        return _extract_scenes_from_json(data), _source_key_from_file(resolved_file_path), None

    data, error = _parse_json_value(json_text)
    if error:
        return [], _source_key_from_json_value(json_text), error
    return _extract_scenes_from_json(data), _source_key_from_json_value(data), None


def _normalize_unique_id(unique_id: Optional[str]) -> str:
    if isinstance(unique_id, (list, tuple)) and unique_id:
        return str(unique_id[0])
    if unique_id is None:
        return "LinePrompt_MasterLoad"
    return str(unique_id)


def _resolve_source(text_file: str, style_file: str) -> Tuple[List[str], str, Optional[str]]:
    selected_file = style_file if style_file and style_file != _NONE_FILE else text_file
    text, error = _read_text_from_file(selected_file)
    return _parse_lines(text), _source_key_from_file(selected_file), error


def _initial_index(mode_key: str, line_count: int) -> int:
    if mode_key == "from_end":
        return line_count - 1
    if mode_key == "random":
        return random.randrange(line_count)
    return 0


def _next_index(mode_key: str, current_index: int, line_count: int) -> int:
    if mode_key == "random":
        if line_count == 1:
            return 0
        next_index = current_index
        for _ in range(20):
            next_index = random.randrange(line_count)
            if next_index != current_index:
                break
        return next_index
    if mode_key == "from_end":
        return (current_index - 1) % line_count
    return (current_index + 1) % line_count


def _make_output(
    lines: List[str],
    start_index: int,
    count: int,
    mode_key: str,
    delimiter: str,
    append_delimiter: bool = True,
) -> str:
    direction = -1 if mode_key == "from_end" else 1
    take = min(count, len(lines))
    chosen_lines = [lines[(start_index + direction * i) % len(lines)] for i in range(take)]
    out_text = " ".join(chosen_lines).strip()

    delimiter_s = str(delimiter or "")
    if append_delimiter and out_text and delimiter_s and not out_text.endswith(delimiter_s):
        out_text += delimiter_s
    return out_text


def _join_prefix(prefix: str, selected_text: str) -> str:
    p = str(prefix or "").strip()
    s = str(selected_text or "").strip()
    if not p:
        return s
    if not s:
        return p
    return f"{p.rstrip(',')}, {s}"


def _style_file_input_name(slot: int) -> str:
    return "style_file" if slot == 1 else f"style_file_{slot}"


def _style_enabled_input_name(slot: int) -> str:
    return f"style_{slot}_enabled"


def _style_inputs() -> Dict[str, Any]:
    files = _available_txt_files()
    inputs: Dict[str, Any] = {}
    for slot in range(1, _STYLE_SLOT_COUNT + 1):
        inputs[_style_enabled_input_name(slot)] = ("BOOLEAN", {"default": slot == 1})
        inputs[_style_file_input_name(slot)] = (files, {"default": _NONE_FILE})
    return inputs


def _combined_return_names() -> Tuple[str, ...]:
    return ("text",) + tuple(f"style_{slot}_text" for slot in range(1, _STYLE_SLOT_COUNT + 1))


def _empty_masterload_result() -> Tuple[str, ...]:
    return tuple("" for _ in _combined_return_names())


def _resolve_image_folder(path: str) -> str:
    folder = str(path or "").strip().strip('"').strip("'")
    if not folder:
        return ""
    if os.path.isabs(folder):
        return os.path.abspath(folder)
    return os.path.abspath(os.path.join(os.getcwd(), folder))


def _scan_image_files(folder: str, recursive: bool) -> List[str]:
    folder_abs = _resolve_image_folder(folder)
    if not folder_abs or not os.path.isdir(folder_abs):
        return []

    files: List[str] = []
    if recursive:
        for dirpath, _, filenames in os.walk(folder_abs):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if os.path.splitext(filename)[1].lower() in _IMAGE_EXTS and os.path.isfile(path):
                    files.append(path)
    else:
        for filename in os.listdir(folder_abs):
            path = os.path.join(folder_abs, filename)
            if os.path.splitext(filename)[1].lower() in _IMAGE_EXTS and os.path.isfile(path):
                files.append(path)

    files.sort(key=lambda p: p.lower())
    return files


def _source_key_from_image_files(folder: str, recursive: bool, files: List[str]) -> str:
    folder_abs = _resolve_image_folder(folder)
    parts = [folder_abs, str(bool(recursive))]
    for path in files:
        try:
            st = os.stat(path)
            parts.append(f"{os.path.abspath(path)}:{int(st.st_mtime)}:{st.st_size}")
        except Exception:
            parts.append(f"missing:{os.path.abspath(path)}")
    data = "\n".join(parts).encode("utf-8", errors="ignore")
    return "images:" + hashlib.sha256(data).hexdigest()


def _scene_number_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    match = _SCENE_RE.search(text)
    if match is None:
        match = _DIGIT_RE.search(text)
    if match is None:
        return ""

    digits = match.group(1)
    try:
        return str(int(digits))
    except Exception:
        return digits.lstrip("0") or "0"


def _scene_number_or_row(scene_id: Any, row_index: int) -> int:
    number_key = _scene_number_key(scene_id)
    if number_key:
        try:
            return int(number_key)
        except Exception:
            pass
    return row_index + 1


def _filter_scenes_by_interval(
    scenes: List[Tuple[str, str]],
    from_scene: int,
    to_scene: int,
) -> Tuple[List[Tuple[str, str]], int, int]:
    start = _clamp_int(from_scene, 1, 100000)
    end = _clamp_int(to_scene, 1, 100000)
    if end < start:
        start, end = end, start

    filtered = [
        (scene_id, prompt)
        for row_index, (scene_id, prompt) in enumerate(scenes)
        if start <= _scene_number_or_row(scene_id, row_index) <= end
    ]
    return filtered, start, end


def _scene_exact_key(value: Any) -> str:
    text = os.path.splitext(os.path.basename(str(value or "").strip()))[0]
    return re.sub(r"[^0-9a-z]+", "", text.lower())


def _build_scene_image_index(files: List[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    exact: Dict[str, str] = {}
    by_number: Dict[str, str] = {}
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        exact_key = _scene_exact_key(stem)
        if exact_key:
            exact.setdefault(exact_key, path)

        number_key = _scene_number_key(stem)
        if number_key:
            by_number.setdefault(number_key, path)

    return exact, by_number


def _find_image_for_scene(scene_id: Any, exact: Dict[str, str], by_number: Dict[str, str]) -> Optional[str]:
    exact_key = _scene_exact_key(scene_id)
    if exact_key and exact_key in exact:
        return exact[exact_key]

    number_key = _scene_number_key(scene_id)
    if number_key and number_key in by_number:
        return by_number[number_key]

    return None


def _blank_image_tensor() -> torch.Tensor:
    return torch.zeros((1, 1, 1, 3), dtype=torch.float32)


def _load_image_tensor(path: str) -> Tuple[torch.Tensor, Image.Image, int, int]:
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")

        preview = img.copy()
        arr = np.asarray(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0)
        width, height = img.size
    return tensor, preview, int(width), int(height)


def _save_preview_image(img: Image.Image) -> Dict[str, Any]:
    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)

    name = f"lineprompt_scene_{uuid.uuid4().hex[:12]}.png"
    path = os.path.join(temp_dir, name)
    img.save(path, "PNG")
    return {
        "images": [{
            "filename": name,
            "subfolder": "",
            "type": "temp",
        }]
    }


def _json_image_empty_result(preview: str = "", status: str = "") -> Dict[str, Any]:
    return {
        "ui": {"preview": (preview,), "status": (status,)},
        "result": ("", "", _blank_image_tensor(), "", "", 1, 1),
    }


def _json_image_scene_result(
    prompt: str,
    scene_id: str,
    image_path: str,
    status: str,
    show_preview: bool,
) -> Dict[str, Any]:
    tensor, preview_img, width, height = _load_image_tensor(image_path)
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    ui: Dict[str, Any] = {"preview": (prompt,), "status": (status,)}
    if show_preview:
        ui.update(_save_preview_image(preview_img))

    return {
        "ui": ui,
        "result": (prompt, scene_id, tensor, image_name, os.path.abspath(image_path), width, height),
    }


class LinePrompt_MasterLoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
                "input_text": ("STRING", {"default": "", "multiline": True}),
                "text_file": ("STRING", {"default": ""}),
                **_style_inputs(),
                "lines_to_take": ("INT", {"default": 1, "min": 1, "max": 3, "step": 1}),
                "read_mode": (["sequential", "random", "from_end"], {"default": "sequential"}),
                "freeze_iterations": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "delimiter": ([",", "/", ".", ";"], {"default": ","}),
                "nav": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING",) * len(_combined_return_names())
    RETURN_NAMES = _combined_return_names()
    FUNCTION = "load"
    CATEGORY = "AntiMatter/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force execution every prompt so sequential/random modes work even when
        # widget values stay the same (ComfyUI caching).
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        read_mode = str(kwargs.get("read_mode", "sequential")).strip().lower()
        if read_mode not in _MODE_MAP:
            return f"Invalid read_mode: {kwargs.get('read_mode')}"

        delimiter = str(kwargs.get("delimiter", ","))
        if delimiter not in [",", "/", ".", ";"]:
            return f"Invalid delimiter: {delimiter}"

        _clamp_int(kwargs.get("lines_to_take", 1), 1, 3)
        _clamp_int(kwargs.get("freeze_iterations", 0), 0, 100000)
        _clamp_int(kwargs.get("nav", 0), -2147483648, 2147483647)
        return True

    def load(
        self,
        enabled: bool = True,
        input_text: str = "",
        text_file: str = "",
        style_1_enabled: bool = True,
        style_file: str = _NONE_FILE,
        style_2_enabled: bool = False,
        style_file_2: str = _NONE_FILE,
        style_3_enabled: bool = False,
        style_file_3: str = _NONE_FILE,
        style_4_enabled: bool = False,
        style_file_4: str = _NONE_FILE,
        style_5_enabled: bool = False,
        style_file_5: str = _NONE_FILE,
        style_6_enabled: bool = False,
        style_file_6: str = _NONE_FILE,
        style_7_enabled: bool = False,
        style_file_7: str = _NONE_FILE,
        style_8_enabled: bool = False,
        style_file_8: str = _NONE_FILE,
        style_9_enabled: bool = False,
        style_file_9: str = _NONE_FILE,
        style_10_enabled: bool = False,
        style_file_10: str = _NONE_FILE,
        lines_to_take: int = 1,
        read_mode: str = "sequential",
        freeze_iterations: int = 0,
        delimiter: str = ",",
        nav: int = 0,
        unique_id: Optional[str] = None,
    ):
        if not enabled:
            return {"ui": {"preview": ("",), "status": ("OFF",)}, "result": _empty_masterload_result()}

        uid = _normalize_unique_id(unique_id)
        mode_key = _MODE_MAP.get(str(read_mode).strip().lower(), "sequential")
        lines_to_take_i = _clamp_int(lines_to_take, 1, 3)
        freeze_i = _clamp_int(freeze_iterations, 0, 100000)

        style_enabled = {
            1: style_1_enabled,
            2: style_2_enabled,
            3: style_3_enabled,
            4: style_4_enabled,
            5: style_5_enabled,
            6: style_6_enabled,
            7: style_7_enabled,
            8: style_8_enabled,
            9: style_9_enabled,
            10: style_10_enabled,
        }
        style_files = {
            1: style_file,
            2: style_file_2,
            3: style_file_3,
            4: style_file_4,
            5: style_file_5,
            6: style_file_6,
            7: style_file_7,
            8: style_file_8,
            9: style_file_9,
            10: style_file_10,
        }

        state = _STATE.get(uid)
        if not isinstance(state, dict) or not isinstance(state.get("slots"), dict):
            state = {"slots": {}}
            _STATE[uid] = state

        try:
            nav_i = int(nav)
        except Exception:
            nav_i = int(state.get("nav", 0))
        nav_prev = int(state.get("nav", nav_i))
        nav_diff = nav_i - nav_prev
        state["nav"] = nav_i

        slots_state: Dict[str, Dict[str, Any]] = state["slots"]
        style_outputs: List[str] = []
        combined_parts: List[str] = []
        status_parts: List[str] = []

        for slot in range(1, _STYLE_SLOT_COUNT + 1):
            if not bool(style_enabled[slot]):
                style_outputs.append("")
                continue

            current_text_file = text_file if slot == 1 else ""
            lines, source_key, source_error = _resolve_source(current_text_file, style_files[slot])

            if not lines:
                style_outputs.append("")
                if source_error:
                    status_parts.append(f"{slot}:{source_error}")
                continue

            slot_key = str(slot)
            slot_state = slots_state.get(slot_key)
            source_changed = slot_state is None or slot_state.get("source_key") != source_key

            if source_changed:
                slot_state = {
                    "idx": _initial_index(mode_key, len(lines)),
                    "hold": max(freeze_i, 1),
                    "source_key": source_key,
                }
                slots_state[slot_key] = slot_state

            idx = int(slot_state.get("idx", 0)) % len(lines)
            slot_state["idx"] = idx

            if nav_diff != 0:
                idx = (idx + nav_diff) % len(lines)
                slot_state["idx"] = idx
                slot_state["hold"] = max(freeze_i, 1)
            elif int(slot_state.get("hold", 0)) <= 0:
                idx = _next_index(mode_key, idx, len(lines))
                slot_state["idx"] = idx
                slot_state["hold"] = max(freeze_i, 1)

            selected_text = _make_output(
                lines,
                idx,
                lines_to_take_i,
                mode_key,
                delimiter,
                append_delimiter=False,
            )
            style_outputs.append(selected_text)
            if selected_text.strip():
                combined_parts.append(selected_text.strip().rstrip(",").strip())

            # Decrement hold AFTER using the current selection.
            slot_state["hold"] = int(slot_state.get("hold", 1)) - 1
            status_parts.append(f"{slot}:{idx + 1}/{len(lines)}")

        combined_text = _join_prefix(input_text, ", ".join(part for part in combined_parts if part))
        status = "; ".join(status_parts)
        if not status:
            status = "text_only" if str(input_text or "").strip() else "no_enabled_styles"
        preview = combined_text or status
        return {
            "ui": {"preview": (preview,), "status": (status,)},
            "result": (combined_text, *style_outputs),
        }


class LinePrompt_MasterLoad_JSON:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
                "json_text": ("STRING", {"default": "", "multiline": True}),
                "json_file": ("STRING", {"default": ""}),
                "scene_mode": (["sequential", "manual", "row"], {"default": "sequential"}),
                "manual_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "repeat_each_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "after_last_scene": (["stop_empty", "loop"], {"default": "stop_empty"}),
                "nav": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
                "row": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
            },
            "optional": {
                "json_input": (any_type,),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "Scene Name")
    FUNCTION = "load"
    CATEGORY = "AntiMatter/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        scene_mode = str(kwargs.get("scene_mode", "sequential")).strip().lower()
        if scene_mode not in _JSON_SCENE_MODE_MAP:
            return f"Invalid scene_mode: {kwargs.get('scene_mode')}"

        after_last_scene = str(kwargs.get("after_last_scene", "stop_empty")).strip().lower()
        if after_last_scene not in _JSON_AFTER_LAST_MAP:
            return f"Invalid after_last_scene: {kwargs.get('after_last_scene')}"

        _clamp_int(kwargs.get("manual_scene", 1), 1, 100000)
        _clamp_int(kwargs.get("repeat_each_scene", 1), 1, 100000)
        _clamp_int(kwargs.get("nav", 0), -2147483648, 2147483647)
        _clamp_int(kwargs.get("row", 1), 1, 100000)
        return True

    def load(
        self,
        enabled: bool,
        json_text: str,
        json_file: str,
        scene_mode: str,
        manual_scene: int,
        repeat_each_scene: int,
        after_last_scene: str,
        nav: int,
        row: int = 1,
        unique_id: Optional[str] = None,
        json_input: Any = None,
    ):
        if not enabled:
            return {"ui": {"preview": ("",), "status": ("OFF",)}, "result": ("", "")}

        scenes, source_key, source_error = _resolve_json_source(json_input, json_file, json_text)
        if not scenes:
            msg = f"[LinePrompt_MasterLoad_JSON] {source_error or 'no_scene_prompts'}"
            return {"ui": {"preview": (msg,), "status": (msg,)}, "result": ("", "")}

        uid = "LinePrompt_MasterLoad_JSON:" + _normalize_unique_id(unique_id)
        scene_mode_key = _JSON_SCENE_MODE_MAP.get(str(scene_mode).strip().lower(), "sequential")
        after_last_key = _JSON_AFTER_LAST_MAP.get(str(after_last_scene).strip().lower(), "stop_empty")
        repeat_i = _clamp_int(repeat_each_scene, 1, 100000)

        if scene_mode_key == "manual":
            idx = _clamp_int(manual_scene, 1, len(scenes)) - 1
            scene_id, prompt = scenes[idx]
            status = f"{scene_id} {idx + 1}/{len(scenes)} MANUAL"
            return {"ui": {"preview": (prompt,), "status": (status,)}, "result": (prompt, scene_id)}

        if scene_mode_key == "row":
            idx = _clamp_int(row, 1, len(scenes)) - 1
            scene_id, prompt = scenes[idx]
            status = f"{scene_id} row {idx + 1}/{len(scenes)}"
            return {"ui": {"preview": (prompt,), "status": (status,)}, "result": (prompt, scene_id)}

        state = _JSON_STATE.get(uid)
        source_changed = state is None or state.get("source_key") != source_key
        if source_changed:
            state = {
                "idx": 0,
                "hold": repeat_i,
                "nav": int(nav),
                "done": False,
                "source_key": source_key,
            }
            _JSON_STATE[uid] = state

        idx = int(state.get("idx", 0)) % len(scenes)
        state["idx"] = idx

        try:
            nav_i = int(nav)
        except Exception:
            nav_i = int(state.get("nav", 0))
        nav_prev = int(state.get("nav", nav_i))
        nav_diff = nav_i - nav_prev
        state["nav"] = nav_i

        if nav_diff != 0:
            idx = (idx + nav_diff) % len(scenes)
            state["idx"] = idx
            state["hold"] = repeat_i
            state["done"] = False

        if bool(state.get("done", False)):
            status = f"DONE {len(scenes)}/{len(scenes)}"
            return {"ui": {"preview": ("",), "status": (status,)}, "result": ("", "")}

        scene_id, prompt = scenes[idx]

        state["hold"] = int(state.get("hold", repeat_i)) - 1
        if int(state.get("hold", 0)) <= 0:
            if idx >= len(scenes) - 1:
                if after_last_key == "loop":
                    state["idx"] = 0
                    state["hold"] = repeat_i
                    state["done"] = False
                else:
                    state["done"] = True
                    state["hold"] = 0
            else:
                state["idx"] = idx + 1
                state["hold"] = repeat_i
                state["done"] = False

        status = f"{scene_id} {idx + 1}/{len(scenes)}"
        if after_last_key == "stop_empty" and idx >= len(scenes) - 1:
            status += " END"
        return {"ui": {"preview": (prompt,), "status": (status,)}, "result": (prompt, scene_id)}


class LinePrompt_MasterLoad_JSON_Image:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
                "json_text": ("STRING", {"default": "", "multiline": True}),
                "json_file": ("STRING", {"default": ""}),
                "image_folder": ("STRING", {"default": ".uploading"}),
                "recursive": ("BOOLEAN", {"default": False}),
                "scene_mode": (["sequential", "manual", "row", "interval"], {"default": "sequential"}),
                "manual_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "interval_from_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "interval_to_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "repeat_each_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "after_last_scene": (["stop_empty", "loop"], {"default": "stop_empty"}),
                "nav": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
                "row": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "show_preview": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "json_input": (any_type,),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING", "STRING", "IMAGE", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("prompt", "Scene Name", "image", "image_filename", "image_path", "width", "height")
    FUNCTION = "load"
    CATEGORY = "AntiMatter/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        scene_mode = str(kwargs.get("scene_mode", "sequential")).strip().lower()
        if scene_mode not in _JSON_IMAGE_SCENE_MODE_MAP:
            return f"Invalid scene_mode: {kwargs.get('scene_mode')}"

        after_last_scene = str(kwargs.get("after_last_scene", "stop_empty")).strip().lower()
        if after_last_scene not in _JSON_AFTER_LAST_MAP:
            return f"Invalid after_last_scene: {kwargs.get('after_last_scene')}"

        _clamp_int(kwargs.get("manual_scene", 1), 1, 100000)
        _clamp_int(kwargs.get("interval_from_scene", 1), 1, 100000)
        _clamp_int(kwargs.get("interval_to_scene", 1), 1, 100000)
        _clamp_int(kwargs.get("repeat_each_scene", 1), 1, 100000)
        _clamp_int(kwargs.get("nav", 0), -2147483648, 2147483647)
        _clamp_int(kwargs.get("row", 1), 1, 100000)
        return True

    def _load_scene_image(
        self,
        scene_id: str,
        prompt: str,
        idx: int,
        scene_count: int,
        image_folder: str,
        recursive: bool,
        show_preview: bool,
        status_suffix: str = "",
    ) -> Dict[str, Any]:
        image_files = _scan_image_files(image_folder, recursive)
        folder_abs = _resolve_image_folder(image_folder)
        if not image_files:
            raise ValueError(f"No images found in folder: {folder_abs or image_folder}")

        exact, by_number = _build_scene_image_index(image_files)
        image_path = _find_image_for_scene(scene_id, exact, by_number)
        if image_path is None:
            scene_number = _scene_number_key(scene_id) or str(scene_id)
            raise ValueError(
                f"No image found for scene {scene_id} (number {scene_number}) "
                f"in folder: {folder_abs or image_folder}"
            )

        image_name = os.path.splitext(os.path.basename(image_path))[0]
        status = f"{scene_id} {idx + 1}/{scene_count} -> {image_name}"
        if status_suffix:
            status += f" {status_suffix}"
        return _json_image_scene_result(prompt, scene_id, image_path, status, show_preview)

    def load(
        self,
        enabled: bool,
        json_text: str,
        json_file: str,
        image_folder: str,
        recursive: bool,
        scene_mode: str,
        manual_scene: int,
        interval_from_scene: int,
        interval_to_scene: int,
        repeat_each_scene: int,
        after_last_scene: str,
        nav: int,
        row: int = 1,
        show_preview: bool = True,
        unique_id: Optional[str] = None,
        json_input: Any = None,
    ):
        if not enabled:
            return _json_image_empty_result("", "OFF")

        scenes, json_source_key, source_error = _resolve_json_source(json_input, json_file, json_text)
        if not scenes:
            msg = f"[LinePrompt_MasterLoad_JSON_Image] {source_error or 'no_scene_prompts'}"
            return _json_image_empty_result(msg, msg)

        image_files = _scan_image_files(image_folder, recursive)
        if not image_files:
            folder_abs = _resolve_image_folder(image_folder)
            raise ValueError(f"No images found in folder: {folder_abs or image_folder}")

        image_source_key = _source_key_from_image_files(image_folder, recursive, image_files)

        uid = "LinePrompt_MasterLoad_JSON_Image:" + _normalize_unique_id(unique_id)
        scene_mode_key = _JSON_IMAGE_SCENE_MODE_MAP.get(str(scene_mode).strip().lower(), "sequential")
        after_last_key = _JSON_AFTER_LAST_MAP.get(str(after_last_scene).strip().lower(), "stop_empty")
        repeat_i = _clamp_int(repeat_each_scene, 1, 100000)
        interval_from_i = _clamp_int(interval_from_scene, 1, 100000)
        interval_to_i = _clamp_int(interval_to_scene, 1, 100000)

        if scene_mode_key == "manual":
            idx = _clamp_int(manual_scene, 1, len(scenes)) - 1
            scene_id, prompt = scenes[idx]
            return self._load_scene_image(
                scene_id,
                prompt,
                idx,
                len(scenes),
                image_folder,
                recursive,
                show_preview,
                "MANUAL",
            )

        if scene_mode_key == "row":
            idx = _clamp_int(row, 1, len(scenes)) - 1
            scene_id, prompt = scenes[idx]
            return self._load_scene_image(
                scene_id,
                prompt,
                idx,
                len(scenes),
                image_folder,
                recursive,
                show_preview,
                "ROW",
            )

        interval_suffix = ""
        if scene_mode_key == "interval":
            scenes, interval_from_i, interval_to_i = _filter_scenes_by_interval(
                scenes,
                interval_from_i,
                interval_to_i,
            )
            if not scenes:
                msg = (
                    "[LinePrompt_MasterLoad_JSON_Image] "
                    f"no_scene_prompts_in_interval: {interval_from_i}-{interval_to_i}"
                )
                return _json_image_empty_result(msg, msg)
            interval_suffix = f"RANGE {interval_from_i}-{interval_to_i}"

        combined_source_key = (
            f"{json_source_key}|{image_source_key}|{scene_mode_key}:"
            f"{interval_from_i}:{interval_to_i}"
        )

        state = _JSON_IMAGE_STATE.get(uid)
        source_changed = state is None or state.get("source_key") != combined_source_key
        if source_changed:
            state = {
                "idx": 0,
                "hold": repeat_i,
                "nav": int(nav),
                "done": False,
                "source_key": combined_source_key,
            }
            _JSON_IMAGE_STATE[uid] = state

        idx = int(state.get("idx", 0)) % len(scenes)
        state["idx"] = idx

        try:
            nav_i = int(nav)
        except Exception:
            nav_i = int(state.get("nav", 0))
        nav_prev = int(state.get("nav", nav_i))
        nav_diff = nav_i - nav_prev
        state["nav"] = nav_i

        if nav_diff != 0:
            idx = (idx + nav_diff) % len(scenes)
            state["idx"] = idx
            state["hold"] = repeat_i
            state["done"] = False

        if bool(state.get("done", False)):
            status = f"DONE {len(scenes)}/{len(scenes)}"
            return _json_image_empty_result("", status)

        scene_id, prompt = scenes[idx]

        state["hold"] = int(state.get("hold", repeat_i)) - 1
        if int(state.get("hold", 0)) <= 0:
            if idx >= len(scenes) - 1:
                if after_last_key == "loop":
                    state["idx"] = 0
                    state["hold"] = repeat_i
                    state["done"] = False
                else:
                    state["done"] = True
                    state["hold"] = 0
            else:
                state["idx"] = idx + 1
                state["hold"] = repeat_i
                state["done"] = False

        status_suffix = ""
        if after_last_key == "stop_empty" and idx >= len(scenes) - 1:
            status_suffix = "END"
        if interval_suffix:
            status_suffix = f"{interval_suffix} {status_suffix}".strip()

        return self._load_scene_image(
            scene_id,
            prompt,
            idx,
            len(scenes),
            image_folder,
            recursive,
            show_preview,
            status_suffix,
        )
