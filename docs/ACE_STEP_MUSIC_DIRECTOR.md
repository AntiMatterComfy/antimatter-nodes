# Antimeter ACE-Step Music Director

## Included Tier 2 nodes

- **Antimeter Music Director — User Brief** turns one natural-language request into a structured generation brief.
- **Antimeter Music Director — Plan Validator & Router** validates a strict local-Qwen plan and routes safe values to ACE-Step.
- **Antimeter Music Director — Save MP3 + Metadata** saves every result with matching plan and metadata sidecars.

## Workflow dependency

These three nodes are self-contained and add no Python dependencies. The complete Tier 2 workflow additionally requires:

1. **ComfyUI-QwenVL** for `AILab_QwenVL_GGUF_PromptEnhancer`.
2. **ComfyUI-Easy-Use** for the optional Final Generation Card preview node.
3. The ACE-Step 1.5 Turbo AIO checkpoint and the chosen local Qwen GGUF model.

The Music Director validates a plan before it reaches ACE-Step. Keep the validator in the workflow: it ensures that instrumental requests receive `[Instrumental]`, video duration remains locked when supplied, and output metadata matches the effective settings.

## Support

Antimeter

Patreon: https://patreon.com/AntiMatterComfy
YouTube: https://www.youtube.com/@AntIMatter-comfy
