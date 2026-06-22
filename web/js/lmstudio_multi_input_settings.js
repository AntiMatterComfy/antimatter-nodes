import { app } from "/scripts/app.js";

const TARGET_NODE = "LMStudioMultiInputSettingsAgent";

const FIELD_SECTIONS = [
  {
    id: "instructions",
    title: "Instructions",
    content: `
      <div class="lmstudio-instructions">
        <h3>Placeholder Inputs</h3>
        <p>The node has five text placeholder inputs. Use explicit indexed tokens in any User Query field.</p>
        <table>
          <tr><th>Socket</th><th>Use in query</th><th>Aliases</th></tr>
          <tr><td>input_text_placeholder</td><td>[p1]</td><td>[placeholder_1], [input_text_1], [text_1]</td></tr>
          <tr><td>placeholder_2</td><td>[p2]</td><td>[placeholder_2], [input_text_2], [text_2]</td></tr>
          <tr><td>placeholder_3</td><td>[p3]</td><td>[placeholder_3], [input_text_3], [text_3]</td></tr>
          <tr><td>placeholder_4</td><td>[p4]</td><td>[placeholder_4], [input_text_4], [text_4]</td></tr>
          <tr><td>placeholder_5</td><td>[p5]</td><td>[placeholder_5], [input_text_5], [text_5]</td></tr>
        </table>
        <h3>Compatibility</h3>
        <p>[...] and [input_text] still map to [p1] for older workflows. Unknown bracket tokens are left unchanged so mistakes are visible.</p>
        <h3>Outputs</h3>
        <p>Use image_1_text, image_2_text, image_3_text, or input_text_output for separate branches. Use combined_text when the next node should receive every non-empty result in execution order.</p>
        <h3>Examples</h3>
        <pre>Describe image_1 character named [p1] in the scene [p3].
Compare outfit notes: [p2] with background note: [p4].
Write a final combined summary using [p1], [p2], [p3], [p4], [p5].</pre>
      </div>
    `,
  },
  {
    id: "project",
    title: "Project",
    fields: [
      { name: "project_path", label: "Project Path", type: "text" },
      { name: "run_folder_name", label: "Run Folder Name", type: "text" },
      { name: "save_json", label: "Save JSON", type: "checkbox" },
    ],
  },
  {
    id: "image_1",
    title: "Image 1",
    fields: [
      { name: "image_1_system_prompt", label: "System Prompt", type: "textarea" },
      { name: "image_1_user_query", label: "User Query", type: "textarea" },
    ],
  },
  {
    id: "image_2",
    title: "Image 2",
    fields: [
      { name: "image_2_system_prompt", label: "System Prompt", type: "textarea" },
      { name: "image_2_user_query", label: "User Query", type: "textarea" },
    ],
  },
  {
    id: "image_3",
    title: "Image 3",
    fields: [
      { name: "image_3_system_prompt", label: "System Prompt", type: "textarea" },
      { name: "image_3_user_query", label: "User Query", type: "textarea" },
    ],
  },
  {
    id: "text",
    title: "Input Text",
    fields: [
      { name: "text_system_prompt", label: "System Prompt", type: "textarea" },
      { name: "text_user_query", label: "User Query", type: "textarea" },
    ],
  },
  {
    id: "model",
    title: "Model",
    fields: [
      { name: "lmstudio_base_url", label: "LM Studio Base URL", type: "text" },
      { name: "api_key", label: "API Key", type: "text" },
      { name: "model", label: "Model", type: "text" },
      { name: "response_format", label: "Response Format", type: "select", options: ["text", "json_object"] },
    ],
  },
  {
    id: "generation",
    title: "Generation",
    fields: [
      { name: "temperature", label: "Temperature", type: "number", step: "0.05" },
      { name: "max_tokens", label: "Max Tokens", type: "number", step: "64" },
      { name: "top_p", label: "Top P", type: "number", step: "0.01" },
      { name: "presence_penalty", label: "Presence Penalty", type: "number", step: "0.05" },
      { name: "frequency_penalty", label: "Frequency Penalty", type: "number", step: "0.05" },
      { name: "seed", label: "Seed", type: "number", step: "1" },
      { name: "stop_sequences", label: "Stop Sequences", type: "textarea" },
      { name: "extra_body_json", label: "Extra Body JSON", type: "textarea" },
    ],
  },
  {
    id: "images",
    title: "Images",
    fields: [
      { name: "image_detail", label: "Image Detail", type: "select", options: ["auto", "low", "high"] },
      { name: "image_format", label: "Image Format", type: "select", options: ["PNG", "JPEG"] },
      { name: "max_image_side", label: "Max Image Side", type: "number", step: "64" },
      { name: "request_timeout_seconds", label: "Request Timeout Seconds", type: "number", step: "30" },
      { name: "keep_model_loaded", label: "Keep Model Loaded", type: "checkbox" },
      { name: "idle_ttl_seconds", label: "Idle TTL Seconds", type: "number", step: "300" },
      { name: "always_run", label: "Always Run", type: "checkbox" },
    ],
  },
];

const SETTINGS_FIELD_NAMES = new Set(
  FIELD_SECTIONS.flatMap((section) => (section.fields || []).map((field) => field.name))
);

function getWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function hideWidget(node, widget) {
  if (!widget || widget._lmstudioSettingsHidden) return;
  widget._lmstudioOriginalType = widget.type;
  widget._lmstudioOriginalComputeSize = widget.computeSize;
  widget.type = "lmstudio_settings_hidden";
  widget.computeSize = () => [0, -4];
  widget.hidden = true;
  widget._lmstudioSettingsHidden = true;
}

function hideSettingsWidgets(node) {
  for (const widget of node.widgets || []) {
    if (SETTINGS_FIELD_NAMES.has(widget.name)) {
      hideWidget(node, widget);
    }
  }
}

function setWidgetValue(node, name, value) {
  const widget = getWidget(node, name);
  if (!widget) return;
  widget.value = value;
  widget.callback?.call(widget, value);
}

function readWidgetValue(node, name) {
  const widget = getWidget(node, name);
  return widget ? widget.value : "";
}

function fieldValueFromElement(field, element) {
  if (field.type === "checkbox") {
    return Boolean(element.checked);
  }
  if (field.type === "number") {
    const raw = element.value;
    if (raw === "") return 0;
    return raw.includes(".") ? parseFloat(raw) : parseInt(raw, 10);
  }
  return element.value;
}

function createSettingsButton(node) {
  if (node._lmstudioSettingsButtonCreated) return;
  node._lmstudioSettingsButtonCreated = true;

  const uid = `lmstudio-settings-${Math.random().toString(36).slice(2, 10)}`;
  const root = document.createElement("div");
  root.id = uid;
  root.innerHTML = `
<style>
#${uid} {
  width: 100%;
  min-height: 58px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
#${uid} .lmstudio-settings-button {
  position: relative;
  width: calc(100% - 14px);
  min-height: 48px;
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 8px;
  color: #f4f4f4;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1.8px;
  background:
    linear-gradient(180deg, rgba(118,118,118,.42) 0%, rgba(28,28,28,.98) 34%, #030303 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.22),
    inset 0 -14px 24px rgba(0,0,0,.72),
    0 10px 22px rgba(0,0,0,.46);
  cursor: pointer;
  overflow: hidden;
  pointer-events: auto;
}
#${uid} .lmstudio-settings-button::before {
  content: "";
  position: absolute;
  top: 6px;
  left: -38%;
  width: 62%;
  height: 16px;
  transform: skewX(-22deg);
  background: linear-gradient(90deg, transparent, rgba(220,220,220,.5), transparent);
  filter: blur(1px);
}
#${uid} .lmstudio-settings-button:hover {
  border-color: rgba(235,235,235,.42);
  background:
    linear-gradient(180deg, rgba(150,150,150,.52) 0%, rgba(34,34,34,.98) 34%, #050505 100%);
}
#${uid} .lmstudio-settings-button:active {
  transform: translateY(1px);
}
</style>
<button class="lmstudio-settings-button" type="button">SETTINGS</button>
  `;

  const button = root.querySelector("button");
  button.addEventListener("click", () => openSettingsDialog(node));

  if (typeof node.addDOMWidget === "function") {
    const widget = node.addDOMWidget("lmstudio_settings_button", "custom", root, {
      serialize: false,
      hideOnZoom: false,
    });
    widget.computeSize = (width) => [Math.max(300, (width || node.size?.[0] || 360) - 20), 64];
  } else {
    const widget = node.addWidget("button", "SETTINGS", null, () => openSettingsDialog(node), {
      serialize: false,
    });
    widget.serialize = false;
  }

  node.size = [Math.max(node.size?.[0] || 360, 420), Math.max(node.size?.[1] || 160, 190)];
}

function createField(node, field) {
  const wrapper = document.createElement("label");
  wrapper.className = "lmstudio-field";
  wrapper.dataset.fieldName = field.name;

  const label = document.createElement("span");
  label.textContent = field.label;
  wrapper.appendChild(label);

  let input;
  const value = readWidgetValue(node, field.name);

  if (field.type === "textarea") {
    input = document.createElement("textarea");
    input.value = value ?? "";
    input.spellcheck = false;
  } else if (field.type === "select") {
    input = document.createElement("select");
    for (const optionValue of field.options || []) {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      input.appendChild(option);
    }
    input.value = value ?? field.options?.[0] ?? "";
  } else if (field.type === "checkbox") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(value);
    wrapper.classList.add("lmstudio-field-checkbox");
  } else {
    input = document.createElement("input");
    input.type = field.type || "text";
    input.value = value ?? "";
    if (field.step) input.step = field.step;
  }

  input.dataset.widgetName = field.name;
  input.dataset.fieldType = field.type;
  wrapper.appendChild(input);
  return wrapper;
}

function openSettingsDialog(node) {
  const uid = `lmstudio-modal-${Math.random().toString(36).slice(2, 10)}`;
  const overlay = document.createElement("div");
  overlay.id = uid;
  overlay.innerHTML = `
<style>
#${uid} {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,.72);
  backdrop-filter: blur(3px);
  color: #ededed;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
}
#${uid} * { box-sizing: border-box; }
#${uid} .lmstudio-modal {
  width: min(1180px, calc(100vw - 36px));
  height: min(820px, calc(100vh - 36px));
  background: #151515;
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 8px;
  box-shadow: 0 28px 80px rgba(0,0,0,.7);
  display: grid;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
}
#${uid} .lmstudio-header,
#${uid} .lmstudio-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  background: #101010;
  border-bottom: 1px solid rgba(255,255,255,.12);
}
#${uid} .lmstudio-footer {
  border-top: 1px solid rgba(255,255,255,.12);
  border-bottom: 0;
  justify-content: flex-end;
}
#${uid} .lmstudio-title {
  font-size: 18px;
  font-weight: 750;
  letter-spacing: .2px;
}
#${uid} .lmstudio-body {
  display: grid;
  grid-template-columns: 220px 1fr;
  min-height: 0;
}
#${uid} .lmstudio-tabs {
  padding: 12px;
  background: #111;
  border-right: 1px solid rgba(255,255,255,.12);
  overflow-y: auto;
}
#${uid} .lmstudio-tab {
  width: 100%;
  height: 36px;
  margin-bottom: 7px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 6px;
  background: #1d1d1d;
  color: #d8d8d8;
  text-align: left;
  padding: 0 11px;
  cursor: pointer;
}
#${uid} .lmstudio-tab.active {
  color: #fff;
  border-color: rgba(255,255,255,.32);
  background: linear-gradient(180deg, #383838, #191919);
}
#${uid} .lmstudio-panel {
  display: none;
  padding: 18px;
  overflow-y: auto;
  min-height: 0;
}
#${uid} .lmstudio-panel.active {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-content: start;
}
#${uid} .lmstudio-panel.lmstudio-panel-instructions.active {
  display: block;
}
#${uid} .lmstudio-instructions {
  max-width: 940px;
  color: #e8e8e8;
  font-size: 14px;
  line-height: 1.55;
}
#${uid} .lmstudio-instructions h3 {
  margin: 0 0 10px;
  color: #ffffff;
  font-size: 18px;
}
#${uid} .lmstudio-instructions h3:not(:first-child) {
  margin-top: 22px;
}
#${uid} .lmstudio-instructions p {
  margin: 0 0 12px;
  color: #cfcfcf;
}
#${uid} .lmstudio-instructions table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  overflow: hidden;
  border-radius: 6px;
}
#${uid} .lmstudio-instructions th,
#${uid} .lmstudio-instructions td {
  border: 1px solid rgba(255,255,255,.12);
  padding: 9px 10px;
  text-align: left;
  font: 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
#${uid} .lmstudio-instructions th {
  background: #242424;
  color: #ffffff;
}
#${uid} .lmstudio-instructions td {
  background: #191919;
  color: #eeeeee;
}
#${uid} .lmstudio-instructions pre {
  margin: 10px 0 0;
  padding: 12px;
  white-space: pre-wrap;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 6px;
  background: #111111;
  color: #f3f3f3;
  font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
#${uid} .lmstudio-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
#${uid} .lmstudio-field span {
  font-size: 12px;
  font-weight: 700;
  color: #bdbdbd;
  text-transform: uppercase;
  letter-spacing: .5px;
}
#${uid} input,
#${uid} select,
#${uid} textarea {
  width: 100%;
  border: 1px solid rgba(255,255,255,.15);
  border-radius: 6px;
  background: #202020;
  color: #f3f3f3;
  padding: 9px 10px;
  font: 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  outline: none;
}
#${uid} textarea {
  min-height: 160px;
  resize: vertical;
  line-height: 1.45;
}
#${uid} input:focus,
#${uid} select:focus,
#${uid} textarea:focus {
  border-color: rgba(180,180,180,.62);
  box-shadow: 0 0 0 3px rgba(255,255,255,.06);
}
#${uid} .lmstudio-field-checkbox {
  flex-direction: row;
  align-items: center;
  min-height: 38px;
  padding: 9px 10px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 6px;
  background: #1c1c1c;
}
#${uid} .lmstudio-field-checkbox input {
  width: 18px;
  height: 18px;
  margin-left: auto;
  padding: 0;
}
#${uid} .lmstudio-actions {
  display: flex;
  gap: 10px;
}
#${uid} .lmstudio-action {
  min-width: 96px;
  height: 34px;
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 6px;
  background: #242424;
  color: #f1f1f1;
  cursor: pointer;
  font-weight: 700;
}
#${uid} .lmstudio-action.primary {
  background: linear-gradient(180deg, #f2f2f2, #b9b9b9);
  color: #080808;
  border-color: rgba(255,255,255,.55);
}
#${uid} .lmstudio-close {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 6px;
  background: #222;
  color: #fff;
  cursor: pointer;
}
@media (max-width: 760px) {
  #${uid} .lmstudio-body { grid-template-columns: 1fr; }
  #${uid} .lmstudio-tabs { display: flex; overflow-x: auto; border-right: 0; border-bottom: 1px solid rgba(255,255,255,.12); }
  #${uid} .lmstudio-tab { white-space: nowrap; width: auto; }
  #${uid} .lmstudio-panel.active { grid-template-columns: 1fr; }
}
</style>
<div class="lmstudio-modal">
  <div class="lmstudio-header">
    <div class="lmstudio-title">LM Studio Multi Input Settings</div>
    <button class="lmstudio-close" type="button">X</button>
  </div>
  <div class="lmstudio-body">
    <div class="lmstudio-tabs"></div>
    <div class="lmstudio-panels"></div>
  </div>
  <div class="lmstudio-footer">
    <div class="lmstudio-actions">
      <button class="lmstudio-action" type="button" data-action="cancel">Cancel</button>
      <button class="lmstudio-action primary" type="button" data-action="save">Save</button>
    </div>
  </div>
</div>
  `;

  const tabs = overlay.querySelector(".lmstudio-tabs");
  const panels = overlay.querySelector(".lmstudio-panels");

  for (const [index, section] of FIELD_SECTIONS.entries()) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = `lmstudio-tab ${index === 0 ? "active" : ""}`;
    tab.dataset.section = section.id;
    tab.textContent = section.title;
    tabs.appendChild(tab);

    const panel = document.createElement("div");
    panel.className = `lmstudio-panel ${index === 0 ? "active" : ""}`;
    panel.dataset.section = section.id;
    if (section.content) {
      panel.classList.add("lmstudio-panel-instructions");
      panel.innerHTML = section.content;
    }
    for (const field of section.fields || []) {
      panel.appendChild(createField(node, field));
    }
    panels.appendChild(panel);
  }

  function activate(sectionId) {
    overlay.querySelectorAll(".lmstudio-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.section === sectionId);
    });
    overlay.querySelectorAll(".lmstudio-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.section === sectionId);
    });
  }

  function close() {
    overlay.remove();
  }

  tabs.addEventListener("click", (event) => {
    const tab = event.target.closest(".lmstudio-tab");
    if (tab) activate(tab.dataset.section);
  });

  overlay.querySelector(".lmstudio-close").addEventListener("click", close);
  overlay.querySelector('[data-action="cancel"]').addEventListener("click", close);
  overlay.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  overlay.querySelector('[data-action="save"]').addEventListener("click", () => {
    for (const section of FIELD_SECTIONS) {
      for (const field of section.fields || []) {
        const element = overlay.querySelector(`[data-widget-name="${field.name}"]`);
        if (!element) continue;
        setWidgetValue(node, field.name, fieldValueFromElement(field, element));
      }
    }
    hideSettingsWidgets(node);
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
    close();
  });

  document.body.appendChild(overlay);
}

function decorateNode(node) {
  hideSettingsWidgets(node);
  createSettingsButton(node);
  node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "ComfyUI.LMStudio.MultiInputSettingsAgent",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== TARGET_NODE) return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = originalOnNodeCreated?.apply(this, arguments);
      decorateNode(this);
      return result;
    };

    const originalOnConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = originalOnConfigure?.apply(this, arguments);
      setTimeout(() => decorateNode(this), 0);
      return result;
    };
  },
});
