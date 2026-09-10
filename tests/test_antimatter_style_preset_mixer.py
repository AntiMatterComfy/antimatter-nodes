from pathlib import Path
import sys
import tempfile
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

import antimatter_style_preset_mixer as mixer_module
from antimatter_style_preset_mixer import AntiMatterStylePresetMixer


class StylePresetMixerTests(unittest.TestCase):
    def setUp(self):
        self._original_style_directory = mixer_module.STYLE_DIRECTORY
        self._temporary_directory = tempfile.TemporaryDirectory()
        mixer_module.STYLE_DIRECTORY = Path(self._temporary_directory.name)
        (mixer_module.STYLE_DIRECTORY / "poses.txt").write_text(
            "first pose\n# ignored comment\nsecond pose\n", encoding="utf-8"
        )

    def tearDown(self):
        mixer_module.STYLE_DIRECTORY = self._original_style_directory
        self._temporary_directory.cleanup()

    def _kwargs(self, **values):
        kwargs = {}
        for slot in range(8):
            suffix = "" if slot == 0 else f"_{slot}"
            kwargs[f"enabled{suffix}"] = False
            kwargs[f"style_file{suffix}"] = "none"
            kwargs[f"read_mode{suffix}"] = "random"
        kwargs.update(values)
        return kwargs

    def test_sequential_selection_combines_with_input_text(self):
        node = AntiMatterStylePresetMixer()
        kwargs = self._kwargs(enabled=True, style_file="poses.txt", read_mode="sequential")

        first_text, first_sources = node.mix(input_text="portrait", **kwargs)
        second_text, second_sources = node.mix(input_text="portrait", **kwargs)

        self.assertEqual(first_text, "portrait, first pose")
        self.assertEqual(second_text, "portrait, second pose")
        self.assertEqual(first_sources, "poses.txt")
        self.assertEqual(second_sources, "poses.txt")

    def test_paths_outside_the_node_style_folder_are_rejected(self):
        result = AntiMatterStylePresetMixer.VALIDATE_INPUTS(
            **self._kwargs(style_file="../Style_evo/styles/17_poses.txt")
        )
        self.assertIsInstance(result, str)

    def test_missing_or_disabled_slots_leave_input_text_unchanged(self):
        text, selected_files = AntiMatterStylePresetMixer().mix(
            input_text="portrait", **self._kwargs()
        )
        self.assertEqual(text, "portrait")
        self.assertEqual(selected_files, "")


if __name__ == "__main__":
    unittest.main()
