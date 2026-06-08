from __future__ import annotations

import base64
import json
import re
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib import error, request


try:
    import folder_paths
except Exception:  # pragma: no cover - only absent outside ComfyUI
    folder_paths = None


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_TEXT_USER_QUERY = "Process this input text and return the final answer: [...]"


def _chat_completions_url(base_url: str) -> str:
    normalized = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _safe_filename(value: str, fallback: str = "lmstudio_response") -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", value or "").strip("._-")
    return safe or fallback


def _output_dir(output_dir: str) -> Path:
    value = (output_dir or "lmstudio_json").strip()
    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    if folder_paths is not None:
        try:
            return Path(folder_paths.get_output_directory()) / path
        except Exception:
            pass

    return Path.cwd() / "output" / path


def _tensor_to_pil(image: Any):
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc:  # pragma: no cover - ComfyUI normally has these
        raise RuntimeError("Pillow and numpy are required to encode ComfyUI IMAGE inputs.") from exc

    tensor = image
    if hasattr(tensor, "detach"):
        tensor = tensor.detach().cpu().numpy()

    tensor = np.asarray(tensor)
    if tensor.ndim == 4:
        tensor = tensor[0]
    if tensor.ndim != 3:
        raise RuntimeError(f"Expected IMAGE tensor with 3 or 4 dimensions, got shape {tensor.shape}.")

    if tensor.shape[0] in (1, 3, 4) and tensor.shape[-1] not in (1, 3, 4):
        tensor = np.transpose(tensor, (1, 2, 0))

    if tensor.shape[-1] == 1:
        tensor = np.repeat(tensor, 3, axis=-1)

    if tensor.dtype != np.uint8:
        if tensor.size and float(np.nanmax(tensor)) <= 1.0:
            tensor = tensor * 255.0
        tensor = np.clip(tensor, 0, 255).astype(np.uint8)

    if tensor.shape[-1] == 4:
        return Image.fromarray(tensor, "RGBA")
    if tensor.shape[-1] >= 3:
        return Image.fromarray(tensor[..., :3], "RGB")

    raise RuntimeError(f"Unsupported IMAGE channel count: {tensor.shape[-1]}.")


def _image_to_data_uri(image: Any, image_format: str, max_image_side: int) -> str:
    from PIL import Image

    pil_image = _tensor_to_pil(image)
    max_side = int(max_image_side or 0)
    if max_side > 0 and max(pil_image.size) > max_side:
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        pil_image.thumbnail((max_side, max_side), resampling)

    fmt = "JPEG" if (image_format or "PNG").upper() == "JPEG" else "PNG"
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    if fmt == "JPEG" and pil_image.mode in {"RGBA", "LA", "P"}:
        pil_image = pil_image.convert("RGB")

    buffer = BytesIO()
    if fmt == "JPEG":
        pil_image.save(buffer, format=fmt, quality=92, optimize=True)
    else:
        pil_image.save(buffer, format=fmt)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _parse_stop_sequences(stop_sequences: str) -> list[str] | None:
    stops = [line.strip() for line in (stop_sequences or "").splitlines() if line.strip()]
    return stops or None


def _merge_extra_body(payload: dict[str, Any], extra_body_json: str) -> None:
    text = (extra_body_json or "").strip()
    if not text:
        return
    try:
        extra = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"extra_body_json is not valid JSON: {exc}") from exc
    if not isinstance(extra, dict):
        raise RuntimeError("extra_body_json must be a JSON object, for example {\"top_k\": 40}.")
    payload.update(extra)


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(content)


def _post_json(url: str, payload: dict[str, Any], api_key: str, timeout_seconds: int) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if (api_key or "").strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=max(1, int(timeout_seconds))) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LM Studio request failed with HTTP {exc.code} at {url}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Cannot reach LM Studio at {url}: {exc}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"LM Studio request timed out after {timeout_seconds} seconds.") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LM Studio returned non-JSON response: {body[:1000]}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("LM Studio returned a JSON value, but not a response object.")
    return parsed


def _normalize_placeholder_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def _replace_square_placeholders(
    template: str,
    input_text: str,
    current_input_name: str,
    placeholder_values: dict[str, str] | None = None,
) -> str:
    values = {f"p{i}": "" for i in range(1, 6)}
    values["p1"] = input_text
    for key, value in (placeholder_values or {}).items():
        normalized = _normalize_placeholder_name(key)
        if normalized in values:
            values[normalized] = "" if value is None else str(value)

    placeholders = {
        "": values["p1"],
        "input_text": values["p1"],
        "text": values["p1"],
        "placeholder": values["p1"],
        "input": values["p1"],
        "input_text_placeholder": values["p1"],
        "image_1": "image_1",
        "image_2": "image_2",
        "image_3": "image_3",
        "current_input": current_input_name,
    }
    for index in range(1, 6):
        value = values[f"p{index}"]
        placeholders[f"p{index}"] = value
        placeholders[f"placeholder_{index}"] = value
        placeholders[f"input_text_{index}"] = value
        placeholders[f"text_{index}"] = value

    def replace(match: re.Match[str]) -> str:
        raw_key = match.group(1)
        key = _normalize_placeholder_name(raw_key)
        if key in placeholders:
            return placeholders[key]
        return match.group(0)

    return re.sub(r"\[([^\[\]]*)\]", replace, template or "")


def _build_single_payload(
    *,
    model: str,
    system_prompt: str,
    user_query: str,
    image: Any | None,
    image_label: str,
    input_text: str,
    placeholder_values: dict[str, str] | None,
    response_format: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    presence_penalty: float,
    frequency_penalty: float,
    seed: int,
    stop_sequences: str,
    image_detail: str,
    image_format: str,
    max_image_side: int,
    keep_model_loaded: bool,
    idle_ttl_seconds: int,
    extra_body_json: str,
) -> tuple[dict[str, Any], str]:
    resolved_query = _replace_square_placeholders(user_query, input_text, image_label, placeholder_values).strip()
    if not resolved_query:
        resolved_query = "Analyze the provided input and return the requested text."

    messages: list[dict[str, Any]] = []
    if (system_prompt or "").strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    if image is None:
        content: Any = resolved_query
    else:
        content = [
            {"type": "text", "text": f"{resolved_query}\n\nAttached visual input: {image_label}."},
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_to_data_uri(image, image_format, max_image_side),
                    "detail": image_detail,
                },
            },
        ]

    messages.append({"role": "user", "content": content})

    payload: dict[str, Any] = {
        "model": (model or "").strip(),
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "top_p": float(top_p),
        "presence_penalty": float(presence_penalty),
        "frequency_penalty": float(frequency_penalty),
        "stream": False,
    }

    if keep_model_loaded and int(idle_ttl_seconds) > 0:
        payload["ttl"] = int(idle_ttl_seconds)
    if int(seed) >= 0:
        payload["seed"] = int(seed)
    stops = _parse_stop_sequences(stop_sequences)
    if stops:
        payload["stop"] = stops
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    _merge_extra_body(payload, extra_body_json)
    return payload, resolved_query


def _extract_first_choice_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message", {})
    return _content_to_text(message.get("content")).strip()


def _default_project_root(project_path: str) -> Path:
    value = (project_path or "").strip()
    if value:
        return Path(value).expanduser()
    if folder_paths is not None:
        try:
            return Path(folder_paths.get_output_directory()) / "lmstudio_multi_input_projects"
        except Exception:
            pass
    return Path.cwd() / "output" / "lmstudio_multi_input_projects"


def _make_project_run_dir(project_path: str, run_folder_name: str) -> Path:
    root = _default_project_root(project_path)
    folder = _safe_filename(run_folder_name or "lmstudio_multi_input_agent", "lmstudio_multi_input_agent")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / f"{folder}_{timestamp}_{time.time_ns() % 1000000:06d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _save_route_json(
    *,
    run_dir: Path,
    route_name: str,
    url: str,
    payload: dict[str, Any],
    resolved_query: str,
    response_text: str,
    response_json: dict[str, Any],
    has_image: bool,
) -> str:
    path = run_dir / f"{_safe_filename(route_name)}.json"
    snapshot = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "route": route_name,
        "lmstudio_url": url,
        "model": payload.get("model", ""),
        "has_image": has_image,
        "resolved_user_query": resolved_query,
        "request": {key: value for key, value in payload.items() if key != "messages"},
        "messages_without_image_data": _messages_without_image_data(payload.get("messages", [])),
        "text": response_text,
        "response": response_json,
    }
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


class LMStudioThreeImageAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "default": "Analyze the attached images and return the requested text.",
                        "multiline": True,
                    },
                ),
                "system_prompt": (
                    "STRING",
                    {
                        "default": "You are a precise vision-language assistant.",
                        "multiline": True,
                    },
                ),
                "agent_instructions": (
                    "STRING",
                    {
                        "default": "Use every attached image as context. Return only the final answer unless the user asks for JSON.",
                        "multiline": True,
                    },
                ),
                "lmstudio_base_url": ("STRING", {"default": DEFAULT_BASE_URL, "multiline": False}),
                "api_key": ("STRING", {"default": "lm-studio", "multiline": False}),
                "model": ("STRING", {"default": "local-vision-model-name", "multiline": False}),
                "response_format": (["text", "json_object"], {"default": "text"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 2048, "min": 1, "max": 65536, "step": 64}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "presence_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.05}),
                "frequency_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.05}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "step": 1}),
                "stop_sequences": ("STRING", {"default": "", "multiline": True}),
                "image_detail": (["auto", "low", "high"], {"default": "auto"}),
                "image_format": (["PNG", "JPEG"], {"default": "PNG"}),
                "max_image_side": ("INT", {"default": 1344, "min": 256, "max": 4096, "step": 64}),
                "request_timeout_seconds": ("INT", {"default": 300, "min": 1, "max": 3600, "step": 30}),
                "keep_model_loaded": ("BOOLEAN", {"default": True}),
                "idle_ttl_seconds": ("INT", {"default": 86400, "min": 0, "max": 604800, "step": 300}),
                "save_json": ("BOOLEAN", {"default": True}),
                "json_output_dir": ("STRING", {"default": "lmstudio_json", "multiline": False}),
                "json_filename_prefix": ("STRING", {"default": "lmstudio_response", "multiline": False}),
                "extra_body_json": ("STRING", {"default": "{}", "multiline": True}),
                "always_run": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "image_1": ("IMAGE", {"forceInput": True}),
                "image_2": ("IMAGE", {"forceInput": True}),
                "image_3": ("IMAGE", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "json_path", "raw_response_json")
    FUNCTION = "run"
    CATEGORY = "AntiMatter/LM Studio"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time() if kwargs.get("always_run", True) else False

    def run(
        self,
        prompt: str,
        system_prompt: str,
        agent_instructions: str,
        lmstudio_base_url: str,
        api_key: str,
        model: str,
        response_format: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        presence_penalty: float,
        frequency_penalty: float,
        seed: int,
        stop_sequences: str,
        image_detail: str,
        image_format: str,
        max_image_side: int,
        request_timeout_seconds: int,
        keep_model_loaded: bool,
        idle_ttl_seconds: int,
        save_json: bool,
        json_output_dir: str,
        json_filename_prefix: str,
        extra_body_json: str,
        always_run: bool,
        image_1=None,
        image_2=None,
        image_3=None,
    ):
        attached_images = []
        for index, image in enumerate((image_1, image_2, image_3), start=1):
            if image is not None:
                attached_images.append(
                    {
                        "label": f"image_{index}",
                        "data_uri": _image_to_data_uri(image, image_format, max_image_side),
                    }
                )

        system_parts = [part.strip() for part in (system_prompt, agent_instructions) if (part or "").strip()]
        messages: list[dict[str, Any]] = []
        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        user_text = (prompt or "").strip() or "Analyze the attached images."
        if attached_images:
            image_names = ", ".join(item["label"] for item in attached_images)
            user_text = f"{user_text}\n\nAttached visual inputs: {image_names}."
            content: Any = [{"type": "text", "text": user_text}]
            for item in attached_images:
                content.append({"type": "text", "text": item["label"]})
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": item["data_uri"],
                            "detail": image_detail,
                        },
                    }
                )
        else:
            content = user_text
        messages.append({"role": "user", "content": content})

        payload: dict[str, Any] = {
            "model": (model or "").strip(),
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "top_p": float(top_p),
            "presence_penalty": float(presence_penalty),
            "frequency_penalty": float(frequency_penalty),
            "stream": False,
        }

        if keep_model_loaded and int(idle_ttl_seconds) > 0:
            payload["ttl"] = int(idle_ttl_seconds)
        if int(seed) >= 0:
            payload["seed"] = int(seed)
        stops = _parse_stop_sequences(stop_sequences)
        if stops:
            payload["stop"] = stops
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        _merge_extra_body(payload, extra_body_json)

        url = _chat_completions_url(lmstudio_base_url)
        response_json = _post_json(url, payload, api_key, request_timeout_seconds)

        choices = response_json.get("choices") or []
        if not choices:
            text = ""
        else:
            message = (choices[0] or {}).get("message", {})
            text = _content_to_text(message.get("content")).strip()

        json_path = ""
        if save_json:
            out_dir = _output_dir(json_output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{_safe_filename(json_filename_prefix)}_{timestamp}_{time.time_ns() % 1000000:06d}.json"
            path = out_dir / filename
            snapshot = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "lmstudio_url": url,
                "model": payload.get("model", ""),
                "image_count": len(attached_images),
                "request": {
                    key: value
                    for key, value in payload.items()
                    if key != "messages"
                },
                "messages_without_image_data": _messages_without_image_data(messages),
                "text": text,
                "response": response_json,
            }
            path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            json_path = str(path)

        return (text, json_path, json.dumps(response_json, ensure_ascii=False, indent=2))


def _messages_without_image_data(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            clean_content = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    clean_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "<base64 image omitted>",
                                "detail": item.get("image_url", {}).get("detail", "auto"),
                            },
                        }
                    )
                else:
                    clean_content.append(item)
            sanitized.append({**message, "content": clean_content})
        else:
            sanitized.append(dict(message))
    return sanitized


class LMStudioMultiInputSettingsAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lmstudio_base_url": ("STRING", {"default": DEFAULT_BASE_URL, "multiline": False}),
                "api_key": ("STRING", {"default": "lm-studio", "multiline": False}),
                "model": ("STRING", {"default": "local-vision-model-name", "multiline": False}),
                "project_path": ("STRING", {"default": "", "multiline": False}),
                "run_folder_name": ("STRING", {"default": "lmstudio_multi_input_agent", "multiline": False}),
                "save_json": ("BOOLEAN", {"default": True}),
                "image_1_system_prompt": (
                    "STRING",
                    {"default": "You are a precise vision-language assistant for image 1.", "multiline": True},
                ),
                "image_1_user_query": (
                    "STRING",
                    {"default": "Analyze image_1. Use this text context if present: [...]", "multiline": True},
                ),
                "image_2_system_prompt": (
                    "STRING",
                    {"default": "You are a precise vision-language assistant for image 2.", "multiline": True},
                ),
                "image_2_user_query": (
                    "STRING",
                    {"default": "Analyze image_2. Use this text context if present: [...]", "multiline": True},
                ),
                "image_3_system_prompt": (
                    "STRING",
                    {"default": "You are a precise vision-language assistant for image 3.", "multiline": True},
                ),
                "image_3_user_query": (
                    "STRING",
                    {"default": "Analyze image_3. Use this text context if present: [...]", "multiline": True},
                ),
                "text_system_prompt": (
                    "STRING",
                    {"default": "You are a helpful text-only assistant.", "multiline": True},
                ),
                "text_user_query": (
                    "STRING",
                    {"default": DEFAULT_TEXT_USER_QUERY, "multiline": True},
                ),
                "response_format": (["text", "json_object"], {"default": "text"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 2048, "min": 1, "max": 65536, "step": 64}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "presence_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.05}),
                "frequency_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.05}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 0xFFFFFFFF, "step": 1}),
                "stop_sequences": ("STRING", {"default": "", "multiline": True}),
                "image_detail": (["auto", "low", "high"], {"default": "auto"}),
                "image_format": (["PNG", "JPEG"], {"default": "PNG"}),
                "max_image_side": ("INT", {"default": 1344, "min": 256, "max": 4096, "step": 64}),
                "request_timeout_seconds": ("INT", {"default": 300, "min": 1, "max": 3600, "step": 30}),
                "keep_model_loaded": ("BOOLEAN", {"default": True}),
                "idle_ttl_seconds": ("INT", {"default": 86400, "min": 0, "max": 604800, "step": 300}),
                "extra_body_json": ("STRING", {"default": "{}", "multiline": True}),
                "always_run": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "image_1": ("IMAGE", {"forceInput": True}),
                "image_2": ("IMAGE", {"forceInput": True}),
                "image_3": ("IMAGE", {"forceInput": True}),
                "input_text_placeholder": ("STRING", {"forceInput": True}),
                "placeholder_2": ("STRING", {"forceInput": True}),
                "placeholder_3": ("STRING", {"forceInput": True}),
                "placeholder_4": ("STRING", {"forceInput": True}),
                "placeholder_5": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "image_1_text",
        "image_2_text",
        "image_3_text",
        "input_text_output",
        "json_project_dir",
        "combined_text",
    )
    FUNCTION = "run"
    CATEGORY = "AntiMatter/LM Studio"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time() if kwargs.get("always_run", True) else False

    def _run_single_route(
        self,
        *,
        route_name: str,
        system_prompt: str,
        user_query: str,
        image: Any | None,
        input_text: str,
        placeholder_values: dict[str, str],
        url: str,
        api_key: str,
        model: str,
        response_format: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        presence_penalty: float,
        frequency_penalty: float,
        seed: int,
        stop_sequences: str,
        image_detail: str,
        image_format: str,
        max_image_side: int,
        request_timeout_seconds: int,
        keep_model_loaded: bool,
        idle_ttl_seconds: int,
        extra_body_json: str,
        save_json: bool,
        run_dir: Path | None,
    ) -> tuple[str, str]:
        payload, resolved_query = _build_single_payload(
            model=model,
            system_prompt=system_prompt,
            user_query=user_query,
            image=image,
            image_label=route_name,
            input_text=input_text,
            placeholder_values=placeholder_values,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            seed=seed,
            stop_sequences=stop_sequences,
            image_detail=image_detail,
            image_format=image_format,
            max_image_side=max_image_side,
            keep_model_loaded=keep_model_loaded,
            idle_ttl_seconds=idle_ttl_seconds,
            extra_body_json=extra_body_json,
        )
        response_json = _post_json(url, payload, api_key, request_timeout_seconds)
        response_text = _extract_first_choice_text(response_json)
        json_path = ""
        if save_json and run_dir is not None:
            json_path = _save_route_json(
                run_dir=run_dir,
                route_name=route_name,
                url=url,
                payload=payload,
                resolved_query=resolved_query,
                response_text=response_text,
                response_json=response_json,
                has_image=image is not None,
            )
        return response_text, json_path

    def run(
        self,
        lmstudio_base_url: str,
        api_key: str,
        model: str,
        project_path: str,
        run_folder_name: str,
        save_json: bool,
        image_1_system_prompt: str,
        image_1_user_query: str,
        image_2_system_prompt: str,
        image_2_user_query: str,
        image_3_system_prompt: str,
        image_3_user_query: str,
        text_system_prompt: str,
        text_user_query: str,
        response_format: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        presence_penalty: float,
        frequency_penalty: float,
        seed: int,
        stop_sequences: str,
        image_detail: str,
        image_format: str,
        max_image_side: int,
        request_timeout_seconds: int,
        keep_model_loaded: bool,
        idle_ttl_seconds: int,
        extra_body_json: str,
        always_run: bool,
        image_1=None,
        image_2=None,
        image_3=None,
        input_text_placeholder=None,
        placeholder_2=None,
        placeholder_3=None,
        placeholder_4=None,
        placeholder_5=None,
    ):
        url = _chat_completions_url(lmstudio_base_url)
        input_text = "" if input_text_placeholder is None else str(input_text_placeholder)
        placeholder_values = {
            "p1": input_text,
            "p2": "" if placeholder_2 is None else str(placeholder_2),
            "p3": "" if placeholder_3 is None else str(placeholder_3),
            "p4": "" if placeholder_4 is None else str(placeholder_4),
            "p5": "" if placeholder_5 is None else str(placeholder_5),
        }
        run_dir = _make_project_run_dir(project_path, run_folder_name) if save_json else None

        outputs = {
            "image_1": {"text": "", "json_path": ""},
            "image_2": {"text": "", "json_path": ""},
            "image_3": {"text": "", "json_path": ""},
            "input_text": {"text": "", "json_path": ""},
        }

        route_configs = [
            ("image_1", image_1, image_1_system_prompt, image_1_user_query),
            ("image_2", image_2, image_2_system_prompt, image_2_user_query),
            ("image_3", image_3, image_3_system_prompt, image_3_user_query),
        ]

        for route_name, image, system_prompt, user_query in route_configs:
            if image is None:
                continue
            text, json_path = self._run_single_route(
                route_name=route_name,
                system_prompt=system_prompt,
                user_query=user_query,
                image=image,
                input_text=input_text,
                placeholder_values=placeholder_values,
                url=url,
                api_key=api_key,
                model=model,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                seed=seed,
                stop_sequences=stop_sequences,
                image_detail=image_detail,
                image_format=image_format,
                max_image_side=max_image_side,
                request_timeout_seconds=request_timeout_seconds,
                keep_model_loaded=keep_model_loaded,
                idle_ttl_seconds=idle_ttl_seconds,
                extra_body_json=extra_body_json,
                save_json=save_json,
                run_dir=run_dir,
            )
            outputs[route_name] = {"text": text, "json_path": json_path}

        has_image_input = image_1 is not None or image_2 is not None or image_3 is not None
        text_query = (text_user_query or "").strip()
        text_route_is_custom = text_query != DEFAULT_TEXT_USER_QUERY
        should_run_text = bool(text_query) and (not has_image_input or text_route_is_custom)
        if should_run_text:
            text, json_path = self._run_single_route(
                route_name="input_text",
                system_prompt=text_system_prompt,
                user_query=text_user_query,
                image=None,
                input_text=input_text,
                placeholder_values=placeholder_values,
                url=url,
                api_key=api_key,
                model=model,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                seed=seed,
                stop_sequences=stop_sequences,
                image_detail=image_detail,
                image_format=image_format,
                max_image_side=max_image_side,
                request_timeout_seconds=request_timeout_seconds,
                keep_model_loaded=keep_model_loaded,
                idle_ttl_seconds=idle_ttl_seconds,
                extra_body_json=extra_body_json,
                save_json=save_json,
                run_dir=run_dir,
            )
            outputs["input_text"] = {"text": text, "json_path": json_path}

        combined_text = "\n\n".join(
            value
            for value in (
                outputs["image_1"]["text"],
                outputs["image_2"]["text"],
                outputs["image_3"]["text"],
                outputs["input_text"]["text"],
            )
            if value
        )

        if save_json and run_dir is not None:
            manifest = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "lmstudio_url": url,
                "model": model,
                "input_text_placeholder": input_text,
                "placeholders": placeholder_values,
                "routes": outputs,
                "combined_text": combined_text,
            }
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        return (
            outputs["image_1"]["text"],
            outputs["image_2"]["text"],
            outputs["image_3"]["text"],
            outputs["input_text"]["text"],
            str(run_dir) if run_dir is not None else "",
            combined_text,
        )


NODE_CLASS_MAPPINGS = {
    "LMStudioThreeImageAgent": LMStudioThreeImageAgent,
    "LMStudioMultiInputSettingsAgent": LMStudioMultiInputSettingsAgent,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LMStudioThreeImageAgent": "LM Studio 3 Image Agent",
    "LMStudioMultiInputSettingsAgent": "LM Studio Multi Input Settings Agent",
}
