from pathlib import Path
import sys
import types
import unittest

import torch


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from anti_aspect_ratio_master import AntiAspectRatioMaster


class _ResizeUtils:
    @staticmethod
    def common_upscale(samples, width, height, upscale_method, crop):
        assert upscale_method in {"nearest-exact", "bilinear", "area", "bicubic", "lanczos"}
        assert crop == "disabled"
        return torch.nn.functional.interpolate(samples, size=(height, width), mode="nearest")


class AntiAspectRatioMasterTests(unittest.TestCase):
    def setUp(self):
        self._original_comfy = sys.modules.get("comfy")
        self._original_comfy_utils = sys.modules.get("comfy.utils")
        comfy = types.ModuleType("comfy")
        comfy.utils = _ResizeUtils()
        sys.modules["comfy"] = comfy
        sys.modules["comfy.utils"] = comfy.utils

    def tearDown(self):
        if self._original_comfy is None:
            sys.modules.pop("comfy", None)
        else:
            sys.modules["comfy"] = self._original_comfy
        if self._original_comfy_utils is None:
            sys.modules.pop("comfy.utils", None)
        else:
            sys.modules["comfy.utils"] = self._original_comfy_utils

    def test_signed_resize_preserves_aspect_ratio_and_updates_image_dimensions(self):
        image = torch.zeros((1, 100, 200, 3))
        result = AntiAspectRatioMaster().make(
            source="from_image",
            preset="832x1216",
            manual_width=0,
            manual_height=0,
            round_to=64,
            orientation="auto",
            batch_size=1,
            latent_channels=16,
            resize_image=True,
            resize_scale=-0.7,
            upscale_method="lanczos",
            image=image,
        )

        _, width, height, final_preset, _, resized_image = result
        self.assertEqual((width, height, final_preset), (140, 70, "140x70"))
        self.assertEqual(tuple(resized_image.shape), (1, 70, 140, 3))

    def test_negative_whole_factor_is_a_downscale_divisor(self):
        self.assertEqual(AntiAspectRatioMaster._resize_multiplier(-2), 0.5)
        self.assertEqual(AntiAspectRatioMaster._resize_multiplier(2), 2.0)

    def test_invalid_signed_factors_are_rejected(self):
        with self.assertRaises(ValueError):
            AntiAspectRatioMaster._resize_multiplier(0)
        with self.assertRaises(ValueError):
            AntiAspectRatioMaster._resize_multiplier(0.7)


if __name__ == "__main__":
    unittest.main()
