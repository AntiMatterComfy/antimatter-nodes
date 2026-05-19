# AntiMatter Nodes for ComfyUI

AntiMatter is a ComfyUI custom node collection. The first node in the pack is:

- `Anti_aspect_ratio_master`

Node tree:

```text
AntiMatter/Image/Anti_aspect_ratio_master
```

## Nodes

### Anti_aspect_ratio_master

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
