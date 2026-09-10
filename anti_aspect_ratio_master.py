from __future__ import annotations

import re

import torch


PRESETS = [
    "832x1216",
    "896x1152",
    "960x1344",
    "1024x1024",
    "1024x1536",
    "1152x896",
    "1152x1408",
    "1216x832",
    "1216x1664",
    "1344x768",
    "1408x1152",
    "1536x1024",
    "720x1280",
    "1080x1920",
    "800x1920",
    "480x832",
]

UPSCALE_METHODS = ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"]


def _parse_hw(preset: str) -> tuple[int, int]:
    match = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", preset)
    if not match:
        raise ValueError(f"Bad preset '{preset}'. Use 'WxH' like '832x1216'.")

    width, height = int(match.group(1)), int(match.group(2))
    return width, height


def _apply_orientation(width: int, height: int, mode: str) -> tuple[int, int]:
    mode = (mode or "auto").lower()
    if mode == "portrait" and width > height:
        width, height = height, width
    elif mode == "landscape" and height > width:
        width, height = height, width
    elif mode == "swap":
        width, height = height, width
    return width, height


class AntiAspectRatioMaster:
    """Create a latent resolution and optionally resize an input image proportionally."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source": (["from_preset", "from_manual", "from_image"], {"default": "from_preset"}),
                "preset": (PRESETS, {"default": "832x1216"}),
                "manual_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 16}),
                "manual_height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 16}),
                "round_to": ("INT", {"default": 64, "min": 1, "max": 256}),
                "orientation": (["auto", "portrait", "landscape", "swap"], {"default": "auto"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64}),
                "latent_channels": ("INT", {"default": 16, "min": 1, "max": 64}),
                "resize_image": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                "resize_scale": ("FLOAT", {"default": 1.0, "min": -8.0, "max": 8.0, "step": 0.01}),
                "upscale_method": (UPSCALE_METHODS, {"default": "lanczos"}),
            },
            "optional": {
                "image": ("IMAGE",),
                "downsample_factor": ("INT", {"default": 8, "min": 1, "max": 16}),
            },
        }

    RETURN_TYPES = ("LATENT", "INT", "INT", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("latent", "width", "height", "final_preset", "image_name", "resized_image")
    FUNCTION = "make"
    CATEGORY = "AntiMatter/Image"

    def make(
        self,
        source: str,
        preset: str,
        manual_width: int,
        manual_height: int,
        round_to: int,
        orientation: str,
        batch_size: int,
        latent_channels: int = 16,
        resize_image: bool = False,
        resize_scale: float = 1.0,
        upscale_method: str = "lanczos",
        image=None,
        downsample_factor: int = 8,
    ):
        image_name = ""
        resized_image = image
        resized_width = resized_height = None

        if resize_image:
            if image is None:
                raise ValueError("Connect an image before enabling resize_image.")

            scale = self._resize_multiplier(resize_scale)
            original_height = int(image.shape[1])
            original_width = int(image.shape[2])
            resized_width = max(1, round(original_width * scale))
            resized_height = max(1, round(original_height * scale))

            # This is the same resize backend and interpolation menu used by
            # ComfyUI's built-in Image Scale By node. Applying one multiplier
            # to both dimensions keeps the input aspect ratio intact.
            import comfy.utils

            samples = image.movedim(-1, 1)
            resized_image = comfy.utils.common_upscale(
                samples,
                resized_width,
                resized_height,
                upscale_method,
                "disabled",
            ).movedim(1, -1)

        if source == "from_image" and image is not None:
            height = int(image.shape[1])
            width = int(image.shape[2])
            if resize_image:
                # Do not round a resized image: independent width/height
                # rounding would alter the aspect ratio the resize preserves.
                width, height = resized_width, resized_height
            else:
                width = self._round_to(width, round_to)
                height = self._round_to(height, round_to)

            if hasattr(image, "filename") and image.filename:
                image_name = str(image.filename)
            elif hasattr(image, "metadata") and isinstance(image.metadata, dict):
                image_name = image.metadata.get("filename", "")

            if not image_name:
                image_name = "input_image"

        elif source == "from_manual" and manual_width > 0 and manual_height > 0:
            width = self._round_to(manual_width, round_to)
            height = self._round_to(manual_height, round_to)

        else:
            preset_width, preset_height = _parse_hw(preset)
            width = self._round_to(preset_width, round_to)
            height = self._round_to(preset_height, round_to)

        width, height = _apply_orientation(width, height, orientation)

        factor = max(1, int(downsample_factor))
        latent_height = max(1, height // factor)
        latent_width = max(1, width // factor)
        samples = torch.zeros(
            (batch_size, int(latent_channels), latent_height, latent_width),
            dtype=torch.float32,
            device="cpu",
        )
        latent = {"samples": samples}

        final_preset = f"{width}x{height}"

        return (latent, width, height, final_preset, image_name, resized_image)

    @staticmethod
    def _resize_multiplier(resize_scale: float) -> float:
        """Translate the signed UI factor into a positive image multiplier.

        A negative value is always a reduction.  Fractions are interpreted as
        the retained size (``-0.7`` means 70%); whole factors above one are
        interpreted as divisors (``-2`` means one half).  A positive factor is
        an enlargement and must be at least one (``+2`` means 200%).
        """
        value = float(resize_scale)
        if value == 0:
            raise ValueError("resize_scale cannot be 0. Use -0.7 for 70% or +2 for 200%.")

        magnitude = abs(value)
        if value < 0:
            return magnitude if magnitude <= 1 else 1 / magnitude
        if magnitude < 1:
            raise ValueError("A positive resize_scale must be at least +1. Use -0.7 to reduce to 70%.")
        return magnitude

    @staticmethod
    def _round_to(value: int, step: int) -> int:
        if step <= 1:
            return int(value)
        return max(step, int(round(int(value) / step) * step))
