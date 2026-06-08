import glob
import importlib
import math
import os
import random
import sys
import uuid
from typing import Any, List, Optional, Tuple

import numpy as np
from PIL import Image
import torch

import folder_paths


VIDEO_EXTS = (
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".wmv",
    ".flv",
    ".gif",
    ".3gp",
    ".ts",
    ".mts",
    ".m2ts",
)

VideoMeta = Tuple[int, int, float, int, float]


class MultiInput(str):
    def __new__(cls, string, allowed_types="*"):
        res = super().__new__(cls, string)
        res.allowed_types = allowed_types
        return res

    def __ne__(self, other):
        if self.allowed_types == "*" or other == "*":
            return False
        return other not in self.allowed_types


IMAGE_OR_LATENT = MultiInput("IMAGE", ["IMAGE", "LATENT"])
FLOAT_OR_INT = MultiInput("FLOAT", ["FLOAT", "INT"])


def _resolve_folder(path: str) -> str:
    path = path.strip()
    if not path:
        path = ".uploading"
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(os.getcwd(), path))
    return path


def _scan_videos(folder: str, recursive: bool) -> List[str]:
    if not os.path.isdir(folder):
        return []
    pattern = "**/*" if recursive else "*"
    files = glob.glob(os.path.join(folder, pattern), recursive=recursive)
    out = []
    for f in files:
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in VIDEO_EXTS:
            out.append(f)
    out.sort(key=lambda x: x.lower())
    return out


def _title_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _signature(path: str) -> Tuple[float, int]:
    try:
        stat = os.stat(path)
        return (stat.st_mtime, stat.st_size)
    except OSError:
        return (0.0, 0)


def _load_av():
    try:
        import av
    except Exception as exc:
        raise ImportError(
            "PyAV is required for Video_Batch_Loader metadata and previews. "
            "It is normally installed with ComfyUI video support."
        ) from exc
    return av


def _clear_conflicting_utils_module():
    utils_mod = sys.modules.get("utils")
    if utils_mod is None or hasattr(utils_mod, "__path__"):
        return

    module_file = os.path.abspath(getattr(utils_mod, "__file__", "") or "")
    comfy_utils_dir = os.path.abspath(os.path.join(os.path.dirname(folder_paths.__file__), "utils"))
    if module_file and not module_file.startswith(comfy_utils_dir):
        sys.modules.pop("utils", None)
        importlib.invalidate_caches()


def _clear_partial_vhs_modules():
    for module_name in ("videohelpersuite.load_video_nodes", "videohelpersuite.utils"):
        sys.modules.pop(module_name, None)


def _load_vhs_video_nodes():
    _clear_conflicting_utils_module()
    import utils.install_util  # noqa: F401
    try:
        import videohelpersuite.load_video_nodes as load_video_nodes
        return load_video_nodes
    except ModuleNotFoundError:
        pass
    except Exception:
        _clear_partial_vhs_modules()

    for custom_nodes_dir in folder_paths.get_folder_paths("custom_nodes"):
        for folder_name in ("comfyui-videohelpersuite", "ComfyUI-VideoHelperSuite", "VideoHelperSuite"):
            candidate = os.path.join(custom_nodes_dir, folder_name)
            if os.path.isdir(os.path.join(candidate, "videohelpersuite")) and candidate not in sys.path:
                sys.path.append(candidate)

    try:
        import videohelpersuite.load_video_nodes as load_video_nodes
        return load_video_nodes
    except Exception as exc:
        _clear_partial_vhs_modules()
        raise ImportError(
            "Video_Batch_Loader requires ComfyUI-VideoHelperSuite for FFmpeg video loading."
        ) from exc


def _get_vhs_load_formats():
    try:
        formats, config = _load_vhs_video_nodes().get_load_formats()
        config = dict(config)
        if "Wan" in formats:
            config["default"] = "Wan"
        return (formats, config)
    except Exception:
        return (
            ["None", "AnimateDiff", "Mochi", "LTXV", "Hunyuan", "Cosmos", "Wan"],
            {"default": "Wan"},
        )


def _target_size(width: int, height: int, custom_width: int, custom_height: int, downscale_ratio: int = 8) -> Tuple[int, int]:
    if downscale_ratio is None:
        downscale_ratio = 8
    if custom_width == 0 and custom_height == 0:
        pass
    elif custom_height == 0:
        height *= custom_width / width
        width = custom_width
    elif custom_width == 0:
        width *= custom_height / height
        height = custom_height
    else:
        width = custom_width
        height = custom_height
    width = max(downscale_ratio, int(width / downscale_ratio + 0.5) * downscale_ratio)
    height = max(downscale_ratio, int(height / downscale_ratio + 0.5) * downscale_ratio)
    return (width, height)


def _to_float_rate(rate: Any, default: float = 0.0) -> float:
    try:
        return float(rate)
    except Exception:
        return default


def _normalize_start_time_and_format(start_time: Any, format_name: str) -> Tuple[float, str]:
    try:
        return float(start_time), format_name
    except Exception:
        pass

    if isinstance(start_time, str) and start_time.strip():
        shifted_format = start_time.strip()
        return 0.0, shifted_format

    return 0.0, format_name


class VideoBatchLoader:

    def __init__(self):
        self._folder: Optional[str] = None
        self._recursive: Optional[bool] = None
        self._files: List[str] = []
        self._seq_index = 0
        self._freeze_left = 0
        self._frozen_selection: Optional[List[str]] = None
        self._random_step = 0
        self._pool: List[str] = []
        self._pool_cycle = 0
        self._pool_seed_last: Optional[int] = None
        self._pool_signature: Optional[Tuple[str, ...]] = None
        self._metadata_cache: dict[str, Tuple[Tuple[float, int], VideoMeta]] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder": ("STRING", {"default": ".uploading"}),
                "mode": (["random", "sequential", "batch_freeze"], {"default": "random"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64, "step": 1}),
                "freeze_count": ("INT", {"default": 1, "min": 1, "max": 999, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0x7FFFFFFF}),
                "no_repeat_random": ("BOOLEAN", {"default": True}),
                "recursive": ("BOOLEAN", {"default": False}),
                "reload": ("BOOLEAN", {"default": False}),
                "reset": ("BOOLEAN", {"default": False}),
                "skip_exact_mode": (
                    ["disabled", "width or height", "width and height", "width only", "height only"],
                    {"default": "disabled"},
                ),
                "skip_exact_width": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
                "skip_exact_height": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
                "move_processed_to_subfolder": (
                    "BOOLEAN",
                    {"default": False, "label_on": "move on", "label_off": "move off"},
                ),
                "processed_subfolder_name": ("STRING", {"default": "_processed"}),
                "force_rate": (FLOAT_OR_INT, {"default": 24, "min": 0, "max": 60, "step": 1, "disable": 0}),
                "custom_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1, "disable": 0}),
                "custom_height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1, "disable": 0}),
                "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": 9007199254740991, "step": 1, "disable": 0}),
                "start_time": ("STRING", {"default": "0"}),
            },
            "optional": {
                "input_video": ("VIDEO", {"forceInput": True, "display_name": "input video"}),
                "meta_batch": ("VHS_BatchManager",),
                "vae": ("VAE",),
                "format": _get_vhs_load_formats(),
            },
            "hidden": {
                "force_size": "STRING",
                "unique_id": "UNIQUE_ID",
            }
        }

    RETURN_TYPES = (
        IMAGE_OR_LATENT,
        "MASK",
        "AUDIO",
        "VHS_VIDEOINFO",
        "STRING",
        "STRING",
        "STRING",
        "INT",
        "INT",
        "FLOAT",
        "INT",
        "FLOAT",
        "INT",
    )
    RETURN_NAMES = (
        "IMAGE",
        "mask",
        "audio",
        "video_info",
        "video_path",
        "filename",
        "format",
        "width",
        "height",
        "fps",
        "frame_count",
        "duration",
        "batch_count",
    )
    OUTPUT_IS_LIST = (True, True, True, True, True, True, True, True, True, True, True, True, False)
    FUNCTION = "load"
    CATEGORY = "AntiMatter"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("inf")

    def _reset_runtime_state(self):
        self._seq_index = 0
        self._freeze_left = 0
        self._frozen_selection = None
        self._random_step = 0
        self._pool = []
        self._pool_cycle = 0
        self._pool_seed_last = None
        self._pool_signature = None

    def _ensure_files(self, folder: str, recursive: bool, reload: bool, reset: bool):
        folder_abs = _resolve_folder(folder)
        folder_changed = (self._folder != folder_abs) or (self._recursive != recursive)

        if reset or folder_changed:
            self._reset_runtime_state()

        if reload or folder_changed or not self._files:
            self._files = _scan_videos(folder_abs, recursive)
            self._pool = []
            self._pool_cycle = 0
            self._pool_signature = None

        self._folder = folder_abs
        self._recursive = recursive

    def _pool_refill_if_needed(self, seed: int, files: List[str]):
        if not self._pool:
            self._pool = list(files)
            rng = random.Random(seed + self._pool_cycle)
            rng.shuffle(self._pool)
            self._pool_cycle += 1

    def _choose_random_no_repeat(self, files: List[str], seed: int, n: int) -> List[str]:
        if not files:
            return []
        out = []
        while len(out) < n:
            self._pool_refill_if_needed(seed, files)
            take = min(n - len(out), len(self._pool))
            out.extend(self._pool[:take])
            self._pool = self._pool[take:]
        return out

    def _choose_random_with_repeats(self, files: List[str], seed: int, n: int) -> List[str]:
        if not files:
            return []
        rng = random.Random(seed + self._random_step)
        self._random_step += 1
        if n == 1:
            return [rng.choice(files)]
        if len(files) >= n:
            return rng.sample(files, n)
        return [rng.choice(files) for _ in range(n)]

    def _choose_random(self, files: List[str], seed: int, n: int, no_repeat: bool) -> List[str]:
        signature = tuple(files)
        if no_repeat and (
            self._pool_seed_last is None
            or self._pool_seed_last != seed
            or self._pool_signature != signature
        ):
            self._pool = []
            self._pool_cycle = 0
            self._pool_seed_last = seed
            self._pool_signature = signature

        if no_repeat:
            return self._choose_random_no_repeat(files, seed, n)
        return self._choose_random_with_repeats(files, seed, n)

    def _choose_sequential(self, files: List[str], n: int) -> List[str]:
        if not files:
            return []
        available = set(files)
        out = []
        total = len(self._files) if self._files else len(files)
        checked = 0
        while len(out) < n and checked < total:
            idx = self._seq_index % total
            candidate = self._files[idx] if self._files else files[idx % len(files)]
            self._seq_index += 1
            checked += 1
            if candidate in available:
                out.append(candidate)
        return out

    def _processed_subfolder_path(self, folder_abs: str, processed_subfolder_name: str) -> Optional[str]:
        subfolder = processed_subfolder_name.strip()
        if not subfolder:
            return None
        if os.path.isabs(subfolder):
            return subfolder
        return os.path.abspath(os.path.join(folder_abs, subfolder))

    def _is_in_processed_subfolder(
        self,
        path: str,
        folder_abs: str,
        processed_subfolder_name: str,
    ) -> bool:
        processed_dir = self._processed_subfolder_path(folder_abs, processed_subfolder_name)
        if not processed_dir:
            return False
        try:
            return os.path.commonpath((processed_dir, os.path.abspath(path))) == processed_dir
        except ValueError:
            return False

    def _move_to_processed_subfolder(
        self,
        selected_paths: List[str],
        folder_abs: str,
        processed_subfolder_name: str,
    ) -> dict[str, str]:
        processed_dir = self._processed_subfolder_path(folder_abs, processed_subfolder_name)
        if not processed_dir:
            return {}

        os.makedirs(processed_dir, exist_ok=True)

        selected_set = set(selected_paths)
        self._files = [path for path in self._files if path not in selected_set]

        moved_paths: dict[str, str] = {}
        for src in dict.fromkeys(selected_paths):
            if not os.path.isfile(src):
                continue

            base_name = os.path.basename(src)
            dst = os.path.join(processed_dir, base_name)

            if os.path.abspath(src) == os.path.abspath(dst):
                moved_paths[src] = src
                continue

            if os.path.exists(dst):
                name, ext = os.path.splitext(base_name)
                suffix = 1
                while True:
                    candidate = os.path.join(processed_dir, f"{name}_{suffix}{ext}")
                    if not os.path.exists(candidate):
                        dst = candidate
                        break
                    suffix += 1

            os.replace(src, dst)
            moved_paths[src] = dst

            cached = self._metadata_cache.pop(src, None)
            if cached is not None:
                self._metadata_cache[dst] = (_signature(dst), cached[1])

        self._pool = []
        self._pool_cycle = 0
        self._pool_signature = None
        return moved_paths

    def _probe_video_metadata(self, path: str) -> Optional[VideoMeta]:
        sig = _signature(path)
        cached = self._metadata_cache.get(path)
        if cached is not None and cached[0] == sig:
            return cached[1]

        try:
            av = _load_av()
            with av.open(path, mode="r") as container:
                stream = next((s for s in container.streams if s.type == "video"), None)
                if stream is None:
                    return None

                width = int(stream.width or 0)
                height = int(stream.height or 0)
                fps = float(stream.average_rate) if stream.average_rate else 0.0
                frame_count = int(stream.frames or 0)

                duration = 0.0
                if container.duration is not None:
                    duration = float(container.duration / av.time_base)
                elif getattr(stream, "duration", None) is not None and getattr(stream, "time_base", None) is not None:
                    duration = float(stream.duration * stream.time_base)

                if frame_count <= 0 and duration > 0 and fps > 0:
                    frame_count = int(round(duration * fps))
        except Exception:
            return None

        metadata = (width, height, fps, frame_count, duration)
        self._metadata_cache[path] = (sig, metadata)
        return metadata

    def _should_skip_exact(
        self,
        path: str,
        skip_exact_mode: str,
        skip_exact_width: int,
        skip_exact_height: int,
    ) -> bool:
        if skip_exact_mode == "disabled":
            return False
        if skip_exact_width <= 0 and skip_exact_height <= 0:
            return False

        metadata = self._probe_video_metadata(path)
        if metadata is None:
            return False

        width, height, _, _, _ = metadata
        width_match = skip_exact_width > 0 and width == skip_exact_width
        height_match = skip_exact_height > 0 and height == skip_exact_height

        if skip_exact_mode == "width and height":
            width_ok = width_match if skip_exact_width > 0 else True
            height_ok = height_match if skip_exact_height > 0 else True
            return width_ok and height_ok
        if skip_exact_mode == "width only":
            return width_match
        if skip_exact_mode == "height only":
            return height_match
        return width_match or height_match

    def _get_candidate_files(
        self,
        folder_abs: str,
        skip_exact_mode: str,
        skip_exact_width: int,
        skip_exact_height: int,
        processed_subfolder_name: str,
    ) -> List[str]:
        return [
            path
            for path in self._files
            if not self._is_in_processed_subfolder(path, folder_abs, processed_subfolder_name)
            if not self._should_skip_exact(path, skip_exact_mode, skip_exact_width, skip_exact_height)
        ]

    def _select_files(
        self,
        files: List[str],
        mode: str,
        batch_size: int,
        freeze_count: int,
        seed: int,
        no_repeat_random: bool,
    ) -> List[str]:
        if self._freeze_left > 0 and self._frozen_selection is not None:
            available = set(files)
            if all(path in available for path in self._frozen_selection):
                self._freeze_left -= 1
                return self._frozen_selection
            self._freeze_left = 0
            self._frozen_selection = None

        if mode == "random":
            selection = self._choose_random(files, seed, batch_size, no_repeat_random)
        elif mode == "sequential":
            selection = self._choose_sequential(files, batch_size)
        elif mode == "batch_freeze":
            one = self._choose_random(files, seed, 1, no_repeat_random) if files else []
            selection = one * batch_size if one else []
        else:
            selection = self._choose_random(files, seed, batch_size, no_repeat_random)

        self._frozen_selection = selection
        self._freeze_left = max(0, freeze_count - 1)
        return selection

    def _save_preview(self, video_paths: List[str], max_count: int) -> dict:
        if not video_paths:
            return {}

        temp_dir = folder_paths.get_temp_directory()
        os.makedirs(temp_dir, exist_ok=True)

        ui_images = []
        av = _load_av()
        for path in video_paths[:max(1, max_count)]:
            try:
                with av.open(path, mode="r") as container:
                    stream = next((s for s in container.streams if s.type == "video"), None)
                    if stream is None:
                        continue
                    frame = next(container.decode(stream), None)
                    if frame is None:
                        continue
                    arr = frame.to_ndarray(format="rgb24")
                    if frame.rotation != 0:
                        k = int(round(frame.rotation // 90))
                        arr = np.rot90(arr, k=k, axes=(0, 1)).copy()
                    img = Image.fromarray(arr)
            except Exception:
                continue

            name = f"video_preview_{uuid.uuid4().hex[:12]}.png"
            preview_path = os.path.join(temp_dir, name)
            img.save(preview_path, "PNG")
            ui_images.append({
                "filename": name,
                "subfolder": "",
                "type": "temp",
            })

        return {"images": ui_images} if ui_images else {}

    def _load_video_ffmpeg(
        self,
        path: str,
        force_rate: float,
        custom_width: int,
        custom_height: int,
        frame_load_cap: int,
        start_time: float,
        meta_batch: Any,
        vae: Any,
        format: str,
        unique_id: str,
    ):
        vhs = _load_vhs_video_nodes()
        image, _, audio, video_info = vhs.load_video(
            video=path,
            force_rate=force_rate,
            custom_width=custom_width,
            custom_height=custom_height,
            frame_load_cap=frame_load_cap,
            start_time=start_time,
            meta_batch=meta_batch,
            vae=vae,
            format=format,
            unique_id=unique_id,
            generator=vhs.ffmpeg_frame_generator,
        )

        if isinstance(image, dict):
            return image, None, audio, video_info
        if image.size(3) == 4:
            return image[:, :, :, :3], 1 - image[:, :, :, 3], audio, video_info
        return image, torch.zeros(image.size(0), 64, 64, device="cpu"), audio, video_info

    def _sample_input_frames(
        self,
        images: torch.Tensor,
        mask: Optional[torch.Tensor],
        source_fps: float,
        force_rate: float,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], float]:
        if source_fps <= 0:
            return images, mask, force_rate if force_rate > 0 else 1.0

        target_fps = force_rate if force_rate > 0 else source_fps
        if len(images) <= 1 or abs(target_fps - source_fps) < 1e-6:
            return images, mask, target_fps

        duration = len(images) / source_fps
        frame_count = max(1, int(math.ceil(duration * target_fps)))
        indices = torch.clamp(
            torch.floor(torch.arange(frame_count, dtype=torch.float64) * source_fps / target_fps).long(),
            min=0,
            max=len(images) - 1,
        )
        images = images.index_select(0, indices)
        if mask is not None:
            mask = mask.index_select(0, indices)
        return images, mask, target_fps

    def _resize_input_frames(
        self,
        images: torch.Tensor,
        mask: Optional[torch.Tensor],
        custom_width: int,
        custom_height: int,
        downscale_ratio: int,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        if custom_width == 0 and custom_height == 0:
            return images, mask

        from comfy.utils import common_upscale

        height = int(images.shape[1])
        width = int(images.shape[2])
        new_width, new_height = _target_size(width, height, custom_width, custom_height, downscale_ratio)
        if new_width == width and new_height == height:
            return images, mask

        image_channels = images.movedim(-1, 1)
        image_channels = common_upscale(image_channels, new_width, new_height, "lanczos", "center")
        images = image_channels.movedim(1, -1)

        if mask is not None:
            mask_channels = mask.unsqueeze(1)
            mask_channels = common_upscale(mask_channels, new_width, new_height, "lanczos", "center")
            mask = mask_channels.squeeze(1)

        return images, mask

    def _load_input_video(
        self,
        input_video: Any,
        force_rate: float,
        custom_width: int,
        custom_height: int,
        frame_load_cap: int,
        start_time: float,
        vae: Any,
    ):
        source_video = input_video
        if start_time > 0 and hasattr(input_video, "as_trimmed"):
            try:
                trimmed = input_video.as_trimmed(start_time=start_time, duration=0, strict_duration=False)
                if trimmed is not None:
                    source_video = trimmed
            except Exception:
                source_video = input_video

        components = source_video.get_components()
        images = components.images
        audio = components.audio

        if images is None or len(images) == 0:
            raise ValueError("input_video did not produce any frames")

        source_fps = _to_float_rate(getattr(components, "frame_rate", 0.0), 0.0)
        try:
            source_width, source_height = source_video.get_dimensions()
        except Exception:
            source_height = int(images.shape[1])
            source_width = int(images.shape[2])

        try:
            source_frame_count = int(source_video.get_frame_count())
        except Exception:
            source_frame_count = int(len(images))

        try:
            source_duration = float(source_video.get_duration())
        except Exception:
            source_duration = (source_frame_count / source_fps) if source_fps > 0 else 0.0

        mask = None
        alpha = getattr(components, "alpha", None)
        if alpha is not None and len(alpha) > 0:
            mask = 1 - alpha.squeeze(-1)
        elif images.shape[-1] == 4:
            mask = 1 - images[:, :, :, 3]
            images = images[:, :, :, :3]

        images, mask, loaded_fps = self._sample_input_frames(images, mask, source_fps, force_rate)

        if frame_load_cap > 0:
            images = images[:frame_load_cap]
            if mask is not None:
                mask = mask[:frame_load_cap]

        downscale_ratio = getattr(vae, "downscale_ratio", 8) if vae is not None else 8
        images, mask = self._resize_input_frames(
            images,
            mask,
            custom_width,
            custom_height,
            downscale_ratio,
        )

        if mask is None:
            mask = torch.zeros(images.size(0), 64, 64, device="cpu")

        loaded_width = int(images.shape[2])
        loaded_height = int(images.shape[1])
        loaded_frame_count = int(len(images))
        loaded_duration = loaded_frame_count / loaded_fps if loaded_fps > 0 else 0.0

        output_image = {"samples": vae.encode(images[:, :, :, :3])} if vae is not None else images[:, :, :, :3]
        video_info = {
            "source_fps": source_fps,
            "source_frame_count": source_frame_count,
            "source_duration": source_duration,
            "source_width": int(source_width),
            "source_height": int(source_height),
            "loaded_fps": loaded_fps,
            "loaded_frame_count": loaded_frame_count,
            "loaded_duration": loaded_duration,
            "loaded_width": loaded_width,
            "loaded_height": loaded_height,
        }

        return (
            [output_image],
            [mask],
            [audio],
            [video_info],
            [""],
            ["input_video"],
            ["input"],
            [int(source_width)],
            [int(source_height)],
            [source_fps],
            [source_frame_count],
            [source_duration],
            1,
        )

    def load(
        self,
        folder: str,
        mode: str,
        batch_size: int,
        freeze_count: int,
        seed: int,
        no_repeat_random: bool,
        recursive: bool,
        reload: bool,
        reset: bool,
        skip_exact_mode: str,
        skip_exact_width: int,
        skip_exact_height: int,
        move_processed_to_subfolder: bool,
        processed_subfolder_name: str,
        force_rate: float,
        custom_width: int,
        custom_height: int,
        frame_load_cap: int,
        start_time: Any,
        input_video=None,
        meta_batch=None,
        vae=None,
        format: str = "Wan",
        force_size: str = "",
        unique_id: str = "",
    ) -> Tuple[
        List[Any],
        List[Any],
        List[Any],
        List[dict],
        List[str],
        List[str],
        List[str],
        List[int],
        List[int],
        List[float],
        List[int],
        List[float],
        int,
    ]:

        start_time, format = _normalize_start_time_and_format(start_time, format)
        force_rate = _to_float_rate(force_rate, 0.0)

        if input_video is not None:
            return self._load_input_video(
                input_video=input_video,
                force_rate=force_rate,
                custom_width=custom_width,
                custom_height=custom_height,
                frame_load_cap=frame_load_cap,
                start_time=start_time,
                vae=vae,
            )

        self._ensure_files(folder, recursive, reload, reset)

        if not self._files:
            raise ValueError(f"No videos found in folder: {self._folder}")

        candidate_files = self._get_candidate_files(
            self._folder,
            skip_exact_mode,
            skip_exact_width,
            skip_exact_height,
            processed_subfolder_name,
        )

        if not candidate_files:
            raise ValueError(
                "No videos left after skip filters. "
                "Change filters or add more videos."
            )

        if move_processed_to_subfolder and mode != "batch_freeze" and len(candidate_files) < batch_size:
            raise ValueError(
                f"Only {len(candidate_files)} eligible videos left, but batch_size={batch_size}. "
                "Lower batch_size or add more videos."
            )

        selected_paths = self._select_files(
            candidate_files,
            mode,
            batch_size,
            freeze_count,
            seed,
            no_repeat_random,
        )

        if not selected_paths:
            raise ValueError("Failed to select any videos")

        if move_processed_to_subfolder:
            moved_paths = self._move_to_processed_subfolder(
                selected_paths,
                self._folder,
                processed_subfolder_name,
            )
            selected_paths = [moved_paths.get(path, path) for path in selected_paths]

        images = []
        masks = []
        audios = []
        video_infos = []
        metadata = []

        for i, path in enumerate(selected_paths):
            item_unique_id = f"{unique_id}_{i}" if unique_id else str(i)
            image, mask, audio, video_info = self._load_video_ffmpeg(
                path=path,
                force_rate=force_rate,
                custom_width=custom_width,
                custom_height=custom_height,
                frame_load_cap=frame_load_cap,
                start_time=start_time,
                meta_batch=meta_batch,
                vae=vae,
                format=format,
                unique_id=item_unique_id,
            )
            images.append(image)
            masks.append(mask)
            audios.append(audio)
            video_infos.append(video_info)

            meta = (
                int(video_info.get("source_width", 0)),
                int(video_info.get("source_height", 0)),
                float(video_info.get("source_fps", 0.0)),
                int(video_info.get("source_frame_count", 0)),
                float(video_info.get("source_duration", 0.0)),
            )
            if meta[0] <= 0 or meta[1] <= 0:
                probed = self._probe_video_metadata(path)
                if probed is None:
                    raise ValueError(f"Could not read video metadata: {path}")
                meta = probed
            metadata.append(meta)

        video_paths = [os.path.abspath(path) for path in selected_paths]
        filenames = [_title_from_path(path) for path in selected_paths]
        formats = [os.path.splitext(path)[1].lower().lstrip(".") for path in selected_paths]
        widths = [m[0] for m in metadata]
        heights = [m[1] for m in metadata]
        fps_values = [m[2] for m in metadata]
        frame_counts = [m[3] for m in metadata]
        durations = [m[4] for m in metadata]

        return (
            images,
            masks,
            audios,
            video_infos,
            video_paths,
            filenames,
            formats,
            widths,
            heights,
            fps_values,
            frame_counts,
            durations,
            len(selected_paths),
        )


NODE_CLASS_MAPPINGS = {
    "Antimetter_Video_Batch_Loader": VideoBatchLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Antimetter_Video_Batch_Loader": "Video_Batch_Loader",
}
