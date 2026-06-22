import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EXTENSION = "Antimatter.LtxDirectorX";
const ANTIMATTER_LOGO_URL = new URL("./assets/logo.png", import.meta.url).href;
const PRO_NODE_CLASSES = new Set(["AntimatterLtxDirectorXPro", "AntimatterLtxDirectorXOneNode"]);

const HIDDEN_WIDGETS = new Set([
  "timeline_data",
  "local_prompts",
  "segment_lengths",
  "guide_strength",
  "timeline_edit_actions",
  "selected_segment_id",
  "selection_start_frame",
  "selection_end_frame",
  "duration_seconds",
]);

const PRO_HIDDEN_WIDGETS = new Set([
  ...HIDDEN_WIDGETS,
  "pro_lora_stack_json",
  "pro_lora_preset",
  "distilled_enabled",
  "distilled_strength",
  "union_control_enabled",
  "union_control_strength",
  "motion_track_enabled",
  "motion_track_strength",
  "lipdub_enabled",
  "lipdub_strength",
  "transition_enabled",
  "transition_strength",
  "camera_control_enabled",
  "camera_control_strength",
  "missing_lora_policy",
  "camera_control_json",
  "camera_mode",
  "camera_lora_auto_enable",
  "camera_width",
  "camera_height",
  "camera_frame_count",
  "camera_motion_pixels",
  "pro_editor_settings_json",
  "final_video_preview_path",
  "auto_load_models",
  "run_integrated_pipeline",
  "two_stage_mode",
  "stage_run_mode",
  "stage1_draft_scale",
  "stage2_require_stage1_source",
  "use_latest_stage1_result",
  "advanced_mode",
  "save_final_video",
  "pipeline_noise_seed",
  "latent_upscale_model_name",
  "pipeline_sampler",
  "pipeline_scheduler",
  "stage1_steps",
  "stage1_denoise",
  "stage1_guide_scale_by",
  "stage2_steps",
  "stage2_denoise",
  "stage2_guide_scale_by",
  "fast_preview_rate",
]);

const PRO_VISIBLE_WIDGETS = new Set([
  "director_x_surface",
  "AMX EDIT",
  "AMX Settings",
  "AMX Help",
]);

const PRO_LORAS = [
  { id: "distilled", label: "Distilled 384 v1.1", file: "ltx-2.3-22b-distilled-lora-384-1.1.safetensors", preferred: "LTX/ltx-2.3-22b-distilled-lora-384-1.1.safetensors", settingsKey: "distilled_lora", role: "base speed/quality", enabled: true, strength: 1 },
  { id: "union_control", label: "Union Control", file: "ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors", preferred: "LTX/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors", settingsKey: "union_control_lora", role: "reference control", enabled: false, strength: 0.65 },
  { id: "motion_track", label: "Motion Track", file: "ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors", preferred: "LTX/ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors", settingsKey: "motion_track_lora", role: "track steering", enabled: false, strength: 0.72 },
  { id: "lipdub", label: "LipDub", file: "ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors", preferred: "LTX/ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors", settingsKey: "lipdub_lora", role: "speech shots", enabled: false, strength: 0.85 },
  { id: "transition", label: "Transition", file: "ltx2.3-transition.safetensors", preferred: "LTX/ltx2.3-transition.safetensors", settingsKey: "transition_lora", role: "shot transitions", enabled: false, strength: 0.7 },
  { id: "camera_control", label: "Camera Control", file: "LTX2.3_CameraControls.safetensors", preferred: "LTX/CAMERA/LTX2.3_CameraControls.safetensors", settingsKey: "camera_control_lora", role: "viewer motion", enabled: false, strength: 0.9 },
  { id: "detailer", label: "Detailer IC-LoRA", file: "ltx-2-19b-ic-lora-detailer.safetensors", preferred: "LTX/ltx-2-19b-ic-lora-detailer.safetensors", settingsKey: "detailer_lora", role: "detail restoration", enabled: false, strength: 0.65, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-IC-LoRA-Detailer/resolve/main/ltx-2-19b-ic-lora-detailer.safetensors?download=true" },
  { id: "pose_control", label: "Pose Control IC-LoRA", file: "ltx-2-19b-ic-lora-pose-control.safetensors", preferred: "LTX/ltx-2-19b-ic-lora-pose-control.safetensors", settingsKey: "pose_control_lora", role: "pose guidance", enabled: false, strength: 0.7, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-IC-LoRA-Pose-Control/resolve/main/ltx-2-19b-ic-lora-pose-control.safetensors?download=true" },
  { id: "camera_dolly_in", label: "Camera Dolly In", file: "ltx-2-19b-lora-camera-control-dolly-in.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-in.safetensors", settingsKey: "camera_dolly_in_lora", role: "camera push in", enabled: false, strength: 0.8, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-In/resolve/main/ltx-2-19b-lora-camera-control-dolly-in.safetensors?download=true" },
  { id: "camera_dolly_out", label: "Camera Dolly Out", file: "ltx-2-19b-lora-camera-control-dolly-out.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-out.safetensors", settingsKey: "camera_dolly_out_lora", role: "camera pull back", enabled: false, strength: 0.8, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Out/resolve/main/ltx-2-19b-lora-camera-control-dolly-out.safetensors?download=true" },
  { id: "camera_dolly_left", label: "Camera Dolly Left", file: "ltx-2-19b-lora-camera-control-dolly-left.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-left.safetensors", settingsKey: "camera_dolly_left_lora", role: "camera truck left", enabled: false, strength: 0.8, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Left/resolve/main/ltx-2-19b-lora-camera-control-dolly-left.safetensors?download=true" },
  { id: "camera_dolly_right", label: "Camera Dolly Right", file: "ltx-2-19b-lora-camera-control-dolly-right.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-right.safetensors", settingsKey: "camera_dolly_right_lora", role: "camera truck right", enabled: false, strength: 0.8, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Right/resolve/main/ltx-2-19b-lora-camera-control-dolly-right.safetensors?download=true" },
  { id: "camera_jib_up", label: "Camera Jib Up", file: "ltx-2-19b-lora-camera-control-jib-up.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-up.safetensors", settingsKey: "camera_jib_up_lora", role: "camera rise", enabled: false, strength: 0.8, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Jib-Up/resolve/main/ltx-2-19b-lora-camera-control-jib-up.safetensors?download=true" },
  { id: "camera_jib_down", label: "Camera Jib Down", file: "ltx-2-19b-lora-camera-control-jib-down.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-down.safetensors", settingsKey: "camera_jib_down_lora", role: "camera descend", enabled: false, strength: 0.8, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Jib-Down/resolve/main/ltx-2-19b-lora-camera-control-jib-down.safetensors?download=true" },
  { id: "camera_static", label: "Camera Static", file: "ltx-2-19b-lora-camera-control-static.safetensors", preferred: "LTX/CAMERA/ltx-2-19b-lora-camera-control-static.safetensors", settingsKey: "camera_static_lora", role: "locked-off shot", enabled: false, strength: 0.75, downloadUrl: "https://huggingface.co/Lightricks/LTX-2-19b-LoRA-Camera-Control-Static/resolve/main/ltx-2-19b-lora-camera-control-static.safetensors?download=true" },
];

const CAMERA_MODE_OPTIONS = [
  ["off", "Off"],
  ["dolly_in", "Dolly In"],
  ["dolly_out", "Dolly Out"],
  ["dolly_left", "Dolly Left"],
  ["dolly_right", "Dolly Right"],
  ["jib_up", "Jib Up"],
  ["jib_down", "Jib Down"],
  ["static", "Static"],
  ["custom", "Custom"],
];

const CAMERA_LORA_MODE_MAP = {
  dolly_in: "camera_dolly_in",
  dolly_out: "camera_dolly_out",
  dolly_left: "camera_dolly_left",
  dolly_right: "camera_dolly_right",
  jib_up: "camera_jib_up",
  jib_down: "camera_jib_down",
  static: "camera_static",
};

const CAMERA_LORA_IDS = new Set(Object.values(CAMERA_LORA_MODE_MAP));

const LORA_GROUPS = [
  { id: "core", label: "Core", ids: ["distilled"] },
  { id: "control", label: "Control", ids: ["union_control", "motion_track", "detailer", "pose_control"] },
  { id: "speech", label: "Speech", ids: ["lipdub"] },
  { id: "transition", label: "Transition", ids: ["transition"] },
  { id: "camera", label: "Camera", ids: ["camera_control", ...Object.values(CAMERA_LORA_MODE_MAP)] },
];

function loraGroupForId(id) {
  return LORA_GROUPS.find((group) => group.ids.includes(id))?.id || "advanced";
}

function cameraModeForLoraId(id) {
  return Object.entries(CAMERA_LORA_MODE_MAP).find(([, loraId]) => loraId === id)?.[0] || "";
}

const PRO_PRESETS = {
  clean_default: { distilled: [true, 1], union_control: [false, 0], motion_track: [false, 0], lipdub: [false, 0], transition: [false, 0], camera_control: [false, 0], detailer: [false, 0], pose_control: [false, 0] },
  director_balanced: { distilled: [true, 1], union_control: [false, 0], motion_track: [false, 0], lipdub: [false, 0], transition: [false, 0], camera_control: [false, 0] },
  camera_control: { distilled: [true, 1], union_control: [false, 0], motion_track: [false, 0], lipdub: [false, 0], transition: [false, 0], camera_control: [true, 0.95] },
  motion_tracking: { distilled: [true, 1], union_control: [true, 0.6], motion_track: [true, 0.85], lipdub: [false, 0], transition: [false, 0], camera_control: [false, 0] },
  lipdub: { distilled: [true, 1], union_control: [false, 0], motion_track: [false, 0], lipdub: [true, 0.9], transition: [false, 0], camera_control: [false, 0] },
  transition: { distilled: [true, 1], union_control: [false, 0], motion_track: [false, 0], lipdub: [false, 0], transition: [true, 0.82], camera_control: [false, 0] },
  max_control: { distilled: [true, 1], union_control: [true, 0.65], motion_track: [true, 0.8], lipdub: [false, 0], transition: [false, 0], camera_control: [false, 0] },
};

const RESOLUTION_PRESETS = [
  { id: "ltx_fast_512x288", label: "Fast Preview 512 x 288", width: 512, height: 288, fastPreview: true },
  { id: "ltx_wide_768x432", label: "Wide 768 x 432", width: 768, height: 432, fastPreview: true },
  { id: "ltx_hd_1280x720", label: "HD 1280 x 720", width: 1280, height: 720, fastPreview: false },
  { id: "ltx_fullhd_1920x1080", label: "Full HD 1920 x 1080", width: 1920, height: 1080, fastPreview: false },
  { id: "ltx_square_1024x1024", label: "Square 1024 x 1024", width: 1024, height: 1024, fastPreview: false },
  { id: "ltx_portrait_720x1280", label: "Portrait 720 x 1280", width: 720, height: 1280, fastPreview: false },
  { id: "custom", label: "Custom from Settings", width: 0, height: 0, fastPreview: false },
];

const STYLE_ID = "antimatter-ltx-director-x-styles";
const STYLES = `
  .amx {
    --bg: #151719;
    --panel: #1f2326;
    --panel2: #242a2e;
    --line: #394047;
    --text: #e8edf2;
    --muted: #9aa5ae;
    --accent: #63d2c6;
    --accent2: #f0b85a;
    --danger: #e06262;
    --video: #3e8ed0;
    --audio: #57b36b;
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--text);
    background: var(--bg);
    border: 1px solid #0e1012;
    border-radius: 6px;
    padding: 8px;
    box-sizing: border-box;
    display: grid;
    gap: 8px;
    width: 100%;
  }
  .amx * { box-sizing: border-box; }
  .amx-top, .amx-tools, .amx-status, .amx-props-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .amx-top { justify-content: space-between; }
  .amx-title {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
  }
  .amx-status {
    font-size: 11px;
    color: var(--muted);
    justify-content: flex-end;
  }
  .amx-btn, .amx-icon-btn {
    background: var(--panel2);
    border: 1px solid var(--line);
    color: var(--text);
    border-radius: 5px;
    min-height: 26px;
    cursor: pointer;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
  }
  .amx-btn { padding: 4px 8px; }
  .amx-icon-btn { width: 28px; padding: 3px; }
  .amx-btn:hover, .amx-icon-btn:hover { border-color: #69747d; background: #2c3439; }
  .amx-btn.primary { border-color: #3fa99e; background: #183b39; color: #dffffb; }
  .amx-btn.warning { border-color: #856230; background: #3a2d17; color: #ffe4b6; }
  .amx-btn.danger { border-color: #894244; background: #3b1c1e; color: #ffd8d8; }
  .amx-btn.active { border-color: var(--accent); box-shadow: inset 0 0 0 1px rgba(99,210,198,.35); }
  .amx-file { display: none; }
  .amx-timebar {
    height: 22px;
    position: relative;
    background: #101214;
    border: 1px solid #0a0b0c;
    border-radius: 5px 5px 0 0;
    overflow: hidden;
    cursor: pointer;
  }
  .amx-ruler-tick {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(255,255,255,.16);
  }
  .amx-ruler-label {
    position: absolute;
    top: 3px;
    transform: translateX(4px);
    font-size: 10px;
    color: #8f9aa3;
    pointer-events: none;
  }
  .amx-track {
    height: 78px;
    position: relative;
    background: #181b1e;
    border-left: 1px solid #0a0b0c;
    border-right: 1px solid #0a0b0c;
    border-bottom: 1px solid #0a0b0c;
    overflow: hidden;
  }
  .amx-track.audio { height: 46px; background: #171d19; border-radius: 0 0 5px 5px; }
  .amx-track-label {
    position: absolute;
    left: 8px;
    top: 7px;
    font-size: 10px;
    color: rgba(255,255,255,.62);
    pointer-events: none;
    z-index: 3;
  }
  .amx-segment {
    position: absolute;
    top: 22px;
    height: 46px;
    min-width: 10px;
    border-radius: 5px;
    border: 1px solid rgba(255,255,255,.22);
    background: linear-gradient(180deg, rgba(62,142,208,.9), rgba(31,81,123,.94));
    color: white;
    overflow: hidden;
    cursor: grab;
    user-select: none;
  }
  .amx-segment.has-thumb {
    background: #07090a;
  }
  .amx-segment.has-thumb:after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(0,0,0,.45), rgba(0,0,0,.08) 45%, rgba(0,0,0,.34));
    pointer-events: none;
    z-index: 1;
  }
  .amx-thumb {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    pointer-events: none;
    z-index: 0;
  }
  .amx-track.audio .amx-segment {
    top: 17px;
    height: 22px;
    background: linear-gradient(180deg, rgba(87,179,107,.85), rgba(35,94,48,.9));
  }
  .amx-segment.selected {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px rgba(99,210,198,.9), 0 0 18px rgba(99,210,198,.18);
  }
  .amx-transition {
    position: absolute;
    top: 25px;
    height: 40px;
    min-width: 12px;
    border: 1px solid rgba(240,184,90,.72);
    border-radius: 4px;
    background:
      linear-gradient(135deg, rgba(240,184,90,.9) 0 12%, transparent 12% 24%, rgba(99,210,198,.8) 24% 36%, transparent 36% 48%, rgba(240,184,90,.85) 48% 60%, transparent 60% 72%, rgba(99,210,198,.75) 72% 84%, transparent 84%),
      rgba(18,20,22,.78);
    box-shadow: 0 0 14px rgba(240,184,90,.18);
    z-index: 4;
    pointer-events: none;
  }
  .amx-transition span {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    font-size: 9px;
    font-weight: 700;
    color: #fff4d6;
    text-shadow: 0 1px 4px rgba(0,0,0,.9);
  }
  .amx-seg-name {
    position: relative;
    z-index: 2;
    font-size: 10px;
    padding: 4px 7px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #fff;
    text-shadow: 0 1px 4px rgba(0,0,0,.9);
  }
  .amx-handle {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 8px;
    background: rgba(255,255,255,.18);
    cursor: ew-resize;
    z-index: 3;
  }
  .amx-handle.left { left: 0; }
  .amx-handle.right { right: 0; }
  .amx-playhead, .amx-range-edge {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 2px;
    background: var(--accent2);
    z-index: 6;
    pointer-events: none;
    transform: translateX(0);
    transition: transform 190ms cubic-bezier(.18,.82,.22,1);
    will-change: transform;
    box-shadow: 0 0 12px rgba(240,184,90,.45);
  }
  .amx-playhead:after {
    content: "";
    position: absolute;
    left: -3px;
    top: 0;
    width: 8px;
    height: 8px;
    border-radius: 0 0 4px 4px;
    background: var(--accent2);
    box-shadow: 0 0 12px rgba(240,184,90,.5);
  }
  .amx-ruler-playhead {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 2px;
    background: var(--accent2);
    z-index: 8;
    pointer-events: none;
    transform: translateX(0);
    transition: transform 190ms cubic-bezier(.18,.82,.22,1);
    will-change: transform;
    box-shadow: 0 0 12px rgba(240,184,90,.45);
  }
  .amx-ruler-playhead:before {
    content: "";
    position: absolute;
    left: -5px;
    top: 0;
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid var(--accent2);
    filter: drop-shadow(0 0 7px rgba(240,184,90,.55));
  }
  .amx.is-scrubbing .amx-playhead,
  .amx.is-scrubbing .amx-ruler-playhead,
  .amx.is-dragging .amx-playhead,
  .amx.is-dragging .amx-ruler-playhead {
    transition-duration: 70ms;
  }
  .amx-range {
    position: absolute;
    top: 0;
    bottom: 0;
    background: rgba(99,210,198,.12);
    border-left: 1px solid rgba(99,210,198,.7);
    border-right: 1px solid rgba(99,210,198,.7);
    z-index: 1;
    pointer-events: none;
  }
  .amx-props {
    display: grid;
    grid-template-columns: 1fr 150px;
    gap: 8px;
  }
  .amx-textarea {
    width: 100%;
    min-height: 86px;
    resize: vertical;
    color: var(--text);
    background: #111416;
    border: 1px solid var(--line);
    border-radius: 5px;
    padding: 7px;
    font-size: 11px;
    line-height: 1.38;
    outline: none;
  }
  .amx-textarea:focus, .amx-input:focus { border-color: var(--accent); }
  .amx-prompt-inspector {
    display: grid;
    gap: 7px;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--panel);
    padding: 8px;
    min-height: 0;
  }
  .amx-prompt-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: #f4f7f9;
    font-weight: 700;
  }
  .amx-prompt-head span {
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .amx-prompt-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .amx-side {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 5px;
    padding: 7px;
    display: grid;
    align-content: start;
    gap: 6px;
  }
  .amx-label {
    font-size: 10px;
    color: var(--muted);
    display: grid;
    gap: 3px;
  }
  .amx-input {
    width: 100%;
    min-height: 24px;
    color: var(--text);
    background: #111416;
    border: 1px solid var(--line);
    border-radius: 4px;
    padding: 3px 5px;
    font-size: 11px;
  }
  .amx-small {
    font-size: 10px;
    color: var(--muted);
  }
  .amx-pro-header {
    display: grid;
    grid-template-columns: minmax(260px, 1fr) auto auto;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border: 1px solid #4b3d23;
    border-radius: 6px;
    background: linear-gradient(180deg, #242321, #181b1d);
    min-height: 42px;
  }
  .amx-pro-brand {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    align-items: center;
    gap: 2px;
  }
  .amx-pro-logo-img {
    width: 36px;
    height: 36px;
    border-radius: 6px;
    border: 1px solid rgba(240,184,90,.5);
    background: #050607;
    object-fit: cover;
    box-shadow: 0 0 18px rgba(99,210,198,.12);
  }
  .amx-pro-brand-copy {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  .amx-pro-brand b {
    font-size: 12px;
    color: #fff4d6;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .amx-pro-brand span {
    font-size: 9px;
    color: #c7b98d;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .amx-pro-presetbar {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .amx-pro-header .amx-tools {
    justify-content: flex-start;
    gap: 5px;
    flex-wrap: wrap;
  }
  .amx-pro-header .amx-btn {
    min-height: 25px;
    padding: 3px 7px;
  }
  .amx-pro-grid {
    display: grid;
    grid-template-columns: minmax(360px, 1fr) 330px;
    gap: 8px;
  }
  .amx-lora-rack, .amx-camera-rig {
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--panel);
    padding: 8px;
    display: grid;
    gap: 7px;
    align-content: start;
  }
  .amx-section-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-weight: 700;
    color: #f4f7f9;
  }
  .amx-lora-row {
    display: grid;
    grid-template-columns: 22px minmax(120px, 1fr) 84px 92px 44px 28px;
    align-items: center;
    gap: 7px;
    min-height: 34px;
    border: 1px solid #303840;
    border-radius: 5px;
    background: #171b1f;
    padding: 5px;
  }
  .amx-lora-row.on {
    border-color: rgba(99,210,198,.58);
    background: #162321;
  }
  .amx-lora-group {
    display: grid;
    gap: 5px;
  }
  .amx-lora-group-title {
    font-size: 10px;
    color: #e8d39b;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-top: 3px;
  }
  .amx-lora-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
  }
  .amx-lora-badges span {
    font-size: 8px;
    color: #aab5bd;
    border: 1px solid #354049;
    border-radius: 999px;
    padding: 1px 5px;
    line-height: 14px;
    white-space: nowrap;
  }
  .amx-lora-badges span.on {
    color: #071111;
    background: var(--accent);
    border-color: var(--accent);
  }
  .amx-lora-row.camera-mode-row .amx-toggle-dot {
    border-radius: 4px;
  }
  .amx-toggle-dot {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 1px solid #55616b;
    background: #262c31;
    cursor: pointer;
  }
  .amx-toggle-dot.on {
    background: var(--accent);
    border-color: #b6fff7;
    box-shadow: 0 0 12px rgba(99,210,198,.28);
  }
  .amx-lora-name {
    display: grid;
    gap: 1px;
    min-width: 0;
  }
  .amx-lora-name b {
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .amx-lora-name span {
    font-size: 9px;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .amx-slider {
    width: 100%;
    accent-color: var(--accent);
  }
  .amx-num {
    background: #101315;
    border: 1px solid #37414a;
    color: var(--text);
    border-radius: 4px;
    height: 23px;
    padding: 2px 4px;
    font-size: 10px;
    width: 44px;
  }
  .amx-download-btn {
    width: 26px;
    height: 24px;
    padding: 0;
    border-radius: 4px;
    border: 1px solid #3e5961;
    background: #111b20;
    color: #d8fffb;
    display: inline-grid;
    place-items: center;
    cursor: pointer;
  }
  .amx-download-btn:hover {
    border-color: var(--accent);
    background: #183734;
  }
  .amx-download-btn.disabled {
    opacity: .35;
    cursor: default;
  }
  .amx-camera-view {
    position: relative;
    height: 180px;
    border-radius: 6px;
    border: 1px solid #111;
    background:
      linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px),
      radial-gradient(circle at 50% 45%, rgba(99,210,198,.2), transparent 45%),
      #101315;
    background-size: 24px 24px, 24px 24px, 100% 100%, 100% 100%;
    overflow: hidden;
    cursor: grab;
    perspective: 650px;
  }
  .amx-camera-reticle {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 70px;
    height: 48px;
    margin-left: -35px;
    margin-top: -24px;
    border: 2px solid rgba(99,210,198,.85);
    border-radius: 6px;
    transform-style: preserve-3d;
    box-shadow: 0 0 24px rgba(99,210,198,.18);
  }
  .amx-camera-reticle:before, .amx-camera-reticle:after {
    content: "";
    position: absolute;
    background: rgba(99,210,198,.75);
  }
  .amx-camera-reticle:before { left: 50%; top: -16px; width: 2px; height: 80px; }
  .amx-camera-reticle:after { left: -20px; top: 50%; width: 110px; height: 2px; }
  .amx-camera-readout {
    position: absolute;
    left: 8px;
    bottom: 7px;
    font-size: 10px;
    color: #d8fffb;
    background: rgba(0,0,0,.38);
    border: 1px solid rgba(99,210,198,.32);
    border-radius: 4px;
    padding: 4px 6px;
  }
  .amx-camera-controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .amx-camera-controls label {
    display: grid;
    gap: 2px;
    font-size: 10px;
    color: var(--muted);
  }
  .amx-surface {
    --bg: #151719;
    --panel: #1f2326;
    --line: #394047;
    --text: #e8edf2;
    --muted: #9aa5ae;
    --accent: #63d2c6;
    --gold: #f0b85a;
    width: 100%;
    min-height: 360px;
    padding: 10px;
    display: grid;
    grid-template-rows: auto 1fr auto;
    gap: 9px;
    color: var(--text);
    background: linear-gradient(180deg, #191d20, #111315);
    border: 1px solid #08090a;
    border-radius: 7px;
    box-sizing: border-box;
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .amx-surface-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .amx-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .amx-logo-img {
    width: 34px;
    height: 34px;
    border-radius: 7px;
    border: 1px solid rgba(240,184,90,.55);
    background: #050607;
    display: block;
    object-fit: cover;
    box-shadow: 0 0 16px rgba(99,210,198,.13);
  }
  .amx-logo-text {
    display: grid;
    gap: 1px;
    min-width: 0;
  }
  .amx-logo-text b {
    font-size: 13px;
    color: #fff4d6;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .amx-logo-text span {
    font-size: 10px;
    color: var(--muted);
  }
  .amx-surface-actions {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .amx-edit-big {
    min-width: 126px;
    height: 36px;
    border-radius: 6px;
    border: 1px solid #4fbfb3;
    background: linear-gradient(180deg, #245b58, #183734);
    color: #eafffb;
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
    letter-spacing: .4px;
  }
  .amx-round-btn {
    width: 30px;
    height: 30px;
    border-radius: 6px;
    border: 1px solid var(--line);
    background: #20262a;
    color: var(--text);
    cursor: pointer;
    font-weight: 700;
  }
  .amx-node-preview {
    position: relative;
    min-height: 220px;
    border-radius: 7px;
    border: 1px solid #090a0b;
    background: radial-gradient(circle at 50% 40%, rgba(99,210,198,.14), transparent 42%), #07090a;
    overflow: hidden;
    display: grid;
    place-items: center;
  }
  .amx-node-preview video {
    width: 100%;
    height: 100%;
    object-fit: contain;
    background: #000;
  }
  .amx-preview-empty {
    text-align: center;
    color: #6f7b84;
    font-size: 11px;
    display: grid;
    gap: 6px;
    padding: 16px;
  }
  .amx-surface-footer {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    color: var(--muted);
    font-size: 10px;
  }
  .amx-floating-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.36);
    z-index: 999;
  }
  .amx-floating {
    position: fixed;
    left: 5vw;
    top: 5vh;
    width: min(1680px, 90vw);
    height: min(1040px, 88vh);
    min-width: 980px;
    min-height: 650px;
    resize: both;
    overflow: hidden;
    z-index: 1000;
    border: 1px solid #48515a;
    border-radius: 8px;
    background: #101214;
    box-shadow: 0 22px 80px rgba(0,0,0,.58);
    display: grid;
    grid-template-rows: 38px 1fr;
  }
  .amx-floating-titlebar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    background: linear-gradient(180deg, #20252a, #15181b);
    border-bottom: 1px solid #343b42;
    padding: 0 9px;
    cursor: move;
    user-select: none;
  }
  .amx-floating-titlebar b {
    color: #fff4d6;
    font-size: 12px;
  }
  .amx-floating-body {
    min-height: 0;
    overflow: hidden;
  }
  .amx-editor-root {
    height: 100%;
    border: 0;
    border-radius: 0;
    --left-pane: 46px;
    --right-pane: 46px;
    --timeline-pane: 186px;
    grid-template-rows: auto 1fr 6px var(--timeline-pane);
    overflow: hidden;
  }
  .amx-editor-middle {
    display: grid;
    grid-template-columns: var(--left-pane) 6px minmax(360px, 1fr) 6px var(--right-pane);
    gap: 0;
    min-height: 0;
  }
  .amx-editor-panel {
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--panel);
    padding: 8px;
  }
  .amx-side-dock {
    position: relative;
    padding: 8px;
  }
  .amx-side-dock.collapsed {
    padding: 0;
    overflow: hidden;
    display: grid;
    place-items: stretch;
  }
  .amx-dock-content {
    display: grid;
    gap: 10px;
    align-content: start;
  }
  .amx-side-dock.collapsed .amx-dock-content {
    display: none;
  }
  .amx-dock-tab {
    display: none;
    width: 100%;
    height: 100%;
    min-height: 220px;
    border: 0;
    background: linear-gradient(180deg, #20262a, #131719);
    color: #d8fffb;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    writing-mode: vertical-rl;
    text-orientation: mixed;
    letter-spacing: .6px;
  }
  .amx-side-dock.collapsed .amx-dock-tab {
    display: block;
  }
  .amx-dock-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .amx-dock-head b {
    font-size: 11px;
    color: #fff4d6;
  }
  .amx-splitter-v, .amx-splitter-h {
    background: #121518;
    border: 1px solid #252c32;
    position: relative;
    z-index: 5;
  }
  .amx-splitter-v {
    cursor: col-resize;
    border-top: 0;
    border-bottom: 0;
  }
  .amx-splitter-h {
    cursor: row-resize;
    border-left: 0;
    border-right: 0;
  }
  .amx-splitter-v:hover, .amx-splitter-h:hover {
    background: #26433f;
    border-color: rgba(99,210,198,.7);
  }
  .amx-editor-preview {
    display: grid;
    grid-template-rows: auto 1fr auto;
    gap: 7px;
  }
  .amx-preview-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  .amx-tabs {
    display: inline-flex;
    gap: 4px;
    align-items: center;
  }
  .amx-tab {
    min-height: 24px;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: #171c20;
    color: var(--muted);
    font-size: 10px;
    padding: 3px 7px;
    cursor: pointer;
  }
  .amx-tab.active {
    color: #eafffb;
    border-color: var(--accent);
    background: #183b39;
  }
  .amx-editor-video {
    min-height: 260px;
    background: #050607;
    border: 1px solid #0c0d0e;
    border-radius: 6px;
    overflow: hidden;
    display: grid;
    place-items: center;
  }
  .amx-editor-video video {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .amx-preview-stages {
    width: 100%;
    height: 100%;
    min-height: 260px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 8px;
  }
  .amx-stage-panel {
    min-width: 0;
    min-height: 0;
    display: grid;
    grid-template-rows: auto 1fr;
    border: 1px solid #1d252b;
    border-radius: 6px;
    overflow: hidden;
    background: #080a0b;
  }
  .amx-stage-title {
    min-height: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 5px 7px;
    background: #14191d;
    color: #f4f7f9;
    font-size: 11px;
    font-weight: 700;
  }
  .amx-stage-title span {
    color: var(--muted);
    font-size: 9px;
    font-weight: 600;
  }
  .amx-stage-body {
    min-height: 0;
    display: grid;
    place-items: center;
    background: #000;
  }
  .amx-stage-body video {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .amx-project-gallery {
    width: 100%;
    height: 100%;
    min-height: 260px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    align-content: start;
    gap: 8px;
    padding: 9px;
    overflow: auto;
    background: #0b0d0f;
  }
  .amx-gallery-card {
    min-width: 0;
    border: 1px solid #2f3941;
    border-radius: 6px;
    background: #151a1e;
    overflow: hidden;
    cursor: grab;
  }
  .amx-gallery-card:hover {
    border-color: rgba(99,210,198,.78);
  }
  .amx-gallery-thumb {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #050607;
    object-fit: cover;
    display: block;
  }
  .amx-gallery-name {
    font-size: 10px;
    color: #e8edf2;
    padding: 5px 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .amx-gallery-empty {
    grid-column: 1 / -1;
    place-self: center;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.45;
  }
  .amx-editor-timeline {
    min-height: 0;
    overflow-x: auto;
    overflow-y: hidden;
    display: grid;
    gap: 0;
    scrollbar-color: #3e595f #101214;
    scrollbar-width: thin;
  }
  .amx-editor-timeline .amx-timebar,
  .amx-editor-timeline .amx-track {
    width: var(--timeline-content-width, 100%);
    min-width: 100%;
  }
  .amx-settings-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 7px;
  }
  .amx-settings-grid label {
    display: grid;
    gap: 3px;
    color: var(--muted);
    font-size: 10px;
  }
  .amx-settings-grid label.wide {
    grid-column: 1 / -1;
  }
  .amx-duration-tools {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .amx-duration-tools label {
    display: grid;
    gap: 3px;
    color: var(--muted);
    font-size: 10px;
  }
  .amx-zoom-readout {
    font-size: 10px;
    color: #c7b98d;
    text-align: right;
  }
  .amx-workflow-panel {
    border: 1px solid var(--line);
    border-radius: 6px;
    background: #1b2023;
    padding: 8px;
    display: grid;
    gap: 8px;
  }
  .amx-workflow-mode,
  .amx-workflow-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .amx-workflow-mode label,
  .amx-label {
    display: grid;
    gap: 3px;
    color: var(--muted);
    font-size: 10px;
  }
  .amx-stage-card {
    border: 1px solid #303840;
    border-radius: 5px;
    background: #15191c;
    padding: 7px;
    display: grid;
    gap: 6px;
  }
  .amx-validation-box {
    display: grid;
    gap: 4px;
    min-height: 24px;
  }
  .amx-warning-line,
  .amx-ok-line {
    border-radius: 5px;
    padding: 5px 7px;
    font-size: 10px;
    line-height: 1.35;
  }
  .amx-warning-line {
    color: #ffd8a0;
    border: 1px solid rgba(240,184,90,.35);
    background: rgba(94,61,12,.32);
  }
  .amx-ok-line {
    color: #b7fff7;
    border: 1px solid rgba(99,210,198,.25);
    background: rgba(17,55,52,.28);
  }
  .amx-help-panel {
    max-width: 920px;
    max-height: 82vh;
    overflow: auto;
    padding: 18px;
    color: #eaf0f5;
    background: #14171a;
    border: 1px solid #3b444c;
    border-radius: 8px;
    box-shadow: 0 20px 70px rgba(0,0,0,.55);
  }
  .amx-help-panel h2 { margin: 0 0 8px; color: #fff4d6; }
  .amx-help-panel h3 { margin: 16px 0 6px; color: #d8fffb; }
  .amx-help-panel p, .amx-help-panel li { font-size: 12px; line-height: 1.55; }
  .amx-help-panel code { color: #ffe0a0; }
`;

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = STYLES;
  document.head.appendChild(style);
}

function icon(path) {
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
}

const ICONS = {
  add: icon(`<path d="M12 5v14"></path><path d="M5 12h14"></path>`),
  split: icon(`<path d="M4 7h8"></path><path d="M4 17h8"></path><path d="M16 4l4 8-4 8"></path>`),
  cut: icon(`<circle cx="6" cy="7" r="3"></circle><circle cx="6" cy="17" r="3"></circle><path d="M8.6 8.6 19 19"></path><path d="M8.6 15.4 19 5"></path>`),
  trash: icon(`<path d="M3 6h18"></path><path d="M8 6V4h8v2"></path><path d="M19 6l-1 14H6L5 6"></path>`),
  retry: icon(`<path d="M21 12a9 9 0 0 1-15.3 6.4"></path><path d="M3 12A9 9 0 0 1 18.3 5.6"></path><path d="M3 5v7h7"></path><path d="M21 19v-7h-7"></path>`),
  audio: icon(`<path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>`),
  prompt: icon(`<path d="M4 4h16v12H5.5L4 18.5V4z"></path><path d="M8 8h8"></path><path d="M8 12h5"></path>`),
  marker: icon(`<path d="M6 4h12v16l-6-3-6 3V4z"></path>`),
  download: icon(`<path d="M12 3v12"></path><path d="m7 10 5 5 5-5"></path><path d="M5 21h14"></path>`),
};

function hideWidget(widget) {
  if (!widget) return;
  widget.hidden = true;
  if (!widget.options) widget.options = {};
  widget.options.hidden = true;
  widget.computeSize = () => [0, 0];
  if (widget.element) widget.element.style.display = "none";
}

function getWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function setWidget(node, name, value) {
  const widget = getWidget(node, name);
  if (!widget) return;
  widget.value = value;
  widget.callback?.(value);
}

function getWidgetValue(node, name, fallback = "") {
  const widget = getWidget(node, name);
  return widget?.value ?? fallback;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function uid(prefix = "seg") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

function cloneData(value) {
  if (typeof structuredClone === "function") return structuredClone(value);
  return JSON.parse(JSON.stringify(value));
}

function parseTimeline(raw, durationFrames) {
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch (_) {
    data = {};
  }
  const timeline = {
    schema: "antimatter-ltx-director-x-timeline-v1",
    segments: Array.isArray(data.segments) ? data.segments : [],
    audioSegments: Array.isArray(data.audioSegments) ? data.audioSegments : [],
    transitions: Array.isArray(data.transitions) ? data.transitions : [],
    assets: Array.isArray(data.assets) ? data.assets : [],
    markers: Array.isArray(data.markers) ? data.markers : [],
    selectedSegmentId: data.selectedSegmentId || "",
    selection: data.selection || { start: 0, end: durationFrames },
    editActions: Array.isArray(data.editActions) ? data.editActions : [],
    zoom: Number(data.zoom || 1),
  };
  timeline.segments = timeline.segments.map((seg, index) => ({
    ...seg,
    id: seg.id || uid("seg"),
    type: seg.type || "image",
    start: Math.max(0, Math.round(Number(seg.start ?? 0))),
    length: Math.max(1, Math.round(Number(seg.length ?? Math.max(1, durationFrames)))),
    prompt: String(seg.prompt || ""),
    imageFile: seg.imageFile || "",
    imageB64: seg.imageB64 || "",
    guideStrength: Number(seg.guideStrength ?? seg.strength ?? 1),
    name: seg.name || `Shot ${index + 1}`,
  })).sort((a, b) => a.start - b.start);
  timeline.audioSegments = timeline.audioSegments.map((seg, index) => ({
    ...seg,
    id: seg.id || uid("aud"),
    type: "audio",
    start: Math.max(0, Math.round(Number(seg.start ?? 0))),
    length: Math.max(1, Math.round(Number(seg.length ?? 24))),
    trimStart: Math.max(0, Math.round(Number(seg.trimStart ?? 0))),
    name: seg.name || `Audio ${index + 1}`,
  })).sort((a, b) => a.start - b.start);
  timeline.transitions = timeline.transitions.map((transition, index) => ({
    ...transition,
    id: transition.id || uid("tr"),
    type: transition.type || "crossfade",
    from: transition.from || "",
    to: transition.to || "",
    start: Math.max(0, Math.round(Number(transition.start ?? 0))),
    length: Math.max(1, Math.round(Number(transition.length ?? Math.max(4, Math.round(durationFrames * 0.04))))),
    name: transition.name || `Transition ${index + 1}`,
  })).sort((a, b) => a.start - b.start);
  timeline.assets = timeline.assets.map((asset, index) => ({
    ...asset,
    id: asset.id || uid("asset"),
    type: asset.type || "image",
    name: asset.name || asset.imageFile || `Image ${index + 1}`,
    imageFile: asset.imageFile || "",
    imageB64: asset.imageB64 || "",
    prompt: String(asset.prompt || ""),
    guideStrength: Number(asset.guideStrength ?? 1),
  })).filter((asset) => asset.imageFile || asset.imageB64);
  if (!timeline.selectedSegmentId) timeline.selectedSegmentId = timeline.segments[0]?.id || "";
  const selected = timeline.segments.find((seg) => seg.id === timeline.selectedSegmentId);
  if (!timeline.selection || timeline.selection.end <= timeline.selection.start) {
    timeline.selection = selected
      ? { start: selected.start, end: selected.start + selected.length }
      : { start: 0, end: Math.max(1, durationFrames) };
  }
  return timeline;
}

async function uploadFile(file, type = "image") {
  const body = new FormData();
  body.append("image", file);
  body.append("overwrite", "false");
  const response = await api.fetchApi("/upload/image", { method: "POST", body });
  if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
  return await response.json();
}

function segmentImageUrl(seg) {
  const raw = String(seg?.imageB64 || "").trim();
  if (raw) {
    if (/^(data:image|https?:|blob:|\/api\/view|\/view\?)/i.test(raw)) return raw;
    if (raw.startsWith("api/view")) return `/${raw}`;
  }
  const file = String(seg?.imageFile || "").trim();
  if (!file) return "";
  const normalized = file.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  const filename = parts.pop() || normalized;
  const subfolder = parts.join("/");
  return `/api/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${encodeURIComponent(subfolder)}`;
}

function galleryAssetKey(asset) {
  return String(asset?.imageFile || asset?.imageB64 || asset?.name || asset?.id || "");
}

function projectGalleryAssets(timeline) {
  const seen = new Set();
  const assets = [];
  const add = (asset) => {
    if (!asset || !(asset.imageFile || asset.imageB64)) return;
    const key = galleryAssetKey(asset);
    if (!key || seen.has(key)) return;
    seen.add(key);
    assets.push({
      id: asset.id || uid("asset"),
      type: "image",
      name: asset.name || asset.imageFile || "Image",
      imageFile: asset.imageFile || "",
      imageB64: asset.imageB64 || "",
      prompt: asset.prompt || "",
      guideStrength: Number(asset.guideStrength ?? 1),
    });
  };
  for (const asset of timeline.assets || []) add(asset);
  for (const seg of timeline.segments || []) {
    if (seg.imageFile || seg.imageB64) add({
      id: `asset_${seg.id}`,
      name: seg.name || seg.imageFile,
      imageFile: seg.imageFile || "",
      imageB64: seg.imageB64 || "",
      prompt: seg.prompt || "",
      guideStrength: Number(seg.guideStrength ?? 1),
    });
  }
  return assets;
}

class DirectorXUI {
  constructor(node, container, domWidget) {
    this.node = node;
    this.container = container;
    this.domWidget = domWidget;
    this.durationFrames = Math.max(1, Math.round(Number(getWidgetValue(node, "duration_frames", 120))));
    this.frameRate = Math.max(1, Number(getWidgetValue(node, "frame_rate", 24)));
    this.timeline = parseTimeline(getWidgetValue(node, "timeline_data", ""), this.durationFrames);
    this.playhead = this.timeline.selection?.start || 0;
    this.renderedPlayheadFrame = this.playhead;
    this.overlayFromPlayhead = this.playhead;
    this.timelineZoom = clamp(Number(this.timeline.zoom || 1), 0.5, 8);
    this.timelineViewport = null;
    this.previewTab = "final";
    this.drag = null;
    this.scrub = null;
    this.trackWidth = 1;
    this.build();
    this.syncAll(false);
    this.render();
  }

  selectedSegment() {
    return this.timeline.segments.find((seg) => seg.id === this.timeline.selectedSegmentId) || this.timeline.segments[0];
  }

  selectedAudio() {
    return this.timeline.audioSegments.find((seg) => seg.id === this.timeline.selectedSegmentId);
  }

  currentSelection() {
    const seg = this.selectedSegment();
    const start = Number(this.timeline.selection?.start ?? seg?.start ?? 0);
    const end = Number(this.timeline.selection?.end ?? (seg ? seg.start + seg.length : this.durationFrames));
    return { start: clamp(Math.round(start), 0, this.durationFrames), end: clamp(Math.round(end), 1, this.durationFrames) };
  }

  videoTailFrame() {
    const segments = this.sortedVideoSegments();
    if (!segments.length) return 0;
    return Math.max(0, ...segments.map((seg) => Math.round(Number(seg.start || 0) + Number(seg.length || 1))));
  }

  defaultClipLength() {
    return Math.max(24, Math.round(this.frameRate * 4));
  }

  appendStartForLength(length) {
    const tail = this.videoTailFrame();
    if (tail >= this.durationFrames) {
      this.setTimelineDuration(tail + Math.max(1, length), false);
    }
    return clamp(tail, 0, Math.max(0, this.durationFrames - 1));
  }

  sortedVideoSegments() {
    return [...(this.timeline.segments || [])].sort((a, b) => (a.start - b.start) || String(a.id).localeCompare(String(b.id)));
  }

  rebuildTransitions() {
    const segments = this.sortedVideoSegments();
    const transitions = [];
    const transitionLength = Math.max(6, Math.round(this.frameRate * 0.5));
    for (let i = 0; i < segments.length - 1; i += 1) {
      const left = segments[i];
      const right = segments[i + 1];
      const boundary = Math.round(Number(left.start || 0) + Number(left.length || 1));
      if (Math.abs(boundary - Number(right.start || 0)) > 1) continue;
      if (left.type !== "image" || right.type !== "image") continue;
      const length = Math.max(2, Math.min(transitionLength, Math.floor(Number(left.length || 1) / 2), Math.floor(Number(right.length || 1) / 2)));
      transitions.push({
        id: `tr_${left.id}_${right.id}`,
        type: "crossfade",
        from: left.id,
        to: right.id,
        start: Math.max(0, boundary - Math.floor(length / 2)),
        length,
        name: "Transition",
      });
    }
    this.timeline.transitions = transitions;
  }

  clampVideoSegmentToLane(seg) {
    if (!seg) return;
    const others = this.sortedVideoSegments().filter((item) => item.id !== seg.id);
    let start = clamp(Math.round(Number(seg.start || 0)), 0, Math.max(0, this.durationFrames - 1));
    const length = Math.max(1, Math.round(Number(seg.length || 1)));
    for (let pass = 0; pass < 3; pass += 1) {
      let changed = false;
      for (const other of others) {
        const otherStart = Math.round(Number(other.start || 0));
        const otherEnd = otherStart + Math.max(1, Math.round(Number(other.length || 1)));
        const overlaps = start < otherEnd && start + length > otherStart;
        if (!overlaps) continue;
        if (start < otherStart) start = Math.max(0, otherStart - length);
        else start = otherEnd;
        changed = true;
      }
      if (!changed) break;
    }
    if (start + length > this.durationFrames) {
      const newDuration = start + length;
      this.setTimelineDuration(newDuration, false);
    }
    seg.start = clamp(start, 0, Math.max(0, this.durationFrames - 1));
    seg.length = Math.min(length, Math.max(1, this.durationFrames - seg.start));
  }

  frameToX(frame) {
    return (frame / Math.max(1, this.durationFrames)) * this.trackWidth;
  }

  xToFrame(x) {
    return clamp(Math.round((x / Math.max(1, this.trackWidth)) * this.durationFrames), 0, this.durationFrames);
  }

  record(action, extra = {}) {
    this.timeline.editActions ||= [];
    this.timeline.editActions.push({
      action,
      at: Date.now(),
      playhead: this.playhead,
      selectedSegmentId: this.timeline.selectedSegmentId,
      ...extra,
    });
    this.timeline.editActions = this.timeline.editActions.slice(-80);
  }

  build() {
    ensureStyles();
    this.container.innerHTML = "";
    this.root = document.createElement("div");
    this.root.className = "amx";
    this.container.appendChild(this.root);

    const top = document.createElement("div");
    top.className = "amx-top";
    top.innerHTML = `<div class="amx-title">Antimatter Ltx Director X</div>`;
    this.status = document.createElement("div");
    this.status.className = "amx-status";
    top.appendChild(this.status);
    this.root.appendChild(top);

    const tools = document.createElement("div");
    tools.className = "amx-tools";
    this.root.appendChild(tools);

    this.imageInput = document.createElement("input");
    this.imageInput.type = "file";
    this.imageInput.accept = "image/*";
    this.imageInput.className = "amx-file";
    this.imageInput.addEventListener("change", (event) => this.handleImageFile(event.target.files?.[0]));
    this.root.appendChild(this.imageInput);

    this.audioInput = document.createElement("input");
    this.audioInput.type = "file";
    this.audioInput.accept = "audio/*,video/*";
    this.audioInput.className = "amx-file";
    this.audioInput.addEventListener("change", (event) => this.handleAudioFile(event.target.files?.[0]));
    this.root.appendChild(this.audioInput);

    const buttons = [
      ["Add Shot", ICONS.add, () => this.addSegment()],
      ["Image", ICONS.add, () => this.imageInput.click()],
      ["Audio", ICONS.audio, () => this.audioInput.click()],
      ["Split", ICONS.split, () => this.splitAtPlayhead()],
      ["Cut", ICONS.cut, () => this.cutSelection()],
      ["Ripple Delete", ICONS.trash, () => this.rippleDelete()],
      ["Detach Audio", ICONS.audio, () => this.detachAudio()],
      ["Marker", ICONS.marker, () => this.addMarker()],
      ["AI Assistant Prompt", ICONS.prompt, () => this.applyPromptRequest()],
      ["Retry This", ICONS.retry, () => this.retrySelection(), "primary"],
    ];
    for (const [label, svg, handler, kind] of buttons) {
      const btn = document.createElement("button");
      btn.className = `amx-btn ${kind || ""}`;
      btn.innerHTML = `${svg}<span>${label}</span>`;
      btn.title = label;
      btn.addEventListener("click", handler);
      tools.appendChild(btn);
    }

    this.timebar = document.createElement("div");
    this.timebar.className = "amx-timebar";
    this.timebar.addEventListener("pointerdown", (event) => this.seekFromEvent(event));
    this.timebar.addEventListener("wheel", (event) => this.handleTimelineWheel(event), { passive: false });
    this.root.appendChild(this.timebar);

    this.videoTrack = document.createElement("div");
    this.videoTrack.className = "amx-track video";
    this.videoTrack.innerHTML = `<div class="amx-track-label">Video / image guide lane</div>`;
    this.videoTrack.addEventListener("pointerdown", (event) => this.trackPointerDown(event, "video"));
    this.videoTrack.addEventListener("wheel", (event) => this.handleTimelineWheel(event), { passive: false });
    this.videoTrack.addEventListener("dragover", (event) => this.galleryDragOver(event));
    this.videoTrack.addEventListener("drop", (event) => this.dropGalleryAsset(event));
    this.root.appendChild(this.videoTrack);

    this.audioTrack = document.createElement("div");
    this.audioTrack.className = "amx-track audio";
    this.audioTrack.innerHTML = `<div class="amx-track-label">Detached audio lane</div>`;
    this.audioTrack.addEventListener("pointerdown", (event) => this.trackPointerDown(event, "audio"));
    this.audioTrack.addEventListener("wheel", (event) => this.handleTimelineWheel(event), { passive: false });
    this.root.appendChild(this.audioTrack);

    const props = document.createElement("div");
    props.className = "amx-props";
    this.root.appendChild(props);

    this.promptInspector = document.createElement("div");
    this.promptInspector.className = "amx-prompt-inspector";
    this.promptInspector.innerHTML = `
      <div class="amx-prompt-head">
        <span class="amx-prompt-title">Selected shot prompt</span>
        <div class="amx-prompt-actions">
          <button class="amx-btn primary" data-prompt-action="ai">AI Assistant Prompt</button>
          <button class="amx-btn" data-prompt-action="apply">Apply</button>
        </div>
      </div>
    `;
    this.promptTitle = this.promptInspector.querySelector(".amx-prompt-title");
    this.promptBox = document.createElement("textarea");
    this.promptBox.className = "amx-textarea";
    this.promptBox.placeholder = "Selected shot prompt";
    this.promptBox.addEventListener("input", () => {
      const seg = this.selectedSegment();
      if (seg) seg.prompt = this.promptBox.value;
      this.syncAll();
    });
    this.promptInspector.appendChild(this.promptBox);
    this.promptInspector.querySelector('[data-prompt-action="ai"]').addEventListener("click", () => this.applyPromptRequest());
    this.promptInspector.querySelector('[data-prompt-action="apply"]').addEventListener("click", () => {
      const seg = this.selectedSegment();
      if (seg) seg.prompt = this.promptBox.value;
      this.record("apply_prompt", { id: seg?.id || "" });
      this.syncAll();
      this.render();
    });
    props.appendChild(this.promptInspector);

    const side = document.createElement("div");
    side.className = "amx-side";
    props.appendChild(side);
    side.innerHTML = `
      <label class="amx-label">Start frame<input class="amx-input" data-field="start" type="number" min="0"></label>
      <label class="amx-label">Length<input class="amx-input" data-field="length" type="number" min="1"></label>
      <label class="amx-label">Guide strength<input class="amx-input" data-field="guideStrength" type="number" min="0" max="2" step="0.01"></label>
      <label class="amx-label">Selection in/out<input class="amx-input" data-field="selection" type="text"></label>
      <div class="amx-small">Tip: select a range, press Retry This, then queue only the selected fragment.</div>
    `;
    for (const input of side.querySelectorAll("input")) {
      input.addEventListener("change", () => this.updateFromInspector(input));
    }

    window.addEventListener("pointermove", this.onPointerMove = (event) => this.pointerMove(event));
    window.addEventListener("pointerup", this.onPointerUp = () => this.pointerUp());
  }

  destroy() {
    window.removeEventListener("pointermove", this.onPointerMove);
    window.removeEventListener("pointerup", this.onPointerUp);
  }

  resizeInfo() {
    const visibleWidth = Math.max(
      1,
      this.timelineViewport?.clientWidth ||
        this.videoTrack?.parentElement?.clientWidth ||
        this.videoTrack?.clientWidth ||
        1
    );
    this.timelineZoom = clamp(Number(this.timelineZoom || 1), 0.5, 8);
    this.trackWidth = Math.max(1, visibleWidth * this.timelineZoom);
    if (this.timelineViewport) {
      this.timelineViewport.style.setProperty("--timeline-content-width", `${this.trackWidth}px`);
    }
    this.durationFrames = Math.max(1, Math.round(Number(getWidgetValue(this.node, "duration_frames", this.durationFrames))));
    this.frameRate = Math.max(1, Number(getWidgetValue(this.node, "frame_rate", this.frameRate)));
  }

  render() {
    this.resizeInfo();
    this.rebuildTransitions();
    this.overlayFromPlayhead = Number.isFinite(this.renderedPlayheadFrame) ? this.renderedPlayheadFrame : this.playhead;
    this.renderRuler();
    this.renderTimebarPlayhead();
    this.renderTrack(this.videoTrack, this.timeline.segments, "video");
    this.renderTrack(this.audioTrack, this.timeline.audioSegments, "audio");
    this.renderOverlay(this.videoTrack);
    this.renderOverlay(this.audioTrack);
    this.renderedPlayheadFrame = this.playhead;
    this.overlayFromPlayhead = null;
    this.updateInspector();
    if (this.previewTab === "gallery") this.renderProjectGallery();
    this.updateStatus();
    this.updateDurationControls();
    this.updateResolutionControls?.();
    this.domWidget?.callback?.();
    app.graph?.setDirtyCanvas(true, true);
  }

  renderRuler() {
    this.timebar.innerHTML = "";
    const major = this.durationFrames > 360 ? Math.round(this.frameRate * 2) : Math.round(this.frameRate);
    const step = Math.max(1, major);
    for (let f = 0; f <= this.durationFrames; f += step) {
      const tick = document.createElement("div");
      tick.className = "amx-ruler-tick";
      tick.style.left = `${this.frameToX(f)}px`;
      this.timebar.appendChild(tick);
      const label = document.createElement("div");
      label.className = "amx-ruler-label";
      label.style.left = `${this.frameToX(f)}px`;
      label.textContent = `${(f / this.frameRate).toFixed(1)}s`;
      this.timebar.appendChild(label);
    }
  }

  renderPlayheadElement(host, className) {
    if (!host) return;
    const fromFrame = Number.isFinite(this.overlayFromPlayhead) ? this.overlayFromPlayhead : this.playhead;
    const fromX = this.frameToX(fromFrame);
    const targetX = this.frameToX(this.playhead);
    const el = document.createElement("div");
    el.className = className;
    el.style.transitionDuration = `${this.scrub || this.drag ? 70 : 190}ms`;
    el.style.transform = `translateX(${fromX}px)`;
    host.appendChild(el);
    if (Math.abs(fromX - targetX) <= 0.5) {
      el.style.transform = `translateX(${targetX}px)`;
      return;
    }
    requestAnimationFrame(() => {
      if (el.isConnected) el.style.transform = `translateX(${targetX}px)`;
    });
  }

  renderTimebarPlayhead() {
    this.renderPlayheadElement(this.timebar, "amx-ruler-playhead");
  }

  renderOverlay(track) {
    const sel = this.currentSelection();
    const range = document.createElement("div");
    range.className = "amx-range";
    range.style.left = `${this.frameToX(sel.start)}px`;
    range.style.width = `${Math.max(2, this.frameToX(sel.end) - this.frameToX(sel.start))}px`;
    track.appendChild(range);

    this.renderPlayheadElement(track, "amx-playhead");
  }

  updateStatus() {
    const sel = this.currentSelection();
    if (this.status) {
      this.status.textContent = `${this.timeline.segments.length} shots | ${this.timeline.audioSegments.length} audio | selection ${sel.start}-${sel.end}f`;
    }
  }

  updateSelectionField() {
    const input = this.root?.querySelector('[data-field="selection"]');
    if (!input) return;
    const sel = this.currentSelection();
    input.value = `${sel.start}-${sel.end}`;
  }

  refreshTimelineOverlays() {
    this.resizeInfo();
    this.overlayFromPlayhead = Number.isFinite(this.renderedPlayheadFrame) ? this.renderedPlayheadFrame : this.playhead;
    this.timebar?.querySelectorAll(".amx-ruler-playhead").forEach((el) => el.remove());
    for (const track of [this.videoTrack, this.audioTrack]) {
      track?.querySelectorAll(".amx-range, .amx-playhead").forEach((el) => el.remove());
    }
    this.renderTimebarPlayhead();
    this.renderOverlay(this.videoTrack);
    this.renderOverlay(this.audioTrack);
    this.renderedPlayheadFrame = this.playhead;
    this.overlayFromPlayhead = null;
    this.updateSelectionField();
    this.updateStatus();
    this.updateDurationControls();
    this.domWidget?.callback?.();
    app.graph?.setDirtyCanvas(true, true);
  }

  renderTrack(track, segments, kind) {
    const label = track.querySelector(".amx-track-label")?.outerHTML || "";
    track.innerHTML = label;
    for (const seg of segments) {
      const thumbUrl = kind === "video" ? segmentImageUrl(seg) : "";
      const el = document.createElement("div");
      el.className = `amx-segment ${thumbUrl ? "has-thumb" : ""} ${this.timeline.selectedSegmentId === seg.id ? "selected" : ""}`;
      el.dataset.id = seg.id;
      el.dataset.kind = kind;
      el.style.left = `${this.frameToX(seg.start)}px`;
      el.style.width = `${Math.max(10, this.frameToX(seg.start + seg.length) - this.frameToX(seg.start))}px`;
      el.innerHTML = `
        ${thumbUrl ? `<img class="amx-thumb" src="${thumbUrl}" loading="lazy" draggable="false">` : ""}
        <div class="amx-handle left" data-handle="left"></div>
        <div class="amx-seg-name">${seg.name || seg.imageFile || seg.audioFile || seg.id}</div>
        <div class="amx-handle right" data-handle="right"></div>
      `;
      el.addEventListener("pointerdown", (event) => this.segmentPointerDown(event, seg, kind));
      el.addEventListener("dblclick", () => {
        this.playhead = seg.start + Math.floor(seg.length / 2);
        this.splitAtPlayhead();
      });
      track.appendChild(el);
    }
    if (kind === "video") {
      for (const tr of this.timeline.transitions || []) {
        const el = document.createElement("div");
        el.className = "amx-transition";
        el.style.left = `${this.frameToX(tr.start)}px`;
        el.style.width = `${Math.max(12, this.frameToX(tr.start + tr.length) - this.frameToX(tr.start))}px`;
        el.innerHTML = "<span>FX</span>";
        el.title = `${tr.name || "Transition"} ${tr.length}f`;
        track.appendChild(el);
      }
    }
  }

  updateInspector() {
    const seg = this.selectedSegment();
    if (!seg) {
      if (this.promptTitle) this.promptTitle.textContent = "No shot selected";
      if (this.promptBox) this.promptBox.value = "";
      for (const selector of ['[data-field="start"]', '[data-field="length"]', '[data-field="guideStrength"]']) {
        const input = this.root?.querySelector(selector);
        if (input) input.value = "";
      }
      const selectionInput = this.root?.querySelector('[data-field="selection"]');
      if (selectionInput) {
        const sel = this.currentSelection();
        selectionInput.value = `${sel.start}-${sel.end}`;
      }
      return;
    }
    if (this.promptTitle) {
      this.promptTitle.textContent = `${seg.name || seg.imageFile || seg.id} | ${seg.start}-${seg.start + seg.length}f`;
    }
    this.promptBox.value = seg.prompt || "";
    this.root.querySelector('[data-field="start"]').value = seg.start;
    this.root.querySelector('[data-field="length"]').value = seg.length;
    this.root.querySelector('[data-field="guideStrength"]').value = Number(seg.guideStrength ?? 1).toFixed(2);
    const sel = this.currentSelection();
    this.root.querySelector('[data-field="selection"]').value = `${sel.start}-${sel.end}`;
  }

  updateFromInspector(input) {
    const seg = this.selectedSegment();
    if (!seg) return;
    const field = input.dataset.field;
    if (field === "start") seg.start = clamp(Math.round(Number(input.value || 0)), 0, this.durationFrames - 1);
    if (field === "length") seg.length = Math.max(1, Math.round(Number(input.value || 1)));
    if (field === "guideStrength") seg.guideStrength = Number(input.value || 1);
    if (field === "selection") {
      const match = String(input.value || "").match(/(\d+)\s*[-:]\s*(\d+)/);
      if (match) {
        this.timeline.selection = {
          start: clamp(Number(match[1]), 0, this.durationFrames),
          end: clamp(Number(match[2]), 1, this.durationFrames),
        };
      }
    } else {
      this.timeline.selection = { start: seg.start, end: Math.min(this.durationFrames, seg.start + seg.length) };
    }
    this.record("inspect_edit", { field });
    this.syncAll();
    this.render();
  }

  syncAll(markDirty = true) {
    this.rebuildTransitions();
    const segments = [...this.timeline.segments].sort((a, b) => a.start - b.start);
    const prompts = segments.map((seg) => String(seg.prompt || "Cinematic image-to-video continuation with stable identity."));
    const lengths = segments.map((seg) => Math.max(1, Math.round(Number(seg.length || 1))).toString());
    const strengths = segments.map((seg) => Number(seg.guideStrength ?? seg.strength ?? 1).toFixed(4));
    const sel = this.currentSelection();
    this.timeline.zoom = Number(this.timelineZoom || 1);
    const json = JSON.stringify(this.timeline);

    setWidget(this.node, "timeline_data", json);
    setWidget(this.node, "local_prompts", prompts.join(" | "));
    setWidget(this.node, "segment_lengths", lengths.join(","));
    setWidget(this.node, "guide_strength", strengths.join(","));
    setWidget(this.node, "selected_segment_id", this.timeline.selectedSegmentId || "");
    setWidget(this.node, "selection_start_frame", sel.start);
    setWidget(this.node, "selection_end_frame", sel.end);
    setWidget(this.node, "timeline_edit_actions", JSON.stringify(this.timeline.editActions || []));
    setWidget(this.node, "duration_frames", this.durationFrames);
    setWidget(this.node, "duration_seconds", this.durationFrames / this.frameRate);

    if (markDirty) app.graph?.setDirtyCanvas(true, true);
  }

  selectSegment(seg, kind = "video") {
    this.timeline.selectedSegmentId = seg.id;
    this.timeline.selection = { start: seg.start, end: Math.min(this.durationFrames, seg.start + seg.length) };
    this.playhead = seg.start;
    if (kind === "video") this.promptBox.value = seg.prompt || "";
    this.syncAll();
    this.render();
  }

  setPlayhead(frame, options = {}) {
    const next = clamp(Math.round(Number(frame || 0)), 0, this.durationFrames);
    this.playhead = next;
    if (options.extend) {
      const anchor = clamp(Math.round(Number(options.anchor ?? this.currentSelection().start)), 0, this.durationFrames);
      const end = clamp(Math.max(anchor + 1, next), 1, this.durationFrames);
      this.timeline.selection = {
        start: clamp(Math.min(anchor, next, end - 1), 0, Math.max(0, this.durationFrames - 1)),
        end,
      };
    }
    this.syncAll(false);
    this.refreshTimelineOverlays();
  }

  handleTimelineWheel(event) {
    event.preventDefault();
    const clientX = event.clientX;
    const beforeFrame = this.xToFrame(clientX - this.videoTrack.getBoundingClientRect().left);
    const factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
    const nextZoom = clamp(this.timelineZoom * factor, 0.5, 8);
    if (Math.abs(nextZoom - this.timelineZoom) < 0.001) return;
    this.timelineZoom = nextZoom;
    this.timeline.zoom = this.timelineZoom;
    this.render();
    const viewport = this.timelineViewport;
    if (viewport) {
      requestAnimationFrame(() => {
        const rect = viewport.getBoundingClientRect();
        const targetX = this.frameToX(beforeFrame);
        viewport.scrollLeft = clamp(targetX - (clientX - rect.left), 0, Math.max(0, viewport.scrollWidth - viewport.clientWidth));
      });
    }
    this.syncAll(false);
  }

  setTimelineDuration(frames, recordAction = true) {
    const nextFrames = clamp(Math.round(Number(frames || 1)), 1, 20000);
    this.durationFrames = nextFrames;
    const clampSegment = (seg) => {
      seg.start = clamp(Math.round(Number(seg.start || 0)), 0, Math.max(0, nextFrames - 1));
      seg.length = Math.max(1, Math.min(Math.round(Number(seg.length || 1)), nextFrames - seg.start));
    };
    for (const seg of this.timeline.segments || []) clampSegment(seg);
    for (const seg of this.timeline.audioSegments || []) clampSegment(seg);
    this.playhead = clamp(this.playhead, 0, nextFrames);
    const sel = this.currentSelection();
    this.timeline.selection = {
      start: clamp(sel.start, 0, Math.max(0, nextFrames - 1)),
      end: clamp(Math.max(sel.start + 1, sel.end), 1, nextFrames),
    };
    if (recordAction) this.record("set_timeline_duration", { durationFrames: nextFrames });
    this.syncAll();
    this.render();
  }

  updateDurationControls() {
    if (this.durationFramesInput && document.activeElement !== this.durationFramesInput) {
      this.durationFramesInput.value = String(this.durationFrames);
    }
    if (this.durationSecondsInput && document.activeElement !== this.durationSecondsInput) {
      this.durationSecondsInput.value = (this.durationFrames / Math.max(1, this.frameRate)).toFixed(2);
    }
    if (this.zoomReadout) this.zoomReadout.textContent = `Timeline zoom ${(this.timelineZoom * 100).toFixed(0)}%`;
  }

  rememberAsset(asset) {
    if (!asset || !(asset.imageFile || asset.imageB64)) return;
    this.timeline.assets ||= [];
    const key = galleryAssetKey(asset);
    if (this.timeline.assets.some((item) => galleryAssetKey(item) === key)) return;
    this.timeline.assets.push({
      id: asset.id || uid("asset"),
      type: "image",
      name: asset.name || asset.imageFile || "Image",
      imageFile: asset.imageFile || "",
      imageB64: asset.imageB64 || "",
      prompt: asset.prompt || "",
      guideStrength: Number(asset.guideStrength ?? 1),
    });
  }

  createSegmentFromAsset(asset, startFrame = null) {
    const requestedLength = this.defaultClipLength();
    const start = startFrame == null
      ? this.appendStartForLength(requestedLength)
      : clamp(Math.round(Number(startFrame || 0)), 0, Math.max(0, this.durationFrames - 1));
    const length = Math.min(requestedLength, Math.max(1, this.durationFrames - start));
    const seg = {
      id: uid("seg"),
      type: "image",
      start,
      length,
      prompt: asset.prompt || "",
      guideStrength: Number(asset.guideStrength ?? 1),
      imageFile: asset.imageFile || "",
      imageB64: asset.imageB64 || "",
      name: asset.name || asset.imageFile || `Shot ${this.timeline.segments.length + 1}`,
    };
    this.timeline.segments.push(seg);
    this.clampVideoSegmentToLane(seg);
    this.rememberAsset(asset);
    this.record("gallery_drop_image", { id: seg.id, source: galleryAssetKey(asset), frame: start });
    this.selectSegment(seg);
  }

  galleryDragOver(event) {
    const hasAsset = Array.from(event.dataTransfer?.types || []).includes("application/x-antimatter-gallery-asset") ||
      Array.from(event.dataTransfer?.types || []).includes("text/plain");
    if (!hasAsset) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }

  dropGalleryAsset(event) {
    const raw = event.dataTransfer?.getData("application/x-antimatter-gallery-asset") || event.dataTransfer?.getData("text/plain");
    if (!raw) return;
    let asset = null;
    try {
      asset = JSON.parse(raw);
    } catch (_) {
      return;
    }
    if (!asset?.imageFile && !asset?.imageB64) return;
    event.preventDefault();
    this.createSegmentFromAsset(asset);
  }

  beginScrub(event, target) {
    if (event.button != null && event.button !== 0) return;
    event.preventDefault();
    const sel = this.currentSelection();
    this.scrub = {
      target,
      extend: event.shiftKey,
      anchor: event.shiftKey ? sel.start : this.playhead,
      startFrame: this.playhead,
    };
    this.root?.classList.add("is-scrubbing");
    target.setPointerCapture?.(event.pointerId);
    this.updatePlayheadFromPointer(event);
  }

  updatePlayheadFromPointer(event) {
    const target = this.scrub?.target || this.timebar;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const frame = this.xToFrame(event.clientX - rect.left);
    this.setPlayhead(frame, {
      extend: Boolean(this.scrub?.extend || event.shiftKey),
      anchor: this.scrub?.anchor,
    });
  }

  seekFromEvent(event) {
    this.beginScrub(event, event.currentTarget);
  }

  trackPointerDown(event, kind) {
    if (event.target !== event.currentTarget) return;
    this.beginScrub(event, event.currentTarget);
  }

  segmentPointerDown(event, seg, kind) {
    event.stopPropagation();
    this.selectSegment(seg, kind);
    const handle = event.target?.dataset?.handle || "move";
    this.drag = {
      id: seg.id,
      kind,
      handle,
      startX: event.clientX,
      originalStart: seg.start,
      originalLength: seg.length,
      playheadOffset: this.playhead - seg.start,
    };
    this.root?.classList.add("is-dragging");
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  pointerMove(event) {
    if (this.scrub) {
      this.updatePlayheadFromPointer(event);
      return;
    }
    if (!this.drag) return;
    const list = this.drag.kind === "audio" ? this.timeline.audioSegments : this.timeline.segments;
    const seg = list.find((item) => item.id === this.drag.id);
    if (!seg) return;
    const deltaFrames = this.xToFrame(event.clientX - this.videoTrack.getBoundingClientRect().left) -
      this.xToFrame(this.drag.startX - this.videoTrack.getBoundingClientRect().left);
    if (this.drag.handle === "left") {
      const newStart = clamp(this.drag.originalStart + deltaFrames, 0, this.drag.originalStart + this.drag.originalLength - 1);
      seg.length = Math.max(1, this.drag.originalLength + (this.drag.originalStart - newStart));
      seg.start = newStart;
    } else if (this.drag.handle === "right") {
      seg.length = Math.max(1, this.drag.originalLength + deltaFrames);
    } else {
      seg.start = clamp(this.drag.originalStart + deltaFrames, 0, Math.max(0, this.durationFrames - 1));
    }
    if (this.drag.kind === "video") this.clampVideoSegmentToLane(seg);
    this.timeline.selection = { start: seg.start, end: Math.min(this.durationFrames, seg.start + seg.length) };
    this.playhead = clamp(seg.start + Number(this.drag.playheadOffset || 0), 0, this.durationFrames);
    this.syncAll();
    this.render();
  }

  pointerUp() {
    if (this.scrub) {
      const scrub = this.scrub;
      this.scrub = null;
      this.root?.classList.remove("is-scrubbing");
      if (scrub.startFrame !== this.playhead) this.record("scrub_playhead", { frame: this.playhead });
      this.syncAll();
      return;
    }
    if (!this.drag) return;
    this.record("drag_segment", { id: this.drag.id, kind: this.drag.kind, handle: this.drag.handle });
    this.drag = null;
    this.root?.classList.remove("is-dragging");
    this.syncAll();
  }

  addSegment() {
    const length = Math.max(8, Math.round(this.frameRate * 3));
    const start = this.appendStartForLength(length);
    const seg = {
      id: uid("seg"),
      type: "image",
      start,
      length: Math.min(length, Math.max(1, this.durationFrames - start)),
      prompt: "Describe the shot action here.",
      guideStrength: 1,
      name: `Shot ${this.timeline.segments.length + 1}`,
    };
    this.timeline.segments.push(seg);
    this.clampVideoSegmentToLane(seg);
    this.record("add_segment", { id: seg.id });
    this.selectSegment(seg);
  }

  async handleImageFile(file) {
    if (!file) return;
    try {
      const uploaded = await uploadFile(file, "image");
      const filename = uploaded.name || uploaded.filename || file.name;
      const subfolder = uploaded.subfolder || "";
      const inputPath = subfolder ? `${subfolder}/${filename}` : filename;
      const requestedLength = this.defaultClipLength();
      const start = this.appendStartForLength(requestedLength);
      const seg = {
        id: uid("seg"),
        type: "image",
        start,
        length: Math.min(requestedLength, Math.max(1, this.durationFrames - start)),
        prompt: "",
        guideStrength: 1,
        imageFile: inputPath,
        imageB64: `/api/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${encodeURIComponent(subfolder)}`,
        name: file.name,
      };
      this.rememberAsset(seg);
      this.timeline.segments.push(seg);
      this.clampVideoSegmentToLane(seg);
      this.record("add_image", { id: seg.id, file: file.name });
      this.selectSegment(seg);
    } catch (err) {
      console.error("[Antimatter Ltx Director X] image upload failed", err);
    } finally {
      this.imageInput.value = "";
    }
  }

  async handleAudioFile(file) {
    if (!file) return;
    try {
      const uploaded = await uploadFile(file, "audio");
      const filename = uploaded.name || uploaded.filename || file.name;
      const subfolder = uploaded.subfolder || "";
      const inputPath = subfolder ? `${subfolder}/${filename}` : filename;
      const seg = {
        id: uid("aud"),
        type: "audio",
        start: this.playhead,
        length: Math.max(24, Math.round(this.frameRate * 4)),
        trimStart: 0,
        audioFile: inputPath,
        name: file.name,
      };
      this.timeline.audioSegments.push(seg);
      this.timeline.selectedSegmentId = seg.id;
      this.timeline.selection = { start: seg.start, end: Math.min(this.durationFrames, seg.start + seg.length) };
      setWidget(this.node, "use_custom_audio", true);
      this.record("add_audio", { id: seg.id, file: file.name });
      this.syncAll();
      this.render();
    } catch (err) {
      console.error("[Antimatter Ltx Director X] audio upload failed", err);
    } finally {
      this.audioInput.value = "";
    }
  }

  splitAtPlayhead() {
    const seg = this.selectedSegment();
    if (!seg) return;
    if (this.playhead <= seg.start || this.playhead >= seg.start + seg.length) return;
    const rightLength = seg.start + seg.length - this.playhead;
    seg.length = this.playhead - seg.start;
    const right = {
      ...cloneData(seg),
      id: uid("seg"),
      start: this.playhead,
      length: rightLength,
      name: `${seg.name || "Shot"} B`,
    };
    this.timeline.segments.push(right);
    this.clampVideoSegmentToLane(right);
    this.record("split_segment", { id: seg.id, newId: right.id, frame: this.playhead });
    this.selectSegment(right);
  }

  cutSelection() {
    const sel = this.currentSelection();
    if (sel.end <= sel.start) return;
    const next = [];
    for (const seg of this.timeline.segments) {
      const segEnd = seg.start + seg.length;
      if (segEnd <= sel.start || seg.start >= sel.end) {
        next.push(seg);
        continue;
      }
      if (seg.start < sel.start) {
        next.push({ ...seg, id: uid("seg"), length: sel.start - seg.start, name: `${seg.name || "Shot"} head` });
      }
      if (segEnd > sel.end) {
        next.push({ ...seg, id: uid("seg"), start: sel.end, length: segEnd - sel.end, name: `${seg.name || "Shot"} tail` });
      }
    }
    this.timeline.segments = next.sort((a, b) => a.start - b.start);
    this.rebuildTransitions();
    if (this.timeline.segments[0]) this.timeline.selectedSegmentId = this.timeline.segments[0].id;
    this.record("cut_selection", sel);
    this.syncAll();
    this.render();
  }

  rippleDelete() {
    const sel = this.currentSelection();
    const gap = Math.max(0, sel.end - sel.start);
    this.cutSelection();
    for (const seg of this.timeline.segments) {
      if (seg.start >= sel.end) seg.start = Math.max(0, seg.start - gap);
    }
    for (const seg of this.timeline.audioSegments) {
      if (seg.start >= sel.end) seg.start = Math.max(0, seg.start - gap);
    }
    this.durationFrames = Math.max(1, this.durationFrames - gap);
    setWidget(this.node, "duration_frames", this.durationFrames);
    this.record("ripple_delete", sel);
    this.rebuildTransitions();
    this.syncAll();
    this.render();
  }

  detachAudio() {
    const seg = this.selectedSegment();
    if (!seg) return;
    const audio = {
      id: uid("aud"),
      type: "audio",
      start: seg.start,
      length: seg.length,
      trimStart: 0,
      name: `Detached ${seg.name || seg.id}`,
      sourceSegmentId: seg.id,
      audioFile: seg.audioFile || "",
      mutedPlaceholder: !seg.audioFile,
    };
    this.timeline.audioSegments.push(audio);
    setWidget(this.node, "use_custom_audio", true);
    this.record("detach_audio", { source: seg.id, id: audio.id });
    this.syncAll();
    this.render();
  }

  addMarker() {
    this.timeline.markers ||= [];
    this.timeline.markers.push({ id: uid("mark"), frame: this.playhead, label: `M${this.timeline.markers.length + 1}` });
    this.record("add_marker", { frame: this.playhead });
    this.syncAll();
    this.render();
  }

  applyPromptRequest() {
    const seg = this.selectedSegment();
    if (!seg) return;
    const userAction = String(getWidgetValue(this.node, "user_action", "") || "").trim();
    const imageDescription = String(getWidgetValue(this.node, "image_description", "") || "").trim();
    const joy = String(getWidgetValue(this.node, "joy_caption_text", "") || "").trim();
    const existing = String(seg.prompt || "").trim();
    const source = seg.imageFile || seg.name || seg.id;
    const parts = [
      "[VISUAL]",
      `Source clip: ${source}.`,
      imageDescription || "Preserve the source image identity, environment, lighting, clothing, and props.",
      joy ? `JoyCaption: ${joy}` : "",
      existing ? `Current prompt context: ${existing}` : "",
      "",
      "[ACTION]",
      userAction || "Animate this into a coherent cinematic beat.",
      "",
      "[CINEMATOGRAPHY]",
      `${getWidgetValue(this.node, "shot_type", "medium_shot")} with ${getWidgetValue(this.node, "camera_motion", "slow_push_in")}.`,
      "",
      "[SOUNDS]",
      "Natural environmental sound and subtle motion cues.",
    ].filter(Boolean);
    seg.prompt = parts.join("\n");
    this.promptBox.value = seg.prompt;
    this.record("local_prompt_assist", { id: seg.id });
    this.syncAll();
    this.render();
  }

  retrySelection() {
    const sel = this.currentSelection();
    setWidget(this.node, "render_scope", "selected_fragment_only");
    setWidget(this.node, "selection_start_frame", sel.start);
    setWidget(this.node, "selection_end_frame", sel.end);
    const retryWidget = getWidget(this.node, "retry_count");
    if (retryWidget) setWidget(this.node, "retry_count", Number(retryWidget.value || 0) + 1);
    this.record("retry_selection", sel);
    this.syncAll();
    this.render();
  }
}

function parseProLoraState(raw) {
  const state = {};
  for (const spec of PRO_LORAS) state[spec.id] = { enabled: spec.enabled, strength: spec.strength };
  try {
    const data = raw ? JSON.parse(raw) : {};
    for (const item of data.loras || []) {
      if (!item?.id || !state[item.id]) continue;
      state[item.id] = {
        enabled: Boolean(item.enabled),
        strength: Number(item.strength ?? state[item.id].strength),
      };
    }
  } catch (_) {}
  return state;
}

function normalizeCameraMode(mode) {
  const value = String(mode || "off");
  const aliases = { push_in: "dolly_in", truck: "dolly_right", orbit: "custom", handheld: "custom" };
  const normalized = aliases[value] || value;
  return CAMERA_MODE_OPTIONS.some(([id]) => id === normalized) ? normalized : "off";
}

function cameraLoraIdForMode(mode) {
  return CAMERA_LORA_MODE_MAP[normalizeCameraMode(mode)] || "";
}

function enforceCameraExclusive(loraState, cameraState) {
  const mode = normalizeCameraMode(cameraState?.mode || "off");
  const selectedCameraLora = cameraLoraIdForMode(mode);
  for (const id of CAMERA_LORA_IDS) {
    if (!loraState[id]) continue;
    loraState[id].enabled = id === selectedCameraLora && mode !== "off";
    if (loraState[id].enabled) {
      const spec = PRO_LORAS.find((item) => item.id === id);
      loraState[id].strength = Math.max(Number(loraState[id].strength || 0), Number(spec?.strength || 0.8));
    }
  }
  if (loraState.camera_control) {
    loraState.camera_control.enabled = mode !== "off";
    if (loraState.camera_control.enabled) loraState.camera_control.strength = Math.max(Number(loraState.camera_control.strength || 0), 0.75);
  }
  return loraState;
}

function defaultCameraState() {
  return {
    schema: "antimatter-ltx-director-x-pro-camera-v1",
    mode: "off",
    yaw: 0,
    pitch: 0,
    roll: 0,
    zoom: 1,
    truck: 0,
    pedestal: 0,
    dolly: 0,
    focalLength: 35,
    manualOverride: false,
  };
}

function parseCameraState(raw) {
  try {
    const state = { ...defaultCameraState(), ...(raw ? JSON.parse(raw) : {}) };
    state.mode = normalizeCameraMode(state.mode);
    return state;
  } catch (_) {
    return defaultCameraState();
  }
}

function defaultProSettings() {
  const paths = {
    ltx_checkpoint: "models/checkpoints/LTX/ltx-2.3-22b-dev-fp8.safetensors",
    text_encoder: "models/text_encoders/gemma_3_12B_it_fp8_e4m3fn.safetensors",
    text_projection: "models/text_encoders/ltx-2.3_text_projection_bf16.safetensors",
    video_vae: "models/vae/LTX23_video_vae_bf16.safetensors",
    audio_vae: "models/vae/LTX23_audio_vae_bf16.safetensors",
    tiny_vae: "models/vae/taeltx2_3.safetensors",
    distilled_lora: "models/loras/LTX/ltx-2.3-22b-distilled-lora-384-1.1.safetensors",
    union_control_lora: "models/loras/LTX/ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors",
    motion_track_lora: "models/loras/LTX/ltx-2.3-22b-ic-lora-motion-track-control-ref0.5.safetensors",
    lipdub_lora: "models/loras/LTX/ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors",
    transition_lora: "models/loras/LTX/ltx2.3-transition.safetensors",
    camera_control_lora: "models/loras/LTX/CAMERA/LTX2.3_CameraControls.safetensors",
    detailer_lora: "models/loras/LTX/ltx-2-19b-ic-lora-detailer.safetensors",
    pose_control_lora: "models/loras/LTX/ltx-2-19b-ic-lora-pose-control.safetensors",
    camera_dolly_in_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-in.safetensors",
    camera_dolly_out_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-out.safetensors",
    camera_dolly_left_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-left.safetensors",
    camera_dolly_right_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-dolly-right.safetensors",
    camera_jib_up_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-up.safetensors",
    camera_jib_down_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-jib-down.safetensors",
    camera_static_lora: "models/loras/LTX/CAMERA/ltx-2-19b-lora-camera-control-static.safetensors",
    upscale_model: "models/latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.0.safetensors",
  };
  return {
    schema: "antimatter-ltx-director-x-pro-settings-v1",
    paths,
    generation: {
      resolution_preset: "ltx_hd_1280x720",
      width: 1280,
      height: 720,
      two_stage_mode: true,
      stage_run_mode: "full_two_stage",
      stage1_draft_scale: 0.5,
      stage1_source_ready: false,
      stage1_source_label: "",
      stage2_require_stage1_source: true,
      use_latest_stage1_result: true,
      advanced_mode: false,
      fast_preview_enabled: true,
      fast_preview_scale: 0.5,
      use_upscale_model: true,
      upscale_factor: 2,
      auto_load_models: false,
      latent_upscale_model_name: "ltx-2.3-spatial-upscaler-x2-1.0.safetensors",
      pipeline_noise_seed: 12,
      pipeline_sampler: "euler",
      pipeline_scheduler: "linear_quadratic",
      stage1_steps: 8,
      stage1_denoise: 1,
      stage1_guide_scale_by: 0.5,
      stage2_steps: 4,
      stage2_denoise: 0.42,
      stage2_guide_scale_by: 1,
      fast_preview_rate: 24,
      save_final_video: false,
    },
    output: {
      final_video_path: "",
      live_preview_path: "",
      output_directory: "output/antimatter_ltx_director_x/final",
      intermediate_directory: "output/antimatter_ltx_director_x/intermediate",
      container: "mp4",
      codec: "h264",
      quality_mode: "crf",
      crf: 18,
      bitrate_mbps: 24,
      audio_codec: "aac",
      audio_bitrate_kbps: 320,
      save_intermediates: true,
      overwrite: false,
    },
    ui: { preview_url: "", live_preview_url: "", theme: "antimatter_dark" },
  };
}

function parseProSettings(raw) {
  const base = defaultProSettings();
  try {
    const parsed = raw ? JSON.parse(raw) : {};
    return {
      ...base,
      ...parsed,
      paths: { ...base.paths, ...(parsed.paths || {}) },
      generation: { ...base.generation, ...(parsed.generation || {}) },
      output: { ...base.output, ...(parsed.output || {}) },
      ui: { ...base.ui, ...(parsed.ui || {}) },
    };
  } catch (_) {
    return base;
  }
}

function videoSrcFromSettings(settings, fallbackPath = "") {
  const raw = String(settings?.ui?.preview_url || settings?.output?.final_video_path || fallbackPath || "").trim();
  return videoSrcFromValue(raw);
}

function livePreviewSrcFromSettings(settings) {
  const raw = String(settings?.ui?.live_preview_url || settings?.output?.live_preview_path || "").trim();
  return videoSrcFromValue(raw);
}

function videoSrcFromValue(rawValue = "") {
  const raw = String(rawValue || "").trim();
  if (!raw) return "";
  if (/^(https?:|data:|blob:|\/api\/|\/view)/i.test(raw)) return raw;
  if (/^[a-zA-Z]:[\\/]/.test(raw)) return "";
  const normalized = raw.replace(/\\/g, "/").replace(/^output\//i, "");
  const parts = normalized.split("/").filter(Boolean);
  const filename = parts.pop() || normalized;
  const subfolder = parts.join("/");
  return `/api/view?filename=${encodeURIComponent(filename)}&type=output&subfolder=${encodeURIComponent(subfolder)}`;
}

function openHelpWindow() {
  const backdrop = document.createElement("div");
  backdrop.className = "amx-floating-backdrop";
  const panel = document.createElement("div");
  panel.className = "amx-help-panel";
  panel.style.position = "fixed";
  panel.style.left = "50%";
  panel.style.top = "50%";
  panel.style.transform = "translate(-50%, -50%)";
  panel.style.zIndex = "1002";
  panel.innerHTML = `
    <h2>AntimatterLtxDirectorX Pro - Complete User Guide</h2>
    <p><b>Purpose.</b> This node is a premium all-in-one LTX 2.3 video direction workstation. It combines timeline editing, prompt generation, JoyCaption-aware image understanding, fragment retry, LoRA mixing, camera-control metadata, audio lane planning, and stitch-ready outputs.</p>
    <h3>1. Basic Workflow</h3>
    <ol>
      <li>Connect <code>model</code>, <code>clip</code>, and optionally <code>audio_vae</code> exactly as you would connect the original LTX Director.</li>
      <li>Open the node and press <code>EDIT</code>. The full editor opens in a resizable floating window. Drag the title bar to move it and drag the window corner to resize it.</li>
      <li>Add image shots, write or generate prompts, arrange the timeline, and use <code>Retry This</code> when only one fragment needs regeneration.</li>
      <li>Use the first seven outputs like the original LTX Director outputs: patched model, positive conditioning, video latent, audio latent, guide data, frame rate, and combined audio.</li>
    </ol>
    <h3>2. Timeline Editing</h3>
    <p>The bottom timeline contains a video/image guide lane and a detached audio lane. Select clips, drag them, resize edges, split at the playhead, cut a range, ripple-delete, add markers, or detach audio placeholders.</p>
    <h3>3. Prompt Agent</h3>
    <p>Connect JoyCaption output to <code>joy_caption_text</code> and keep <code>use_joycapture</code> enabled when you want image captions included. Disable it when you want the prompt generated only from manual description and user action. For external agents, send <code>agent_prompt_request</code> to an LLM node and connect the answer to <code>agent_response</code>.</p>
    <h3>4. Pro LoRA Rack</h3>
    <p>The LoRA rack applies model-only LoRAs before the Director pipeline runs. Presets quickly configure the stack for balanced direction, camera control, motion tracking, lipdub, transitions, or maximum control. Missing LoRAs are reported in <code>pro_lora_report_json</code>.</p>
    <h3>5. Camera Controller</h3>
    <p>The camera viewer lets you drag yaw and pitch directly, then refine roll, zoom, truck, pedestal, dolly, and focal length. Camera modes automatically enable the camera-control LoRA when enabled in settings. <code>camera_tracks_json</code> is compatible with LTXVDrawTracks-style track JSON.</p>
    <h3>6. Output and Settings</h3>
    <p>Use the Settings panel to define model paths, LoRA paths, final output directory, intermediate directory, video container, codec, CRF or bitrate quality, audio codec, and final preview path. These values are saved into the workflow as JSON and included in <code>pro_product_report_json</code>.</p>
    <h3>7. Fragment Retry</h3>
    <p>Select a range and press <code>Retry This</code>. The node switches to selected-fragment mode and outputs a short fragment plus <code>retry_payload</code>. Use <code>Antimatter LTX Fragment Stitch X</code> to replace that range in the full frame batch.</p>
    <p><b>Tip.</b> Keep the original workflow connected while iterating. Only switch to fragment retry after you have a full base render to stitch into.</p>
    <button class="amx-btn primary" style="margin-top:10px">Close</button>
  `;
  panel.querySelector("button").addEventListener("click", () => {
    panel.remove();
    backdrop.remove();
  });
  backdrop.addEventListener("click", () => {
    panel.remove();
    backdrop.remove();
  });
  document.body.appendChild(backdrop);
  document.body.appendChild(panel);
}

function makeDraggable(win, handle) {
  let drag = null;
  handle.addEventListener("pointerdown", (event) => {
    if (event.target.closest("button")) return;
    const rect = win.getBoundingClientRect();
    drag = { x: event.clientX, y: event.clientY, left: rect.left, top: rect.top };
    handle.setPointerCapture?.(event.pointerId);
  });
  handle.addEventListener("pointermove", (event) => {
    if (!drag) return;
    win.style.left = `${Math.max(0, drag.left + event.clientX - drag.x)}px`;
    win.style.top = `${Math.max(0, drag.top + event.clientY - drag.y)}px`;
  });
  handle.addEventListener("pointerup", () => { drag = null; });
  handle.addEventListener("pointercancel", () => { drag = null; });
}

class DirectorProUI extends DirectorXUI {
  build() {
    this.loraState = parseProLoraState(getWidgetValue(this.node, "pro_lora_stack_json", ""));
    this.cameraState = parseCameraState(getWidgetValue(this.node, "camera_control_json", ""));
    this.proSettings = parseProSettings(getWidgetValue(this.node, "pro_editor_settings_json", ""));
    this.cameraState.mode = normalizeCameraMode(getWidgetValue(this.node, "camera_mode", this.cameraState.mode || "off"));
    this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
    this.proPreset = String(getWidgetValue(this.node, "pro_lora_preset", "clean_default"));
    super.build();
    this.buildProPanel();
    this.enableDockLayout();
  }

  buildProPanel() {
    this.proHeader = document.createElement("div");
    this.proHeader.className = "amx-pro-header";
    this.proHeader.innerHTML = `
      <div class="amx-pro-brand">
        <img class="amx-pro-logo-img" src="${ANTIMATTER_LOGO_URL}" alt="Antimatter">
        <div class="amx-pro-brand-copy">
          <b>AntimatterLtxDirectorX Pro</b>
          <span>Integrated LTX 2.3 LoRA rack, camera controller, retry timeline and prompt agent</span>
        </div>
      </div>
    `;
    const presetBar = document.createElement("div");
    presetBar.className = "amx-pro-presetbar";
    for (const [id, label] of [
      ["clean_default", "Clean Default"],
      ["director_balanced", "Balanced"],
      ["camera_control", "Camera"],
      ["motion_tracking", "Track"],
      ["lipdub", "LipDub"],
      ["transition", "Transition"],
      ["max_control", "Max"],
      ["custom", "Custom"],
    ]) {
      const btn = document.createElement("button");
      btn.className = `amx-btn ${this.proPreset === id ? "active" : ""}`;
      btn.textContent = label;
      btn.addEventListener("click", () => this.applyLoraPreset(id));
      presetBar.appendChild(btn);
    }
    const resetBtn = document.createElement("button");
    resetBtn.className = "amx-btn";
    resetBtn.textContent = "Reset to Safe Defaults";
    resetBtn.addEventListener("click", () => this.resetSafeDefaults());
    presetBar.appendChild(resetBtn);
    this.presetBar = presetBar;
    this.proHeader.appendChild(presetBar);

    this.proGrid = document.createElement("div");
    this.proGrid.className = "amx-pro-grid";
    this.loraRack = document.createElement("div");
    this.loraRack.className = "amx-lora-rack";
    this.cameraRig = document.createElement("div");
    this.cameraRig.className = "amx-camera-rig";
    this.proGrid.appendChild(this.loraRack);
    this.proGrid.appendChild(this.cameraRig);

    this.root.insertBefore(this.proHeader, this.timebar);
    this.root.insertBefore(this.proGrid, this.timebar);
    this.renderPro();
  }

  enableDockLayout() {
    this.root.classList.add("amx-editor-root");
    this.proGrid.style.gridTemplateColumns = "1fr";

    const top = this.root.querySelector(".amx-top");
    const tools = this.root.querySelector(".amx-tools");
    const middle = document.createElement("div");
    middle.className = "amx-editor-middle";
    const left = document.createElement("div");
    left.className = "amx-editor-panel amx-side-dock collapsed";
    left.innerHTML = `
      <button class="amx-dock-tab" data-dock-open="left">Tools / Settings</button>
      <div class="amx-dock-content">
        <div class="amx-dock-head"><b>Tools / Settings</b><button class="amx-icon-btn" data-dock-close="left" title="Hide panel">x</button></div>
      </div>
    `;
    const leftContent = left.querySelector(".amx-dock-content");
    const center = document.createElement("div");
    center.className = "amx-editor-panel amx-editor-preview";
    const right = document.createElement("div");
    right.className = "amx-editor-panel amx-side-dock collapsed";
    right.innerHTML = `
      <button class="amx-dock-tab" data-dock-open="right">LoRA / Camera</button>
      <div class="amx-dock-content">
        <div class="amx-dock-head"><b>LoRA / Camera</b><button class="amx-icon-btn" data-dock-close="right" title="Hide panel">x</button></div>
      </div>
    `;
    const rightContent = right.querySelector(".amx-dock-content");
    const timeline = document.createElement("div");
    timeline.className = "amx-editor-timeline";
    this.timelineViewport = timeline;
    const leftSplit = document.createElement("div");
    leftSplit.className = "amx-splitter-v";
    const rightSplit = document.createElement("div");
    rightSplit.className = "amx-splitter-v";
    const timelineSplit = document.createElement("div");
    timelineSplit.className = "amx-splitter-h";

    leftContent.appendChild(this.createWorkflowPanel());
    leftContent.appendChild(this.createAssetPanel());
    leftContent.appendChild(this.createSettingsPanel());
    center.appendChild(this.createEditorPreviewPanel());
    center.appendChild(this.propsWrapper());
    rightContent.appendChild(this.proGrid);
    timeline.appendChild(this.timebar);
    timeline.appendChild(this.videoTrack);
    timeline.appendChild(this.audioTrack);
    middle.appendChild(left);
    middle.appendChild(leftSplit);
    middle.appendChild(center);
    middle.appendChild(rightSplit);
    middle.appendChild(right);

    this.root.innerHTML = "";
    this.proHeader.appendChild(tools);
    this.root.appendChild(this.proHeader);
    this.root.appendChild(middle);
    this.root.appendChild(timelineSplit);
    this.root.appendChild(timeline);
    this.leftDock = left;
    this.rightDock = right;
    this.leftDock.querySelector('[data-dock-open="left"]').addEventListener("click", () => this.setSideDock("left", true));
    this.rightDock.querySelector('[data-dock-open="right"]').addEventListener("click", () => this.setSideDock("right", true));
    this.leftDock.querySelector('[data-dock-close="left"]').addEventListener("click", () => this.setSideDock("left", false));
    this.rightDock.querySelector('[data-dock-close="right"]').addEventListener("click", () => this.setSideDock("right", false));
    this.setSideDock("left", false);
    this.setSideDock("right", false);
    this.bindPaneSplitters(leftSplit, rightSplit, timelineSplit);
    this.resizeInfo();
    this.updatePreviewVideo();
  }

  bindPaneSplitters(leftSplit, rightSplit, timelineSplit) {
    const minLeft = 230;
    const minRight = 330;
    const minCenter = 360;
    const minTimeline = 130;
    const maxTimeline = 420;

    const dragState = { active: null };
    const startDrag = (kind, event) => {
      const rect = this.root.getBoundingClientRect();
      dragState.active = {
        kind,
        x: event.clientX,
        y: event.clientY,
        width: rect.width,
        height: rect.height,
        left: parseFloat(getComputedStyle(this.root).getPropertyValue("--left-pane")) || 320,
        right: parseFloat(getComputedStyle(this.root).getPropertyValue("--right-pane")) || 500,
        timeline: parseFloat(getComputedStyle(this.root).getPropertyValue("--timeline-pane")) || 186,
      };
      event.currentTarget.setPointerCapture?.(event.pointerId);
    };

    const move = (event) => {
      const s = dragState.active;
      if (!s) return;
      if (s.kind === "left") {
        const next = clamp(s.left + event.clientX - s.x, minLeft, Math.max(minLeft, s.width - s.right - minCenter - 24));
        this.leftPaneOpenWidth = next;
        this.root.style.setProperty("--left-pane", `${next}px`);
      }
      if (s.kind === "right") {
        const next = clamp(s.right - (event.clientX - s.x), minRight, Math.max(minRight, s.width - s.left - minCenter - 24));
        this.rightPaneOpenWidth = next;
        this.root.style.setProperty("--right-pane", `${next}px`);
      }
      if (s.kind === "timeline") {
        const next = clamp(s.timeline - (event.clientY - s.y), minTimeline, Math.min(maxTimeline, s.height - 260));
        this.root.style.setProperty("--timeline-pane", `${next}px`);
        this.render();
      }
    };

    const end = () => { dragState.active = null; };
    for (const [el, kind] of [[leftSplit, "left"], [rightSplit, "right"], [timelineSplit, "timeline"]]) {
      el.addEventListener("pointerdown", (event) => startDrag(kind, event));
      el.addEventListener("pointermove", move);
      el.addEventListener("pointerup", end);
      el.addEventListener("pointercancel", end);
    }
  }

  setSideDock(side, open) {
    const dock = side === "left" ? this.leftDock : this.rightDock;
    if (!dock) return;
    dock.classList.toggle("collapsed", !open);
    if (side === "left") this.root.style.setProperty("--left-pane", open ? `${this.leftPaneOpenWidth || 320}px` : "46px");
    if (side === "right") this.root.style.setProperty("--right-pane", open ? `${this.rightPaneOpenWidth || 500}px` : "46px");
    requestAnimationFrame(() => this.render());
  }

  propsWrapper() {
    this.propsPanel = document.createElement("div");
    this.propsPanel.appendChild(this.promptInspector);
    const side = this.root.querySelector(".amx-side");
    if (side) this.propsPanel.appendChild(side);
    this.propsPanel.style.display = "grid";
    this.propsPanel.style.gridTemplateColumns = "1fr 160px";
    this.propsPanel.style.gap = "8px";
    return this.propsPanel;
  }

  createWorkflowPanel() {
    const generation = this.proSettings.generation ||= {};
    const panel = document.createElement("div");
    panel.className = "amx-workflow-panel";
    panel.innerHTML = `
      <div class="amx-section-title"><span>Director Workflow</span><span class="amx-small">two-stage engine</span></div>
      <div class="amx-workflow-mode">
        <label><span><input data-workflow="two-stage" type="checkbox"> Two-Stage Mode</span></label>
        <select class="amx-input" data-workflow="stage-mode">
          <option value="full_two_stage">Full Two-Stage</option>
          <option value="stage1_only">Stage 1 Only</option>
          <option value="stage2_refine">Stage 2 Refine</option>
          <option value="single_stage">Single Stage</option>
        </select>
      </div>
      <div class="amx-stage-card">
        <div class="amx-stage-title">Final Output<span data-workflow="final-resolution"></span></div>
        <div class="amx-small">Visible resolution is the final Stage 2 output. Stage 1 draft scale stays separate.</div>
      </div>
      <div class="amx-stage-card">
        <div class="amx-stage-title">Stage 1 - Draft Motion<span>live preview</span></div>
        <div class="amx-duration-tools">
          <label>Steps<input class="amx-input" data-workflow="stage1-steps" type="number" min="1" max="10000" step="1"></label>
          <label>Draft scale<input class="amx-input" data-workflow="stage1-scale" type="number" min="0.05" max="1" step="0.01"></label>
        </div>
        <button class="amx-btn primary" data-workflow="generate-stage1">Generate Stage 1</button>
      </div>
      <div class="amx-stage-card">
        <div class="amx-stage-title">Stage 2 - Final Refine<span>upscaled render</span></div>
        <div class="amx-duration-tools">
          <label>Steps<input class="amx-input" data-workflow="stage2-steps" type="number" min="1" max="10000" step="1"></label>
          <label>Denoise<input class="amx-input" data-workflow="stage2-denoise" type="number" min="0" max="1" step="0.01"></label>
        </div>
        <label class="amx-label"><span><input data-workflow="use-latest-stage1" type="checkbox"> Use latest Stage 1 source</span></label>
        <button class="amx-btn primary" data-workflow="refine-stage2">Refine Stage 2</button>
      </div>
      <div class="amx-workflow-actions">
        <button class="amx-btn" data-workflow="single-stage">Generate Single Stage</button>
        <button class="amx-btn" data-workflow="apply-preset">Apply Preset</button>
        <button class="amx-btn warning" data-workflow="safe-defaults">Reset to Safe Defaults</button>
      </div>
      <div class="amx-validation-box" data-workflow="validation"></div>
    `;
    this.workflowPanel = panel;
    this.workflowTwoStage = panel.querySelector('[data-workflow="two-stage"]');
    this.workflowStageMode = panel.querySelector('[data-workflow="stage-mode"]');
    this.workflowStage1Steps = panel.querySelector('[data-workflow="stage1-steps"]');
    this.workflowStage1Scale = panel.querySelector('[data-workflow="stage1-scale"]');
    this.workflowStage2Steps = panel.querySelector('[data-workflow="stage2-steps"]');
    this.workflowStage2Denoise = panel.querySelector('[data-workflow="stage2-denoise"]');
    this.workflowUseLatestStage1 = panel.querySelector('[data-workflow="use-latest-stage1"]');
    this.workflowResolution = panel.querySelector('[data-workflow="final-resolution"]');
    this.validationBox = panel.querySelector('[data-workflow="validation"]');

    this.workflowTwoStage.addEventListener("change", () => {
      generation.two_stage_mode = this.workflowTwoStage.checked;
      generation.stage_run_mode = generation.two_stage_mode ? "full_two_stage" : "single_stage";
      this.updateWorkflowPanel();
      this.syncPro();
    });
    this.workflowStageMode.addEventListener("change", () => {
      generation.stage_run_mode = this.workflowStageMode.value;
      generation.two_stage_mode = generation.stage_run_mode !== "single_stage";
      this.updateWorkflowPanel();
      this.syncPro();
    });
    this.workflowStage1Steps.addEventListener("change", () => {
      generation.stage1_steps = Math.max(1, Math.round(Number(this.workflowStage1Steps.value || 8)));
      this.syncPro();
    });
    this.workflowStage1Scale.addEventListener("change", () => {
      generation.stage1_draft_scale = clamp(Number(this.workflowStage1Scale.value || 0.5), 0.05, 1);
      generation.stage1_guide_scale_by = generation.stage1_draft_scale;
      this.syncPro();
    });
    this.workflowStage2Steps.addEventListener("change", () => {
      generation.stage2_steps = Math.max(1, Math.round(Number(this.workflowStage2Steps.value || 4)));
      this.syncPro();
    });
    this.workflowStage2Denoise.addEventListener("change", () => {
      generation.stage2_denoise = clamp(Number(this.workflowStage2Denoise.value || 0.42), 0, 1);
      this.syncPro();
    });
    this.workflowUseLatestStage1.addEventListener("change", () => {
      generation.use_latest_stage1_result = this.workflowUseLatestStage1.checked;
      this.updateValidationPanel();
      this.syncPro();
    });
    panel.querySelector('[data-workflow="generate-stage1"]').addEventListener("click", () => this.triggerStageRun("stage1_only"));
    panel.querySelector('[data-workflow="refine-stage2"]').addEventListener("click", () => this.triggerStageRun("stage2_refine"));
    panel.querySelector('[data-workflow="single-stage"]').addEventListener("click", () => this.triggerStageRun("single_stage"));
    panel.querySelector('[data-workflow="apply-preset"]').addEventListener("click", () => this.applyLoraPreset(this.proPreset || "clean_default"));
    panel.querySelector('[data-workflow="safe-defaults"]').addEventListener("click", () => this.resetSafeDefaults());
    this.updateWorkflowPanel();
    return panel;
  }

  updateWorkflowPanel() {
    if (!this.workflowPanel) return;
    const generation = this.proSettings.generation ||= {};
    generation.two_stage_mode = generation.two_stage_mode ?? true;
    generation.stage_run_mode = generation.stage_run_mode || (generation.two_stage_mode ? "full_two_stage" : "single_stage");
    if (this.workflowTwoStage) this.workflowTwoStage.checked = Boolean(generation.two_stage_mode);
    if (this.workflowStageMode) this.workflowStageMode.value = generation.stage_run_mode;
    if (this.workflowStage1Steps) this.workflowStage1Steps.value = Math.max(1, Math.round(Number(generation.stage1_steps ?? 8)));
    if (this.workflowStage1Scale) this.workflowStage1Scale.value = Number(generation.stage1_draft_scale ?? generation.stage1_guide_scale_by ?? 0.5);
    if (this.workflowStage2Steps) this.workflowStage2Steps.value = Math.max(1, Math.round(Number(generation.stage2_steps ?? 4)));
    if (this.workflowStage2Denoise) this.workflowStage2Denoise.value = Number(generation.stage2_denoise ?? 0.42);
    if (this.workflowUseLatestStage1) this.workflowUseLatestStage1.checked = Boolean(generation.use_latest_stage1_result ?? true);
    const preset = RESOLUTION_PRESETS.find((item) => item.id === generation.resolution_preset);
    const width = Number(generation.width || preset?.width || 1280);
    const height = Number(generation.height || preset?.height || 720);
    if (this.workflowResolution) this.workflowResolution.textContent = `${width} x ${height}`;
    this.updateValidationPanel();
  }

  computeValidationWarnings() {
    const generation = this.proSettings.generation || {};
    const warnings = [];
    const active = (id) => Boolean(this.loraState?.[id]?.enabled) && Math.abs(Number(this.loraState?.[id]?.strength || 0)) > 0;
    const hasTrackData = normalizeCameraMode(this.cameraState?.mode) !== "off" || Boolean(this.timeline?.motionTracks || this.timeline?.tracks || this.timeline?.trackingData);
    const hasAudio = Boolean(this.timeline?.audioSegments?.length);
    if (active("motion_track") && !hasTrackData) warnings.push("Motion Track enabled, but no track input was detected.");
    if (active("lipdub") && !hasAudio) warnings.push("LipDub is enabled, but no dialogue/audio source is available.");
    if (
      generation.stage_run_mode === "stage2_refine" &&
      Boolean(generation.stage2_require_stage1_source ?? true) &&
      !Boolean(generation.stage1_source_ready)
    ) {
      warnings.push("Stage 1 result required before Stage 2 refinement.");
    }
    if (this.proPreset === "max_control") warnings.push("Max Control is advanced. Use it only with matching guide data.");
    if (this.manualWorkflowWarning) warnings.push(this.manualWorkflowWarning);
    return warnings;
  }

  updateValidationPanel() {
    if (!this.validationBox) return;
    const warnings = this.computeValidationWarnings();
    this.validationBox.innerHTML = warnings.length
      ? warnings.map((item) => `<div class="amx-warning-line">${item}</div>`).join("")
      : `<div class="amx-ok-line">Ready. Safe defaults keep only the distilled LoRA active until you choose more control.</div>`;
  }

  triggerStageRun(mode) {
    const generation = this.proSettings.generation ||= {};
    this.manualWorkflowWarning = "";
    if (mode === "stage2_refine" && !generation.stage1_source_ready) {
      generation.stage_run_mode = "stage2_refine";
      this.manualWorkflowWarning = "Stage 1 result required before Stage 2 refinement.";
      this.updateWorkflowPanel();
      this.syncPro();
      return;
    }
    generation.run_integrated_pipeline = true;
    generation.stage_run_mode = mode;
    generation.two_stage_mode = mode !== "single_stage";
    generation.fast_preview_enabled = true;
    generation.use_upscale_model = true;
    if (mode === "stage1_only") {
      generation.stage1_source_ready = true;
      generation.stage1_source_label = "latest Stage 1 request";
    }
    if (mode === "full_two_stage") generation.stage1_source_ready = true;
    this.updateWorkflowPanel();
    this.syncPro();
    this.queuePrompt();
  }

  queuePrompt() {
    try {
      app.queuePrompt?.(0, 1);
    } catch (_) {
      try { app.queuePrompt?.(); } catch (__) {}
    }
  }

  createAssetPanel() {
    const panel = document.createElement("div");
    panel.innerHTML = `
      <div class="amx-section-title"><span>Project Tools</span><span class="amx-small">editor</span></div>
      <div style="display:grid;gap:6px;margin-top:7px">
        <button class="amx-btn primary" data-tool="add-shot">Add Shot</button>
        <button class="amx-btn" data-tool="add-image">Import Image</button>
        <button class="amx-btn" data-tool="add-audio">Import Audio</button>
        <button class="amx-btn warning" data-tool="retry">Retry Selected Range</button>
        <button class="amx-btn" data-tool="help">Full English Guide</button>
      </div>
      <div class="amx-duration-tools" style="margin-top:8px">
        <label>Total frames<input class="amx-input" data-tool="duration-frames" type="number" min="1" max="20000" step="1"></label>
        <label>Seconds<input class="amx-input" data-tool="duration-seconds" type="number" min="0.04" max="3600" step="0.01"></label>
      </div>
      <label class="amx-label" style="margin-top:8px">Final output resolution preset
        <select class="amx-input" data-tool="resolution-preset">
          ${RESOLUTION_PRESETS.map((preset) => `<option value="${preset.id}">${preset.label}</option>`).join("")}
        </select>
      </label>
      <div class="amx-duration-tools" style="margin-top:6px">
        <label><span><input data-tool="fast-preview" type="checkbox"> Fast preview</span></label>
        <label><span><input data-tool="use-upscale" type="checkbox"> Upscale model</span></label>
      </div>
      <div class="amx-zoom-readout" data-tool="zoom-readout" style="margin-top:6px"></div>
      <div class="amx-small" style="margin-top:8px">All node parameters live in this editor. The node surface stays clean and focused on final preview.</div>
    `;
    panel.querySelector('[data-tool="add-shot"]').addEventListener("click", () => this.addSegment());
    panel.querySelector('[data-tool="add-image"]').addEventListener("click", () => this.imageInput.click());
    panel.querySelector('[data-tool="add-audio"]').addEventListener("click", () => this.audioInput.click());
    panel.querySelector('[data-tool="retry"]').addEventListener("click", () => this.retrySelection());
    panel.querySelector('[data-tool="help"]').addEventListener("click", () => openHelpWindow());
    this.durationFramesInput = panel.querySelector('[data-tool="duration-frames"]');
    this.durationSecondsInput = panel.querySelector('[data-tool="duration-seconds"]');
    this.resolutionPresetSelect = panel.querySelector('[data-tool="resolution-preset"]');
    this.fastPreviewToggle = panel.querySelector('[data-tool="fast-preview"]');
    this.useUpscaleToggle = panel.querySelector('[data-tool="use-upscale"]');
    this.zoomReadout = panel.querySelector('[data-tool="zoom-readout"]');
    this.durationFramesInput.addEventListener("change", () => this.setTimelineDuration(this.durationFramesInput.value));
    this.durationSecondsInput.addEventListener("change", () => {
      this.setTimelineDuration(Math.max(1, Math.round(Number(this.durationSecondsInput.value || 0) * this.frameRate)));
    });
    this.resolutionPresetSelect.addEventListener("change", () => this.applyResolutionPreset(this.resolutionPresetSelect.value));
    this.fastPreviewToggle.addEventListener("change", () => {
      this.proSettings.generation ||= {};
      this.proSettings.generation.fast_preview_enabled = true;
      this.fastPreviewToggle.checked = true;
      this.syncPro();
    });
    this.useUpscaleToggle.addEventListener("change", () => {
      this.proSettings.generation ||= {};
      this.proSettings.generation.use_upscale_model = true;
      this.useUpscaleToggle.checked = true;
      this.syncPro();
    });
    this.updateResolutionControls();
    this.updateDurationControls();
    return panel;
  }

  updateResolutionControls() {
    const generation = this.proSettings?.generation || {};
    if (this.resolutionPresetSelect) this.resolutionPresetSelect.value = generation.resolution_preset || "ltx_hd_1280x720";
    if (this.fastPreviewToggle) {
      this.fastPreviewToggle.checked = true;
      this.fastPreviewToggle.disabled = true;
    }
    if (this.useUpscaleToggle) {
      this.useUpscaleToggle.checked = true;
      this.useUpscaleToggle.disabled = true;
    }
  }

  applyResolutionPreset(id) {
    const preset = RESOLUTION_PRESETS.find((item) => item.id === id) || RESOLUTION_PRESETS[2];
    this.proSettings.generation ||= {};
    this.proSettings.generation.resolution_preset = preset.id;
    if (preset.width && preset.height) {
      this.proSettings.generation.width = preset.width;
      this.proSettings.generation.height = preset.height;
      setWidget(this.node, "custom_width", preset.width);
      setWidget(this.node, "custom_height", preset.height);
      setWidget(this.node, "camera_width", preset.width);
      setWidget(this.node, "camera_height", preset.height);
    }
    this.proSettings.generation.fast_preview_enabled = true;
    this.updateResolutionControls();
    this.updateWorkflowPanel();
    this.syncPro();
  }

  createEditorPreviewPanel() {
    const panel = document.createElement("div");
    panel.innerHTML = `
      <div class="amx-preview-head">
        <div class="amx-section-title"><span>Preview / Project Gallery</span><span class="amx-small">drag assets to timeline</span></div>
        <div class="amx-tabs">
          <button class="amx-tab active" data-preview-tab="final">Final Video</button>
          <button class="amx-tab" data-preview-tab="gallery">Project Gallery</button>
        </div>
      </div>
      <div class="amx-editor-video"><div class="amx-preview-empty">No final video path set yet.<br>Open Settings and set final preview path or preview URL.</div></div>
      <div class="amx-small" data-preview-help>This preview mirrors the compact preview on the node surface.</div>
    `;
    this.editorPreviewHost = panel.querySelector(".amx-editor-video");
    this.previewHelp = panel.querySelector("[data-preview-help]");
    this.previewTabs = Array.from(panel.querySelectorAll("[data-preview-tab]"));
    for (const btn of this.previewTabs) {
      btn.addEventListener("click", () => this.showPreviewTab(btn.dataset.previewTab));
    }
    return panel;
  }

  showPreviewTab(tab) {
    this.previewTab = tab === "gallery" ? "gallery" : "final";
    for (const btn of this.previewTabs || []) {
      btn.classList.toggle("active", btn.dataset.previewTab === this.previewTab);
    }
    if (this.previewTab === "gallery") this.renderProjectGallery();
    else this.updatePreviewVideo();
  }

  renderProjectGallery() {
    if (!this.editorPreviewHost || this.previewTab !== "gallery") return;
    const assets = projectGalleryAssets(this.timeline);
    this.editorPreviewHost.innerHTML = "";
    const gallery = document.createElement("div");
    gallery.className = "amx-project-gallery";
    if (!assets.length) {
      gallery.innerHTML = `<div class="amx-gallery-empty">No images in Project Gallery yet.<br>Import Image, then drag thumbnails here to append them to the timeline.</div>`;
    } else {
      for (const asset of assets) {
        const card = document.createElement("div");
        card.className = "amx-gallery-card";
        card.draggable = true;
        card.title = "Drag to append to the video timeline";
        const thumb = document.createElement("img");
        thumb.className = "amx-gallery-thumb";
        thumb.src = segmentImageUrl(asset);
        thumb.draggable = false;
        const name = document.createElement("div");
        name.className = "amx-gallery-name";
        name.textContent = asset.name || asset.imageFile || "Image";
        card.appendChild(thumb);
        card.appendChild(name);
        card.addEventListener("dragstart", (event) => {
          const payload = JSON.stringify(asset);
          event.dataTransfer.effectAllowed = "copy";
          event.dataTransfer.setData("application/x-antimatter-gallery-asset", payload);
          event.dataTransfer.setData("text/plain", payload);
        });
        gallery.appendChild(card);
      }
    }
    this.editorPreviewHost.appendChild(gallery);
    if (this.previewHelp) this.previewHelp.textContent = "Drag any image from Project Gallery onto the video/image lane to append a new shot after the last clip.";
  }

  createSettingsPanel() {
    this.settingsPanel = document.createElement("div");
    this.settingsPanel.style.marginTop = "10px";
    this.settingsPanel.innerHTML = `
      <div class="amx-section-title"><span>Settings</span><span class="amx-small">models / export</span></div>
      <div class="amx-settings-grid" style="margin-top:7px"></div>
    `;
    const grid = this.settingsPanel.querySelector(".amx-settings-grid");
    const fields = [
      ["paths.ltx_checkpoint", "LTX checkpoint", "wide"],
      ["paths.text_encoder", "Text encoder", "wide"],
      ["paths.video_vae", "Video VAE", ""],
      ["paths.audio_vae", "Audio VAE", ""],
      ["paths.tiny_vae", "Tiny VAE", ""],
      ["paths.text_projection", "Text projection", ""],
      ["paths.distilled_lora", "Distilled LoRA", "wide"],
      ["paths.union_control_lora", "Union Control LoRA", "wide"],
      ["paths.motion_track_lora", "Motion Track LoRA", "wide"],
      ["paths.lipdub_lora", "LipDub LoRA", "wide"],
      ["paths.transition_lora", "Transition LoRA", "wide"],
      ["paths.camera_control_lora", "Camera Control LoRA", "wide"],
      ["paths.detailer_lora", "Detailer IC-LoRA", "wide"],
      ["paths.pose_control_lora", "Pose Control IC-LoRA", "wide"],
      ["paths.camera_dolly_in_lora", "Camera Dolly In LoRA", "wide"],
      ["paths.camera_dolly_out_lora", "Camera Dolly Out LoRA", "wide"],
      ["paths.camera_dolly_left_lora", "Camera Dolly Left LoRA", "wide"],
      ["paths.camera_dolly_right_lora", "Camera Dolly Right LoRA", "wide"],
      ["paths.camera_jib_up_lora", "Camera Jib Up LoRA", "wide"],
      ["paths.camera_jib_down_lora", "Camera Jib Down LoRA", "wide"],
      ["paths.camera_static_lora", "Camera Static LoRA", "wide"],
      ["paths.upscale_model", "Upscale model", "wide"],
      ["generation.fast_preview_scale", "Fast preview scale", ""],
      ["generation.upscale_factor", "Upscale factor", ""],
      ["generation.auto_load_models", "Auto-load models", ""],
      ["generation.run_integrated_pipeline", "Run one-node pipeline", ""],
      ["generation.two_stage_mode", "Two-Stage Mode", ""],
      ["generation.stage_run_mode", "Stage run mode", ""],
      ["generation.stage1_draft_scale", "Stage 1 draft scale", ""],
      ["generation.stage2_require_stage1_source", "Stage 2 requires Stage 1", ""],
      ["generation.use_latest_stage1_result", "Use latest Stage 1", ""],
      ["generation.advanced_mode", "Advanced mode", ""],
      ["generation.save_final_video", "Save final video", ""],
      ["generation.pipeline_noise_seed", "Pipeline noise seed", ""],
      ["generation.latent_upscale_model_name", "LTX latent upscaler", "wide"],
      ["generation.pipeline_sampler", "Pipeline sampler", ""],
      ["generation.pipeline_scheduler", "Pipeline scheduler", ""],
      ["generation.stage1_steps", "Stage 1 steps", ""],
      ["generation.stage1_denoise", "Stage 1 denoise", ""],
      ["generation.stage1_guide_scale_by", "Stage 1 guide scale", ""],
      ["generation.stage2_steps", "Stage 2 steps", ""],
      ["generation.stage2_denoise", "Stage 2 denoise", ""],
      ["generation.stage2_guide_scale_by", "Stage 2 guide scale", ""],
      ["generation.fast_preview_rate", "Fast preview rate", ""],
      ["output.live_preview_path", "Live preview Stage 1 path", "wide"],
      ["output.final_video_path", "Final preview video path", "wide"],
      ["output.output_directory", "Final output directory", "wide"],
      ["output.intermediate_directory", "Intermediate directory", "wide"],
      ["output.container", "Container", ""],
      ["output.codec", "Codec", ""],
      ["output.crf", "CRF quality", ""],
      ["output.bitrate_mbps", "Bitrate Mbps", ""],
      ["output.audio_codec", "Audio codec", ""],
      ["output.audio_bitrate_kbps", "Audio kbps", ""],
      ["ui.live_preview_url", "Live preview URL", "wide"],
      ["ui.preview_url", "Preview URL", "wide"],
    ];
    for (const [path, label, wide] of fields) {
      const value = this.getSettingPath(path);
      const el = document.createElement("label");
      el.className = wide;
      el.innerHTML = `${label}<input class="amx-input" data-setting-path="${path}" value="${String(value ?? "").replace(/"/g, "&quot;")}">`;
      el.querySelector("input").addEventListener("change", (event) => {
        this.setSettingPath(path, event.target.value);
        this.syncPro();
        this.updatePreviewVideo();
      });
      grid.appendChild(el);
    }
    return this.settingsPanel;
  }

  getSettingPath(path) {
    return path.split(".").reduce((obj, key) => obj?.[key], this.proSettings);
  }

  setSettingPath(path, value) {
    const parts = path.split(".");
    let target = this.proSettings;
    for (const part of parts.slice(0, -1)) {
      target[part] ||= {};
      target = target[part];
    }
    const last = parts[parts.length - 1];
    if (/^(crf|bitrate_mbps|audio_bitrate_kbps|width|height|fast_preview_scale|upscale_factor|pipeline_noise_seed|stage1_steps|stage1_denoise|stage1_guide_scale_by|stage1_draft_scale|stage2_steps|stage2_denoise|stage2_guide_scale_by|fast_preview_rate)$/.test(last)) target[last] = Number(value || 0);
    else if (/^(auto_load_models|run_integrated_pipeline|two_stage_mode|stage2_require_stage1_source|use_latest_stage1_result|advanced_mode|save_final_video)$/.test(last)) target[last] = /^(true|1|yes|on)$/i.test(String(value || "").trim());
    else target[last] = value;
    this.updateWorkflowPanel();
  }

  updatePreviewVideo() {
    if (this.previewTab === "gallery") {
      this.renderProjectGallery();
      return;
    }
    const finalPath = String(getWidgetValue(this.node, "final_video_preview_path", "") || "");
    const liveSrc = livePreviewSrcFromSettings(this.proSettings);
    const finalSrc = videoSrcFromSettings(this.proSettings, finalPath);
    for (const host of [this.editorPreviewHost].filter(Boolean)) {
      host.innerHTML = "";
      const stages = document.createElement("div");
      stages.className = "amx-preview-stages";
      for (const stage of [
        {
          title: "Live Preview Stage 1",
          badge: this.proSettings?.generation?.fast_preview_enabled ? "fast preview" : "preview path",
          src: liveSrc,
          empty: "No live preview path set yet.",
        },
        {
          title: "Final Video Stage 2",
          badge: this.proSettings?.generation?.use_upscale_model ? "upscale model" : "final render",
          src: finalSrc,
          empty: "No final video path set yet.",
        },
      ]) {
        const panel = document.createElement("div");
        panel.className = "amx-stage-panel";
        panel.innerHTML = `
          <div class="amx-stage-title">${stage.title}<span>${stage.badge}</span></div>
          <div class="amx-stage-body"></div>
        `;
        const body = panel.querySelector(".amx-stage-body");
        if (stage.src) {
          const video = document.createElement("video");
          video.controls = true;
          video.loop = true;
          video.src = stage.src;
          body.appendChild(video);
        } else {
          body.innerHTML = `<div class="amx-preview-empty">${stage.empty}<br>Set path or URL in Settings.</div>`;
        }
        stages.appendChild(panel);
      }
      host.appendChild(stages);
    }
    if (this.previewHelp) this.previewHelp.textContent = "Stage 1 is the fast live preview. Stage 2 is the final upscaled video output.";
  }

  renderPro() {
    this.renderLoraRack();
    this.renderCameraRig();
    this.updateValidationPanel();
    this.syncPro(false);
  }

  renderLoraRack() {
    this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
    const selectedCameraLora = cameraLoraIdForMode(this.cameraState?.mode);
    const specById = new Map(PRO_LORAS.map((spec) => [spec.id, spec]));
    this.loraRack.innerHTML = `<div class="amx-section-title"><span>LTX 2.3 LoRA Mixer</span><span class="amx-small">available / selected / active</span></div>`;
    for (const group of LORA_GROUPS) {
      const groupWrap = document.createElement("div");
      groupWrap.className = "amx-lora-group";
      groupWrap.innerHTML = `<div class="amx-lora-group-title">${group.label}</div>`;
      for (const id of group.ids) {
        const spec = specById.get(id);
        if (!spec) continue;
        const state = this.loraState[spec.id] || { enabled: spec.enabled, strength: spec.strength };
        const isCameraSpecific = CAMERA_LORA_IDS.has(spec.id);
        const selected = isCameraSpecific ? selectedCameraLora === spec.id : Boolean(state.enabled);
        const active = selected && Math.abs(Number(state.strength || 0)) > 0;
        const stateLabel = active ? "Active" : (selected ? "Selected" : "Available");
        const row = document.createElement("div");
        row.className = `amx-lora-row ${active ? "on" : ""} ${isCameraSpecific ? "camera-mode-row" : ""}`;
        row.innerHTML = `
          <button class="amx-toggle-dot ${active ? "on" : ""}" title="${isCameraSpecific ? "Select camera mode" : `Enable ${spec.label}`}"></button>
          <div class="amx-lora-name"><b>${spec.label}</b><span>${spec.role} / ${spec.file}</span></div>
          <div class="amx-lora-badges"><span>Available</span><span class="${selected ? "on" : ""}">${stateLabel}</span></div>
          <input class="amx-slider" type="range" min="-2" max="2" step="0.01" value="${state.strength}">
          <input class="amx-num" type="number" min="-2" max="2" step="0.01" value="${Number(state.strength).toFixed(2)}">
          <button class="amx-download-btn ${spec.downloadUrl ? "" : "disabled"}" title="${spec.downloadUrl ? `Download ${spec.label}` : "No download URL configured"}">${ICONS.download}</button>
        `;
        const toggle = row.querySelector(".amx-toggle-dot");
        const slider = row.querySelector(".amx-slider");
        const num = row.querySelector(".amx-num");
        const download = row.querySelector(".amx-download-btn");
        toggle.addEventListener("click", () => {
          if (isCameraSpecific) {
            this.setCameraMode(cameraModeForLoraId(spec.id));
            return;
          }
          if (spec.id === "camera_control") {
            this.setCameraMode(normalizeCameraMode(this.cameraState?.mode) === "off" ? "dolly_in" : "off");
            return;
          }
          state.enabled = !state.enabled;
          this.proPreset = "custom";
          this.updateValidationPanel();
          this.renderPro();
          this.syncPro();
        });
        slider.addEventListener("input", () => {
          state.strength = Number(slider.value);
          num.value = state.strength.toFixed(2);
          this.proPreset = "custom";
          this.updateValidationPanel();
          this.syncPro();
        });
        num.addEventListener("change", () => {
          state.strength = Number(num.value || 0);
          slider.value = state.strength;
          this.proPreset = "custom";
          this.updateValidationPanel();
          this.syncPro();
        });
        download.addEventListener("click", () => this.openLoraDownload(spec));
        this.loraState[spec.id] = state;
        groupWrap.appendChild(row);
      }
      this.loraRack.appendChild(groupWrap);
    }
  }

  openLoraDownload(spec) {
    if (!spec.downloadUrl) return;
    const targetPath = `ComfyUI/models/loras/${spec.preferred || spec.file}`;
    navigator.clipboard?.writeText(targetPath).catch(() => {});
    window.open(spec.downloadUrl, "_blank", "noopener,noreferrer");
  }

  renderCameraRig() {
    this.cameraState.mode = normalizeCameraMode(this.cameraState.mode);
    this.cameraRig.innerHTML = `
      <div class="amx-section-title"><span>Camera Control Viewer</span><span class="amx-small">drag viewport</span></div>
      <div class="amx-pro-presetbar">
        ${CAMERA_MODE_OPTIONS.map(([mode, label]) => `<button class="amx-btn ${this.cameraState.mode === mode ? "active" : ""}" data-cam-mode="${mode}">${label}</button>`).join("")}
      </div>
      <div class="amx-camera-view">
        <div class="amx-camera-reticle"></div>
        <div class="amx-camera-readout"></div>
      </div>
      <div class="amx-camera-controls"></div>
    `;
    for (const btn of this.cameraRig.querySelectorAll("[data-cam-mode]")) {
      btn.addEventListener("click", () => this.setCameraMode(btn.dataset.camMode));
    }
    this.cameraView = this.cameraRig.querySelector(".amx-camera-view");
    this.cameraReticle = this.cameraRig.querySelector(".amx-camera-reticle");
    this.cameraReadout = this.cameraRig.querySelector(".amx-camera-readout");
    this.cameraView.addEventListener("pointerdown", (event) => {
      this.cameraDrag = {
        x: event.clientX,
        y: event.clientY,
        yaw: Number(this.cameraState.yaw || 0),
        pitch: Number(this.cameraState.pitch || 0),
      };
      this.cameraView.setPointerCapture?.(event.pointerId);
    });
    this.cameraView.addEventListener("pointermove", (event) => {
      if (!this.cameraDrag) return;
      this.cameraState.yaw = clamp(this.cameraDrag.yaw + (event.clientX - this.cameraDrag.x) * 0.35, -90, 90);
      this.cameraState.pitch = clamp(this.cameraDrag.pitch - (event.clientY - this.cameraDrag.y) * 0.25, -45, 45);
      this.cameraState.mode = "custom";
      this.cameraState.manualOverride = true;
      this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
      this.proPreset = "custom";
      this.updateCameraVisuals();
      this.renderLoraRack();
      this.syncPro();
    });
    this.cameraView.addEventListener("pointerup", () => { this.cameraDrag = null; });
    this.cameraView.addEventListener("pointercancel", () => { this.cameraDrag = null; });

    const controls = this.cameraRig.querySelector(".amx-camera-controls");
    for (const item of [
      ["yaw", -90, 90, 1],
      ["pitch", -45, 45, 1],
      ["roll", -25, 25, 0.5],
      ["zoom", 0.5, 2, 0.01],
      ["truck", -120, 120, 1],
      ["pedestal", -120, 120, 1],
      ["dolly", -120, 120, 1],
      ["focalLength", 12, 120, 1],
    ]) {
      const [key, min, max, step] = item;
      const label = document.createElement("label");
      label.innerHTML = `${key}<input class="amx-slider" type="range" min="${min}" max="${max}" step="${step}" value="${this.cameraState[key] ?? defaultCameraState()[key]}">`;
      const input = label.querySelector("input");
      input.addEventListener("input", () => {
        this.cameraState[key] = Number(input.value);
        this.cameraState.mode = "custom";
        this.cameraState.manualOverride = true;
        this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
        this.proPreset = "custom";
        this.updateCameraVisuals();
        this.renderLoraRack();
        this.syncPro();
      });
      controls.appendChild(label);
    }
    this.updateCameraVisuals();
  }

  applyLoraPreset(id) {
    this.proPreset = id;
    const preset = PRO_PRESETS[id];
    if (preset) {
      for (const spec of PRO_LORAS) {
        const pair = preset[spec.id] || [spec.enabled, spec.strength];
        this.loraState[spec.id] = { enabled: Boolean(pair[0]), strength: Number(pair[1]) };
      }
    }
    if (id === "camera_control" && normalizeCameraMode(this.cameraState.mode) === "off") this.applyCameraPresetValues("dolly_in");
    if (id === "clean_default" || id === "director_balanced") this.applyCameraPresetValues("off");
    this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
    this.updateWorkflowPanel();
    this.renderPro();
    this.syncPro();
  }

  resetSafeDefaults() {
    this.applyLoraPreset("clean_default");
    this.proSettings.generation ||= {};
    Object.assign(this.proSettings.generation, {
      two_stage_mode: true,
      stage_run_mode: "full_two_stage",
      stage1_draft_scale: 0.5,
      stage1_source_ready: false,
      stage1_source_label: "",
      stage2_require_stage1_source: true,
      use_latest_stage1_result: true,
      advanced_mode: false,
      fast_preview_enabled: true,
      use_upscale_model: true,
    });
    this.manualWorkflowWarning = "";
    this.updateWorkflowPanel();
    this.syncPro();
  }

  applyCameraPresetValues(mode) {
    const normalized = normalizeCameraMode(mode);
    const presets = {
      off: { yaw: 0, pitch: 0, roll: 0, zoom: 1, truck: 0, pedestal: 0, dolly: 0 },
      dolly_in: { yaw: 0, pitch: 0, roll: 0, zoom: 1.18, truck: 0, pedestal: 0, dolly: 80 },
      dolly_out: { yaw: 0, pitch: 0, roll: 0, zoom: 0.92, truck: 0, pedestal: 0, dolly: -80 },
      dolly_left: { yaw: 0, pitch: 0, roll: 0, zoom: 1, truck: -90, pedestal: 0, dolly: 0 },
      dolly_right: { yaw: 0, pitch: 0, roll: 0, zoom: 1, truck: 90, pedestal: 0, dolly: 0 },
      jib_up: { yaw: 0, pitch: -4, roll: 0, zoom: 1, truck: 0, pedestal: 90, dolly: 0 },
      jib_down: { yaw: 0, pitch: 4, roll: 0, zoom: 1, truck: 0, pedestal: -90, dolly: 0 },
      static: { yaw: 0, pitch: 0, roll: 0, zoom: 1, truck: 0, pedestal: 0, dolly: 0 },
    };
    this.cameraState.mode = normalized;
    this.cameraState.manualOverride = normalized === "custom";
    if (presets[normalized]) Object.assign(this.cameraState, presets[normalized]);
  }

  setCameraMode(mode) {
    this.applyCameraPresetValues(mode);
    this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
    this.proPreset = normalizeCameraMode(mode) !== "off" ? "custom" : this.proPreset;
    this.updateValidationPanel();
    this.renderPro();
    this.syncPro();
  }

  updateCameraVisuals() {
    if (!this.cameraReticle || !this.cameraReadout) return;
    const yaw = Number(this.cameraState.yaw || 0);
    const pitch = Number(this.cameraState.pitch || 0);
    const roll = Number(this.cameraState.roll || 0);
    const zoom = Number(this.cameraState.zoom || 1);
    const truck = Number(this.cameraState.truck || 0);
    const pedestal = Number(this.cameraState.pedestal || 0);
    this.cameraReticle.style.transform =
      `translate(${truck * 0.22}px, ${pedestal * 0.18}px) rotateX(${pitch}deg) rotateY(${yaw}deg) rotateZ(${roll}deg) scale(${zoom})`;
    this.cameraReadout.textContent = `${this.cameraState.mode} | yaw ${yaw.toFixed(0)} pitch ${pitch.toFixed(0)} roll ${roll.toFixed(1)} zoom ${zoom.toFixed(2)}`;
  }

  syncPro(markDirty = true) {
    if (!this.loraState || !this.cameraState) return;
    this.cameraState.mode = normalizeCameraMode(this.cameraState.mode);
    this.loraState = enforceCameraExclusive(this.loraState, this.cameraState);
    const selectedCameraLora = cameraLoraIdForMode(this.cameraState.mode);
    const loraPayload = {
      schema: "antimatter-ltx-director-x-pro-loras-v1",
      preset: this.proPreset,
      loras: PRO_LORAS.map((spec) => {
        const isCameraSpecific = CAMERA_LORA_IDS.has(spec.id);
        const enabled = isCameraSpecific
          ? selectedCameraLora === spec.id && this.cameraState.mode !== "off"
          : Boolean(this.loraState[spec.id]?.enabled);
        const strength = Number(this.loraState[spec.id]?.strength ?? spec.strength);
        const active = enabled && Math.abs(strength) > 0;
        return {
          id: spec.id,
          group: loraGroupForId(spec.id),
          filename: spec.file,
          preferred: spec.preferred || spec.file,
          download_url: spec.downloadUrl || "",
          enabled,
          selected: enabled,
          active,
          state: active ? "active" : "available",
          strength,
        };
      }),
    };
    const cam = {
      ...defaultCameraState(),
      ...this.cameraState,
      keyframes: [
        { time: 0, yaw: 0, pitch: 0, roll: 0, zoom: 1, truck: 0, pedestal: 0, dolly: 0, focalLength: Number(this.cameraState.focalLength || 35) },
        {
          time: 1,
          yaw: Number(this.cameraState.yaw || 0),
          pitch: Number(this.cameraState.pitch || 0),
          roll: Number(this.cameraState.roll || 0),
          zoom: Number(this.cameraState.zoom || 1),
          truck: Number(this.cameraState.truck || 0),
          pedestal: Number(this.cameraState.pedestal || 0),
          dolly: Number(this.cameraState.dolly || 0),
          focalLength: Number(this.cameraState.focalLength || 35),
        },
      ],
    };

    setWidget(this.node, "pro_lora_stack_json", JSON.stringify(loraPayload));
    setWidget(this.node, "pro_lora_preset", this.proPreset);
    const generation = this.proSettings?.generation || {};
    this.proSettings.generation ||= {};
    this.proSettings.generation.two_stage_mode = Boolean(generation.two_stage_mode ?? true);
    this.proSettings.generation.stage_run_mode = String(generation.stage_run_mode || (this.proSettings.generation.two_stage_mode ? "full_two_stage" : "single_stage"));
    this.proSettings.generation.stage1_draft_scale = Number(generation.stage1_draft_scale ?? generation.stage1_guide_scale_by ?? 0.5);
    this.proSettings.generation.stage2_require_stage1_source = Boolean(generation.stage2_require_stage1_source ?? true);
    this.proSettings.generation.use_latest_stage1_result = Boolean(generation.use_latest_stage1_result ?? true);
    this.proSettings.generation.advanced_mode = Boolean(generation.advanced_mode ?? false);
    this.proSettings.generation.fast_preview_enabled = true;
    this.proSettings.generation.use_upscale_model = true;
    const isOneNode = this.node.comfyClass === "AntimatterLtxDirectorXOneNode";
    const autoLoad = isOneNode ? true : (this.proSettings.generation.auto_load_models ?? getWidgetValue(this.node, "auto_load_models", false));
    const runIntegrated = isOneNode ? true : (this.proSettings.generation.run_integrated_pipeline ?? getWidgetValue(this.node, "run_integrated_pipeline", false));
    this.proSettings.generation.auto_load_models = Boolean(autoLoad);
    this.proSettings.generation.run_integrated_pipeline = Boolean(runIntegrated);
    if (Number(generation.width) > 0 && Number(generation.height) > 0) {
      setWidget(this.node, "custom_width", Math.round(Number(generation.width)));
      setWidget(this.node, "custom_height", Math.round(Number(generation.height)));
      setWidget(this.node, "camera_width", Math.round(Number(generation.width)));
      setWidget(this.node, "camera_height", Math.round(Number(generation.height)));
    }
    for (const spec of PRO_LORAS) {
      setWidget(this.node, `${spec.id}_enabled`, Boolean(this.loraState[spec.id]?.enabled));
      setWidget(this.node, `${spec.id}_strength`, Number(this.loraState[spec.id]?.strength ?? spec.strength));
    }
    setWidget(this.node, "camera_control_json", JSON.stringify(cam));
    setWidget(this.node, "camera_mode", cam.mode || "off");
    setWidget(this.node, "auto_load_models", Boolean(this.proSettings.generation.auto_load_models));
    setWidget(this.node, "run_integrated_pipeline", Boolean(this.proSettings.generation.run_integrated_pipeline));
    setWidget(this.node, "two_stage_mode", Boolean(this.proSettings.generation.two_stage_mode));
    setWidget(this.node, "stage_run_mode", String(this.proSettings.generation.stage_run_mode || "full_two_stage"));
    setWidget(this.node, "stage1_draft_scale", Number(this.proSettings.generation.stage1_draft_scale ?? 0.5));
    setWidget(this.node, "stage2_require_stage1_source", Boolean(this.proSettings.generation.stage2_require_stage1_source));
    setWidget(this.node, "use_latest_stage1_result", Boolean(this.proSettings.generation.use_latest_stage1_result));
    setWidget(this.node, "advanced_mode", Boolean(this.proSettings.generation.advanced_mode));
    setWidget(this.node, "save_final_video", Boolean(this.proSettings.generation.save_final_video));
    setWidget(this.node, "pipeline_noise_seed", Math.round(Number(this.proSettings.generation.pipeline_noise_seed ?? 12)));
    setWidget(this.node, "latent_upscale_model_name", String(this.proSettings.generation.latent_upscale_model_name || this.proSettings.paths?.upscale_model || "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"));
    setWidget(this.node, "pipeline_sampler", String(this.proSettings.generation.pipeline_sampler || "euler"));
    setWidget(this.node, "pipeline_scheduler", String(this.proSettings.generation.pipeline_scheduler || "linear_quadratic"));
    setWidget(this.node, "stage1_steps", Math.max(1, Math.round(Number(this.proSettings.generation.stage1_steps ?? 8))));
    setWidget(this.node, "stage1_denoise", Number(this.proSettings.generation.stage1_denoise ?? 1));
    setWidget(this.node, "stage1_guide_scale_by", Number(this.proSettings.generation.stage1_guide_scale_by ?? 0.5));
    setWidget(this.node, "stage2_steps", Math.max(1, Math.round(Number(this.proSettings.generation.stage2_steps ?? 4))));
    setWidget(this.node, "stage2_denoise", Number(this.proSettings.generation.stage2_denoise ?? 0.42));
    setWidget(this.node, "stage2_guide_scale_by", Number(this.proSettings.generation.stage2_guide_scale_by ?? 1));
    setWidget(this.node, "fast_preview_rate", Math.max(1, Math.round(Number(this.proSettings.generation.fast_preview_rate ?? 24))));
    setWidget(this.node, "pro_editor_settings_json", JSON.stringify(this.proSettings || defaultProSettings()));
    setWidget(this.node, "final_video_preview_path", String(this.proSettings?.output?.final_video_path || ""));
    setWidget(this.node, "camera_control_enabled", Boolean(this.loraState.camera_control?.enabled));
    this.updateWorkflowPanel();
    if (markDirty) app.graph?.setDirtyCanvas(true, true);
  }

  syncAll(markDirty = true) {
    super.syncAll(markDirty);
    this.syncPro(markDirty);
  }
}

class DirectorProSurface {
  constructor(node, container, domWidget) {
    this.node = node;
    this.container = container;
    this.domWidget = domWidget;
    this.settings = parseProSettings(getWidgetValue(node, "pro_editor_settings_json", ""));
    this.build();
    this.updatePreview();
  }

  build() {
    ensureStyles();
    this.container.innerHTML = "";
    this.root = document.createElement("div");
    this.root.className = "amx-surface";
    const productName = this.node.comfyClass === "AntimatterLtxDirectorXOneNode"
      ? "AntimatterLtxDirectorX One Node"
      : "AntimatterLtxDirectorX Pro";
    const productSubline = this.node.comfyClass === "AntimatterLtxDirectorXOneNode"
      ? "full workflow inside one node"
      : "premium LTX timeline workstation";
    this.root.innerHTML = `
      <div class="amx-surface-top">
        <div class="amx-logo">
          <img class="amx-logo-img" src="${ANTIMATTER_LOGO_URL}" alt="Antimatter">
          <div class="amx-logo-text"><b>${productName}</b><span>${productSubline}</span></div>
        </div>
        <div class="amx-surface-actions">
          <button class="amx-edit-big">EDIT</button>
          <button class="amx-round-btn" title="Settings">⚙</button>
          <button class="amx-round-btn" title="Full guide">?</button>
        </div>
      </div>
      <div class="amx-node-preview"></div>
      <div class="amx-surface-footer">
        <span>Final video preview</span>
        <span class="amx-surface-state">ready</span>
      </div>
    `;
    this.container.appendChild(this.root);
    this.previewHost = this.root.querySelector(".amx-node-preview");
    this.stateLabel = this.root.querySelector(".amx-surface-state");
    this.root.querySelector(".amx-edit-big").addEventListener("click", () => this.openEditor());
    this.root.querySelector('[title="Settings"]').addEventListener("click", () => this.openEditor("settings"));
    this.root.querySelector('[title="Full guide"]').addEventListener("click", () => openHelpWindow());
  }

  updatePreview() {
    this.settings = parseProSettings(getWidgetValue(this.node, "pro_editor_settings_json", ""));
    const finalPath = String(getWidgetValue(this.node, "final_video_preview_path", "") || "");
    const src = videoSrcFromSettings(this.settings, finalPath);
    this.previewHost.innerHTML = "";
    if (src) {
      const video = document.createElement("video");
      video.controls = true;
      video.loop = true;
      video.src = src;
      this.previewHost.appendChild(video);
      this.stateLabel.textContent = "preview linked";
    } else {
      this.previewHost.innerHTML = `
        <div class="amx-preview-empty">
          <b>Final video window</b>
          <span>No preview path yet. Press Settings and set final video path or preview URL.</span>
        </div>
      `;
      this.stateLabel.textContent = "no preview path";
    }
  }

  openEditor(focus = "") {
    if (this.editorWindow?.isConnected) {
      this.editorWindow.style.zIndex = String(1001 + Math.floor(Math.random() * 50));
      return;
    }
    const win = document.createElement("div");
    win.className = "amx-floating";
    win.innerHTML = `
      <div class="amx-floating-titlebar">
        <b>AntimatterLtxDirectorX Pro Editor</b>
        <div style="display:flex;gap:6px">
          <button class="amx-btn" data-action="help">Guide</button>
          <button class="amx-btn" data-action="settings">Settings</button>
          <button class="amx-btn danger" data-action="close">Close</button>
        </div>
      </div>
      <div class="amx-floating-body"></div>
    `;
    document.body.appendChild(win);
    this.editorWindow = win;
    const titlebar = win.querySelector(".amx-floating-titlebar");
    const body = win.querySelector(".amx-floating-body");
    makeDraggable(win, titlebar);

    const widgetProxy = {
      callback: () => {
        this.updatePreview();
        this.domWidget?.callback?.();
      },
    };
    this.editor = new DirectorProUI(this.node, body, widgetProxy);
    win.querySelector('[data-action="close"]').addEventListener("click", () => this.closeEditor());
    win.querySelector('[data-action="help"]').addEventListener("click", () => openHelpWindow());
    win.querySelector('[data-action="settings"]').addEventListener("click", () => {
      this.editor?.setSideDock?.("left", true);
      this.editor?.settingsPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    if (focus === "settings") {
      setTimeout(() => {
        this.editor?.setSideDock?.("left", true);
        this.editor?.settingsPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    }
  }

  closeEditor() {
    this.editor?.destroy?.();
    this.editor = null;
    this.editorWindow?.remove();
    this.editorWindow = null;
    this.updatePreview();
  }

  destroy() {
    this.closeEditor();
  }
}

function ensureProFallbackButtons(node) {
  if (!getWidget(node, "AMX EDIT")) {
    node.addWidget("button", "AMX EDIT", "open", () => {
      if (!node._antimatterDirectorX?.openEditor) {
        node._antimatterDirectorX = new DirectorProSurface(node, document.createElement("div"), {
          callback: () => app.graph?.setDirtyCanvas(true, true),
        });
      }
      node._antimatterDirectorX.openEditor();
    });
  }
  if (!getWidget(node, "AMX Settings")) {
    node.addWidget("button", "AMX Settings", "open", () => {
      if (!node._antimatterDirectorX?.openEditor) {
        node._antimatterDirectorX = new DirectorProSurface(node, document.createElement("div"), {
          callback: () => app.graph?.setDirtyCanvas(true, true),
        });
      }
      node._antimatterDirectorX.openEditor("settings");
    });
  }
  if (!getWidget(node, "AMX Help")) {
    node.addWidget("button", "AMX Help", "open", () => openHelpWindow());
  }
}

function attachDirectorDom(node, isPro) {
  if (!node?.addDOMWidget) return false;
  const widgetName = isPro ? "director_x_surface" : "director_x_timeline";
  if (getWidget(node, widgetName)) return true;

  const container = document.createElement("div");
  const domWidget = node.addDOMWidget(widgetName, widgetName, container, {
    getValue: () => "",
    setValue: () => {},
  });
  domWidget.computeSize = function (width) {
    return [width, isPro ? 390 : 345];
  };

  node.size[0] = Math.max(node.size[0] || 0, isPro ? 620 : 1040);
  node.size[1] = Math.max(node.size[1] || 0, isPro ? 470 : 740);

  setTimeout(() => {
    try {
      node._antimatterDirectorX = isPro
        ? new DirectorProSurface(node, container, domWidget)
        : new DirectorXUI(node, container, domWidget);
      app.graph?.setDirtyCanvas(true, true);
    } catch (err) {
      console.error(`[Antimatter Ltx Director X${isPro ? " Pro" : ""}] DOM UI init failed`, err);
      if (isPro) ensureProFallbackButtons(node);
    }
  }, 0);
  return true;
}

app.registerExtension({
  name: EXTENSION,
  async nodeCreated(node) {
    const isPro = PRO_NODE_CLASSES.has(node.comfyClass);
    const isBase = node.comfyClass === "AntimatterLtxDirectorX";
    if (!isPro && !isBase) return;

    const hiddenSet = isPro ? PRO_HIDDEN_WIDGETS : HIDDEN_WIDGETS;
    for (const widget of node.widgets || []) {
      if ((isPro && !PRO_VISIBLE_WIDGETS.has(widget.name)) || hiddenSet.has(widget.name)) hideWidget(widget);
    }
    if (isPro) ensureProFallbackButtons(node);
    attachDirectorDom(node, isPro);
  },

  async beforeRegisterNodeDef(nodeType, nodeData) {
    const isBase = nodeData.name === "AntimatterLtxDirectorX";
    const isPro = PRO_NODE_CLASSES.has(nodeData.name);
    if (!isBase && !isPro) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onNodeCreated?.apply(this, arguments);

      const hiddenSet = isPro ? PRO_HIDDEN_WIDGETS : HIDDEN_WIDGETS;
      for (const widget of this.widgets || []) {
        if ((isPro && !PRO_VISIBLE_WIDGETS.has(widget.name)) || hiddenSet.has(widget.name)) hideWidget(widget);
      }

      if (!getWidget(this, "timeline_data")) this.addWidget("string", "timeline_data", "", () => {});
      if (!getWidget(this, "local_prompts")) this.addWidget("string", "local_prompts", "", () => {});
      if (!getWidget(this, "segment_lengths")) this.addWidget("string", "segment_lengths", "", () => {});
      if (isPro) ensureProFallbackButtons(this);
      attachDirectorDom(this, isPro);
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const out = onConfigure?.apply(this, arguments);
      const hiddenSet = isPro ? PRO_HIDDEN_WIDGETS : HIDDEN_WIDGETS;
      for (const widget of this.widgets || []) {
        if ((isPro && !PRO_VISIBLE_WIDGETS.has(widget.name)) || hiddenSet.has(widget.name)) hideWidget(widget);
      }
      if (isPro) ensureProFallbackButtons(this);
      attachDirectorDom(this, isPro);
      setTimeout(() => {
        if (this._antimatterDirectorX) {
          if (isPro && this._antimatterDirectorX instanceof DirectorProSurface) {
            this._antimatterDirectorX.updatePreview();
            return;
          }
          this._antimatterDirectorX.durationFrames = Math.max(1, Math.round(Number(getWidgetValue(this, "duration_frames", 120))));
          this._antimatterDirectorX.timeline = parseTimeline(getWidgetValue(this, "timeline_data", ""), this._antimatterDirectorX.durationFrames);
          if (isPro) {
            this._antimatterDirectorX.loraState = parseProLoraState(getWidgetValue(this, "pro_lora_stack_json", ""));
            this._antimatterDirectorX.cameraState = parseCameraState(getWidgetValue(this, "camera_control_json", ""));
            this._antimatterDirectorX.cameraState.mode = normalizeCameraMode(getWidgetValue(this, "camera_mode", this._antimatterDirectorX.cameraState.mode || "off"));
            this._antimatterDirectorX.loraState = enforceCameraExclusive(this._antimatterDirectorX.loraState, this._antimatterDirectorX.cameraState);
            this._antimatterDirectorX.proPreset = String(getWidgetValue(this, "pro_lora_preset", "clean_default"));
          }
          this._antimatterDirectorX.render();
          if (isPro) this._antimatterDirectorX.renderPro();
        }
      }, 0);
      return out;
    };

    const onRemoved = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function () {
      this._antimatterDirectorX?.destroy();
      return onRemoved?.apply(this, arguments);
    };
  },
});
