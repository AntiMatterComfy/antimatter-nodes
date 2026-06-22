# AntiMatter Nodes for ComfyUI

AntiMatter is a ComfyUI custom node collection for practical image workflows.

## Nodes

- `Anti_aspect_ratio_master`
- `Antimatter Text File Appender`
- `Batch Loader from folder`
- `Video_Batch_Loader`
- `Save_Video_in_Folder`
- `LinePrompt_MasterLoad`
- `LinePrompt_MasterLoad_JSON`
- `LinePrompt_MasterLoad_JSON_Image`
- `LM Studio 3 Image Agent`
- `LM Studio Multi Input Settings Agent`
- `AntiMatter LTX Director X`
- `AntiMatter LTX Director X Pro`
- `AntiMatter LTX Director X One Node`
- `AntiMatter LTX Fragment Stitch X`
- `AntiMatter LTX Audio Track X`

Node tree:

```text
AntiMatter/Image/Anti_aspect_ratio_master
AntiMatter/Text/Antimatter Text File Appender
AntiMatter/Image/Batch Loader from folder
AntiMatter/Video_Batch_Loader
AntiMatter/Save_Video_in_Folder
AntiMatter/Text/LinePrompt_MasterLoad
AntiMatter/Text/LinePrompt_MasterLoad_JSON
AntiMatter/Text/LinePrompt_MasterLoad_JSON_Image
AntiMatter/LM Studio/LM Studio 3 Image Agent
AntiMatter/LM Studio/LM Studio Multi Input Settings Agent
AntiMatter/LTX/AntiMatter LTX Director X
AntiMatter/LTX Pro/AntiMatter LTX Director X Pro
AntiMatter/LTX Pro/AntiMatter LTX Director X One Node
AntiMatter/LTX/AntiMatter LTX Fragment Stitch X
AntiMatter/LTX/AntiMatter LTX Audio Track X
```

## Anti_aspect_ratio_master

Creates an empty latent using Flux, Z-Image, and ERNIE-oriented presets, manual dimensions, or an input image size. It also returns the final width, height, final preset string, and detected image name.

Inputs:

- `source`: `from_preset`, `from_manual`, or `from_image`
- `preset`: Flux, Z-Image, and ERNIE-oriented width x height presets
- `manual_width`, `manual_height`: manual dimensions when `source` is `from_manual`
- `round_to`: rounds dimensions to a selected multiple
- `orientation`: `auto`, `portrait`, `landscape`, or `swap`
- `batch_size`: latent batch size
- `latent_channels`: latent channel count, default `16` for Flux, Z-Image, and ERNIE-style workflows
- `image`: optional image source for dimensions
- `downsample_factor`: latent downsample factor, usually `8` for VAE latent workflows

Outputs:

- `latent`
- `width`
- `height`
- `final_preset`
- `image_name`

## Antimatter Text File Appender

Saves incoming text to `.txt` or `.json` files. It can append normally, or replace a specific scene when a scene name/number is connected.

Inputs:

- `text`: manual text/string to save.
- `text_input`: optional connected string input. If connected, this is saved instead of `text`.
- `scene_name`: optional scene number/name for replacement workflows. Accepts values like `35`, `scene-035`, or `scene_35`.
- `directory`: folder path on any disk.
- `filename`: output file name. If no extension is provided, the node adds `.txt` or `.json`.
- `file_format`: `txt` or `json`.
- `prefix`: optional prefix added before every saved text.
- `blank_lines_between_entries`: spacing between appended `.txt` entries.
- `index_start`, `index_padding`: controls `{index}` and `{counter}` prefix placeholders.
- `json_indent`: pretty-print indent for `.json`; set `0` for compact JSON.

Outputs:

- `saved_text`
- `file_path`

Scene replacement:

Connect `Scene Name` from `LinePrompt_MasterLoad_JSON` to `scene_name` when manually regenerating a scene. For `.json`, the node replaces a record with the same `scene_name` or `index`. For `.txt`, it replaces the block containing that scene marker; if no marker is found, it replaces the N-th text block.

## Batch Loader from folder

Loads images directly from a local folder and outputs them as a ComfyUI `IMAGE` batch. It is built for repeated processing, dataset testing, prompt/model comparisons, and long workflows where manually uploading files one by one becomes slow.

Supported image formats:

- PNG
- JPG / JPEG
- WEBP
- BMP
- TIFF / TIF

### Advantages

- Loads full batches from any local folder without manual upload steps.
- Supports `random`, `sequential`, and `batch_freeze` modes.
- Uses deterministic seed control for repeatable random selections.
- Supports no-repeat random selection, so images are not repeated until the pool is exhausted.
- Can repeat one chosen image across a batch with `batch_freeze`, useful for seed, prompt, model, LoRA, or sampler testing.
- Can scan nested folders with recursive mode, useful for organized datasets and project folders.
- Has reload and reset controls, so folder changes can be picked up without restarting ComfyUI.
- Can skip images by exact width, height, or both, which is useful for filtering already resized or already processed files.
- Can move processed images into a subfolder after loading, helping separate completed and pending files during long runs.
- Returns filename text without extension, useful for output naming, captions, logging, or metadata chains.
- Returns source format, useful when branching workflow logic or tracking dataset composition.
- Returns width and height, useful for routing images by dimensions.
- Shows optional previews in the ComfyUI UI.
- Handles EXIF orientation, so camera and phone images load in the expected direction.
- Converts images to RGB automatically for stable ComfyUI image tensors.
- Can resize later batch images to the first image size, allowing mixed-size folders to become a valid ComfyUI batch.
- Works with relative paths such as `.uploading` and full absolute paths.

Inputs:

- `folder`: source folder path. Relative paths are resolved from the current ComfyUI working directory.
- `mode`: `random`, `sequential`, or `batch_freeze`.
- `batch_size`: number of images to output.
- `freeze_count`: number of queue executions to reuse the current selection.
- `seed`: controls deterministic random selection.
- `no_repeat_random`: prevents repeated random picks until all eligible files are used.
- `recursive`: scans nested folders when enabled.
- `reload`: rescans the folder.
- `reset`: resets sequence, freeze, and random pool state.
- `skip_exact_mode`: enables dimension-based skipping.
- `skip_exact_width`: width value for skip filters.
- `skip_exact_height`: height value for skip filters.
- `move_processed_to_subfolder`: moves selected images after processing.
- `processed_subfolder_name`: destination folder for processed images.
- `resize_to_first`: resizes later batch images to the first image size.
- `show_preview`: shows selected images in the node UI.
- `preview_max`: maximum preview images to display.

Outputs:

- `images`: ComfyUI image batch.
- `filename`: selected filename without extension, or a comma-separated list for mixed batches.
- `format`: selected file extension, or a comma-separated list for mixed batches.
- `width`: output image width.
- `height`: output image height.

## Video_Batch_Loader

Loads videos directly from a local folder through VideoHelperSuite's FFmpeg loader. The node appears in the menu as:

```text
AntiMatter/Video_Batch_Loader
```

Supported video formats:

- MP4
- MOV
- MKV
- WEBM
- AVI
- M4V
- MPG / MPEG
- WMV
- FLV
- GIF
- 3GP
- TS / MTS / M2TS

Inputs:

- `folder`: source folder path. Relative paths are resolved from the current ComfyUI working directory.
- `mode`: `random`, `sequential`, or `batch_freeze`.
- `batch_size`: number of videos to output as list items.
- `freeze_count`: number of queue executions to reuse the current selection.
- `seed`: controls deterministic random selection.
- `no_repeat_random`: prevents repeated random picks until all eligible files are used.
- `recursive`: scans nested folders when enabled.
- `reload`: rescans the folder.
- `reset`: resets sequence, freeze, and random pool state.
- `skip_exact_mode`: enables width/height metadata-based skipping.
- `skip_exact_width`: width value for skip filters.
- `skip_exact_height`: height value for skip filters.
- `move_processed_to_subfolder`: moves selected videos after selection and loads from the moved paths.
- `processed_subfolder_name`: destination folder for processed videos.
- `force_rate`: output frame rate, matching `Load Video FFmpeg (Path)`.
- `custom_width`: optional output width.
- `custom_height`: optional output height.
- `frame_load_cap`: maximum frames to load, or `0` for no cap.
- `start_time`: start time in seconds.
- `input_video`: optional connected ComfyUI `VIDEO`. When connected, this video is loaded instead of selecting a file from `folder`.
- `format`: VideoHelperSuite load format, default `Wan`.
- `meta_batch`: optional VideoHelperSuite batch manager.
- `vae`: optional VAE for latent loading.

Outputs:

- `IMAGE`: loaded video frames, matching `Load Video FFmpeg (Path)`.
- `mask`: alpha mask output, matching `Load Video FFmpeg (Path)`.
- `audio`: audio output, matching `Load Video FFmpeg (Path)`.
- `video_info`: VideoHelperSuite video info output.
- `video_path`: absolute path for each selected video.
- `filename`: selected filename without extension.
- `format`: selected file extension.
- `width`: source video width.
- `height`: source video height.
- `fps`: source video average FPS.
- `frame_count`: source frame count when available, or metadata-based estimate.
- `duration`: source duration in seconds.
- `batch_count`: number of selected videos.

## Save_Video_in_Folder

Saves a ComfyUI `IMAGE` frame batch, or `LATENT` frames with a connected VAE, as a video in any local folder path. The node appears in the menu as:

```text
AntiMatter/Save_Video_in_Folder
```

Inputs:

- `images`: input frames as `IMAGE`, or latents when `vae` is connected.
- `output_folder`: destination folder. Absolute paths on any disk are supported.
- `filename_prefix`: filename prefix. It may include subfolders under `output_folder`.
- `frame_rate`: output video FPS.
- `loop_count`: repeats the output sequence.
- `format`: `video/h264-mp4`, `video/h265-mp4`, or `video/webm`.
- `pix_fmt`: `yuv420p` or `yuv420p10le`.
- `crf`: encoder quality value; lower is higher quality/larger file.
- `save_metadata`: writes prompt/workflow metadata into the video comment field.
- `trim_to_audio`: when audio is connected, avoids padding audio beyond video duration.
- `pingpong`: plays frames forward and then backward.
- `show_preview`: shows or hides an in-node video preview with controls/timeline.
- `audio`: optional audio to mux into the saved video.
- `vae`: optional VAE for latent input.

When audio is connected, the node saves only one final video file with the audio track included. It does not keep a second no-audio version.

Outputs:

- `file_path`: absolute path to the saved video.
- `filename`: saved file name.

## LinePrompt_MasterLoad

Loads prompt lines from `.txt` files. It supports manual text prefixing, selectable style files, sequential/random/reverse reading, freeze count, delimiter handling, and preview updates.

Inputs:

- `enabled`: when disabled, returns an empty string.
- `input_text`: optional prefix added before the selected line as `input_text, selected_line`.
- `text_file`: manual path to a `.txt` file.
- `style_file`: dropdown populated from the configured styles folder.
- `lines_to_take`: selects 1, 2, or 3 consecutive lines.
- `read_mode`: `sequential`, `random`, or `from_end`.
- `freeze_iterations`: keeps the selected line for N queue runs.
- `delimiter`: appends `,`, `/`, `.`, or `;` to the selected line if missing.

Outputs:

- `text`
- `style_1_text` through `style_10_text`

The ComfyUI setting `LinePrompt_MasterLoad styles txt folder` controls the parent folder scanned recursively for `style_file`.

## LinePrompt_MasterLoad_JSON

Loads scene prompts from JSON. It is designed for scene-based generation where manual rework should use the current scene number/name.

Inputs:

- `json_input`: optional connected JSON/string input.
- `enabled`: when disabled, returns empty strings.
- `json_text`: manual JSON content.
- `json_file`: path to a JSON file.
- `scene_mode`: `sequential`, `manual`, or `row`.
- `manual_scene`: scene number used in manual mode.
- `repeat_each_scene`: number of queue runs per scene.
- `after_last_scene`: `stop_empty` or `loop`.
- `row`: row number used in row mode.

Outputs:

- `prompt`
- `Scene Name`

## LinePrompt_MasterLoad_JSON_Image

Loads scene prompts from JSON and the matching image from a folder in one node. It keeps the same scene selection behavior as `LinePrompt_MasterLoad_JSON`, then matches the selected scene to an image whose filename contains the same scene number, such as `scene-001.jpg`, `scene_001.png`, or `001.webp`.

Inputs:

- `json_input`: optional connected JSON/string input.
- `enabled`: when disabled, returns empty strings and a 1x1 blank image.
- `json_text`: manual JSON content.
- `json_file`: path to a JSON file.
- `image_folder`: folder containing scene images.
- `recursive`: scans nested folders when enabled.
- `scene_mode`: `sequential`, `manual`, `row`, or `interval`.
- `manual_scene`: scene number used in manual mode.
- `interval_from_scene`: first scene number included in interval mode.
- `interval_to_scene`: last scene number included in interval mode.
- `repeat_each_scene`: number of queue runs per scene.
- `after_last_scene`: `stop_empty` or `loop`.
- `row`: row number used in row mode.
- `show_preview`: shows the matched image in the node UI.

Outputs:

- `prompt`
- `Scene Name`
- `image`
- `image_filename`
- `image_path`
- `width`
- `height`

## LM Studio 3 Image Agent

Calls a local LM Studio OpenAI-compatible `/v1/chat/completions` API with up to three optional images and returns generated text. The node is useful for vision-language description passes before Flux prompt generation.

Inputs:

- `image_1`, `image_2`, `image_3`: optional ComfyUI image inputs.
- `prompt`: main user prompt.
- `system_prompt`: optional system instruction.
- `lmstudio_base_url`: LM Studio base URL, default `http://127.0.0.1:1234/v1`.
- `model`: local LM Studio model name.
- `temperature`, `max_tokens`, `top_p`, penalties, seed, stop sequences, image detail/format/size, timeout.
- `keep_model_loaded` and `idle_ttl_seconds`: keep the local model warm between queued generations.
- `save_json`, `output_dir`, `json_filename_prefix`: save request/response snapshots.

Outputs:

- `text`
- `json_path`
- `raw_response_json`

## LM Studio Multi Input Settings Agent

Runs independent LM Studio routes for three optional images plus a text-only route. The Pixorama-style `SETTINGS` button opens the full prompt/settings editor with AntiMatter black/purple styling.

Inputs:

- `image_1`, `image_2`, `image_3`: optional image routes, each with its own system prompt and user query.
- `input_text_placeholder`, `placeholder_2`, `placeholder_3`, `placeholder_4`, `placeholder_5`: optional text inputs.
- `text_system_prompt`, `text_user_query`: text-only route. This route works even when no images are connected.
- `project_path`, `run_folder_name`, `save_json`: create per-run folders with route JSON files and a manifest.
- LM Studio model, sampling, timeout, image encoding, and keep-loaded settings.

Placeholder tokens:

- `[p1]`: `input_text_placeholder`
- `[p2]`: `placeholder_2`
- `[p3]`: `placeholder_3`
- `[p4]`: `placeholder_4`
- `[p5]`: `placeholder_5`
- `[...]` and `[input_text]`: backward-compatible aliases for `[p1]`

Unknown bracket tokens are left unchanged, so prompt templates such as `[pose]` remain visible instead of being silently erased.

Outputs:

- `image_1_text`
- `image_2_text`
- `image_3_text`
- `input_text_output`
- `json_project_dir`
- `combined_text`: every non-empty route output joined in execution order, useful for sending the final text onward to Flux prompt chains.

## AntiMatter LTX Director X

Five LTX workflow nodes are bundled under the same AntiMatter package:

- `AntiMatter LTX Director X`: timeline ranges, retry-fragment rendering, prompt-agent fields, JoyCaption input, audio-lane metadata, and edit-decision outputs.
- `AntiMatter LTX Director X Pro`: a resizable editor with preview, timeline, LoRA rack, camera controls, gallery assets, project settings, and camera-track JSON.
- `AntiMatter LTX Director X One Node`: runs the two-stage LTX generation, latent upscale, decode, live preview, and final-video outputs inside one node.
- `AntiMatter LTX Fragment Stitch X`: replaces or inserts regenerated frames in an existing frame batch.
- `AntiMatter LTX Audio Track X`: extracts, removes, or trims audio by frame range.

The LTX nodes preserve their original workflow class IDs, so workflows made with the standalone `Antimatter_Ltx_Director_X` package can resolve the same nodes after switching to this combined repository. Remove or disable the standalone copy after installing the combined pack to avoid duplicate node registration.

## Manual Install

Clone this repository into your ComfyUI custom nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/AntiMatterComfy/antimatter-nodes.git
```

Restart ComfyUI after installing.

## ComfyUI Manager

For automatic installation through ComfyUI Manager's "Install Missing Custom Nodes", this repository must be discoverable by ComfyUI Manager. Use one of these routes:

- Publish the package to the ComfyUI Registry.
- Or submit a pull request to ComfyUI Manager that adds this repository to `custom-node-list.json`.

This repository includes `pyproject.toml` and `node_list.json` to make the node metadata easy for ComfyUI tools to scan.
