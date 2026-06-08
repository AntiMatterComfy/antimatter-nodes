import datetime
import json
import os
import re
import shutil
import subprocess
import uuid
from typing import Any, Iterable, Tuple

import folder_paths
import numpy as np
import torch


ENCODE_ARGS = ("utf-8", "backslashreplace")


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


def _find_ffmpeg() -> str:
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg = get_ffmpeg_exe()
        if ffmpeg and os.path.isfile(ffmpeg):
            return ffmpeg
    except Exception:
        pass

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    raise ProcessLookupError(
        "ffmpeg is required to save video. Install imageio-ffmpeg or add ffmpeg to PATH."
    )


def _resolve_output_folder(path: str) -> str:
    path = (path or "").strip()
    if not path:
        raise ValueError("output_folder cannot be empty")
    path = os.path.expanduser(os.path.expandvars(path))
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    return path


def _split_prefix(output_folder: str, filename_prefix: str) -> Tuple[str, str]:
    prefix = (filename_prefix or "ComfyUI").strip().replace("\\", os.sep).replace("/", os.sep)
    if not prefix:
        prefix = "ComfyUI"

    if os.path.isabs(prefix):
        target_folder = os.path.dirname(prefix)
        base = os.path.basename(prefix)
    else:
        target_folder = os.path.join(output_folder, os.path.dirname(prefix))
        base = os.path.basename(prefix)

    if not base:
        base = "ComfyUI"

    os.makedirs(target_folder, exist_ok=True)
    return target_folder, base


def _next_counter(folder: str, filename: str, extension: str) -> int:
    matcher = re.compile(rf"{re.escape(filename)}_(\d+)(?:-audio)?\.{re.escape(extension)}$", re.IGNORECASE)
    max_counter = 0
    if os.path.isdir(folder):
        for existing_file in os.listdir(folder):
            match = matcher.fullmatch(existing_file)
            if match:
                max_counter = max(max_counter, int(match.group(1)))
    return max_counter + 1


def _tensor_to_bytes(frame: torch.Tensor) -> bytes:
    frame = frame.detach().cpu()
    if frame.shape[-1] > 3:
        frame = frame[..., :3]
    arr = frame.numpy() * 255.0 + 0.5
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return arr.tobytes()


def _iter_frames(images: torch.Tensor, pingpong: bool, loop_count: int) -> Iterable[torch.Tensor]:
    frame_count = len(images)
    if frame_count <= 0:
        return

    indices = list(range(frame_count))
    if pingpong and frame_count > 2:
        indices += list(range(frame_count - 2, 0, -1))

    loops = max(1, int(loop_count) + 1)
    for _ in range(loops):
        for index in indices:
            yield images[index]


def _output_frame_count(images: torch.Tensor, pingpong: bool, loop_count: int) -> int:
    frame_count = len(images)
    if frame_count <= 0:
        return 0

    sequence_count = frame_count
    if pingpong and frame_count > 2:
        sequence_count += frame_count - 2

    return sequence_count * max(1, int(loop_count) + 1)


def _normalize_images(images: Any, vae: Any = None) -> torch.Tensor:
    if vae is not None and isinstance(images, dict):
        images = vae.decode(images["samples"])

    if isinstance(images, dict):
        raise ValueError("Latent input requires a connected VAE")

    if isinstance(images, list):
        tensors = []
        for item in images:
            if isinstance(item, dict):
                if vae is None:
                    raise ValueError("Latent list input requires a connected VAE")
                item = vae.decode(item["samples"])
            tensors.append(item)
        images = torch.cat(tensors, dim=0)

    if not isinstance(images, torch.Tensor):
        raise ValueError("images must be an IMAGE tensor or LATENT dict")

    if images.ndim == 3:
        images = images.unsqueeze(0)
    if images.ndim != 4:
        raise ValueError(f"Expected images with shape [frames, height, width, channels], got {tuple(images.shape)}")
    if images.shape[-1] < 3:
        raise ValueError("images must have at least 3 channels")
    if images.size(0) == 0:
        raise ValueError("No frames to save")

    return images


def _pad_to_even_dimensions(images: torch.Tensor) -> torch.Tensor:
    height = int(images.shape[1])
    width = int(images.shape[2])
    pad_width = width % 2
    pad_height = height % 2
    if pad_width == 0 and pad_height == 0:
        return images

    channels_first = images.movedim(-1, 1)
    padded = torch.nn.functional.pad(
        channels_first,
        (0, pad_width, 0, pad_height),
        mode="replicate",
    )
    return padded.movedim(1, -1)


def _audio_is_usable(audio: Any) -> bool:
    if not isinstance(audio, dict):
        return False

    waveform = audio.get("waveform")
    sample_rate = int(audio.get("sample_rate", 0) or 0)
    return waveform is not None and sample_rate > 0


def _make_temp_video_path(target_folder: str, filename: str, counter: int, extension: str) -> str:
    temp_name = f".{filename}_{counter:05}_{uuid.uuid4().hex[:8]}_noaudio.{extension}"
    return os.path.join(target_folder, temp_name)


def _copy_preview_to_temp(final_path: str, extension: str) -> dict:
    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)

    preview_name = f"antimatter_preview_{uuid.uuid4().hex[:12]}.{extension}"
    preview_path = os.path.join(temp_dir, preview_name)
    shutil.copy2(final_path, preview_path)

    return {
        "filename": preview_name,
        "subfolder": "",
        "type": "temp",
        "format": f"video/{extension}",
        "fullpath": final_path,
    }


class SaveVideoInFolder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": (IMAGE_OR_LATENT,),
                "output_folder": ("STRING", {"default": "E:/ComfyUI_Output"}),
                "filename_prefix": ("STRING", {"default": "Video"}),
                "frame_rate": (FLOAT_OR_INT, {"default": 24, "min": 1, "max": 240, "step": 1}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "format": (["video/h264-mp4", "video/h265-mp4", "video/webm"], {"default": "video/h264-mp4"}),
                "pix_fmt": (["yuv420p", "yuv420p10le"], {"default": "yuv420p"}),
                "crf": ("INT", {"default": 19, "min": 0, "max": 100, "step": 1}),
                "save_metadata": ("BOOLEAN", {"default": False}),
                "trim_to_audio": ("BOOLEAN", {"default": False}),
                "pingpong": ("BOOLEAN", {"default": False}),
                "show_preview": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "audio": ("AUDIO",),
                "vae": ("VAE",),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("file_path", "filename")
    OUTPUT_NODE = True
    FUNCTION = "save_video"
    CATEGORY = "AntiMatter"

    def _video_codec_args(self, format_name: str, pix_fmt: str, crf: int) -> Tuple[str, list[str], list[str]]:
        if format_name == "video/h264-mp4":
            return "mp4", ["-c:v", "libx264", "-pix_fmt", pix_fmt, "-crf", str(crf), "-movflags", "+faststart"], ["-c:a", "aac"]
        if format_name == "video/h265-mp4":
            return "mp4", ["-c:v", "libx265", "-pix_fmt", pix_fmt, "-crf", str(crf), "-movflags", "+faststart"], ["-c:a", "aac"]
        if format_name == "video/webm":
            return "webm", ["-c:v", "libvpx-vp9", "-pix_fmt", pix_fmt, "-crf", str(crf), "-b:v", "0"], ["-c:a", "libopus"]
        raise ValueError(f"Unsupported format: {format_name}")

    def _metadata_args(self, save_metadata: bool, prompt: Any, extra_pnginfo: Any) -> list[str]:
        if not save_metadata:
            return []

        metadata = {
            "CreationTime": datetime.datetime.now().isoformat(" ")[:19],
        }
        if prompt is not None:
            metadata["prompt"] = prompt
        if extra_pnginfo is not None:
            metadata.update(extra_pnginfo)

        return [
            "-metadata",
            "creation_time=now",
            "-metadata",
            f"comment={json.dumps(metadata, ensure_ascii=False)}",
        ]

    def _mux_audio(
        self,
        ffmpeg_path: str,
        video_path: str,
        audio: dict,
        extension: str,
        audio_args: list[str],
        frame_rate: float,
        frame_count: int,
        trim_to_audio: bool,
        output_path: str,
    ) -> str:
        waveform = audio.get("waveform")
        sample_rate = int(audio.get("sample_rate", 0) or 0)
        if waveform is None or sample_rate <= 0:
            return video_path

        waveform = waveform.detach().cpu()
        if waveform.ndim == 3:
            waveform = waveform[0]
        channels = int(waveform.size(0))
        audio_data = waveform.transpose(0, 1).contiguous().numpy().astype(np.float32).tobytes()

        min_audio_dur = frame_count / frame_rate + 1
        apad = [] if trim_to_audio else ["-af", f"apad=whole_dur={min_audio_dur}"]
        args = [
            ffmpeg_path,
            "-v",
            "error",
            "-y",
            "-i",
            video_path,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-f",
            "f32le",
            "-i",
            "-",
            "-c:v",
            "copy",
        ] + audio_args + apad
        if extension == "mp4":
            args += ["-movflags", "+faststart"]
        args += ["-shortest", output_path]

        try:
            subprocess.run(args, input=audio_data, capture_output=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "An error occurred while muxing audio:\n" + exc.stderr.decode(*ENCODE_ARGS)
            ) from exc

        return output_path

    def save_video(
        self,
        images,
        output_folder: str,
        filename_prefix: str,
        frame_rate: float,
        loop_count: int,
        format: str,
        pix_fmt: str,
        crf: int,
        save_metadata: bool,
        trim_to_audio: bool,
        pingpong: bool,
        show_preview: bool,
        audio=None,
        vae=None,
        prompt=None,
        extra_pnginfo=None,
    ):
        images = _normalize_images(images, vae)
        images = _pad_to_even_dimensions(images)
        output_folder = _resolve_output_folder(output_folder)
        target_folder, filename = _split_prefix(output_folder, filename_prefix)
        extension, video_args, audio_args = self._video_codec_args(format, pix_fmt, crf)
        counter = _next_counter(target_folder, filename, extension)
        output_filename = f"{filename}_{counter:05}.{extension}"
        output_path = os.path.join(target_folder, output_filename)
        has_audio = _audio_is_usable(audio)
        video_only_path = (
            _make_temp_video_path(target_folder, filename, counter, extension)
            if has_audio
            else output_path
        )

        ffmpeg_path = _find_ffmpeg()
        height = int(images.shape[1])
        width = int(images.shape[2])
        frame_rate = float(frame_rate)
        total_frames = _output_frame_count(images, pingpong, loop_count)

        args = [
            ffmpeg_path,
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(frame_rate),
            "-i",
            "-",
            "-vf",
            "scale=out_color_matrix=bt709",
            "-color_range",
            "tv",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
        ] + video_args + self._metadata_args(save_metadata, prompt, extra_pnginfo) + [video_only_path]

        try:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            assert proc.stdin is not None
            for frame in _iter_frames(images, pingpong, loop_count):
                proc.stdin.write(_tensor_to_bytes(frame))
            proc.stdin.close()
            stderr = proc.stderr.read() if proc.stderr is not None else b""
            return_code = proc.wait()
        except BrokenPipeError as exc:
            stderr = proc.stderr.read() if proc.stderr is not None else b""
            raise RuntimeError(
                "An error occurred while saving video:\n" + stderr.decode(*ENCODE_ARGS)
            ) from exc

        if return_code != 0:
            raise RuntimeError(
                "An error occurred while saving video:\n" + stderr.decode(*ENCODE_ARGS)
            )

        final_path = output_path
        if has_audio:
            try:
                final_path = self._mux_audio(
                    ffmpeg_path=ffmpeg_path,
                    video_path=video_only_path,
                    audio=audio,
                    extension=extension,
                    audio_args=audio_args,
                    frame_rate=frame_rate,
                    frame_count=total_frames,
                    trim_to_audio=trim_to_audio,
                    output_path=output_path,
                )
            finally:
                if os.path.exists(video_only_path):
                    os.remove(video_only_path)

        result = (final_path, os.path.basename(final_path))
        if show_preview:
            preview = _copy_preview_to_temp(final_path, extension)
            preview["frame_rate"] = frame_rate
            return {"ui": {"gifs": [preview]}, "result": result}

        return {"ui": {"gifs": []}, "result": result}


class AntiMatterVideoSavePopular(SaveVideoInFolder):
    CATEGORY = "AntiMatter/Popular"


NODE_CLASS_MAPPINGS = {
    "AntiMatter_Save_Video_in_Folder": SaveVideoInFolder,
    "AntiMatter_Video_Save_Popular": AntiMatterVideoSavePopular,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AntiMatter_Save_Video_in_Folder": "Save_Video_in_Folder",
    "AntiMatter_Video_Save_Popular": "Video Save",
}
