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
    """Create an empty latent with quick aspect ratio and resolution switching."""

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
            },
            "optional": {
                "image": ("IMAGE",),
                "downsample_factor": ("INT", {"default": 8, "min": 1, "max": 16}),
            },
        }

    RETURN_TYPES = ("LATENT", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("latent", "width", "height", "final_preset", "image_name")
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
        image=None,
        downsample_factor: int = 8,
    ):
        image_name = ""

        if source == "from_image" and image is not None:
            height = int(image.shape[1])
            width = int(image.shape[2])
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

        return (latent, width, height, final_preset, image_name)

    @staticmethod
    def _round_to(value: int, step: int) -> int:
        if step <= 1:
            return int(value)
        return max(step, int(round(int(value) / step) * step))
