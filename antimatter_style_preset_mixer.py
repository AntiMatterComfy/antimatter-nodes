from __future__ import annotations

import random
from pathlib import Path
from typing import Any


STYLE_DIRECTORY = Path(__file__).resolve().parent / "styles" / "krea2_batch_wild"
NONE_FILE = "none"
STYLE_SLOT_COUNT = 8
READ_MODES = ["random", "random_no_repeat", "sequential", "reverse"]

# These defaults reproduce the eight exposed controls in KREA2_BATCH_WILD's
# former "New Subgraph". Every file lives inside this package, not Style_evo.
DEFAULT_SLOTS = (
    (False, "17_poses.txt", "random"),
    (False, "01_emotions_expressions.txt", "random"),
    (False, "03_nsfw_body_focus_anatomy.txt", "random"),
    (False, "14_undressing.txt", "random"),
    (False, "09_sexy_outfits_clubwear_latex_leather.txt", "random"),
    (True, "Flux/POSES/crawling.txt", "random"),
    (False, "Flux/2GIRLS/2GIRL_FINGERING.txt", "random"),
    (False, "13_hairy_pussy_details.txt", "random"),
)


def _field_name(base: str, slot: int) -> str:
    return base if slot == 0 else f"{base}_{slot}"


def _available_style_files() -> list[str]:
    if not STYLE_DIRECTORY.is_dir():
        return [NONE_FILE]
    files = sorted(
        path.relative_to(STYLE_DIRECTORY).as_posix()
        for path in STYLE_DIRECTORY.rglob("*.txt")
        if path.is_file()
    )
    return [NONE_FILE, *files]


def _style_path(relative_path: str) -> Path | None:
    candidate = str(relative_path or "").strip().replace("\\", "/")
    if not candidate or candidate == NONE_FILE:
        return None

    root = STYLE_DIRECTORY.resolve()
    path = (root / candidate).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.suffix.lower() == ".txt" else None


def _read_lines(relative_path: str) -> list[str]:
    path = _style_path(relative_path)
    if path is None or not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


class AntiMatterStylePresetMixer:
    """Mix text selected from up to eight editable bundled style files."""

    DESCRIPTION = (
        "Replaces the KREA2_BATCH_WILD style subgraph. Select up to eight editable "
        "preset text files from AntiMatter's own styles/krea2_batch_wild folder."
    )

    def __init__(self) -> None:
        self._sequential_positions: dict[str, int] = {}
        self._random_pools: dict[str, list[int]] = {}

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, dict[str, Any]]:
        files = _available_style_files()
        required: dict[str, Any] = {}
        for slot, (default_enabled, default_file, default_mode) in enumerate(DEFAULT_SLOTS):
            required[_field_name("enabled", slot)] = ("BOOLEAN", {"default": default_enabled})
            required[_field_name("style_file", slot)] = (
                files,
                {"default": default_file if default_file in files else NONE_FILE},
            )
            required[_field_name("read_mode", slot)] = (READ_MODES, {"default": default_mode})

        return {
            "required": required,
            "optional": {"input_text": ("STRING", {"forceInput": True})},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "selected_style_files")
    FUNCTION = "mix"
    CATEGORY = "AntiMatter/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> float:
        # A queued workflow must execute again so random and sequential modes
        # can select the next line even when no widget value changes.
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs: Any) -> bool | str:
        available = set(_available_style_files())
        for slot in range(STYLE_SLOT_COUNT):
            file_name = str(kwargs.get(_field_name("style_file", slot), NONE_FILE))
            if file_name not in available:
                return (
                    f"Unknown style file '{file_name}'. Add it under "
                    "styles/krea2_batch_wild and restart ComfyUI."
                )
        return True

    def mix(self, input_text: str = "", **kwargs: Any) -> tuple[str, str]:
        parts = [str(input_text or "").strip()]
        selected_files: list[str] = []

        for slot in range(STYLE_SLOT_COUNT):
            if not bool(kwargs.get(_field_name("enabled", slot), False)):
                continue

            file_name = str(kwargs.get(_field_name("style_file", slot), NONE_FILE))
            mode = str(kwargs.get(_field_name("read_mode", slot), "random")).lower()
            lines = _read_lines(file_name)
            if not lines:
                continue

            selected = self._select_line(slot, file_name, lines, mode)
            if selected:
                parts.append(selected)
                selected_files.append(file_name)

        text = ", ".join(part.strip().strip(",") for part in parts if part and part.strip().strip(","))
        return text, ", ".join(selected_files)

    def _select_line(self, slot: int, file_name: str, lines: list[str], mode: str) -> str:
        key = f"{slot}:{file_name}"
        if mode == "random_no_repeat":
            pool = self._random_pools.get(key, [])
            if not pool:
                pool = list(range(len(lines)))
                random.shuffle(pool)
            index = pool.pop()
            self._random_pools[key] = pool
            return lines[index]

        if mode == "random":
            return random.choice(lines)

        current = self._sequential_positions.get(key)
        if current is None:
            current = len(lines) - 1 if mode == "reverse" else 0
        index = current % len(lines)
        step = -1 if mode == "reverse" else 1
        self._sequential_positions[key] = (index + step) % len(lines)
        return lines[index]
