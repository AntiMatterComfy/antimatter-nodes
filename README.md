# AntiMatter Nodes for ComfyUI

AntiMatter is a ComfyUI custom node collection for practical image workflows.

## Nodes

- `Anti_aspect_ratio_master`
- `Antimatter Text File Appender`
- `Batch Loader from folder`
- `LinePrompt_MasterLoad`
- `LinePrompt_MasterLoad_JSON`

Node tree:

```text
AntiMatter/Image/Anti_aspect_ratio_master
AntiMatter/Text/Antimatter Text File Appender
AntiMatter/Image/Batch Loader from folder
AntiMatter/Text/LinePrompt_MasterLoad
AntiMatter/Text/LinePrompt_MasterLoad_JSON
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

The ComfyUI setting `LinePrompt_MasterLoad styles txt folder` controls the parent folder scanned recursively for `style_file`.

## LinePrompt_MasterLoad_JSON

Loads scene prompts from JSON. It is designed for scene-based generation where manual rework should use the current scene number/name.

Inputs:

- `json_input`: optional connected JSON/string input.
- `enabled`: when disabled, returns empty strings.
- `json_text`: manual JSON content.
- `json_file`: path to a JSON file.
- `scene_mode`: `sequential` or `manual`.
- `manual_scene`: scene number used in manual mode.
- `repeat_each_scene`: number of queue runs per scene.
- `after_last_scene`: `stop_empty` or `loop`.

Outputs:

- `prompt`
- `Scene Name`

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
