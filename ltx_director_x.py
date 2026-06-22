from __future__ import annotations

import importlib
import json
import math
import re
import sys
import types
import traceback
from copy import deepcopy
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from comfy_api.latest import io

try:
    import folder_paths
    import comfy.sd
    import comfy.utils
except Exception:  # pragma: no cover - available inside ComfyUI
    folder_paths = None
    comfy = None


GuideData = io.Custom("GUIDE_DATA")

DEFAULT_LTX_CHECKPOINT = "LTX/ltx-2.3-22b-dev-fp8.safetensors"
DEFAULT_LTX_TEXT_ENCODER = "gemma_3_12B_it_fp8_e4m3fn.safetensors"
DEFAULT_LTX_TEXT_PROJECTION = "ltx-2.3_text_projection_bf16.safetensors"
DEFAULT_LTX_VIDEO_VAE = "LTX23_video_vae_bf16.safetensors"
DEFAULT_LTX_AUDIO_VAE = "LTX23_audio_vae_bf16.safetensors"
DEFAULT_LTX_LATENT_UPSCALE_MODEL = "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"


DEFAULT_AGENT_INSTRUCTIONS = """Write a production-ready LTX image-to-video prompt.
Use explicit continuity, camera, motion, lighting, character action, sound, and avoid vague words.
Return only the final prompt, with clear [VISUAL], [CINEMATOGRAPHY], [CHARACTER MOTION], [SPEECH] if needed, and [SOUNDS] sections."""

DEFAULT_TIMELINE = {
    "schema": "antimatter-ltx-director-x-timeline-v1",
    "segments": [],
    "audioSegments": [],
    "transitions": [],
    "markers": [],
    "selectedSegmentId": "",
    "selection": {"start": 0, "end": 120},
    "editActions": [],
}


def _default_timeline_json() -> str:
    return json.dumps(DEFAULT_TIMELINE, ensure_ascii=False)


PRO_LORA_SPECS = [
    {
        "id": "distilled",
        "label": "LTX 2.3 Distilled 384 v1.1",
        "filename": "ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
        "preferred": "LTX/ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
        "default_enabled": True,
        "default_strength": 1.0,
        "role": "speed/quality distilled base motion",
    },
    {
        "id": "union_control",
        "label": "IC LoRA Union Control Ref 0.5",
        "filename": "ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors",
        "preferred": "LTX/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors",
        "default_enabled": False,
        "default_strength": 0.65,
        "role": "image conditioning and reference control",
    },
    {
        "id": "motion_track",
        "label": "IC LoRA Motion Track Ref 0.5",
        "filename": "ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors",
        "preferred": "LTX/ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors",
        "default_enabled": False,
        "default_strength": 0.72,
        "role": "motion track and sparse control response",
    },
    {
        "id": "lipdub",
        "label": "IC LoRA LipDub 0.9",
        "filename": "ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors",
        "preferred": "LTX/ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors",
        "default_enabled": False,
        "default_strength": 0.85,
        "role": "speech/lip motion shots",
    },
    {
        "id": "transition",
        "label": "LTX 2.3 Transition",
        "filename": "ltx2.3-transition.safetensors",
        "preferred": "LTX/ltx2.3-transition.safetensors",
        "default_enabled": False,
        "default_strength": 0.7,
        "role": "shot transitions and morph continuity",
    },
    {
        "id": "camera_control",
        "label": "LTX 2.3 Camera Controls",
        "filename": "LTX2.3_CameraControls.safetensors",
        "preferred": "LTX/CAMERA/LTX2.3_CameraControls.safetensors",
        "default_enabled": False,
        "default_strength": 0.9,
        "role": "camera movement steering",
    },
    {
        "id": "detailer",
        "label": "Detailer IC-LoRA",
        "filename": "ltx-2-19b-ic-lora-detailer.safetensors",
        "preferred": "LTX/ltx-2-19b-ic-lora-detailer.safetensors",
        "default_enabled": False,
        "default_strength": 0.65,
        "role": "detail restoration",
    },
    {
        "id": "pose_control",
        "label": "Pose Control IC-LoRA",
        "filename": "ltx-2-19b-ic-lora-pose-control.safetensors",
        "preferred": "LTX/ltx-2-19b-ic-lora-pose-control.safetensors",
        "default_enabled": False,
        "default_strength": 0.70,
        "role": "pose guidance",
    },
    {
        "id": "camera_dolly_in",
        "label": "Camera Control Dolly In",
        "filename": "ltx-2-19b-lora-camera-control-dolly-in.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-in.safetensors",
        "default_enabled": False,
        "default_strength": 0.80,
        "role": "camera push in",
    },
    {
        "id": "camera_dolly_out",
        "label": "Camera Control Dolly Out",
        "filename": "ltx-2-19b-lora-camera-control-dolly-out.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-out.safetensors",
        "default_enabled": False,
        "default_strength": 0.80,
        "role": "camera pull back",
    },
    {
        "id": "camera_dolly_left",
        "label": "Camera Control Dolly Left",
        "filename": "ltx-2-19b-lora-camera-control-dolly-left.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-left.safetensors",
        "default_enabled": False,
        "default_strength": 0.80,
        "role": "camera truck left",
    },
    {
        "id": "camera_dolly_right",
        "label": "Camera Control Dolly Right",
        "filename": "ltx-2-19b-lora-camera-control-dolly-right.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-right.safetensors",
        "default_enabled": False,
        "default_strength": 0.80,
        "role": "camera truck right",
    },
    {
        "id": "camera_jib_up",
        "label": "Camera Control Jib Up",
        "filename": "ltx-2-19b-lora-camera-control-jib-up.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-up.safetensors",
        "default_enabled": False,
        "default_strength": 0.80,
        "role": "camera rise",
    },
    {
        "id": "camera_jib_down",
        "label": "Camera Control Jib Down",
        "filename": "ltx-2-19b-lora-camera-control-jib-down.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-down.safetensors",
        "default_enabled": False,
        "default_strength": 0.80,
        "role": "camera descend",
    },
    {
        "id": "camera_static",
        "label": "Camera Control Static",
        "filename": "ltx-2-19b-lora-camera-control-static.safetensors",
        "preferred": "LTX/CAMERA/ltx-2-19b-lora-camera-control-static.safetensors",
        "default_enabled": False,
        "default_strength": 0.75,
        "role": "locked-off shot",
    },
]


PRO_LORA_PRESETS = {
    "clean_default": {
        "distilled": (True, 1.0),
        "union_control": (False, 0.0),
        "motion_track": (False, 0.0),
        "lipdub": (False, 0.0),
        "transition": (False, 0.0),
        "camera_control": (False, 0.0),
        "detailer": (False, 0.0),
        "pose_control": (False, 0.0),
    },
    "director_balanced": {
        "distilled": (True, 1.0),
        "union_control": (False, 0.0),
        "motion_track": (False, 0.0),
        "lipdub": (False, 0.0),
        "transition": (False, 0.0),
        "camera_control": (False, 0.0),
    },
    "camera_control": {
        "distilled": (True, 1.0),
        "union_control": (False, 0.0),
        "motion_track": (False, 0.0),
        "lipdub": (False, 0.0),
        "transition": (False, 0.0),
        "camera_control": (True, 0.95),
    },
    "motion_tracking": {
        "distilled": (True, 1.0),
        "union_control": (True, 0.6),
        "motion_track": (True, 0.85),
        "lipdub": (False, 0.0),
        "transition": (False, 0.0),
        "camera_control": (False, 0.0),
    },
    "lipdub": {
        "distilled": (True, 1.0),
        "union_control": (False, 0.0),
        "motion_track": (False, 0.0),
        "lipdub": (True, 0.9),
        "transition": (False, 0.0),
        "camera_control": (False, 0.0),
    },
    "transition": {
        "distilled": (True, 1.0),
        "union_control": (False, 0.0),
        "motion_track": (False, 0.0),
        "lipdub": (False, 0.0),
        "transition": (True, 0.82),
        "camera_control": (False, 0.0),
    },
    "max_control": {
        "distilled": (True, 1.0),
        "union_control": (True, 0.65),
        "motion_track": (True, 0.8),
        "lipdub": (False, 0.0),
        "transition": (False, 0.0),
        "camera_control": (False, 0.0),
    },
}

CAMERA_LORA_MODE_MAP = {
    "dolly_in": "camera_dolly_in",
    "dolly_out": "camera_dolly_out",
    "dolly_left": "camera_dolly_left",
    "dolly_right": "camera_dolly_right",
    "jib_up": "camera_jib_up",
    "jib_down": "camera_jib_down",
    "static": "camera_static",
}
CAMERA_MODES = ["off", *CAMERA_LORA_MODE_MAP.keys(), "custom"]
CAMERA_LORA_IDS = set(CAMERA_LORA_MODE_MAP.values())
STAGE_RUN_MODES = ["full_two_stage", "stage1_only", "stage2_refine", "single_stage"]


DEFAULT_CAMERA_CONTROL = {
    "schema": "antimatter-ltx-director-x-pro-camera-v1",
    "mode": "off",
    "yaw": 0.0,
    "pitch": 0.0,
    "roll": 0.0,
    "zoom": 1.0,
    "truck": 0.0,
    "pedestal": 0.0,
    "dolly": 0.0,
    "focalLength": 35.0,
    "keyframes": [
        {"time": 0.0, "yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 1.0, "truck": 0.0, "pedestal": 0.0, "dolly": 0.0, "focalLength": 35.0},
        {"time": 1.0, "yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 1.0, "truck": 0.0, "pedestal": 0.0, "dolly": 0.0, "focalLength": 35.0},
    ],
}


def _default_lora_stack_json() -> str:
    return json.dumps(
        {
            "schema": "antimatter-ltx-director-x-pro-loras-v1",
            "loras": [
                {
                    "id": spec["id"],
                    "enabled": spec["default_enabled"],
                    "strength": spec["default_strength"],
                    "filename": spec["filename"],
                    "preferred": spec["preferred"],
                }
                for spec in PRO_LORA_SPECS
            ],
        },
        ensure_ascii=False,
    )


def _default_camera_control_json() -> str:
    return json.dumps(DEFAULT_CAMERA_CONTROL, ensure_ascii=False)


def _default_pro_editor_settings_json() -> str:
    settings = {
        "schema": "antimatter-ltx-director-x-pro-settings-v1",
        "paths": {
            "ltx_checkpoint": f"models/checkpoints/{DEFAULT_LTX_CHECKPOINT}",
            "text_encoder": f"models/text_encoders/{DEFAULT_LTX_TEXT_ENCODER}",
            "text_projection": f"models/text_encoders/{DEFAULT_LTX_TEXT_PROJECTION}",
            "video_vae": f"models/vae/{DEFAULT_LTX_VIDEO_VAE}",
            "audio_vae": f"models/vae/{DEFAULT_LTX_AUDIO_VAE}",
            "tiny_vae": "models/vae/taeltx2_3.safetensors",
            "distilled_lora": "models/loras/LTX/ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
            "union_control_lora": "models/loras/LTX/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors",
            "motion_track_lora": "models/loras/LTX/ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors",
            "lipdub_lora": "models/loras/LTX/ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors",
            "transition_lora": "models/loras/LTX/ltx2.3-transition.safetensors",
            "camera_control_lora": "models/loras/LTX/CAMERA/LTX2.3_CameraControls.safetensors",
            "detailer_lora": "models/loras/LTX/ltx-2-19b-ic-lora-detailer.safetensors",
            "pose_control_lora": "models/loras/LTX/ltx-2-19b-ic-lora-pose-control.safetensors",
            "camera_dolly_in_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-in.safetensors",
            "camera_dolly_out_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-out.safetensors",
            "camera_dolly_left_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-left.safetensors",
            "camera_dolly_right_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-right.safetensors",
            "camera_jib_up_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-up.safetensors",
            "camera_jib_down_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-down.safetensors",
            "camera_static_lora": "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-static.safetensors",
            "upscale_model": f"models/latent_upscale_models/{DEFAULT_LTX_LATENT_UPSCALE_MODEL}",
        },
        "generation": {
            "resolution_preset": "ltx_hd_1280x720",
            "width": 1280,
            "height": 720,
            "two_stage_mode": True,
            "stage_run_mode": "full_two_stage",
            "stage1_draft_scale": 0.5,
            "stage2_require_stage1_source": True,
            "use_latest_stage1_result": True,
            "advanced_mode": False,
            "fast_preview_enabled": True,
            "fast_preview_scale": 0.5,
            "use_upscale_model": True,
            "upscale_factor": 2,
            "auto_load_models": False,
        },
        "output": {
            "final_video_path": "",
            "live_preview_path": "",
            "output_directory": "output/antimatter_ltx_director_x/final",
            "intermediate_directory": "output/antimatter_ltx_director_x/intermediate",
            "container": "mp4",
            "codec": "h264",
            "quality_mode": "crf",
            "crf": 18,
            "bitrate_mbps": 24,
            "audio_codec": "aac",
            "audio_bitrate_kbps": 320,
            "save_intermediates": True,
            "overwrite": False,
        },
        "ui": {
            "preview_url": "",
            "live_preview_url": "",
            "theme": "antimatter_dark",
        },
    }
    return json.dumps(settings, ensure_ascii=False)


def _load_wdc_ltx_director():
    root = Path(__file__).resolve().parents[1] / "WhatDreamsCost-ComfyUI"
    if not root.exists():
        raise RuntimeError(
            "Antimatter Ltx Director X needs WhatDreamsCost-ComfyUI because it reuses "
            "the working LTXDirector conditioning/latent engine. Install or restore "
            f"this folder: {root}"
        )

    package_name = "_antimatter_promptrelay_bridge"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root)]
        package.__file__ = str(root / "__init__.py")
        package.__package__ = package_name
        sys.modules[package_name] = package

    return importlib.import_module(f"{package_name}.ltx_director")


def _load_wdc_ltx_director_guide():
    _load_wdc_ltx_director()
    return importlib.import_module("_antimatter_promptrelay_bridge.ltx_director_guide")


def _node_tuple(value: Any) -> tuple[Any, ...]:
    result = getattr(value, "result", None)
    if result is not None:
        return tuple(result)
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def _try_import_pipeline_nodes() -> dict[str, Any]:
    try:
        import nodes as comfy_nodes
        from comfy_extras.nodes_custom_sampler import (
            BasicScheduler,
            CFGGuider,
            KSamplerSelect,
            RandomNoise,
            SamplerCustomAdvanced,
        )
        from comfy_extras.nodes_hunyuan import LatentUpscaleModelLoader
        from comfy_extras.nodes_lt import (
            LTXVConcatAVLatent,
            LTXVConditioning,
            LTXVCropGuides,
            LTXVSeparateAVLatent,
        )
        from comfy_extras.nodes_lt_audio import LTXVAudioVAEDecode
        from comfy_extras.nodes_lt_upsampler import LTXVLatentUpsampler
        from comfy_extras.nodes_video import CreateVideo, SaveVideo

        guide_mod = _load_wdc_ltx_director_guide()
        return {
            "BasicScheduler": BasicScheduler,
            "CFGGuider": CFGGuider,
            "ConditioningZeroOut": comfy_nodes.ConditioningZeroOut,
            "CreateVideo": CreateVideo,
            "KSamplerSelect": KSamplerSelect,
            "LatentUpscaleModelLoader": LatentUpscaleModelLoader,
            "LTXDirectorGuide": guide_mod.LTXDirectorGuide,
            "LTXVAudioVAEDecode": LTXVAudioVAEDecode,
            "LTXVConcatAVLatent": LTXVConcatAVLatent,
            "LTXVConditioning": LTXVConditioning,
            "LTXVCropGuides": LTXVCropGuides,
            "LTXVLatentUpsampler": LTXVLatentUpsampler,
            "LTXVSeparateAVLatent": LTXVSeparateAVLatent,
            "RandomNoise": RandomNoise,
            "SamplerCustomAdvanced": SamplerCustomAdvanced,
            "SaveVideo": SaveVideo,
            "VAEDecode": comfy_nodes.VAEDecode,
        }
    except Exception as exc:
        raise RuntimeError(f"Could not import the LTX integrated pipeline nodes: {exc}") from exc


def _load_kj_ltxv_nodes():
    root = Path(__file__).resolve().parents[1] / "comfyui-kjnodes"
    if not root.exists():
        return None
    package_name = "_antimatter_kjnodes_bridge"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root)]
        package.__file__ = str(root / "__init__.py")
        package.__package__ = package_name
        sys.modules[package_name] = package
    return importlib.import_module(f"{package_name}.nodes.ltxv_nodes")


def _find_latent_upscale_model_name(raw: str) -> str:
    wanted = str(raw or DEFAULT_LTX_LATENT_UPSCALE_MODEL).replace("\\", "/").strip()
    wanted_name = Path(wanted).name
    if folder_paths is None:
        return wanted_name or DEFAULT_LTX_LATENT_UPSCALE_MODEL
    try:
        names = list(folder_paths.get_filename_list("latent_upscale_models"))
    except Exception:
        names = []
    if not names:
        return wanted_name or DEFAULT_LTX_LATENT_UPSCALE_MODEL

    wanted_lower = wanted.lower()
    wanted_name_lower = wanted_name.lower()
    for name in names:
        normalized = name.replace("\\", "/").lower()
        if normalized == wanted_lower:
            return name
    for name in names:
        if Path(name).name.lower() == wanted_name_lower:
            return name
    for name in names:
        normalized = name.replace("\\", "/").lower()
        if normalized.endswith("/" + wanted_name_lower) or wanted_name_lower in normalized:
            return name
    for name in names:
        if Path(name).name.lower() == DEFAULT_LTX_LATENT_UPSCALE_MODEL.lower():
            return name
    return wanted_name or DEFAULT_LTX_LATENT_UPSCALE_MODEL


def _find_folder_model_name(folder_key: str, raw: str, default_name: str = "") -> str:
    wanted = str(raw or default_name or "").replace("\\", "/").strip()
    wanted_name = Path(wanted).name
    if folder_paths is None:
        return wanted_name or default_name
    try:
        names = list(folder_paths.get_filename_list(folder_key))
    except Exception:
        names = []
    if not names:
        return wanted_name or default_name
    wanted_lower = wanted.lower()
    wanted_name_lower = wanted_name.lower()
    for name in names:
        if name.replace("\\", "/").lower() == wanted_lower:
            return name
    for name in names:
        if Path(name).name.lower() == wanted_name_lower:
            return name
    for name in names:
        normalized = name.replace("\\", "/").lower()
        if wanted_name_lower and (normalized.endswith("/" + wanted_name_lower) or wanted_name_lower in normalized):
            return name
    if default_name:
        default_lower = default_name.replace("\\", "/").lower()
        default_file = Path(default_name).name.lower()
        for name in names:
            normalized = name.replace("\\", "/").lower()
            if normalized == default_lower or Path(name).name.lower() == default_file:
                return name
    return wanted_name or default_name


def _load_vae_from_name(vae_name: str, report: list[dict[str, Any]]) -> Any:
    try:
        _load_kj_ltxv_nodes()
        kj_nodes = importlib.import_module("_antimatter_kjnodes_bridge.nodes.nodes")
        vae = kj_nodes.VAELoaderKJ().load_vae(vae_name, "main_device", "bf16")[0]
        report.append({"asset": vae_name, "loader": "VAELoaderKJ", "status": "loaded"})
        return vae
    except Exception as kj_exc:
        try:
            import nodes as comfy_nodes

            vae = comfy_nodes.VAELoader().load_vae(vae_name)[0]
            report.append({"asset": vae_name, "loader": "VAELoader", "status": "loaded", "kj_fallback": str(kj_exc)})
            return vae
        except Exception as core_exc:
            raise RuntimeError(f"Could not load VAE '{vae_name}' with VAELoaderKJ or VAELoader: {core_exc}") from core_exc


def _auto_load_ltx_assets_from_settings(
    *,
    editor_settings: dict[str, Any],
    model: Any | None,
    clip: Any | None,
    audio_vae: Any | None,
    video_vae: Any | None,
) -> tuple[Any, Any, Any, Any, list[dict[str, Any]]]:
    paths = editor_settings.get("paths") if isinstance(editor_settings.get("paths"), dict) else {}
    report: list[dict[str, Any]] = []

    if model is None:
        import nodes as comfy_nodes

        ckpt_name = _find_folder_model_name("checkpoints", str(paths.get("ltx_checkpoint") or ""), DEFAULT_LTX_CHECKPOINT)
        model, _, _ = comfy_nodes.CheckpointLoaderSimple().load_checkpoint(ckpt_name)
        report.append({"asset": "model", "loader": "CheckpointLoaderSimple", "name": ckpt_name, "status": "loaded"})
    else:
        report.append({"asset": "model", "status": "connected_input"})

    if clip is None:
        import nodes as comfy_nodes

        text_encoder = _find_folder_model_name("text_encoders", str(paths.get("text_encoder") or ""), DEFAULT_LTX_TEXT_ENCODER)
        text_projection = _find_folder_model_name("text_encoders", str(paths.get("text_projection") or ""), DEFAULT_LTX_TEXT_PROJECTION)
        clip = comfy_nodes.DualCLIPLoader().load_clip(text_encoder, text_projection, "ltxv", "default")[0]
        report.append(
            {
                "asset": "clip",
                "loader": "DualCLIPLoader",
                "clip_name1": text_encoder,
                "clip_name2": text_projection,
                "type": "ltxv",
                "status": "loaded",
            }
        )
    else:
        report.append({"asset": "clip", "status": "connected_input"})

    if video_vae is None:
        video_vae_name = _find_folder_model_name("vae", str(paths.get("video_vae") or ""), DEFAULT_LTX_VIDEO_VAE)
        video_vae = _load_vae_from_name(video_vae_name, report)
        report[-1]["asset"] = "video_vae"
    else:
        report.append({"asset": "video_vae", "status": "connected_input"})

    if audio_vae is None:
        audio_vae_name = _find_folder_model_name("vae", str(paths.get("audio_vae") or ""), DEFAULT_LTX_AUDIO_VAE)
        audio_vae = _load_vae_from_name(audio_vae_name, report)
        report[-1]["asset"] = "audio_vae"
    else:
        report.append({"asset": "audio_vae", "status": "connected_input"})

    return model, clip, audio_vae, video_vae, report


def _maybe_apply_sampling_preview_override(
    model: Any,
    preview_rate: int,
    latent_upscale_model: Any | None,
    vae: Any | None,
    report: dict[str, Any],
) -> Any:
    try:
        mod = _load_kj_ltxv_nodes()
        if mod is None or not hasattr(mod, "LTX2SamplingPreviewOverride"):
            report.setdefault("warnings", []).append("KJNodes LTX2SamplingPreviewOverride was not found; fast preview wrapper skipped.")
            return model
        return _node_tuple(
            mod.LTX2SamplingPreviewOverride.execute(
                model=model,
                preview_rate=max(1, _as_int(preview_rate, 8)),
                latent_upscale_model=latent_upscale_model,
                vae=vae,
            )
        )[0]
    except Exception as exc:
        report.setdefault("warnings", []).append(f"Fast preview wrapper skipped: {exc}")
        return model


def _save_video_best_effort(
    video: Any,
    output_settings: dict[str, Any],
    frame_rate: float,
    report: dict[str, Any],
) -> None:
    if video is None:
        return
    try:
        from comfy_extras.nodes_video import SaveVideo

        output_dir = str(output_settings.get("output_directory") or "video").replace("\\", "/").strip("/")
        if output_dir.lower().startswith("output/"):
            output_dir = output_dir[7:]
        prefix = str(output_settings.get("filename_prefix") or "Antimatter_LTX_Director_X").strip() or "Antimatter_LTX_Director_X"
        filename_prefix = f"{output_dir}/{Path(prefix).stem}".strip("/")
        container = str(output_settings.get("container") or "auto")
        codec = str(output_settings.get("codec") or "auto")
        _node_tuple(
            SaveVideo.execute(
                video=video,
                filename_prefix=filename_prefix,
                format=container,
                codec=codec,
            )
        )
        report["saved_video"] = {
            "status": "queued_to_comfy_output",
            "filename_prefix": filename_prefix,
            "format": container,
            "codec": codec,
            "frame_rate": frame_rate,
        }
    except Exception as exc:
        report.setdefault("warnings", []).append(f"SaveVideo skipped: {exc}")


def _run_ltx_integrated_pipeline(
    *,
    model: Any,
    positive: Any,
    video_latent: Any,
    audio_latent: Any,
    guide_data: Any,
    frame_rate: float,
    video_vae: Any | None,
    audio_vae: Any | None,
    combined_audio: Any | None,
    editor_settings: dict[str, Any],
    pro_values: dict[str, Any],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "antimatter-ltx-director-x-one-node-pipeline-v1",
        "status": "skipped",
        "warnings": [],
        "stages": [],
    }
    outputs = {
        "stage1_video_latent": video_latent,
        "stage1_audio_latent": audio_latent,
        "stage2_video_latent": video_latent,
        "stage2_audio_latent": audio_latent,
        "live_preview_frames": None,
        "final_frames": None,
        "final_audio": combined_audio,
        "live_preview_stage1": None,
        "final_video_stage2": None,
        "report": report,
    }
    if video_vae is None:
        report["status"] = "missing_video_vae"
        report["warnings"].append("Connect video_vae to run Stage #1, Stage #2, latent upscale, decode, and CreateVideo inside the node.")
        return outputs

    try:
        nodes = _try_import_pipeline_nodes()
        generation = editor_settings.get("generation") if isinstance(editor_settings.get("generation"), dict) else {}
        paths = editor_settings.get("paths") if isinstance(editor_settings.get("paths"), dict) else {}
        output_settings = editor_settings.get("output") if isinstance(editor_settings.get("output"), dict) else {}
        two_stage_mode = bool(pro_values.get("two_stage_mode", generation.get("two_stage_mode", True)))
        stage_run_mode = str(pro_values.get("stage_run_mode") or generation.get("stage_run_mode") or "full_two_stage")
        if stage_run_mode not in STAGE_RUN_MODES:
            stage_run_mode = "full_two_stage"
        if not two_stage_mode and stage_run_mode == "full_two_stage":
            stage_run_mode = "single_stage"
        stage2_require_source = bool(
            pro_values.get("stage2_require_stage1_source", generation.get("stage2_require_stage1_source", True))
        )
        use_latest_stage1 = bool(
            pro_values.get("use_latest_stage1_result", generation.get("use_latest_stage1_result", True))
        )
        stage1_source_ready = bool(generation.get("stage1_source_ready", False))
        stage1_draft_scale = max(
            0.01,
            min(1.0, _as_float(pro_values.get("stage1_draft_scale", generation.get("stage1_draft_scale", 0.5)), 0.5)),
        )
        report["stage_policy"] = {
            "two_stage_mode": two_stage_mode,
            "stage_run_mode": stage_run_mode,
            "stage1_draft_scale": stage1_draft_scale,
            "stage2_require_stage1_source": stage2_require_source,
            "use_latest_stage1_result": use_latest_stage1,
            "stage1_source_ready": stage1_source_ready,
            "stage1_source": "latest_stage1_result" if stage1_source_ready else "generated_in_this_execution",
        }
        if stage_run_mode == "stage2_refine" and stage2_require_source and not stage1_source_ready:
            report["warnings"].append("Stage 1 result required before Stage 2 refinement.")

        stage1_steps = max(1, _as_int(pro_values.get("stage1_steps"), 8))
        stage1_denoise = max(0.0, min(1.0, _as_float(pro_values.get("stage1_denoise"), 1.0)))
        stage1_scale_by = max(0.01, _as_float(pro_values.get("stage1_guide_scale_by"), stage1_draft_scale))
        stage2_steps = max(1, _as_int(pro_values.get("stage2_steps"), 4))
        stage2_denoise = max(0.0, min(1.0, _as_float(pro_values.get("stage2_denoise"), 0.42)))
        stage2_scale_by = max(0.01, _as_float(pro_values.get("stage2_guide_scale_by"), 1.0))
        sampler_name = str(pro_values.get("pipeline_sampler") or "euler")
        scheduler_name = str(pro_values.get("pipeline_scheduler") or "linear_quadratic")
        noise_seed = _as_int(pro_values.get("pipeline_noise_seed"), 12)
        preview_rate = max(1, _as_int(pro_values.get("fast_preview_rate"), round(frame_rate) or 24))
        upscale_model_name = _find_latent_upscale_model_name(
            str(pro_values.get("latent_upscale_model_name") or paths.get("upscale_model") or DEFAULT_LTX_LATENT_UPSCALE_MODEL)
        )

        latent_upscale_model = _node_tuple(nodes["LatentUpscaleModelLoader"].execute(model_name=upscale_model_name))[0]
        model_for_sampling = _maybe_apply_sampling_preview_override(
            model,
            preview_rate,
            latent_upscale_model if generation.get("use_upscale_model", True) else None,
            video_vae,
            report,
        )

        negative = nodes["ConditioningZeroOut"]().zero_out(positive)[0]
        cond_positive, cond_negative = _node_tuple(
            nodes["LTXVConditioning"].execute(
                positive=positive,
                negative=negative,
                frame_rate=frame_rate,
            )
        )
        guide_positive, guide_negative, guided_video_latent = _node_tuple(
            nodes["LTXDirectorGuide"].execute(
                positive=cond_positive,
                negative=cond_negative,
                vae=video_vae,
                latent=video_latent,
                guide_data=guide_data,
                scale_by=stage1_scale_by,
                upscale_method="bicubic",
            )
        )
        stage1_av_latent = _node_tuple(
            nodes["LTXVConcatAVLatent"].execute(
                video_latent=guided_video_latent,
                audio_latent=audio_latent,
            )
        )[0]
        stage1_noise = _node_tuple(nodes["RandomNoise"].execute(noise_seed=noise_seed))[0]
        stage1_guider = _node_tuple(
            nodes["CFGGuider"].execute(
                model=model_for_sampling,
                positive=guide_positive,
                negative=guide_negative,
                cfg=1.0,
            )
        )[0]
        sampler = _node_tuple(nodes["KSamplerSelect"].execute(sampler_name=sampler_name))[0]
        stage1_sigmas = _node_tuple(
            nodes["BasicScheduler"].execute(
                model=model_for_sampling,
                scheduler=scheduler_name,
                steps=stage1_steps,
                denoise=stage1_denoise,
            )
        )[0]
        sampled_stage1 = _node_tuple(
            nodes["SamplerCustomAdvanced"].execute(
                noise=stage1_noise,
                guider=stage1_guider,
                sampler=sampler,
                sigmas=stage1_sigmas,
                latent_image=stage1_av_latent,
            )
        )[0]
        stage1_video_latent, stage1_audio_latent = _node_tuple(
            nodes["LTXVSeparateAVLatent"].execute(av_latent=sampled_stage1)
        )
        outputs["stage1_video_latent"] = stage1_video_latent
        outputs["stage1_audio_latent"] = stage1_audio_latent
        report["stages"].append(
            {
                "name": "Stage #1",
                "sampler": sampler_name,
                "scheduler": scheduler_name,
                "steps": stage1_steps,
                "denoise": stage1_denoise,
                "guide_scale_by": stage1_scale_by,
                "draft_scale": stage1_draft_scale,
            }
        )

        if stage_run_mode in {"stage1_only", "single_stage"}:
            if stage_run_mode == "single_stage":
                outputs["stage2_video_latent"] = stage1_video_latent
                outputs["stage2_audio_latent"] = stage1_audio_latent
            live_frames = nodes["VAEDecode"]().decode(vae=video_vae, samples=stage1_video_latent)[0]
            outputs["live_preview_frames"] = live_frames
            outputs["final_frames"] = live_frames if stage_run_mode == "single_stage" else None
            final_audio = combined_audio
            live_audio = combined_audio
            if audio_vae is not None:
                live_audio = _node_tuple(
                    nodes["LTXVAudioVAEDecode"].execute(
                        samples=stage1_audio_latent,
                        audio_vae=audio_vae,
                    )
                )[0]
                final_audio = live_audio
            outputs["final_audio"] = final_audio
            outputs["live_preview_stage1"] = _node_tuple(
                nodes["CreateVideo"].execute(images=live_frames, fps=frame_rate, audio=live_audio)
            )[0]
            if stage_run_mode == "single_stage":
                outputs["final_video_stage2"] = _node_tuple(
                    nodes["CreateVideo"].execute(images=live_frames, fps=frame_rate, audio=final_audio)
                )[0]
                if bool(pro_values.get("save_final_video", False)):
                    _save_video_best_effort(outputs["final_video_stage2"], output_settings, frame_rate, report)
            report["stages"].append(
                {
                    "name": "Decode",
                    "live_preview": True,
                    "final_stage": stage_run_mode == "single_stage",
                    "fps": frame_rate,
                }
            )
            report["status"] = "ok_single_stage" if stage_run_mode == "single_stage" else "ok_stage1_only"
            report["output_contract"] = "Stage #1 generated live_preview_stage1. Stage #2 was skipped by stage_run_mode."
            return outputs

        crop_positive, crop_negative, cropped_stage1_video = _node_tuple(
            nodes["LTXVCropGuides"].execute(
                positive=guide_positive,
                negative=guide_negative,
                latent=stage1_video_latent,
            )
        )
        upscaled_latent = _node_tuple(
            nodes["LTXVLatentUpsampler"].execute(
                samples=cropped_stage1_video,
                upscale_model=latent_upscale_model,
                vae=video_vae,
            )
        )[0]
        stage2_positive, stage2_negative, guided_upscaled_latent = _node_tuple(
            nodes["LTXDirectorGuide"].execute(
                positive=crop_positive,
                negative=crop_negative,
                vae=video_vae,
                latent=upscaled_latent,
                guide_data=guide_data,
                scale_by=stage2_scale_by,
                upscale_method="bicubic",
            )
        )
        stage2_av_latent = _node_tuple(
            nodes["LTXVConcatAVLatent"].execute(
                video_latent=guided_upscaled_latent,
                audio_latent=stage1_audio_latent,
            )
        )[0]
        stage2_guider = _node_tuple(
            nodes["CFGGuider"].execute(
                model=model_for_sampling,
                positive=stage2_positive,
                negative=stage2_negative,
                cfg=1.0,
            )
        )[0]
        stage2_sigmas = _node_tuple(
            nodes["BasicScheduler"].execute(
                model=model_for_sampling,
                scheduler=scheduler_name,
                steps=stage2_steps,
                denoise=stage2_denoise,
            )
        )[0]
        sampled_stage2 = _node_tuple(
            nodes["SamplerCustomAdvanced"].execute(
                noise=stage1_noise,
                guider=stage2_guider,
                sampler=sampler,
                sigmas=stage2_sigmas,
                latent_image=stage2_av_latent,
            )
        )[0]
        stage2_video_latent_uncropped, stage2_audio_latent = _node_tuple(
            nodes["LTXVSeparateAVLatent"].execute(av_latent=sampled_stage2)
        )
        _, _, stage2_video_latent = _node_tuple(
            nodes["LTXVCropGuides"].execute(
                positive=guide_positive,
                negative=guide_negative,
                latent=stage2_video_latent_uncropped,
            )
        )
        outputs["stage2_video_latent"] = stage2_video_latent
        outputs["stage2_audio_latent"] = stage2_audio_latent
        report["stages"].append(
            {
                "name": "Stage #2",
                "sampler": sampler_name,
                "scheduler": scheduler_name,
                "steps": stage2_steps,
                "denoise": stage2_denoise,
                "guide_scale_by": stage2_scale_by,
                "latent_upscale_model": upscale_model_name,
            }
        )

        live_frames = nodes["VAEDecode"]().decode(vae=video_vae, samples=stage1_video_latent)[0]
        final_frames = nodes["VAEDecode"]().decode(vae=video_vae, samples=stage2_video_latent)[0]
        outputs["live_preview_frames"] = live_frames
        outputs["final_frames"] = final_frames
        final_audio = combined_audio
        live_audio = combined_audio
        if audio_vae is not None:
            live_audio = _node_tuple(
                nodes["LTXVAudioVAEDecode"].execute(
                    samples=stage1_audio_latent,
                    audio_vae=audio_vae,
                )
            )[0]
            final_audio = _node_tuple(
                nodes["LTXVAudioVAEDecode"].execute(
                    samples=stage2_audio_latent,
                    audio_vae=audio_vae,
                )
            )[0]
        outputs["final_audio"] = final_audio
        outputs["live_preview_stage1"] = _node_tuple(
            nodes["CreateVideo"].execute(images=live_frames, fps=frame_rate, audio=live_audio)
        )[0]
        outputs["final_video_stage2"] = _node_tuple(
            nodes["CreateVideo"].execute(images=final_frames, fps=frame_rate, audio=final_audio)
        )[0]
        report["stages"].append({"name": "Decode", "live_preview": True, "final_stage": True, "fps": frame_rate})

        if bool(pro_values.get("save_final_video", False)):
            _save_video_best_effort(outputs["final_video_stage2"], output_settings, frame_rate, report)
        report["status"] = "ok"
        report["output_contract"] = "The node now emits live_preview_stage1 and final_video_stage2 VIDEO outputs. External Stage #1/#2/Decode subgraphs are no longer required when run_integrated_pipeline is enabled."
        return outputs
    except Exception as exc:
        report["status"] = "error"
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc(limit=6)
        return outputs


_LORA_FILE_CACHE: dict[str, tuple[Any, Any]] = {}


def _available_lora_names() -> list[str]:
    if folder_paths is None:
        return []
    try:
        return list(folder_paths.get_filename_list("loras"))
    except Exception:
        return []


def _find_lora_name(preferred: str, filename: str) -> str | None:
    names = _available_lora_names()
    normalized_preferred = (preferred or "").replace("\\", "/").lower()
    for name in names:
        if name.replace("\\", "/").lower() == normalized_preferred:
            return name
    filename_lower = (filename or "").lower()
    matches = [name for name in names if Path(name).name.lower() == filename_lower]
    if matches:
        return sorted(matches, key=lambda item: ("/LTX/" not in f"/{item.replace('\\', '/')}/", len(item)))[0]
    contains = [name for name in names if filename_lower and filename_lower in Path(name).name.lower()]
    return contains[0] if contains else None


def _load_lora_by_name(lora_name: str):
    if folder_paths is None or comfy is None:
        raise RuntimeError("ComfyUI folder_paths/comfy modules are not available.")
    lora_path = folder_paths.get_full_path_or_raise("loras", lora_name)
    if lora_path in _LORA_FILE_CACHE:
        return _LORA_FILE_CACHE[lora_path]
    lora, metadata = comfy.utils.load_torch_file(lora_path, safe_load=True, return_metadata=True)
    _LORA_FILE_CACHE[lora_path] = (lora, metadata)
    return lora, metadata


def _preset_lora_controls(preset: str) -> dict[str, tuple[bool, float]] | None:
    return PRO_LORA_PRESETS.get(preset)


def _lora_controls_from_json(raw: str) -> dict[str, dict[str, Any]]:
    data = _json_loads(raw, {"loras": []})
    controls = {}
    for item in data.get("loras") or []:
        if isinstance(item, dict) and item.get("id"):
            controls[str(item["id"])] = item
    return controls


def _camera_mode_to_lora_id(camera_mode: str) -> str | None:
    return CAMERA_LORA_MODE_MAP.get(str(camera_mode or "off"))


def _resolve_lora_stack(
    *,
    pro_lora_stack_json: str,
    pro_lora_preset: str,
    camera_mode: str,
    camera_lora_auto_enable: bool,
    widget_values: dict[str, Any],
) -> list[dict[str, Any]]:
    json_controls = _lora_controls_from_json(pro_lora_stack_json)
    preset = _preset_lora_controls(pro_lora_preset)
    stack = []
    normalized_camera_mode = str(camera_mode or "off")
    selected_camera_lora = _camera_mode_to_lora_id(normalized_camera_mode)
    camera_conflicts = [
        sid
        for sid in CAMERA_LORA_IDS
        if bool(json_controls.get(sid, {}).get("enabled", False))
    ]

    for spec in PRO_LORA_SPECS:
        sid = spec["id"]
        enabled = bool(spec["default_enabled"])
        strength = float(spec["default_strength"])

        enabled = bool(widget_values.get(f"{sid}_enabled", enabled))
        strength = _as_float(widget_values.get(f"{sid}_strength", strength), strength)

        if sid in json_controls:
            enabled = bool(json_controls[sid].get("enabled", enabled))
            strength = _as_float(json_controls[sid].get("strength", strength), strength)

        if preset and pro_lora_preset != "custom" and sid in preset:
            enabled, strength = preset[sid]

        if sid in CAMERA_LORA_IDS:
            enabled = sid == selected_camera_lora and normalized_camera_mode != "off"
            if enabled:
                strength = max(strength, float(spec["default_strength"]))

        if sid == "camera_control" and camera_lora_auto_enable and normalized_camera_mode != "off":
            enabled = True
            strength = max(strength, 0.75)
        elif sid == "camera_control" and normalized_camera_mode == "off":
            enabled = False

        lora_name = _find_lora_name(spec["preferred"], spec["filename"])
        stack.append(
            {
                **spec,
                "enabled": enabled,
                "strength": strength,
                "lora_name": lora_name,
                "found": bool(lora_name),
                "camera_selected": sid == selected_camera_lora,
                "camera_conflict_resolved": sid in camera_conflicts and sid != selected_camera_lora,
            }
        )

    return stack


def _apply_lora_stack(model, stack: list[dict[str, Any]], missing_lora_policy: str) -> tuple[Any, list[dict[str, Any]]]:
    patched = model
    report = []
    for item in stack:
        strength = _as_float(item.get("strength"), 0.0)
        if not item.get("enabled") or abs(strength) < 1e-8:
            report.append({**item, "status": "disabled"})
            continue
        lora_name = item.get("lora_name")
        if not lora_name:
            status = "missing"
            report.append({**item, "status": status})
            if missing_lora_policy == "error":
                raise FileNotFoundError(
                    f"Missing Pro LoRA '{item.get('filename')}'. Put it in ComfyUI/models/loras/LTX."
                )
            continue
        lora, metadata = _load_lora_by_name(lora_name)
        patched, _ = comfy.sd.load_lora_for_models(
            patched,
            None,
            lora,
            strength,
            0.0,
            lora_metadata=metadata,
        )
        report.append({**item, "status": "applied"})
    return patched, report


def _lora_group(lora_id: str) -> str:
    if lora_id == "distilled":
        return "core"
    if lora_id in {"union_control", "motion_track", "detailer", "pose_control"}:
        return "control"
    if lora_id == "lipdub":
        return "speech"
    if lora_id == "transition":
        return "transition"
    if lora_id == "camera_control" or lora_id in CAMERA_LORA_IDS:
        return "camera"
    return "advanced"


def _lora_runtime_state(item: dict[str, Any]) -> str:
    strength = _as_float(item.get("strength"), 0.0)
    if not item.get("found"):
        return "missing" if item.get("enabled") else "available_path_missing"
    if item.get("enabled") and abs(strength) > 1e-8:
        return "active"
    return "available"


def _active_lora_ids(stack: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("id"))
        for item in stack
        if item.get("enabled") and abs(_as_float(item.get("strength"), 0.0)) > 1e-8
    }


def _build_pro_validation_warnings(
    *,
    stack: list[dict[str, Any]],
    pro_values: dict[str, Any],
    editor_settings: dict[str, Any],
    timeline: dict[str, Any],
    camera_mode: str,
    camera_tracks_json: str,
    combined_audio: Any | None,
) -> list[str]:
    warnings: list[str] = []
    active_ids = _active_lora_ids(stack)
    generation = editor_settings.get("generation") if isinstance(editor_settings.get("generation"), dict) else {}
    stage_run_mode = str(pro_values.get("stage_run_mode") or generation.get("stage_run_mode") or "full_two_stage")
    stage2_require_source = bool(
        pro_values.get("stage2_require_stage1_source", generation.get("stage2_require_stage1_source", True))
    )
    stage1_source_ready = bool(generation.get("stage1_source_ready", False))
    has_track_data = bool(camera_tracks_json and camera_tracks_json != "[]")
    has_track_data = has_track_data or bool(timeline.get("motionTracks") or timeline.get("tracks") or timeline.get("trackingData"))
    has_audio = combined_audio is not None or bool(timeline.get("audioSegments"))

    if "motion_track" in active_ids and not has_track_data:
        warnings.append("Motion Track enabled, but no track input was detected.")
    if "lipdub" in active_ids and not has_audio:
        warnings.append("LipDub is enabled, but no dialogue/audio source is available.")
    if stage_run_mode == "stage2_refine" and stage2_require_source and not stage1_source_ready:
        warnings.append("Stage 1 result required before Stage 2 refinement.")
    if str(pro_values.get("pro_lora_preset", "")) == "max_control":
        warnings.append("Max Control is advanced. It enables several control LoRAs and should be used only when the shot has matching guide data.")
    if any(item.get("camera_conflict_resolved") for item in stack):
        warnings.append("Camera mode is single-select; disabled conflicting camera LoRAs from the stack.")
    if camera_mode == "off" and "camera_control" in active_ids:
        warnings.append("Camera Control is active while camera mode is off; switch to a camera mode or disable the camera LoRA.")
    return warnings


def _camera_value_at(keyframes: list[dict[str, Any]], t: float, key: str, default: float) -> float:
    if not keyframes:
        return default
    ordered = sorted(keyframes, key=lambda item: _as_float(item.get("time"), 0.0))
    if t <= _as_float(ordered[0].get("time"), 0.0):
        return _as_float(ordered[0].get(key), default)
    if t >= _as_float(ordered[-1].get("time"), 0.0):
        return _as_float(ordered[-1].get(key), default)
    for idx in range(len(ordered) - 1):
        a = ordered[idx]
        b = ordered[idx + 1]
        at = _as_float(a.get("time"), 0.0)
        bt = _as_float(b.get("time"), at)
        if at <= t <= bt:
            span = max(0.0001, bt - at)
            f = (t - at) / span
            f = f * f * (3 - 2 * f)
            return _as_float(a.get(key), default) + (_as_float(b.get(key), default) - _as_float(a.get(key), default)) * f
    return default


def _camera_control_with_mode(raw: str, mode: str) -> dict[str, Any]:
    camera = _json_loads(raw, DEFAULT_CAMERA_CONTROL)
    camera.setdefault("schema", "antimatter-ltx-director-x-pro-camera-v1")
    mode_aliases = {
        "push_in": "dolly_in",
        "truck": "dolly_right",
        "orbit": "custom",
        "handheld": "custom",
    }
    normalized_mode = mode_aliases.get(str(mode or camera.get("mode", "off")), str(mode or camera.get("mode", "off")))
    if normalized_mode not in CAMERA_MODES:
        normalized_mode = "off"
    camera["mode"] = normalized_mode

    presets = {
        "dolly_in": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 1.18, "truck": 0.0, "pedestal": 0.0, "dolly": 80.0},
        "dolly_out": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 0.92, "truck": 0.0, "pedestal": 0.0, "dolly": -80.0},
        "dolly_left": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 1.0, "truck": -90.0, "pedestal": 0.0, "dolly": 0.0},
        "dolly_right": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 1.0, "truck": 90.0, "pedestal": 0.0, "dolly": 0.0},
        "jib_up": {"yaw": 0.0, "pitch": -4.0, "roll": 0.0, "zoom": 1.0, "truck": 0.0, "pedestal": 90.0, "dolly": 0.0},
        "jib_down": {"yaw": 0.0, "pitch": 4.0, "roll": 0.0, "zoom": 1.0, "truck": 0.0, "pedestal": -90.0, "dolly": 0.0},
        "static": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "zoom": 1.0, "truck": 0.0, "pedestal": 0.0, "dolly": 0.0},
    }
    if camera["mode"] in presets and not camera.get("manualOverride"):
        start = deepcopy(DEFAULT_CAMERA_CONTROL["keyframes"][0])
        end = {**start, **presets[camera["mode"]], "time": 1.0}
        camera["keyframes"] = [start, end]
        camera.update(presets[camera["mode"]])

    keyframes = camera.get("keyframes")
    if not isinstance(keyframes, list) or not keyframes:
        keyframes = deepcopy(DEFAULT_CAMERA_CONTROL["keyframes"])
    camera["keyframes"] = keyframes
    return camera


def _camera_tracks_from_control(
    camera: dict[str, Any],
    width: int,
    height: int,
    num_frames: int,
    motion_pixels: float,
) -> str:
    width = max(16, _as_int(width, 1280))
    height = max(16, _as_int(height, 720))
    num_frames = max(2, _as_int(num_frames, 121))
    motion_pixels = max(0.0, _as_float(motion_pixels, 180.0))
    if camera.get("mode") == "off":
        return "[]"

    bases = [
        (width * 0.22, height * 0.22),
        (width * 0.78, height * 0.22),
        (width * 0.78, height * 0.78),
        (width * 0.22, height * 0.78),
        (width * 0.50, height * 0.50),
        (width * 0.50, height * 0.18),
        (width * 0.50, height * 0.82),
    ]
    tracks = [[] for _ in bases]
    cx = width * 0.5
    cy = height * 0.5
    keyframes = camera.get("keyframes") if isinstance(camera.get("keyframes"), list) else []

    for idx in range(num_frames):
        t = idx / max(1, num_frames - 1)
        yaw = _camera_value_at(keyframes, t, "yaw", _as_float(camera.get("yaw"), 0.0))
        pitch = _camera_value_at(keyframes, t, "pitch", _as_float(camera.get("pitch"), 0.0))
        roll = math.radians(_camera_value_at(keyframes, t, "roll", _as_float(camera.get("roll"), 0.0)))
        zoom = _camera_value_at(keyframes, t, "zoom", _as_float(camera.get("zoom"), 1.0))
        truck = _camera_value_at(keyframes, t, "truck", _as_float(camera.get("truck"), 0.0))
        pedestal = _camera_value_at(keyframes, t, "pedestal", _as_float(camera.get("pedestal"), 0.0))
        dolly = _camera_value_at(keyframes, t, "dolly", _as_float(camera.get("dolly"), 0.0))

        dx = (truck + yaw * 0.35) * motion_pixels / 100.0
        dy = (pedestal + pitch * 0.35) * motion_pixels / 100.0
        scale = max(0.05, zoom + dolly * 0.002)
        cos_r = math.cos(roll)
        sin_r = math.sin(roll)

        for track, (x0, y0) in zip(tracks, bases):
            rx = (x0 - cx) * scale
            ry = (y0 - cy) * scale
            x = cx + rx * cos_r - ry * sin_r + dx
            y = cy + rx * sin_r + ry * cos_r + dy
            track.append({"x": round(max(0, min(width - 1, x))), "y": round(max(0, min(height - 1, y)))})

    return json.dumps(tracks, ensure_ascii=False)


def _json_loads(raw: str | dict[str, Any] | None, fallback: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return deepcopy(raw)
    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = {}
    return parsed if isinstance(parsed, dict) else deepcopy(fallback)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+\n", "\n", str(value or "")).strip()


def _clean_agent_response(value: str) -> str:
    text = _clean_text(value)
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip().strip('"')


def _normalize_segment(seg: dict[str, Any], duration_frames: int, fallback_index: int) -> dict[str, Any]:
    out = deepcopy(seg) if isinstance(seg, dict) else {}
    out["id"] = str(out.get("id") or f"seg_{fallback_index + 1}")
    out["type"] = str(out.get("type") or "image")
    out["start"] = max(0, _as_int(out.get("start"), 0))
    out["length"] = max(1, _as_int(out.get("length"), duration_frames))
    out["prompt"] = _clean_text(out.get("prompt"))
    if "guideStrength" not in out:
        out["guideStrength"] = _as_float(out.get("strength"), 1.0)
    return out


def _normalize_audio_segment(seg: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    out = deepcopy(seg) if isinstance(seg, dict) else {}
    out["id"] = str(out.get("id") or f"aud_{fallback_index + 1}")
    out["type"] = "audio"
    out["start"] = max(0, _as_int(out.get("start"), 0))
    out["length"] = max(1, _as_int(out.get("length"), 1))
    out["trimStart"] = max(0, _as_int(out.get("trimStart"), 0))
    return out


def _normalize_timeline(timeline_data: str, duration_frames: int) -> dict[str, Any]:
    timeline = _json_loads(timeline_data, DEFAULT_TIMELINE)
    timeline.setdefault("schema", "antimatter-ltx-director-x-timeline-v1")
    timeline["segments"] = [
        _normalize_segment(seg, duration_frames, index)
        for index, seg in enumerate(timeline.get("segments") or [])
        if isinstance(seg, dict)
    ]
    timeline["audioSegments"] = [
        _normalize_audio_segment(seg, index)
        for index, seg in enumerate(timeline.get("audioSegments") or [])
        if isinstance(seg, dict)
    ]
    timeline["segments"].sort(key=lambda item: (item["start"], item["id"]))
    timeline["audioSegments"].sort(key=lambda item: (item["start"], item["id"]))
    timeline.setdefault("markers", [])
    timeline.setdefault("transitions", [])
    timeline.setdefault("editActions", [])

    if not timeline["segments"]:
        timeline["segments"].append(
            {
                "id": "generated_empty_timeline_fallback",
                "start": 0,
                "length": max(1, duration_frames),
                "type": "image",
                "prompt": "Cinematic image-to-video continuation with stable identity and coherent motion.",
                "guideStrength": 0.0,
            }
        )

    return timeline


def _selected_range(
    timeline: dict[str, Any],
    selected_segment_id: str,
    selection_start_frame: int,
    selection_end_frame: int,
    duration_frames: int,
) -> tuple[str, int, int, dict[str, Any]]:
    segments = timeline.get("segments") or []
    selected = None
    if selected_segment_id:
        selected = next((seg for seg in segments if str(seg.get("id")) == str(selected_segment_id)), None)
    if selected is None and segments:
        selected = segments[0]
        selected_segment_id = str(selected.get("id") or "")

    start = max(0, _as_int(selection_start_frame, -1))
    end = max(0, _as_int(selection_end_frame, -1))
    if end <= start and selected is not None:
        start = _as_int(selected.get("start"), 0)
        end = start + max(1, _as_int(selected.get("length"), duration_frames))

    start = max(0, min(duration_frames, start))
    end = max(start + 1, min(duration_frames, end if end > start else duration_frames))
    return selected_segment_id, start, end, selected or {}


def _build_prompt(
    *,
    agent_instructions: str,
    image_description: str,
    joy_caption_text: str,
    user_action: str,
    use_joycapture: bool,
    style_profile: str,
    shot_type: str,
    camera_motion: str,
    lens_mm: int,
    motion_intensity: float,
    continuity_lock: str,
    global_prompt: str,
    negative_prompt: str,
    prompt_detail: str,
) -> str:
    image_parts = []
    if image_description.strip():
        image_parts.append(f"Image description: {image_description.strip()}")
    if use_joycapture and joy_caption_text.strip():
        image_parts.append(f"JoyCaption read: {joy_caption_text.strip()}")

    action = user_action.strip() or "Animate the image into a coherent cinematic moment with clear subject motion."
    continuity = continuity_lock.replace("_", " ")
    detail_hint = {
        "balanced": "Use precise but compact descriptions.",
        "production": "Use detailed production language with shot continuity and screen direction.",
        "shot_by_shot": "Describe the action as a short sequence of beats.",
        "minimal": "Keep it concise while preserving all critical instructions.",
    }.get(prompt_detail, "Use precise but compact descriptions.")

    sections = [
        "[VISUAL]",
        global_prompt.strip() or "Maintain the same characters, environment, wardrobe, lighting, colors, and art direction from the source image.",
        *image_parts,
        "",
        "[ACTION]",
        action,
        "",
        "[CINEMATOGRAPHY]",
        f"{shot_type.replace('_', ' ')}. {camera_motion.replace('_', ' ')}. {int(lens_mm)}mm lens. Motion intensity {motion_intensity:.2f}.",
        f"Style profile: {style_profile.replace('_', ' ')}. Continuity lock: {continuity}.",
        "",
        "[CHARACTER MOTION]",
        "Preserve identity, anatomy, clothing, props, and spatial relationships. Use natural weight, timing, eye lines, and secondary motion.",
        "",
        "[SOUNDS]",
        "Keep sound cues consistent with the visible action and environment. Avoid adding sounds that contradict the shot.",
    ]

    if negative_prompt.strip():
        sections.extend(["", "[AVOID]", negative_prompt.strip()])
    if agent_instructions.strip():
        sections.extend(["", "[DIRECTOR NOTES]", agent_instructions.strip(), detail_hint])

    return "\n".join(part for part in sections if part is not None).strip()


def _build_agent_request(
    *,
    agent_instructions: str,
    image_description: str,
    joy_caption_text: str,
    user_action: str,
    use_joycapture: bool,
    style_profile: str,
    shot_type: str,
    camera_motion: str,
    lens_mm: int,
    motion_intensity: float,
    continuity_lock: str,
    global_prompt: str,
    negative_prompt: str,
    selected_start: int,
    selected_end: int,
    frame_rate: float,
    prompt_detail: str,
) -> str:
    seconds = f"{selected_start / max(frame_rate, 0.001):.3f}s-{selected_end / max(frame_rate, 0.001):.3f}s"
    joy_part = joy_caption_text.strip() if use_joycapture else "JoyCapture is disabled. Do not rely on JoyCaption."
    return f"""SYSTEM / AGENT INSTRUCTIONS
{agent_instructions.strip() or DEFAULT_AGENT_INSTRUCTIONS}

TASK
Create one final LTX image-to-video prompt for the selected timeline fragment.
Return only the final prompt. No markdown fence, no explanation.

TIMELINE SELECTION
Frames: {selected_start}-{selected_end}
Time: {seconds}

GLOBAL CONTINUITY
{global_prompt.strip() or "Preserve all identity, setting, lighting, wardrobe, and style details from the source image."}

IMAGE DESCRIPTION
{image_description.strip() or "No manual image description was provided."}

JOYCAPTURE
{joy_part or "No JoyCaption text was provided."}

USER ACTION
{user_action.strip() or "Animate the image into a coherent cinematic moment."}

DIRECTOR PARAMETERS
style_profile={style_profile}
shot_type={shot_type}
camera_motion={camera_motion}
lens_mm={int(lens_mm)}
motion_intensity={motion_intensity:.2f}
continuity_lock={continuity_lock}
prompt_detail={prompt_detail}

NEGATIVE / AVOID
{negative_prompt.strip() or "No extra negative prompt."}
""".strip()


def _apply_selected_prompt(
    timeline: dict[str, Any],
    selected_segment_id: str,
    selected_prompt: str,
    auto_apply_prompt: bool,
) -> None:
    if not auto_apply_prompt or not selected_prompt.strip():
        return
    segments = timeline.get("segments") or []
    target = next((seg for seg in segments if str(seg.get("id")) == str(selected_segment_id)), None)
    if target is None and segments:
        target = segments[0]
    if target is not None:
        target["prompt"] = selected_prompt.strip()
        target["promptGeneratedBy"] = "Antimatter Ltx Director X"


def _segment_prompt(seg: dict[str, Any], fallback_prompt: str) -> str:
    prompt = _clean_text(seg.get("prompt"))
    return prompt or fallback_prompt or "Cinematic image-to-video continuation with stable identity and coherent motion."


def _derive_director_fields(
    timeline: dict[str, Any],
    duration_frames: int,
    fallback_prompt: str,
) -> tuple[str, str, str]:
    segments = []
    for seg in timeline.get("segments") or []:
        start = _as_int(seg.get("start"), 0)
        length = max(1, _as_int(seg.get("length"), 1))
        if start >= duration_frames:
            continue
        clamped = deepcopy(seg)
        clamped["length"] = max(1, min(length, duration_frames - start))
        segments.append(clamped)

    if not segments:
        segments = [{"start": 0, "length": max(1, duration_frames), "prompt": fallback_prompt, "guideStrength": 0.0}]

    prompts = [_segment_prompt(seg, fallback_prompt) for seg in segments]
    lengths = [str(max(1, _as_int(seg.get("length"), duration_frames))) for seg in segments]
    strengths = [
        f"{_as_float(seg.get('guideStrength', seg.get('strength')), 1.0):.4g}"
        for seg in segments
    ]
    return " | ".join(prompts), ",".join(lengths), ",".join(strengths)


def _remap_timeline_to_range(
    timeline: dict[str, Any],
    start_frame: int,
    end_frame: int,
    context_padding_frames: int,
    duration_frames: int,
    fallback_prompt: str,
) -> tuple[dict[str, Any], int, int, int]:
    render_start = max(0, start_frame - max(0, context_padding_frames))
    render_end = min(duration_frames, end_frame + max(0, context_padding_frames))
    if render_end <= render_start:
        render_start, render_end = start_frame, min(duration_frames, start_frame + 1)
    render_len = max(1, render_end - render_start)

    scoped = deepcopy(timeline)
    scoped["sourceTimeline"] = {"start": render_start, "end": render_end}

    new_segments = []
    for seg in timeline.get("segments") or []:
        seg_start = _as_int(seg.get("start"), 0)
        seg_end = seg_start + max(1, _as_int(seg.get("length"), 1))
        overlap_start = max(seg_start, render_start)
        overlap_end = min(seg_end, render_end)
        if overlap_end <= overlap_start:
            continue
        new_seg = deepcopy(seg)
        new_seg["sourceStart"] = seg_start
        new_seg["start"] = overlap_start - render_start
        new_seg["length"] = overlap_end - overlap_start
        if not _clean_text(new_seg.get("prompt")):
            new_seg["prompt"] = fallback_prompt
        new_segments.append(new_seg)

    if not new_segments:
        new_segments.append(
            {
                "id": "retry_selection",
                "start": 0,
                "length": render_len,
                "type": "image",
                "prompt": fallback_prompt,
                "guideStrength": 1.0,
            }
        )

    new_audio_segments = []
    for seg in timeline.get("audioSegments") or []:
        seg_start = _as_int(seg.get("start"), 0)
        seg_len = max(1, _as_int(seg.get("length"), 1))
        seg_end = seg_start + seg_len
        overlap_start = max(seg_start, render_start)
        overlap_end = min(seg_end, render_end)
        if overlap_end <= overlap_start:
            continue
        new_seg = deepcopy(seg)
        trim_delta = max(0, overlap_start - seg_start)
        new_seg["sourceStart"] = seg_start
        new_seg["start"] = overlap_start - render_start
        new_seg["trimStart"] = _as_int(new_seg.get("trimStart"), 0) + trim_delta
        new_seg["length"] = overlap_end - overlap_start
        new_audio_segments.append(new_seg)

    scoped["segments"] = sorted(new_segments, key=lambda item: (item["start"], item["id"]))
    scoped["audioSegments"] = sorted(new_audio_segments, key=lambda item: (item["start"], item["id"]))
    scoped["selection"] = {"start": start_frame - render_start, "end": end_frame - render_start}
    return scoped, render_start, render_end, render_len


def _make_retry_payload(
    *,
    render_scope: str,
    selected_segment_id: str,
    selected_prompt: str,
    selected_start: int,
    selected_end: int,
    render_start: int,
    render_end: int,
    frame_rate: float,
    retry_count: int,
    retry_seed_offset: int,
    retry_strength: float,
    blend_handles_frames: int,
    context_padding_frames: int,
    negative_prompt: str,
) -> str:
    payload = {
        "schema": "antimatter-ltx-director-x-retry-v1",
        "mode": render_scope,
        "selected_segment_id": selected_segment_id,
        "selected_range": {
            "start_frame": selected_start,
            "end_frame": selected_end,
            "duration_frames": max(1, selected_end - selected_start),
            "start_seconds": selected_start / max(frame_rate, 0.001),
            "end_seconds": selected_end / max(frame_rate, 0.001),
        },
        "render_range": {
            "start_frame": render_start,
            "end_frame": render_end,
            "duration_frames": max(1, render_end - render_start),
        },
        "stitch": {
            "replace_start_frame": render_start,
            "replace_end_frame": render_end,
            "blend_handles_frames": max(0, blend_handles_frames),
            "context_padding_frames": max(0, context_padding_frames),
        },
        "retry": {
            "count": max(0, retry_count),
            "seed_offset": retry_seed_offset,
            "strength": retry_strength,
        },
        "prompt": selected_prompt,
        "negative_prompt": negative_prompt,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _make_edl(
    *,
    timeline: dict[str, Any],
    render_scope: str,
    frame_rate: float,
    selected_segment_id: str,
    selected_start: int,
    selected_end: int,
    render_start: int,
    render_end: int,
    timeline_edit_actions: str,
) -> str:
    try:
        actions = json.loads(timeline_edit_actions) if timeline_edit_actions else timeline.get("editActions", [])
    except Exception:
        actions = timeline.get("editActions", [])
    payload = {
        "schema": "antimatter-ltx-director-x-edl-v1",
        "frame_rate": frame_rate,
        "render_scope": render_scope,
        "selected_segment_id": selected_segment_id,
        "selected_range": {"start_frame": selected_start, "end_frame": selected_end},
        "render_range": {"start_frame": render_start, "end_frame": render_end},
        "segments": timeline.get("segments", []),
        "audio_segments": timeline.get("audioSegments", []),
        "transitions": timeline.get("transitions", []),
        "markers": timeline.get("markers", []),
        "actions": actions if isinstance(actions, list) else [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


class AntimatterLtxDirectorX(io.ComfyNode):
    """Professional LTX Director wrapper with timeline retry metadata and prompt-agent support."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="AntimatterLtxDirectorX",
            display_name="Antimatter Ltx Director X",
            category="AntiMatter/LTX",
            description=(
                "A professional LTX Director variant with selectable timeline fragments, "
                "retry-only render scope, JoyCaption-aware prompt-agent fields, audio lanes, "
                "and edit decision metadata."
            ),
            inputs=[
                io.Model.Input("model"),
                io.Clip.Input("clip"),
                io.Vae.Input("audio_vae", optional=True, tooltip="Optional audio VAE for LTX audio latents."),
                io.Latent.Input("optional_latent", optional=True, tooltip="Optional full-timeline latent. Ignored in retry-fragment mode."),
                io.String.Input("global_prompt", multiline=True, default="", tooltip="Whole-video continuity anchor."),
                io.Int.Input("duration_frames", default=120, min=1, max=20000, step=1, tooltip="Full timeline duration in frames."),
                io.Float.Input("duration_seconds", default=5.0, min=0.01, max=3600.0, step=0.01, advanced=True),
                io.String.Input("timeline_data", default=_default_timeline_json(), multiline=True, tooltip="Hidden timeline JSON managed by the X editor."),
                io.Combo.Input(
                    "render_scope",
                    options=["full_timeline", "selected_fragment_only"],
                    default="full_timeline",
                    tooltip="Use selected_fragment_only to regenerate only the selected timeline range.",
                ),
                io.String.Input("selected_segment_id", default="", advanced=True),
                io.Int.Input("selection_start_frame", default=0, min=0, max=20000, step=1, advanced=True),
                io.Int.Input("selection_end_frame", default=120, min=1, max=20000, step=1, advanced=True),
                io.String.Input("local_prompts", multiline=True, default="", advanced=True),
                io.String.Input("segment_lengths", default="", advanced=True),
                io.String.Input("guide_strength", default="", advanced=True),
                io.String.Input("timeline_edit_actions", default="[]", multiline=True, advanced=True),
                io.Float.Input("epsilon", default=0.001, min=0.0001, max=0.99, step=0.0001, advanced=True),
                io.Float.Input("frame_rate", default=24.0, min=1.0, max=240.0, step=1.0),
                io.Combo.Input("display_mode", options=["frames", "seconds"], default="seconds", advanced=True),
                io.Boolean.Input("use_custom_audio", default=False, tooltip="Use the timeline audio lane for audio latent generation."),
                io.String.Input("image_description", multiline=True, default="", tooltip="Manual image description or caption."),
                io.Boolean.Input("use_joycapture", default=True, tooltip="When off, JoyCaption text is ignored."),
                io.String.Input("joy_caption_text", multiline=True, default="", tooltip="Connect JoyCaption output here."),
                io.String.Input("user_action", multiline=True, default="", tooltip="Describe exactly what should happen in the selected shot."),
                io.String.Input("agent_instructions", multiline=True, default=DEFAULT_AGENT_INSTRUCTIONS),
                io.Boolean.Input("enable_prompt_agent", default=True, tooltip="Build and apply an agent prompt for the selected segment."),
                io.String.Input("agent_response", multiline=True, default="", tooltip="Optional final prompt from an external agent."),
                io.Boolean.Input("auto_apply_prompt_to_selected", default=True, tooltip="Apply generated/agent prompt to selected segment before encoding."),
                io.Combo.Input("prompt_detail", options=["balanced", "production", "shot_by_shot", "minimal"], default="production"),
                io.Combo.Input(
                    "style_profile",
                    options=["cinematic_3d", "anime_film", "live_action", "product_film", "music_video", "documentary", "custom"],
                    default="cinematic_3d",
                ),
                io.Combo.Input(
                    "shot_type",
                    options=["wide_establishing", "medium_shot", "close_up", "over_the_shoulder", "tracking_shot", "macro_detail", "custom"],
                    default="medium_shot",
                ),
                io.Combo.Input(
                    "camera_motion",
                    options=["locked_off", "slow_push_in", "slow_pull_back", "handheld_soft", "tracking_left", "tracking_right", "orbit", "crane", "custom"],
                    default="slow_push_in",
                ),
                io.Int.Input("lens_mm", default=35, min=8, max=200, step=1),
                io.Float.Input("motion_intensity", default=0.45, min=0.0, max=1.0, step=0.01),
                io.Combo.Input(
                    "continuity_lock",
                    options=["strict_identity", "strict_scene", "balanced", "loose", "experimental"],
                    default="strict_identity",
                ),
                io.String.Input("negative_prompt", multiline=True, default="warping, identity drift, extra limbs, broken hands, flicker, melting textures"),
                io.Int.Input("context_padding_frames", default=8, min=0, max=240, step=1, tooltip="Extra frames around selected retry range."),
                io.Int.Input("blend_handles_frames", default=6, min=0, max=120, step=1, tooltip="Suggested stitch crossfade handles."),
                io.Int.Input("retry_count", default=0, min=0, max=9999, step=1, tooltip="Incremented by the UI retry button."),
                io.Int.Input("retry_seed_offset", default=101, min=-1000000, max=1000000, step=1),
                io.Float.Input("retry_strength", default=0.78, min=0.0, max=1.0, step=0.01),
                io.Int.Input("custom_width", default=0, min=0, max=8192, step=1, advanced=True),
                io.Int.Input("custom_height", default=0, min=0, max=8192, step=1, advanced=True),
                io.Combo.Input(
                    "resize_method",
                    options=["maintain aspect ratio", "stretch to fit", "pad", "crop"],
                    default="maintain aspect ratio",
                    advanced=True,
                ),
                io.Int.Input("divisible_by", default=32, min=1, max=256, step=1, advanced=True),
                io.Int.Input("img_compression", default=18, min=0, max=100, step=1, advanced=True),
            ],
            outputs=[
                io.Model.Output(display_name="model"),
                io.Conditioning.Output(display_name="positive"),
                io.Latent.Output(display_name="video_latent"),
                io.Latent.Output(display_name="audio_latent"),
                GuideData.Output(display_name="guide_data"),
                io.Float.Output(display_name="frame_rate"),
                io.Audio.Output(display_name="combined_audio"),
                io.String.Output(display_name="timeline_json"),
                io.String.Output(display_name="selected_prompt"),
                io.String.Output(display_name="agent_prompt_request"),
                io.String.Output(display_name="retry_payload"),
                io.String.Output(display_name="edit_decision_list"),
                io.Int.Output(display_name="selected_start_frame"),
                io.Int.Output(display_name="selected_end_frame"),
                io.Int.Output(display_name="selected_duration_frames"),
            ],
        )

    @classmethod
    def execute(
        cls,
        model,
        clip,
        global_prompt,
        duration_frames,
        duration_seconds,
        timeline_data,
        render_scope,
        selected_segment_id,
        selection_start_frame,
        selection_end_frame,
        local_prompts,
        segment_lengths,
        guide_strength,
        timeline_edit_actions,
        epsilon=0.001,
        frame_rate=24.0,
        display_mode="seconds",
        use_custom_audio=False,
        image_description="",
        use_joycapture=True,
        joy_caption_text="",
        user_action="",
        agent_instructions=DEFAULT_AGENT_INSTRUCTIONS,
        enable_prompt_agent=True,
        agent_response="",
        auto_apply_prompt_to_selected=True,
        prompt_detail="production",
        style_profile="cinematic_3d",
        shot_type="medium_shot",
        camera_motion="slow_push_in",
        lens_mm=35,
        motion_intensity=0.45,
        continuity_lock="strict_identity",
        negative_prompt="",
        context_padding_frames=8,
        blend_handles_frames=6,
        retry_count=0,
        retry_seed_offset=101,
        retry_strength=0.78,
        custom_width=0,
        custom_height=0,
        resize_method="maintain aspect ratio",
        divisible_by=32,
        img_compression=18,
        audio_vae=None,
        optional_latent=None,
    ) -> io.NodeOutput:
        duration_frames = max(1, _as_int(duration_frames, 120))
        frame_rate = max(0.001, _as_float(frame_rate, 24.0))
        timeline = _normalize_timeline(timeline_data, duration_frames)

        selected_segment_id, selected_start, selected_end, selected_segment = _selected_range(
            timeline,
            selected_segment_id,
            selection_start_frame,
            selection_end_frame,
            duration_frames,
        )

        lens_mm_int = _as_int(lens_mm, 35)
        agent_request = _build_agent_request(
            agent_instructions=agent_instructions,
            image_description=image_description,
            joy_caption_text=joy_caption_text,
            user_action=user_action,
            use_joycapture=bool(use_joycapture),
            style_profile=style_profile,
            shot_type=shot_type,
            camera_motion=camera_motion,
            lens_mm=lens_mm_int,
            motion_intensity=_as_float(motion_intensity, 0.45),
            continuity_lock=continuity_lock,
            global_prompt=global_prompt,
            negative_prompt=negative_prompt,
            selected_start=selected_start,
            selected_end=selected_end,
            frame_rate=frame_rate,
            prompt_detail=prompt_detail,
        )
        selected_prompt = _clean_agent_response(agent_response) if _clean_text(agent_response) else ""
        if bool(enable_prompt_agent) and not selected_prompt:
            selected_prompt = _build_prompt(
                agent_instructions=agent_instructions,
                image_description=image_description,
                joy_caption_text=joy_caption_text,
                user_action=user_action,
                use_joycapture=bool(use_joycapture),
                style_profile=style_profile,
                shot_type=shot_type,
                camera_motion=camera_motion,
                lens_mm=lens_mm_int,
                motion_intensity=_as_float(motion_intensity, 0.45),
                continuity_lock=continuity_lock,
                global_prompt=global_prompt,
                negative_prompt=negative_prompt,
                prompt_detail=prompt_detail,
            )
        if not selected_prompt:
            selected_prompt = _segment_prompt(selected_segment, _clean_text(global_prompt))

        _apply_selected_prompt(
            timeline,
            selected_segment_id,
            selected_prompt,
            bool(enable_prompt_agent) and bool(auto_apply_prompt_to_selected),
        )

        render_start, render_end = 0, duration_frames
        scoped_timeline = timeline
        scoped_duration = duration_frames
        scoped_optional_latent = optional_latent

        if render_scope == "selected_fragment_only":
            scoped_timeline, render_start, render_end, scoped_duration = _remap_timeline_to_range(
                timeline,
                selected_start,
                selected_end,
                _as_int(context_padding_frames, 0),
                duration_frames,
                selected_prompt,
            )
            scoped_optional_latent = None

        scoped_timeline_json = json.dumps(scoped_timeline, ensure_ascii=False)
        derived_prompts, derived_lengths, derived_strengths = _derive_director_fields(
            scoped_timeline,
            scoped_duration,
            selected_prompt,
        )

        ltx_director = _load_wdc_ltx_director()
        base = ltx_director.LTXDirector.execute(
            model=model,
            clip=clip,
            global_prompt=global_prompt,
            duration_frames=scoped_duration,
            duration_seconds=scoped_duration / frame_rate,
            timeline_data=scoped_timeline_json,
            local_prompts=derived_prompts,
            segment_lengths=derived_lengths,
            guide_strength=derived_strengths,
            epsilon=_as_float(epsilon, 0.001),
            frame_rate=frame_rate,
            display_mode=display_mode,
            custom_width=_as_int(custom_width, 0),
            custom_height=_as_int(custom_height, 0),
            resize_method=resize_method,
            divisible_by=max(1, _as_int(divisible_by, 32)),
            img_compression=max(0, _as_int(img_compression, 18)),
            audio_vae=audio_vae,
            optional_latent=scoped_optional_latent,
            use_custom_audio=bool(use_custom_audio),
        )
        base_args = tuple(base.result or ())

        timeline["selectedSegmentId"] = selected_segment_id
        timeline["selection"] = {"start": selected_start, "end": selected_end}
        timeline_json = json.dumps(timeline, ensure_ascii=False, indent=2)
        retry_payload = _make_retry_payload(
            render_scope=render_scope,
            selected_segment_id=selected_segment_id,
            selected_prompt=selected_prompt,
            selected_start=selected_start,
            selected_end=selected_end,
            render_start=render_start,
            render_end=render_end,
            frame_rate=frame_rate,
            retry_count=_as_int(retry_count, 0),
            retry_seed_offset=_as_int(retry_seed_offset, 101),
            retry_strength=_as_float(retry_strength, 0.78),
            blend_handles_frames=_as_int(blend_handles_frames, 0),
            context_padding_frames=_as_int(context_padding_frames, 0),
            negative_prompt=negative_prompt,
        )
        edl = _make_edl(
            timeline=timeline,
            render_scope=render_scope,
            frame_rate=frame_rate,
            selected_segment_id=selected_segment_id,
            selected_start=selected_start,
            selected_end=selected_end,
            render_start=render_start,
            render_end=render_end,
            timeline_edit_actions=timeline_edit_actions,
        )

        return io.NodeOutput(
            *base_args,
            timeline_json,
            selected_prompt,
            agent_request,
            retry_payload,
            edl,
            int(selected_start),
            int(selected_end),
            int(max(1, selected_end - selected_start)),
        )


class AntimatterLtxDirectorXPro(io.ComfyNode):
    """Premium all-in-one LTX Director X with integrated LoRA and camera controls."""

    @classmethod
    def define_schema(cls):
        base = AntimatterLtxDirectorX.define_schema()
        return io.Schema(
            node_id="AntimatterLtxDirectorXPro",
            display_name="AntimatterLtxDirectorX Pro",
            category="AntiMatter/LTX Pro",
            description=(
                "Premium LTX Director X: professional timeline direction, integrated LTX 2.3 LoRA mixer, "
                "camera-control LoRA slot, visual camera controller metadata, retry fragments, prompt agent, "
                "and stitch-ready outputs in one sellable node."
            ),
            inputs=[
                *base.inputs,
                io.String.Input("pro_lora_stack_json", default=_default_lora_stack_json(), multiline=True, advanced=True),
                io.Combo.Input(
                    "pro_lora_preset",
                    options=["clean_default", "director_balanced", "camera_control", "motion_tracking", "lipdub", "transition", "max_control", "custom"],
                    default="clean_default",
                    tooltip="Professional LoRA mix preset. Custom keeps the visual mixer values.",
                ),
                io.Boolean.Input("distilled_enabled", default=True, advanced=True),
                io.Float.Input("distilled_strength", default=1.0, min=-2.0, max=2.0, step=0.01, advanced=True),
                io.Boolean.Input("union_control_enabled", default=False, advanced=True),
                io.Float.Input("union_control_strength", default=0.65, min=-2.0, max=2.0, step=0.01, advanced=True),
                io.Boolean.Input("motion_track_enabled", default=False, advanced=True),
                io.Float.Input("motion_track_strength", default=0.72, min=-2.0, max=2.0, step=0.01, advanced=True),
                io.Boolean.Input("lipdub_enabled", default=False, advanced=True),
                io.Float.Input("lipdub_strength", default=0.85, min=-2.0, max=2.0, step=0.01, advanced=True),
                io.Boolean.Input("transition_enabled", default=False, advanced=True),
                io.Float.Input("transition_strength", default=0.70, min=-2.0, max=2.0, step=0.01, advanced=True),
                io.Boolean.Input("camera_control_enabled", default=False, advanced=True),
                io.Float.Input("camera_control_strength", default=0.90, min=-2.0, max=2.0, step=0.01, advanced=True),
                io.Combo.Input("missing_lora_policy", options=["warn_and_skip", "error"], default="warn_and_skip", advanced=True),
                io.String.Input("camera_control_json", default=_default_camera_control_json(), multiline=True, advanced=True),
                io.Combo.Input("camera_mode", options=CAMERA_MODES, default="off"),
                io.Boolean.Input("camera_lora_auto_enable", default=True, tooltip="Enable the camera-control LoRA whenever camera mode is not off."),
                io.Int.Input("camera_width", default=1280, min=64, max=8192, step=8, advanced=True),
                io.Int.Input("camera_height", default=720, min=64, max=8192, step=8, advanced=True),
                io.Int.Input("camera_frame_count", default=0, min=0, max=20000, step=1, tooltip="0 uses selected fragment duration or full duration."),
                io.Float.Input("camera_motion_pixels", default=180.0, min=0.0, max=4096.0, step=1.0),
                io.String.Input("pro_editor_settings_json", default=_default_pro_editor_settings_json(), multiline=True, advanced=True),
                io.String.Input("final_video_preview_path", default="", multiline=False, advanced=True),
                io.Vae.Input("video_vae", optional=True, tooltip="Video VAE used by the integrated Stage #1, Stage #2, latent upscale, decode, and video output pipeline."),
                io.Boolean.Input("auto_load_models", default=False, tooltip="Load model, CLIP, audio VAE, and video VAE from Settings when inputs are not connected."),
                io.Boolean.Input("run_integrated_pipeline", default=False, tooltip="Run the whole Stage #1 -> Stage #2 -> Decode -> CreateVideo workflow inside this node."),
                io.Boolean.Input("two_stage_mode", default=True, tooltip="When enabled, Stage #1 drafts motion and Stage #2 refines the final render."),
                io.Combo.Input("stage_run_mode", options=STAGE_RUN_MODES, default="full_two_stage", tooltip="Choose which internal stage button/action should run."),
                io.Float.Input("stage1_draft_scale", default=0.5, min=0.05, max=1.0, step=0.01, advanced=True),
                io.Boolean.Input("stage2_require_stage1_source", default=True, advanced=True),
                io.Boolean.Input("use_latest_stage1_result", default=True, advanced=True),
                io.Boolean.Input("advanced_mode", default=False, advanced=True),
                io.Boolean.Input("save_final_video", default=False, tooltip="Best-effort internal SaveVideo call after final_video_stage2 is created."),
                io.Int.Input("pipeline_noise_seed", default=12, min=0, max=0xffffffffffffffff, control_after_generate=True, advanced=True),
                io.String.Input("latent_upscale_model_name", default=DEFAULT_LTX_LATENT_UPSCALE_MODEL, advanced=True),
                io.String.Input("pipeline_sampler", default="euler", advanced=True),
                io.String.Input("pipeline_scheduler", default="linear_quadratic", advanced=True),
                io.Int.Input("stage1_steps", default=8, min=1, max=10000, step=1, advanced=True),
                io.Float.Input("stage1_denoise", default=1.0, min=0.0, max=1.0, step=0.01, advanced=True),
                io.Float.Input("stage1_guide_scale_by", default=0.5, min=0.01, max=8.0, step=0.01, advanced=True),
                io.Int.Input("stage2_steps", default=4, min=1, max=10000, step=1, advanced=True),
                io.Float.Input("stage2_denoise", default=0.42, min=0.0, max=1.0, step=0.01, advanced=True),
                io.Float.Input("stage2_guide_scale_by", default=1.0, min=0.01, max=8.0, step=0.01, advanced=True),
                io.Int.Input("fast_preview_rate", default=24, min=1, max=60, step=1, advanced=True),
            ],
            outputs=[
                *base.outputs,
                io.String.Output(display_name="pro_lora_stack_json"),
                io.String.Output(display_name="pro_lora_report_json"),
                io.String.Output(display_name="camera_control_json"),
                io.String.Output(display_name="camera_tracks_json"),
                io.String.Output(display_name="pro_product_report_json"),
                io.Latent.Output(display_name="stage1_video_latent"),
                io.Latent.Output(display_name="stage1_audio_latent"),
                io.Latent.Output(display_name="stage2_video_latent"),
                io.Latent.Output(display_name="stage2_audio_latent"),
                io.Image.Output(display_name="live_preview_frames"),
                io.Image.Output(display_name="final_frames"),
                io.Audio.Output(display_name="final_audio"),
                io.Video.Output(display_name="live_preview_stage1"),
                io.Video.Output(display_name="final_video_stage2"),
                io.String.Output(display_name="one_node_pipeline_report_json"),
            ],
            search_aliases=["antimatter ltx pro", "ltx director pro", "ltx lora mixer", "ltx camera control"],
        )

    @classmethod
    def execute(cls, *args, **kwargs) -> io.NodeOutput:
        if args:
            input_ids = [item.id for item in cls.define_schema().inputs]
            for key, value in zip(input_ids, args):
                kwargs.setdefault(key, value)

        pro_keys = {
            "pro_lora_stack_json",
            "pro_lora_preset",
            "distilled_enabled",
            "distilled_strength",
            "union_control_enabled",
            "union_control_strength",
            "motion_track_enabled",
            "motion_track_strength",
            "lipdub_enabled",
            "lipdub_strength",
            "transition_enabled",
            "transition_strength",
            "camera_control_enabled",
            "camera_control_strength",
            "missing_lora_policy",
            "camera_control_json",
            "camera_mode",
            "camera_lora_auto_enable",
            "camera_width",
            "camera_height",
            "camera_frame_count",
            "camera_motion_pixels",
            "pro_editor_settings_json",
            "final_video_preview_path",
            "video_vae",
            "auto_load_models",
            "run_integrated_pipeline",
            "two_stage_mode",
            "stage_run_mode",
            "stage1_draft_scale",
            "stage2_require_stage1_source",
            "use_latest_stage1_result",
            "advanced_mode",
            "save_final_video",
            "pipeline_noise_seed",
            "latent_upscale_model_name",
            "pipeline_sampler",
            "pipeline_scheduler",
            "stage1_steps",
            "stage1_denoise",
            "stage1_guide_scale_by",
            "stage2_steps",
            "stage2_denoise",
            "stage2_guide_scale_by",
            "fast_preview_rate",
        }
        pro = {key: kwargs.pop(key) for key in list(kwargs.keys()) if key in pro_keys}
        editor_settings = _json_loads(str(pro.get("pro_editor_settings_json", "")), _json_loads(_default_pro_editor_settings_json(), {}))
        auto_loader_report: list[dict[str, Any]] = []
        if bool(pro.get("auto_load_models", False)):
            try:
                model, clip, audio_vae, video_vae, auto_loader_report = _auto_load_ltx_assets_from_settings(
                    editor_settings=editor_settings,
                    model=kwargs.get("model"),
                    clip=kwargs.get("clip"),
                    audio_vae=kwargs.get("audio_vae"),
                    video_vae=pro.get("video_vae"),
                )
                kwargs["model"] = model
                kwargs["clip"] = clip
                kwargs["audio_vae"] = audio_vae
                pro["video_vae"] = video_vae
            except Exception as exc:
                auto_loader_report.append({"status": "error", "error": str(exc)})
                raise RuntimeError(f"AntimatterLtxDirectorX auto-load failed: {exc}") from exc
        if kwargs.get("model") is None or kwargs.get("clip") is None:
            raise RuntimeError("Connect model and clip, or enable auto_load_models in the One Node settings.")

        camera_mode = str(pro.get("camera_mode", "off") or "off")
        stack = _resolve_lora_stack(
            pro_lora_stack_json=str(pro.get("pro_lora_stack_json", "")),
            pro_lora_preset=str(pro.get("pro_lora_preset", "clean_default")),
            camera_mode=camera_mode,
            camera_lora_auto_enable=bool(pro.get("camera_lora_auto_enable", True)),
            widget_values=pro,
        )
        patched_model, lora_report = _apply_lora_stack(
            kwargs["model"],
            stack,
            str(pro.get("missing_lora_policy", "warn_and_skip")),
        )
        kwargs["model"] = patched_model

        camera = _camera_control_with_mode(str(pro.get("camera_control_json", "")), camera_mode)
        duration_frames = max(1, _as_int(kwargs.get("duration_frames"), 120))
        selected_len = max(
            1,
            _as_int(kwargs.get("selection_end_frame"), duration_frames)
            - _as_int(kwargs.get("selection_start_frame"), 0),
        )
        camera_frames = _as_int(pro.get("camera_frame_count"), 0)
        if camera_frames <= 0:
            camera_frames = selected_len if kwargs.get("render_scope") == "selected_fragment_only" else duration_frames
        generation_settings = editor_settings.get("generation") if isinstance(editor_settings.get("generation"), dict) else {}
        stage_run_mode = str(pro.get("stage_run_mode") or generation_settings.get("stage_run_mode") or "full_two_stage")
        if stage_run_mode not in STAGE_RUN_MODES:
            stage_run_mode = "full_two_stage"
        two_stage_mode = bool(pro.get("two_stage_mode", generation_settings.get("two_stage_mode", True)))
        if not two_stage_mode and stage_run_mode == "full_two_stage":
            stage_run_mode = "single_stage"
            pro["stage_run_mode"] = stage_run_mode
        generation_settings["two_stage_mode"] = two_stage_mode
        generation_settings["stage_run_mode"] = stage_run_mode
        generation_settings["stage1_draft_scale"] = max(0.05, min(1.0, _as_float(pro.get("stage1_draft_scale"), 0.5)))
        generation_settings["stage2_require_stage1_source"] = bool(
            pro.get("stage2_require_stage1_source", generation_settings.get("stage2_require_stage1_source", True))
        )
        generation_settings["use_latest_stage1_result"] = bool(
            pro.get("use_latest_stage1_result", generation_settings.get("use_latest_stage1_result", True))
        )
        generation_settings["advanced_mode"] = bool(pro.get("advanced_mode", generation_settings.get("advanced_mode", False)))
        generation_settings["fast_preview_enabled"] = True
        generation_settings["use_upscale_model"] = True
        editor_settings["generation"] = generation_settings
        generation_width = _as_int(generation_settings.get("width"), 0)
        generation_height = _as_int(generation_settings.get("height"), 0)
        if generation_width > 0 and generation_height > 0:
            if _as_int(kwargs.get("custom_width"), 0) <= 0:
                kwargs["custom_width"] = generation_width
            if _as_int(kwargs.get("custom_height"), 0) <= 0:
                kwargs["custom_height"] = generation_height
        camera_tracks = _camera_tracks_from_control(
            camera,
            _as_int(pro.get("camera_width"), _as_int(kwargs.get("custom_width"), 1280) or 1280),
            _as_int(pro.get("camera_height"), _as_int(kwargs.get("custom_height"), 720) or 720),
            camera_frames,
            _as_float(pro.get("camera_motion_pixels"), 180.0),
        )
        final_video_preview_path = str(pro.get("final_video_preview_path", "") or "")
        if final_video_preview_path:
            editor_settings.setdefault("output", {})["final_video_path"] = final_video_preview_path

        base = AntimatterLtxDirectorX.execute(**kwargs)
        base_args = tuple(base.result or ())

        resolved_stack = {
            "schema": "antimatter-ltx-director-x-pro-loras-v1",
            "preset": pro.get("pro_lora_preset", "clean_default"),
            "loras": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "filename": item["filename"],
                    "preferred": item["preferred"],
                    "lora_name": item.get("lora_name"),
                    "found": bool(item.get("found")),
                    "enabled": bool(item.get("enabled")),
                    "strength": _as_float(item.get("strength"), 0.0),
                    "role": item.get("role", ""),
                    "group": _lora_group(str(item.get("id"))),
                    "state": _lora_runtime_state(item),
                    "available": bool(item.get("found")),
                    "selected": bool(item.get("enabled")),
                    "active": bool(item.get("enabled")) and abs(_as_float(item.get("strength"), 0.0)) > 1e-8,
                    "camera_selected": bool(item.get("camera_selected")),
                }
                for item in stack
            ],
        }
        timeline_payload = _json_loads(str(kwargs.get("timeline_data", "")), deepcopy(DEFAULT_TIMELINE))
        validation_warnings = _build_pro_validation_warnings(
            stack=stack,
            pro_values=pro,
            editor_settings=editor_settings,
            timeline=timeline_payload,
            camera_mode=camera_mode,
            camera_tracks_json=camera_tracks,
            combined_audio=base_args[6] if len(base_args) > 6 else None,
        )
        missing_warnings = [
            f"Missing {item.get('filename')}"
            for item in lora_report
            if item.get("status") == "missing"
        ]
        pro_report = {
            "schema": "antimatter-ltx-director-x-pro-report-v1",
            "product": "AntimatterLtxDirectorX Pro",
            "positioning": "premium all-in-one LTX 2.3 director, LoRA mixer, camera-control and retry workstation",
            "workflow": {
                "two_stage_mode": generation_settings.get("two_stage_mode", True),
                "stage_run_mode": generation_settings.get("stage_run_mode", "full_two_stage"),
                "stage1": "Draft Motion/Base Generation",
                "stage2": "Final Refine/Final Render",
            },
            "applied_loras": [item for item in lora_report if item.get("status") == "applied"],
            "missing_loras": [item for item in lora_report if item.get("status") == "missing"],
            "lora_states": resolved_stack["loras"],
            "camera": {
                "mode": camera.get("mode"),
                "camera_lora_active": any(
                    item.get("id") == "camera_control" and item.get("status") == "applied"
                    for item in lora_report
                ),
                "single_select_lora": _camera_mode_to_lora_id(str(camera.get("mode", "off"))),
                "tracks_frames": camera_frames,
                "tracks_format": "LTXVDrawTracks compatible list-of-point-lists JSON",
            },
            "editor_settings": editor_settings,
            "auto_loader": auto_loader_report,
            "generation": {
                "resolution_preset": generation_settings.get("resolution_preset", "ltx_hd_1280x720"),
                "width": _as_int(kwargs.get("custom_width"), generation_width or 1280),
                "height": _as_int(kwargs.get("custom_height"), generation_height or 720),
                "fast_preview_enabled": True,
                "fast_preview_scale": _as_float(generation_settings.get("fast_preview_scale"), 0.5),
                "use_upscale_model": True,
                "upscale_model": editor_settings.get("paths", {}).get("upscale_model", ""),
                "upscale_factor": _as_int(generation_settings.get("upscale_factor"), 2),
            },
            "validation": {
                "status": "warning" if validation_warnings or missing_warnings else "ok",
                "warnings": validation_warnings,
            },
            "warnings": missing_warnings + validation_warnings,
        }
        pipeline_outputs = _run_ltx_integrated_pipeline(
            model=base_args[0] if len(base_args) > 0 else kwargs.get("model"),
            positive=base_args[1] if len(base_args) > 1 else None,
            video_latent=base_args[2] if len(base_args) > 2 else None,
            audio_latent=base_args[3] if len(base_args) > 3 else None,
            guide_data=base_args[4] if len(base_args) > 4 else {},
            frame_rate=_as_float(base_args[5] if len(base_args) > 5 else kwargs.get("frame_rate"), 24.0),
            video_vae=pro.get("video_vae"),
            audio_vae=kwargs.get("audio_vae"),
            combined_audio=base_args[6] if len(base_args) > 6 else None,
            editor_settings=editor_settings,
            pro_values=pro,
        ) if bool(pro.get("run_integrated_pipeline", False)) else {
            "stage1_video_latent": base_args[2] if len(base_args) > 2 else None,
            "stage1_audio_latent": base_args[3] if len(base_args) > 3 else None,
            "stage2_video_latent": base_args[2] if len(base_args) > 2 else None,
            "stage2_audio_latent": base_args[3] if len(base_args) > 3 else None,
            "live_preview_frames": None,
            "final_frames": None,
            "final_audio": base_args[6] if len(base_args) > 6 else None,
            "live_preview_stage1": None,
            "final_video_stage2": None,
            "report": {
                "schema": "antimatter-ltx-director-x-one-node-pipeline-v1",
                "status": "disabled",
                "message": "Enable run_integrated_pipeline or use AntimatterLtxDirectorX One Node to run Stage #1, Stage #2, Decode, and CreateVideo inside the node.",
            },
        }
        pro_report["integrated_pipeline"] = pipeline_outputs.get("report", {})
        pipeline_warnings = pipeline_outputs.get("report", {}).get("warnings") if isinstance(pipeline_outputs.get("report"), dict) else []
        if pipeline_warnings:
            pro_report["warnings"].extend(str(item) for item in pipeline_warnings)
            pro_report["validation"]["status"] = "warning"

        return io.NodeOutput(
            *base_args,
            json.dumps(resolved_stack, ensure_ascii=False, indent=2),
            json.dumps(lora_report, ensure_ascii=False, indent=2),
            json.dumps(camera, ensure_ascii=False, indent=2),
            camera_tracks,
            json.dumps(pro_report, ensure_ascii=False, indent=2),
            pipeline_outputs.get("stage1_video_latent"),
            pipeline_outputs.get("stage1_audio_latent"),
            pipeline_outputs.get("stage2_video_latent"),
            pipeline_outputs.get("stage2_audio_latent"),
            pipeline_outputs.get("live_preview_frames"),
            pipeline_outputs.get("final_frames"),
            pipeline_outputs.get("final_audio"),
            pipeline_outputs.get("live_preview_stage1"),
            pipeline_outputs.get("final_video_stage2"),
            json.dumps(pipeline_outputs.get("report", {}), ensure_ascii=False, indent=2),
        )


class AntimatterLtxDirectorXOneNode(AntimatterLtxDirectorXPro):
    """Single-node edition that runs the full LTX Director workflow internally."""

    @classmethod
    def define_schema(cls):
        pro_schema = AntimatterLtxDirectorXPro.define_schema()
        inputs = []
        for item in pro_schema.inputs:
            item_id = getattr(item, "id", "")
            if item_id == "model":
                inputs.append(io.Model.Input("model", optional=True, tooltip="Optional. Leave empty to auto-load from Settings."))
            elif item_id == "clip":
                inputs.append(io.Clip.Input("clip", optional=True, tooltip="Optional. Leave empty to auto-load LTXV CLIP from Settings."))
            elif item_id == "audio_vae":
                inputs.append(io.Vae.Input("audio_vae", optional=True, tooltip="Optional. Leave empty to auto-load the LTX audio VAE from Settings."))
            elif item_id == "auto_load_models":
                inputs.append(
                    io.Boolean.Input(
                        "auto_load_models",
                        default=True,
                        tooltip="Load model, CLIP, audio VAE, and video VAE from Settings when inputs are not connected.",
                    )
                )
            elif item_id == "run_integrated_pipeline":
                inputs.append(
                    io.Boolean.Input(
                        "run_integrated_pipeline",
                        default=True,
                        tooltip="Run Stage #1, Stage #2, latent upscale, decode, and CreateVideo inside this one node.",
                    )
                )
            elif item_id == "save_final_video":
                inputs.append(
                    io.Boolean.Input(
                        "save_final_video",
                        default=False,
                        tooltip="Best-effort internal SaveVideo call after final_video_stage2 is created.",
                    )
                )
            else:
                inputs.append(item)
        return io.Schema(
            node_id="AntimatterLtxDirectorXOneNode",
            display_name="AntimatterLtxDirectorX One Node",
            category="AntiMatter/LTX Pro",
            description=(
                "One-node Antimatter LTX Director X: integrated prompt/timeline editor, LoRA rack, camera control, "
                "Stage #1, Stage #2 latent upscale, decode, CreateVideo, live preview, and final video outputs."
            ),
            inputs=inputs,
            outputs=pro_schema.outputs,
            search_aliases=[
                "antimatter ltx one node",
                "ltx director one node",
                "ltx all in one",
                "ltx workflow in one node",
            ],
        )


def _resize_image_batch(images: torch.Tensor, height: int, width: int) -> torch.Tensor:
    if images.shape[1] == height and images.shape[2] == width:
        return images
    nchw = images.movedim(-1, 1)
    resized = F.interpolate(nchw, size=(height, width), mode="bilinear", align_corners=False)
    return resized.movedim(1, -1).clamp(0.0, 1.0)


class AntimatterLtxFragmentStitchX(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="AntimatterLtxFragmentStitchX",
            display_name="Antimatter LTX Fragment Stitch X",
            category="AntiMatter/LTX",
            description="Replace or insert a regenerated frame batch into an original video frame batch.",
            inputs=[
                io.Image.Input("original_frames"),
                io.Image.Input("replacement_frames"),
                io.Int.Input("start_frame", default=0, min=0, max=200000, step=1),
                io.Int.Input("end_frame", default=1, min=1, max=200000, step=1),
                io.Int.Input("blend_frames", default=6, min=0, max=240, step=1),
                io.Combo.Input("mode", options=["replace_range", "insert_at_start", "append_after_range"], default="replace_range"),
                io.Float.Input("frame_rate", default=24.0, min=1.0, max=240.0, step=1.0),
            ],
            outputs=[
                io.Image.Output(display_name="stitched_frames"),
                io.String.Output(display_name="stitch_payload"),
                io.Int.Output(display_name="total_frames"),
            ],
        )

    @classmethod
    def execute(
        cls,
        original_frames,
        replacement_frames,
        start_frame,
        end_frame,
        blend_frames=6,
        mode="replace_range",
        frame_rate=24.0,
    ) -> io.NodeOutput:
        original = original_frames.detach().clone()
        replacement = replacement_frames.detach().clone()
        if original.ndim != 4 or replacement.ndim != 4:
            raise ValueError("Expected IMAGE batches with shape [frames, height, width, channels].")

        total = original.shape[0]
        start = max(0, min(total, _as_int(start_frame, 0)))
        end = max(start, min(total, _as_int(end_frame, start + replacement.shape[0])))
        replacement = _resize_image_batch(replacement, original.shape[1], original.shape[2])

        if mode == "insert_at_start":
            stitched = torch.cat([original[:start], replacement, original[start:]], dim=0)
            replace_end = start
        elif mode == "append_after_range":
            stitched = torch.cat([original[:end], replacement, original[end:]], dim=0)
            replace_end = end
        else:
            blend = max(0, min(_as_int(blend_frames, 0), replacement.shape[0], max(0, end - start)))
            blended = replacement
            if blend > 0 and start < total:
                head = original[start : min(start + blend, total)]
                count = min(head.shape[0], blended.shape[0], blend)
                if count > 0:
                    alpha = torch.linspace(1.0 / (count + 1), count / (count + 1), count, device=blended.device)
                    alpha = alpha.reshape(count, 1, 1, 1)
                    blended[:count] = head[:count] * (1 - alpha) + blended[:count] * alpha
            if blend > 0 and end <= total and end - blend >= start:
                tail_src = original[max(start, end - blend) : end]
                count = min(tail_src.shape[0], blended.shape[0], blend)
                if count > 0:
                    alpha = torch.linspace(count / (count + 1), 1.0 / (count + 1), count, device=blended.device)
                    alpha = alpha.reshape(count, 1, 1, 1)
                    blended[-count:] = tail_src[-count:] * (1 - alpha) + blended[-count:] * alpha
            stitched = torch.cat([original[:start], blended, original[end:]], dim=0)
            replace_end = end

        payload = {
            "schema": "antimatter-ltx-fragment-stitch-x-v1",
            "mode": mode,
            "start_frame": start,
            "end_frame": replace_end,
            "replacement_frames": int(replacement.shape[0]),
            "total_frames": int(stitched.shape[0]),
            "frame_rate": _as_float(frame_rate, 24.0),
        }
        return io.NodeOutput(stitched, json.dumps(payload, ensure_ascii=False, indent=2), int(stitched.shape[0]))


def _audio_waveform(audio: dict[str, Any]) -> tuple[torch.Tensor, int]:
    waveform = audio.get("waveform")
    if waveform is None:
        raise ValueError("AUDIO input has no waveform.")
    if waveform.ndim == 2:
        waveform = waveform.unsqueeze(0)
    if waveform.ndim != 3:
        raise ValueError(f"Expected AUDIO waveform [batch, channels, samples], got {tuple(waveform.shape)}.")
    sample_rate = int(audio.get("sample_rate") or audio.get("sampler_rate") or 44100)
    return waveform.detach().clone(), sample_rate


def _fade_audio(waveform: torch.Tensor, sample_rate: int, fade_ms: float) -> torch.Tensor:
    fade_samples = max(0, int(sample_rate * max(0.0, fade_ms) / 1000.0))
    fade_samples = min(fade_samples, waveform.shape[-1] // 2)
    if fade_samples <= 0:
        return waveform
    device = waveform.device
    fade_in = torch.linspace(0.0, 1.0, fade_samples, device=device).reshape(1, 1, -1)
    fade_out = torch.linspace(1.0, 0.0, fade_samples, device=device).reshape(1, 1, -1)
    waveform[..., :fade_samples] *= fade_in
    waveform[..., -fade_samples:] *= fade_out
    return waveform


class AntimatterLtxAudioTrackX(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="AntimatterLtxAudioTrackX",
            display_name="Antimatter LTX Audio Track X",
            category="AntiMatter/LTX",
            description="Extract, remove, or trim an AUDIO track by frame range for timeline retry workflows.",
            inputs=[
                io.Audio.Input("audio"),
                io.Int.Input("start_frame", default=0, min=0, max=200000, step=1),
                io.Int.Input("end_frame", default=120, min=1, max=200000, step=1),
                io.Float.Input("frame_rate", default=24.0, min=1.0, max=240.0, step=1.0),
                io.Combo.Input("mode", options=["extract_selection", "remove_selection", "keep_before", "keep_after"], default="extract_selection"),
                io.Float.Input("fade_ms", default=12.0, min=0.0, max=5000.0, step=1.0),
                io.Float.Input("gain_db", default=0.0, min=-60.0, max=24.0, step=0.1),
            ],
            outputs=[
                io.Audio.Output(display_name="audio"),
                io.String.Output(display_name="audio_payload"),
                io.Float.Output(display_name="duration_seconds"),
            ],
        )

    @classmethod
    def execute(
        cls,
        audio,
        start_frame,
        end_frame,
        frame_rate=24.0,
        mode="extract_selection",
        fade_ms=12.0,
        gain_db=0.0,
    ) -> io.NodeOutput:
        waveform, sample_rate = _audio_waveform(audio)
        fps = max(0.001, _as_float(frame_rate, 24.0))
        total_samples = waveform.shape[-1]
        start_sample = max(0, min(total_samples, int(_as_int(start_frame, 0) / fps * sample_rate)))
        end_sample = max(start_sample, min(total_samples, int(_as_int(end_frame, 1) / fps * sample_rate)))

        if mode == "remove_selection":
            out = torch.cat([waveform[..., :start_sample], waveform[..., end_sample:]], dim=-1)
        elif mode == "keep_before":
            out = waveform[..., :start_sample]
        elif mode == "keep_after":
            out = waveform[..., end_sample:]
        else:
            out = waveform[..., start_sample:end_sample]

        gain = 10.0 ** (_as_float(gain_db, 0.0) / 20.0)
        out = (out * gain).clamp(-1.0, 1.0)
        out = _fade_audio(out, sample_rate, _as_float(fade_ms, 0.0))
        duration = out.shape[-1] / sample_rate if sample_rate else 0.0
        payload = {
            "schema": "antimatter-ltx-audio-track-x-v1",
            "mode": mode,
            "start_frame": _as_int(start_frame, 0),
            "end_frame": _as_int(end_frame, 1),
            "start_sample": start_sample,
            "end_sample": end_sample,
            "sample_rate": sample_rate,
            "duration_seconds": duration,
        }
        return io.NodeOutput(
            {"waveform": out, "sample_rate": sample_rate},
            json.dumps(payload, ensure_ascii=False, indent=2),
            float(duration),
        )
