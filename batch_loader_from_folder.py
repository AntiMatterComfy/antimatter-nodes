import os
import time
import glob
import random
import uuid
from typing import List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageOps

import folder_paths


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")


def _resolve_folder(path: str) -> str:
    path = path.strip()
    if not path:
        path = ".uploading"
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(os.getcwd(), path))
    return path


def _scan_images(folder: str, recursive: bool) -> List[str]:
    if not os.path.isdir(folder):
        return []
    pattern = "**/*" if recursive else "*"
    files = glob.glob(os.path.join(folder, pattern), recursive=recursive)
    out = []
    for f in files:
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in IMAGE_EXTS:
            out.append(f)
    out.sort(key=lambda x: x.lower())
    return out


def _pil_to_comfy_tensor(img: Image.Image) -> torch.Tensor:
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.mode == "RGBA":
        img = img.convert("RGB")

    arr = np.asarray(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)  # [1,H,W,3]


def _title_from_path(path: str) -> str:
    # Base filename without extension, e.g. "cat.png" -> "cat"
    return os.path.splitext(os.path.basename(path))[0]


class BatchLoaderFromFolder:

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
        self._size_cache: dict[str, Tuple[int, int]] = {}


    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder":           ("STRING",  {"default": ".uploading"}),
                "mode":             (["random", "sequential", "batch_freeze"], {"default": "random"}),
                "batch_size":       ("INT",     {"default": 1,   "min": 1, "max": 64,  "step": 1}),
                "freeze_count":     ("INT",     {"default": 1,   "min": 1, "max": 999, "step": 1}),
                "seed":             ("INT",     {"default": 0,   "min": 0, "max": 0x7FFFFFFF}),
                "no_repeat_random": ("BOOLEAN", {"default": True}),
                "recursive":        ("BOOLEAN", {"default": False}),
                "reload":           ("BOOLEAN", {"default": False}),
                "reset":            ("BOOLEAN", {"default": False}),
                "skip_exact_mode":  (
                    ["disabled", "width or height", "width and height", "width only", "height only"],
                    {"default": "disabled"},
                ),
                "skip_exact_width": ("INT",     {"default": 0,   "min": 0, "max": 65535, "step": 1}),
                "skip_exact_height":("INT",     {"default": 0,   "min": 0, "max": 65535, "step": 1}),
                "move_processed_to_subfolder": (
                    "BOOLEAN",
                    {"default": False, "label_on": "move on", "label_off": "move off"},
                ),
                "processed_subfolder_name": ("STRING", {"default": "_processed"}),
                "resize_to_first":  ("BOOLEAN", {"default": True}),
                "show_preview":     ("BOOLEAN", {"default": True}),
                "preview_max":      ("INT",     {"default": 4,   "min": 1, "max": 12, "step": 1}),
            }
        }


    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("images", "filename", "format", "width", "height")
    FUNCTION = "load"
    CATEGORY = "AntiMatter/Image"
    OUTPUT_NODE = False


    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("inf")   # force re-execution on every queue


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
            self._files = _scan_images(folder_abs, recursive)
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
    ):
        processed_dir = self._processed_subfolder_path(folder_abs, processed_subfolder_name)
        if not processed_dir:
            return

        os.makedirs(processed_dir, exist_ok=True)

        updated_files: List[str] = []
        selected_set = set(selected_paths)
        for path in self._files:
            if path not in selected_set:
                updated_files.append(path)

        for src in selected_paths:
            if not os.path.isfile(src):
                continue

            base_name = os.path.basename(src)
            dst = os.path.join(processed_dir, base_name)

            if os.path.abspath(src) == os.path.abspath(dst):
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

        self._files = updated_files
        self._pool = []
        self._pool_cycle = 0
        self._pool_signature = None


    def _get_image_size(self, path: str) -> Optional[Tuple[int, int]]:
        cached = self._size_cache.get(path)
        if cached is not None:
            return cached

        try:
            with Image.open(path) as img:
                img = ImageOps.exif_transpose(img)
                size = img.size
        except Exception:
            return None

        self._size_cache[path] = size
        return size


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

        size = self._get_image_size(path)
        if size is None:
            return False

        width, height = size
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


    def _save_preview(self, images: List[Image.Image], max_count: int) -> dict:
        if not images:
            return {}

        temp_dir = folder_paths.get_temp_directory()
        os.makedirs(temp_dir, exist_ok=True)

        ui_images = []
        for img in images[:max(1, max_count)]:
            name = f"preview_{uuid.uuid4().hex[:12]}.png"
            path = os.path.join(temp_dir, name)
            img.save(path, "PNG")
            ui_images.append({
                "filename": name,
                "subfolder": "",
                "type": "temp"
            })

        return {"images": ui_images}


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
        resize_to_first: bool,
        show_preview: bool,
        preview_max: int,
    ) -> Tuple[torch.Tensor, str, str, int, int] | dict:

        self._ensure_files(folder, recursive, reload, reset)

        if not self._files:
            raise ValueError(f"No images found in folder: {self._folder}")

        candidate_files = self._get_candidate_files(
            self._folder,
            skip_exact_mode,
            skip_exact_width,
            skip_exact_height,
            processed_subfolder_name,
        )

        if not candidate_files:
            raise ValueError(
                "No images left after skip filters. "
                "Change filters or add more images."
            )

        if move_processed_to_subfolder and mode != "batch_freeze" and len(candidate_files) < batch_size:
            raise ValueError(
                f"Only {len(candidate_files)} eligible images left, but batch_size={batch_size}. "
                "Lower batch_size or add more images."
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
            raise ValueError("Failed to select any images")

        titles = [_title_from_path(p) for p in selected_paths]
        if not titles:
            title_out = ""
        elif len(set(titles)) == 1:
            title_out = titles[0]
        else:
            title_out = ", ".join(titles)

        exts = [os.path.splitext(p)[1].lower().lstrip(".") for p in selected_paths]
        exts = [e for e in exts if e]
        if not exts:
            format_out = ""
        elif len(set(exts)) == 1:
            format_out = exts[0]
        else:
            format_out = ", ".join(exts)

        tensors = []
        preview_images = []
        base_size = None

        for i, path in enumerate(selected_paths):
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)

            if img.mode == "RGBA":
                img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            if i == 0:
                base_size = img.size
            elif img.size != base_size:
                if resize_to_first:
                    img = img.resize(base_size, Image.LANCZOS)
                else:
                    raise ValueError(
                        f"Image size mismatch in batch: first={base_size}, current={img.size}. "
                        "Enable resize_to_first or use batch_size=1."
                    )

            if show_preview:
                preview_images.append(img.copy())

            tensors.append(_pil_to_comfy_tensor(img))

        batch = torch.cat(tensors, dim=0)
        width_out = int(batch.shape[2])
        height_out = int(batch.shape[1])

        if move_processed_to_subfolder:
            self._move_to_processed_subfolder(
                selected_paths,
                self._folder,
                processed_subfolder_name,
            )

        if show_preview and preview_images:
            ui = self._save_preview(preview_images, preview_max)
            return {"ui": ui, "result": (batch, title_out, format_out, width_out, height_out)}

        return (batch, title_out, format_out, width_out, height_out)


NODE_CLASS_MAPPINGS = {
    "Batch_Loader_From_Folder": BatchLoaderFromFolder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Batch_Loader_From_Folder": "Batch Loader from folder",
}
