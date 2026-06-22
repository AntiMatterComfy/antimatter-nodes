import { app } from "/scripts/app.js";

const TARGET_NODE = "LMStudioThreeImageAgent";

const FIELD_SECTIONS = [
  {
    id: "prompt",
    title: "Prompt",
    fields: [
      { name: "prompt", label: "User Prompt", type: "textarea" },
      { name: "system_prompt", label: "System Prompt", type: "textarea" },
      { name: "agent_instructions", label: "Agent Instructions", type: "textarea" },
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
    id: "images_json",
    title: "Images / JSON",
    fields: [
      { name: "image_detail", label: "Image Detail", type: "select", options: ["auto", "low", "high"] },
      { name: "image_format", label: "Image Format", type: "select", options: ["PNG", "JPEG"] },
      { name: "max_image_side", label: "Max Image Side", type: "number", step: "64" },
      { name: "request_timeout_seconds", label: "Request Timeout Seconds", type: "number", step: "30" },
      { name: "keep_model_loaded", label: "Keep Model Loaded", type: "checkbox" },
      { name: "idle_ttl_seconds", label: "Idle TTL Seconds", type: "number", step: "300" },
      { name: "save_json", label: "Save JSON", type: "checkbox" },
      { name: "json_output_dir", label: "JSON Output Dir", type: "text" },
      { name: "json_filename_prefix", label: "JSON Filename Prefix", type: "text" },
      { name: "always_run", label: "Always Run", type: "checkbox" },
    ],
  },
];

const EDITOR_FIELD_NAMES = new Set(FIELD_SECTIONS.flatMap((section) => section.fields.map((field) => field.name)));

function getWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function readWidgetValue(node, name) {
  return getWidget(node, name)?.value ?? "";
}

function setWidgetValue(node, name, value) {
  const widget = getWidget(node, name);
  if (!widget) return;
  widget.value = value;
  widget.callback?.call(widget, value);
}

function hideWidget(widget) {
  if (!widget || widget._amLm3Hidden) return;
  widget._amLm3OriginalType = widget.type;
  widget._amLm3OriginalComputeSize = widget.computeSize;
  widget.type = "am_lm3_hidden";
  widget.computeSize = () => [0, -4];
  widget.hidden = true;
  widget._amLm3Hidden = true;
}

function hideEditorWidgets(node) {
  for (const widget of node.widgets || []) {
    if (EDITOR_FIELD_NAMES.has(widget.name)) hideWidget(widget);
  }
}

function shortText(value, max = 240) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return "Not set";
  return text.length > max ? `${text.slice(0, max - 1)}...` : text;
}

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderNodeContent(node) {
  const body = node._amLm3Body;
  if (!body?.isConnected) return;

  const prompt = readWidgetValue(node, "prompt");
  const systemPrompt = readWidgetValue(node, "system_prompt");
  const model = readWidgetValue(node, "model");
  const baseUrl = readWidgetValue(node, "lmstudio_base_url");
  const temperature = readWidgetValue(node, "temperature");
  const maxTokens = readWidgetValue(node, "max_tokens");
  const saveJson = readWidgetValue(node, "save_json");
  const jsonOutputDir = readWidgetValue(node, "json_output_dir");

  body.innerHTML = `
    <div class="am-lm3-title">LM Studio 3 Image Agent</div>
    <div class="am-lm3-subtitle">3 image inputs to local LM Studio vision model</div>
    <div class="am-lm3-line"></div>
    <div class="am-lm3-grid">
      <div class="am-lm3-card">
        <span>Model</span>
        <b>${esc(model || "local-vision-model-name")}</b>
      </div>
      <div class="am-lm3-card">
        <span>Endpoint</span>
        <b>${esc(baseUrl || "http://127.0.0.1:1234/v1")}</b>
      </div>
      <div class="am-lm3-card">
        <span>Temperature</span>
        <b>${esc(temperature)}</b>
      </div>
      <div class="am-lm3-card">
        <span>Max Tokens</span>
        <b>${esc(maxTokens)}</b>
      </div>
    </div>
    <div class="am-lm3-section">
      <h4>Prompt</h4>
      <pre>${esc(shortText(prompt, 520))}</pre>
    </div>
    <div class="am-lm3-section">
      <h4>System</h4>
      <pre>${esc(shortText(systemPrompt, 360))}</pre>
    </div>
    <div class="am-lm3-footer">
      <span>JSON: ${saveJson ? "enabled" : "disabled"}</span>
      <span>${esc(jsonOutputDir || "lmstudio_json")}</span>
    </div>
  `;
}

function attachEditButton(wrap, onClick) {
  const btn = document.createElement("button");
  btn.className = "am-lm3-editbtn";
  btn.type = "button";
  btn.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 17.25V20h2.75L17.82 8.93l-2.75-2.75L4 17.25Zm15.71-10.04a.996.996 0 0 0 0-1.41L18.2 4.29a.996.996 0 0 0-1.41 0l-1.18 1.18 2.75 2.75 1.35-1.01Z"/>
    </svg>
    <span>Edit</span>
  `;
  btn.addEventListener("mousedown", (event) => {
    event.stopPropagation();
  });
  btn.addEventListener("click", (event) => {
    event.stopPropagation();
    event.preventDefault();
    onClick();
  });
  wrap.appendChild(btn);
  return btn;
}

function createNodeDOM(node) {
  const uid = `am-lm3-${Math.random().toString(36).slice(2, 10)}`;
  const wrap = document.createElement("div");
  wrap.id = uid;
  wrap.className = "am-lm3-wrap";
  wrap.innerHTML = `
<style>
#${uid} {
  width: 100%;
  height: 100%;
  min-height: 260px;
  box-sizing: border-box;
  position: relative;
  color: #f3eefc;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
  pointer-events: none;
}
#${uid} .am-lm3-body {
  height: 100%;
  min-height: 260px;
  box-sizing: border-box;
  padding: 20px 18px 16px;
  border: 1px solid rgba(168, 85, 247, .52);
  border-radius: 10px;
  background:
    radial-gradient(520px 220px at 90% -10%, rgba(147, 51, 234, .25), transparent 62%),
    linear-gradient(180deg, #18111f 0%, #0b0710 100%);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.08),
    0 0 24px rgba(126,34,206,.22);
  overflow: auto;
  pointer-events: auto;
}
#${uid} .am-lm3-title {
  text-align: center;
  font-size: 20px;
  font-weight: 820;
  letter-spacing: .1px;
}
#${uid} .am-lm3-subtitle {
  margin-top: 5px;
  text-align: center;
  color: #c9b7f2;
  font-size: 12px;
  font-weight: 650;
}
#${uid} .am-lm3-line {
  height: 2px;
  margin: 14px 0;
  background: linear-gradient(90deg, transparent, #a855f7 12%, #d8b4fe 50%, #7e22ce 88%, transparent);
  box-shadow: 0 0 14px rgba(168,85,247,.72);
}
#${uid} .am-lm3-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
#${uid} .am-lm3-card,
#${uid} .am-lm3-section pre {
  border: 1px solid rgba(168,85,247,.22);
  border-radius: 6px;
  background: rgba(8, 6, 12, .82);
}
#${uid} .am-lm3-card {
  padding: 8px 10px;
  min-width: 0;
}
#${uid} .am-lm3-card span,
#${uid} .am-lm3-footer span {
  display: block;
  color: #a78bfa;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .55px;
}
#${uid} .am-lm3-card b {
  display: block;
  margin-top: 4px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #faf5ff;
  font-size: 12px;
}
#${uid} .am-lm3-section {
  margin-top: 10px;
}
#${uid} .am-lm3-section h4 {
  margin: 0 0 5px;
  color: #eee7ff;
  font-size: 13px;
}
#${uid} .am-lm3-section pre {
  margin: 0;
  padding: 8px 10px;
  color: #f8f5ff;
  font: 11px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: pre-wrap;
}
#${uid} .am-lm3-footer {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  color: #d8b4fe;
}
#${uid} .am-lm3-editbtn {
  position: absolute;
  top: 10px;
  right: 10px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid rgba(216,180,254,.55);
  border-radius: 7px;
  background:
    linear-gradient(180deg, rgba(216,180,254,.22), rgba(88,28,135,.78)),
    #09070f;
  color: #fff;
  box-shadow: 0 0 16px rgba(168,85,247,.35), inset 0 1px 0 rgba(255,255,255,.12);
  cursor: pointer;
  font-weight: 800;
  pointer-events: auto;
}
#${uid} .am-lm3-editbtn svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}
#${uid} .am-lm3-editbtn:hover {
  background:
    linear-gradient(180deg, rgba(233,213,255,.32), rgba(126,34,206,.92)),
    #0b0710;
  border-color: rgba(233,213,255,.82);
}
</style>
<div class="am-lm3-body"></div>
  `;

  node._amLm3Body = wrap.querySelector(".am-lm3-body");
  attachEditButton(wrap, () => openEditor(node));
  renderNodeContent(node);
  return wrap;
}

function fieldValueFromElement(field, element) {
  if (field.type === "checkbox") return Boolean(element.checked);
  if (field.type === "number") {
    const raw = element.value;
    if (raw === "") return 0;
    return raw.includes(".") ? parseFloat(raw) : parseInt(raw, 10);
  }
  return element.value;
}

function createField(node, field) {
  const row = document.createElement("label");
  row.className = "am-lm3-editor-field";
  row.dataset.fieldName = field.name;

  const label = document.createElement("span");
  label.textContent = field.label;
  row.appendChild(label);

  const value = readWidgetValue(node, field.name);
  let input;

  if (field.type === "textarea") {
    input = document.createElement("textarea");
    input.value = value ?? "";
    input.spellcheck = false;
  } else if (field.type === "select") {
    input = document.createElement("select");
    for (const optValue of field.options || []) {
      const option = document.createElement("option");
      option.value = optValue;
      option.textContent = optValue;
      input.appendChild(option);
    }
    input.value = value ?? field.options?.[0] ?? "";
  } else if (field.type === "checkbox") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(value);
    row.classList.add("am-lm3-editor-check");
  } else {
    input = document.createElement("input");
    input.type = field.type || "text";
    input.value = value ?? "";
    if (field.step) input.step = field.step;
  }

  input.dataset.widgetName = field.name;
  row.appendChild(input);
  return row;
}

function openEditor(node) {
  if (node._amLm3EditorOverlay?.isConnected) return;

  const uid = `am-lm3-editor-${Math.random().toString(36).slice(2, 10)}`;
  const overlay = document.createElement("div");
  node._amLm3EditorOverlay = overlay;
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
  background: rgba(0,0,0,.74);
  backdrop-filter: blur(4px);
  color: #f8f3ff;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
}
#${uid} * { box-sizing: border-box; }
#${uid} .am-lm3-editor {
  width: min(1160px, calc(100vw - 32px));
  height: min(810px, calc(100vh - 32px));
  display: grid;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
  border: 1px solid rgba(168,85,247,.62);
  border-radius: 8px;
  background:
    radial-gradient(760px 260px at 100% -12%, rgba(168,85,247,.22), transparent 64%),
    #17121f;
  box-shadow: 0 34px 90px rgba(0,0,0,.74), 0 0 38px rgba(126,34,206,.3);
}
#${uid} .am-lm3-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 16px;
  background: #0b0710;
  border-bottom: 1px solid rgba(168,85,247,.5);
}
#${uid} .am-lm3-editor-brand {
  display: flex;
  align-items: baseline;
  gap: 9px;
  font-weight: 850;
  font-size: 18px;
}
#${uid} .am-lm3-editor-brand b {
  color: #c084fc;
}
#${uid} .am-lm3-editor-close {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(216,180,254,.32);
  border-radius: 6px;
  background: #17111f;
  color: #d8b4fe;
  cursor: pointer;
  font-size: 18px;
}
#${uid} .am-lm3-editor-body {
  display: grid;
  grid-template-columns: 210px 1fr;
  min-height: 0;
}
#${uid} .am-lm3-editor-tabs {
  padding: 12px;
  background: #100b17;
  border-right: 1px solid rgba(168,85,247,.34);
  overflow-y: auto;
}
#${uid} .am-lm3-editor-tab {
  width: 100%;
  height: 37px;
  margin-bottom: 7px;
  padding: 0 11px;
  border: 1px solid rgba(168,85,247,.22);
  border-radius: 6px;
  background: #191121;
  color: #d8c5ff;
  cursor: pointer;
  text-align: left;
  font-weight: 750;
}
#${uid} .am-lm3-editor-tab.active {
  color: #fff;
  border-color: rgba(216,180,254,.72);
  background: linear-gradient(180deg, rgba(126,34,206,.82), rgba(32,20,44,.96));
  box-shadow: 0 0 16px rgba(168,85,247,.26);
}
#${uid} .am-lm3-editor-panels {
  min-height: 0;
  overflow: hidden;
}
#${uid} .am-lm3-editor-panel {
  display: none;
  height: 100%;
  padding: 16px;
  overflow-y: auto;
}
#${uid} .am-lm3-editor-panel.active {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px;
  align-content: start;
}
#${uid} .am-lm3-editor-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
#${uid} .am-lm3-editor-field span {
  color: #c4b5fd;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: .55px;
  text-transform: uppercase;
}
#${uid} input,
#${uid} select,
#${uid} textarea {
  width: 100%;
  border: 1px solid rgba(168,85,247,.3);
  border-radius: 6px;
  background: #0d0912;
  color: #fbf7ff;
  padding: 9px 10px;
  outline: none;
  font: 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
#${uid} textarea {
  min-height: 180px;
  resize: vertical;
  line-height: 1.45;
}
#${uid} input:focus,
#${uid} select:focus,
#${uid} textarea:focus {
  border-color: rgba(216,180,254,.78);
  box-shadow: 0 0 0 3px rgba(168,85,247,.12);
}
#${uid} .am-lm3-editor-check {
  flex-direction: row;
  align-items: center;
  min-height: 40px;
  padding: 9px 10px;
  border: 1px solid rgba(168,85,247,.22);
  border-radius: 6px;
  background: #120c19;
}
#${uid} .am-lm3-editor-check input {
  width: 18px;
  height: 18px;
  margin-left: auto;
  padding: 0;
  accent-color: #9333ea;
}
#${uid} .am-lm3-editor-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 13px 16px;
  background: #0b0710;
  border-top: 1px solid rgba(168,85,247,.44);
}
#${uid} .am-lm3-editor-action {
  min-width: 96px;
  height: 36px;
  border: 1px solid rgba(168,85,247,.38);
  border-radius: 6px;
  background: #17111f;
  color: #f7edff;
  cursor: pointer;
  font-weight: 820;
}
#${uid} .am-lm3-editor-action.primary {
  border-color: rgba(216,180,254,.72);
  background: linear-gradient(180deg, #a855f7, #581c87);
  color: #fff;
  box-shadow: 0 0 18px rgba(168,85,247,.32);
}
@media (max-width: 760px) {
  #${uid} .am-lm3-editor-body { grid-template-columns: 1fr; }
  #${uid} .am-lm3-editor-tabs { display: flex; gap: 8px; overflow-x: auto; border-right: 0; border-bottom: 1px solid rgba(168,85,247,.34); }
  #${uid} .am-lm3-editor-tab { width: auto; white-space: nowrap; }
  #${uid} .am-lm3-editor-panel.active { grid-template-columns: 1fr; }
}
</style>
<div class="am-lm3-editor">
  <div class="am-lm3-editor-head">
    <div class="am-lm3-editor-brand">LM Studio 3 Image <b>AntiMatter</b></div>
    <button class="am-lm3-editor-close" type="button">X</button>
  </div>
  <div class="am-lm3-editor-body">
    <div class="am-lm3-editor-tabs"></div>
    <div class="am-lm3-editor-panels"></div>
  </div>
  <div class="am-lm3-editor-foot">
    <button class="am-lm3-editor-action" type="button" data-action="cancel">Cancel</button>
    <button class="am-lm3-editor-action primary" type="button" data-action="save">Save</button>
  </div>
</div>
  `;

  const tabs = overlay.querySelector(".am-lm3-editor-tabs");
  const panels = overlay.querySelector(".am-lm3-editor-panels");

  for (const [index, section] of FIELD_SECTIONS.entries()) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = `am-lm3-editor-tab ${index === 0 ? "active" : ""}`;
    tab.dataset.section = section.id;
    tab.textContent = section.title;
    tabs.appendChild(tab);

    const panel = document.createElement("div");
    panel.className = `am-lm3-editor-panel ${index === 0 ? "active" : ""}`;
    panel.dataset.section = section.id;
    for (const field of section.fields) {
      panel.appendChild(createField(node, field));
    }
    panels.appendChild(panel);
  }

  const activate = (sectionId) => {
    overlay.querySelectorAll(".am-lm3-editor-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.section === sectionId);
    });
    overlay.querySelectorAll(".am-lm3-editor-panel").forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.section === sectionId);
    });
  };

  const close = () => {
    overlay.remove();
    if (node._amLm3EditorOverlay === overlay) node._amLm3EditorOverlay = null;
  };

  tabs.addEventListener("click", (event) => {
    const tab = event.target.closest(".am-lm3-editor-tab");
    if (tab) activate(tab.dataset.section);
  });
  overlay.querySelector(".am-lm3-editor-close").addEventListener("click", close);
  overlay.querySelector('[data-action="cancel"]').addEventListener("click", close);
  overlay.querySelector('[data-action="save"]').addEventListener("click", () => {
    for (const section of FIELD_SECTIONS) {
      for (const field of section.fields) {
        const element = overlay.querySelector(`[data-widget-name="${field.name}"]`);
        if (!element) continue;
        setWidgetValue(node, field.name, fieldValueFromElement(field, element));
      }
    }
    hideEditorWidgets(node);
    renderNodeContent(node);
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
    close();
  });

  const keyBlock = (event) => {
    const key = String(event.key || "").toLowerCase();
    if (key === "escape") {
      event.preventDefault();
      event.stopImmediatePropagation();
      close();
      return;
    }
    event.stopPropagation();
  };
  overlay.addEventListener("keydown", keyBlock, true);
  overlay.addEventListener("keyup", keyBlock, true);
  overlay.addEventListener("keypress", keyBlock, true);

  document.body.appendChild(overlay);
}

function setupNode(node) {
  if (node._amLm3Installed) {
    hideEditorWidgets(node);
    renderNodeContent(node);
    return;
  }
  node._amLm3Installed = true;
  hideEditorWidgets(node);

  const wrap = createNodeDOM(node);
  node._amLm3Wrap = wrap;

  if (typeof node.addDOMWidget === "function") {
    const widget = node.addDOMWidget("lmstudio_3image_editor", "custom", wrap, {
      serialize: false,
      hideOnZoom: false,
      getMinHeight: () => 300,
    });
    widget.computeSize = (width) => [Math.max(440, (width || node.size?.[0] || 520) - 20), 320];
  } else {
    const widget = node.addWidget("button", "Edit", null, () => openEditor(node), { serialize: false });
    widget.serialize = false;
  }

  node.color = node.color || "#160b22";
  node.bgcolor = node.bgcolor || "#0b0710";
  node.size = [Math.max(node.size?.[0] || 520, 560), Math.max(node.size?.[1] || 360, 390)];
  node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "AntiMatter.LMStudio.ThreeImageEditor",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== TARGET_NODE) return;

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = originalOnNodeCreated?.apply(this, arguments);
      setupNode(this);
      return result;
    };

    const originalOnConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const result = originalOnConfigure?.apply(this, arguments);
      setTimeout(() => setupNode(this), 0);
      return result;
    };

    nodeType.prototype.onDblClick = function () {
      openEditor(this);
      return false;
    };
  },
});
