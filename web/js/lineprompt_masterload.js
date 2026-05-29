import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

const SETTINGS_ID = "LinePrompt_MasterLoad.StylesRoot";
const DEFAULT_STYLES_ROOT = "custom_nodes/Style_evo/styles";
const TARGET_CLASSES = new Set(["LinePrompt_MasterLoad", "LinePrompt_MasterLoad_JSON"]);
let styleFilesPromise = null;

function chainCallback(object, property, callback) {
	const original = object?.[property];
	object[property] = function () {
		const result = original?.apply(this, arguments);
		callback?.apply(this, arguments);
		return result;
	};
}

function hideWidget(widget) {
	if (!widget) return;
	widget.hidden = true;
	const originalComputeSize = widget.computeSize;
	widget.computeSize = () => [0, -4];
	widget._lpml_originalComputeSize = originalComputeSize;
}

function getStylesRoot() {
	return app.ui?.settings?.getSettingValue?.(SETTINGS_ID) || DEFAULT_STYLES_ROOT;
}

async function getStyleFiles() {
	if (!styleFilesPromise) {
		const root = encodeURIComponent(getStylesRoot());
		styleFilesPromise = api
			.fetchApi(`/lineprompt_masterload/styles?root=${root}`)
			.then((response) => response.json())
			.then((data) => (data?.files?.length ? data.files : ["none"]))
			.catch(() => ["none"]);
	}
	return styleFilesPromise;
}

async function refreshStyleFileWidget(node) {
	const widget = node.widgets?.find((w) => w.name === "style_file");
	if (!widget) return;

	const files = await getStyleFiles();
	const currentValue = widget.value;
	const values = currentValue && !files.includes(currentValue) ? [currentValue, ...files] : files;

	widget.options = widget.options || {};
	widget.options.values = values;
	if (!values.includes(widget.value)) {
		widget.value = values[0] || "none";
	}

	app.graph.setDirtyCanvas(true, false);
}

function refreshAllStyleFileWidgets() {
	styleFilesPromise = null;
	for (const node of app.graph?._nodes || []) {
		if (TARGET_CLASSES.has(node.comfyClass)) {
			refreshStyleFileWidget(node);
		}
	}
}

function removeButtonWidget(node, name) {
	if (!node.widgets) return;
	const index = node.widgets.findIndex((w) => w.type === "button" && w.name === name);
	if (index >= 0) {
		node.widgets[index].onRemove?.();
		node.widgets.splice(index, 1);
	}
}

function bumpNavWidget(node, delta) {
	const sceneModeWidget = node.widgets?.find((w) => w.name === "scene_mode");
	const manualSceneWidget = node.widgets?.find((w) => w.name === "manual_scene");
	if (node.comfyClass === "LinePrompt_MasterLoad_JSON" && sceneModeWidget?.value === "manual" && manualSceneWidget) {
		const currentScene = Number(manualSceneWidget.value || 1);
		manualSceneWidget.value = Math.max(1, currentScene + delta);
		manualSceneWidget.callback?.(manualSceneWidget.value);
		app.graph.setDirtyCanvas(true, true);
		return;
	}

	const navWidget = node.widgets?.find((w) => w.name === "nav");
	if (!navWidget) return;

	const current = Number(navWidget.value || 0);
	navWidget.value = current + delta;
	navWidget.callback?.(navWidget.value);
	app.graph.setDirtyCanvas(true, true);
}

function addButtonWidget(node, name, label, delta) {
	if (!node?.addWidget) return;
	const widget = node.addWidget("button", name, label, () => bumpNavWidget(node, delta));
	if (widget) {
		widget.serializeValue = () => undefined;
	}
}

function setupLinePromptUI(node) {
	if (!node) return;

	// Hide internal navigation counter widget (used by buttons)
	const navWidget = node.widgets?.find((w) => w.name === "nav");
	if (navWidget && !navWidget._lpml_hidden) {
		hideWidget(navWidget);
		navWidget._lpml_hidden = true;
	}

	removeButtonWidget(node, "Previous");
	removeButtonWidget(node, "Next");
	if (navWidget) {
		addButtonWidget(node, "Previous", "Previous", -1);
		addButtonWidget(node, "Next", "Next", 1);
	}

	// Read-only preview widget (updated from backend ui message)
	let previewWidget = node.widgets?.find((w) => w.name === "preview");
	if (!previewWidget) {
		previewWidget = ComfyWidgets["STRING"](node, "preview", ["STRING", { multiline: true }], app).widget;
		previewWidget.serializeValue = () => undefined;
	}
	if (previewWidget?.inputEl) {
		previewWidget.inputEl.readOnly = true;
		previewWidget.inputEl.style.opacity = 0.6;
	}

	node._lpml_previewWidget = previewWidget;
	node._lpml_titleBase = node._lpml_titleBase || node.title;
	refreshStyleFileWidget(node);
}

app.registerExtension({
	name: "LinePrompt_MasterLoad.UI",
	setup() {
		app.ui.settings.addSetting({
			id: SETTINGS_ID,
			name: "LinePrompt_MasterLoad styles txt folder",
			type: "text",
			defaultValue: DEFAULT_STYLES_ROOT,
			tooltip: "Parent folder scanned recursively for .txt files in the LinePrompt_MasterLoad style_file dropdown.",
			onChange() {
				refreshAllStyleFileWidgets();
			},
		});
	},
	async beforeRegisterNodeDef(nodeType, nodeData) {
		if (!TARGET_CLASSES.has(nodeData?.name)) return;

		chainCallback(nodeType.prototype, "onNodeCreated", function () {
			setupLinePromptUI(this);
		});

		chainCallback(nodeType.prototype, "onConfigure", function () {
			// Some frontend versions rebuild widgets; ensure UI exists.
			setupLinePromptUI(this);
		});

		const onExecuted = nodeType.prototype.onExecuted;
		nodeType.prototype.onExecuted = function (message) {
			onExecuted?.apply(this, arguments);

			let preview = message?.preview ?? message?.ui?.preview ?? "";
			let status = message?.status ?? message?.ui?.status ?? "";

			// Backend ui values are often arrays/tuples. Also guard against strings being
			// treated as iterables and split into chars by older frontends.
			if (preview instanceof Array) preview = preview.flat(Infinity).filter((x) => x != null).join("\n");
			if (status instanceof Array) status = status.flat(Infinity).filter((x) => x != null).join("");

			if (this._lpml_previewWidget) {
				this._lpml_previewWidget.value = preview;
			}

			if (status && this._lpml_titleBase) {
				this.title = `${this._lpml_titleBase} [${status}]`;
			}

			this.onResize?.(this.size);
		};
	},
});
