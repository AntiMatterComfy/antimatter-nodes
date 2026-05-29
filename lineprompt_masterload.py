import hashlib
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

import folder_paths

try:
    from aiohttp import web
    from server import PromptServer
except Exception:
    web = None
    PromptServer = None

_STATE: Dict[str, Dict[str, Any]] = {}
_JSON_STATE: Dict[str, Dict[str, Any]] = {}
_NONE_FILE = "none"
_COMMENT_PREFIXES = ("#", "//")
_JSON_PROMPT_KEYS = ("prompt", "image_prompt", "positive", "text", "description")
_JSON_SCENE_ID_KEYS = ("scene", "scene_id", "id", "name", "title")
_JSON_SCENE_LIST_KEYS = ("scenes", "scene_prompts", "items", "data")

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
            elif isinstance(item, (list, tuple)) and len(item) >= 2 and not isinstance(item[1], (list, tuple, dict)):
                _append_scene(scenes, item[0], item[1])
            elif isinstance(item, str):
                _append_scene(scenes, f"scene-{len(scenes) + 1:03d}", item)
            elif isinstance(item, (list, tuple)):
                scenes.extend(_extract_scenes_from_json(item))
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
        text, error = _read_text_from_file(file_path)
        if error:
            return [], _source_key_from_file(file_path), error
        data, parse_error = _parse_json_value(text)
        if parse_error:
            return [], _source_key_from_file(file_path), parse_error
        return _extract_scenes_from_json(data), _source_key_from_file(file_path), None

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


def _make_output(lines: List[str], start_index: int, count: int, mode_key: str, delimiter: str) -> str:
    direction = -1 if mode_key == "from_end" else 1
    take = min(count, len(lines))
    chosen_lines = [lines[(start_index + direction * i) % len(lines)] for i in range(take)]
    out_text = " ".join(chosen_lines).strip()

    delimiter_s = str(delimiter or "")
    if out_text and delimiter_s and not out_text.endswith(delimiter_s):
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


class LinePrompt_MasterLoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
                "input_text": ("STRING", {"default": "", "multiline": True}),
                "text_file": ("STRING", {"default": ""}),
                "style_file": (_available_txt_files(), {"default": _NONE_FILE}),
                "lines_to_take": ("INT", {"default": 1, "min": 1, "max": 3, "step": 1}),
                "read_mode": (["sequential", "random", "from_end"], {"default": "sequential"}),
                "freeze_iterations": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "delimiter": ([",", "/", ".", ";"], {"default": ","}),
                "nav": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
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
        enabled: bool,
        input_text: str,
        text_file: str,
        style_file: str,
        lines_to_take: int,
        read_mode: str,
        freeze_iterations: int,
        delimiter: str,
        nav: int,
        unique_id: Optional[str] = None,
    ):
        if not enabled:
            return {"ui": {"preview": ("",), "status": ("OFF",)}, "result": ("",)}

        uid = _normalize_unique_id(unique_id)
        mode_key = _MODE_MAP.get(str(read_mode).strip().lower(), "sequential")
        lines_to_take_i = _clamp_int(lines_to_take, 1, 3)
        freeze_i = _clamp_int(freeze_iterations, 0, 100000)
        lines, source_key, source_error = _resolve_source(text_file, style_file)

        if not lines:
            msg = ""
            if source_error:
                msg = f"[LinePrompt_MasterLoad] {source_error}"
            return {"ui": {"preview": (msg,), "status": (msg,)}, "result": ("",)}

        state = _STATE.get(uid)
        source_changed = state is None or state.get("source_key") != source_key

        if source_changed:
            state = {
                "idx": _initial_index(mode_key, len(lines)),
                "hold": max(freeze_i, 1),
                "nav": int(nav),
                "source_key": source_key,
            }
            _STATE[uid] = state

        # Keep idx valid if file/text changed length.
        idx = int(state.get("idx", 0)) % len(lines)
        state["idx"] = idx

        # Manual navigation via hidden counter widget (changed by Next/Previous buttons).
        try:
            nav_i = int(nav)
        except Exception:
            nav_i = int(state.get("nav", 0))
        nav_prev = int(state.get("nav", nav_i))
        nav_diff = nav_i - nav_prev
        state["nav"] = nav_i

        if nav_diff != 0:
            idx = (idx + nav_diff) % len(lines)
            state["idx"] = idx
            state["hold"] = max(freeze_i, 1)
        elif int(state.get("hold", 0)) <= 0:
            idx = _next_index(mode_key, idx, len(lines))
            state["idx"] = idx
            state["hold"] = max(freeze_i, 1)

        selected_text = _make_output(lines, idx, lines_to_take_i, mode_key, delimiter)
        out_text = _join_prefix(input_text, selected_text)

        # Decrement hold AFTER using the current selection.
        state["hold"] = int(state.get("hold", 1)) - 1

        status = f"{idx + 1}/{len(lines)}"
        return {"ui": {"preview": (out_text,), "status": (status,)}, "result": (out_text,)}


class LinePrompt_MasterLoad_JSON:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
                "json_text": ("STRING", {"default": "", "multiline": True}),
                "json_file": ("STRING", {"default": ""}),
                "scene_mode": (["sequential", "manual"], {"default": "sequential"}),
                "manual_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "repeat_each_scene": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "after_last_scene": (["stop_empty", "loop"], {"default": "stop_empty"}),
                "nav": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
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
