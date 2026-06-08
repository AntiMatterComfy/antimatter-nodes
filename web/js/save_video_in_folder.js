import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const TARGET_NODES = new Set([
	"AntiMatter_Save_Video_in_Folder",
	"Save_Video_in_Folder",
]);

function isTargetNode(node) {
	return TARGET_NODES.has(node?.type) || TARGET_NODES.has(node?.constructor?.nodeData?.name);
}

function getNodeById(id, graph = app.graph) {
	let currentGraph = graph;
	let node;
	for (const segment of String(id).split(":")) {
		node = currentGraph?.getNodeById?.(segment);
		currentGraph = node?.subgraph;
	}
	return node;
}

function getPreviewFromMessage(message) {
	const gifs = message?.gifs ?? message?.output?.gifs ?? message?.ui?.gifs;
	if (Array.isArray(gifs)) {
		return gifs[0] || null;
	}
	return undefined;
}

function chainCallback(object, property, callback) {
	if (!object) return;

	const original = object[property];
	object[property] = function () {
		const result = original?.apply(this, arguments);
		const callbackResult = callback?.apply(this, arguments);
		return callbackResult ?? result;
	};
}

function fitNode(node) {
	requestAnimationFrame(() => {
		node.setSize?.(node.computeSize?.());
		app.graph.setDirtyCanvas(true, true);
	});
}

function addVideoPreview(nodeType) {
	chainCallback(nodeType.prototype, "onNodeCreated", function () {
		const element = document.createElement("div");
		element.style.width = "100%";

		const previewNode = this;
		let previewWidget;
		previewWidget = this.addDOMWidget("videopreview", "preview", element, {
			serialize: false,
			hideOnZoom: false,
			getValue() {
				return previewWidget.value;
			},
			setValue(value) {
				previewWidget.value = value;
			},
		});

		previewWidget.value = { hidden: true, params: {} };
		previewWidget.parentEl = document.createElement("div");
		previewWidget.parentEl.style.width = "100%";
		previewWidget.parentEl.hidden = true;

		previewWidget.videoEl = document.createElement("video");
		previewWidget.videoEl.controls = true;
		previewWidget.videoEl.autoplay = true;
		previewWidget.videoEl.loop = true;
		previewWidget.videoEl.muted = true;
		previewWidget.videoEl.playsInline = true;
		previewWidget.videoEl.preload = "auto";
		previewWidget.videoEl.style.width = "100%";
		previewWidget.videoEl.style.display = "block";

		previewWidget.parentEl.appendChild(previewWidget.videoEl);
		element.appendChild(previewWidget.parentEl);

		previewWidget.computeSize = function (width) {
			if (this.parentEl.hidden || !this.videoEl.src) {
				return [width, -4];
			}

			const aspectRatio =
				this.videoEl.videoWidth && this.videoEl.videoHeight
					? this.videoEl.videoWidth / this.videoEl.videoHeight
					: 16 / 9;
			const height = Math.max(140, (previewNode.size[0] - 20) / aspectRatio + 36);
			return [width, height];
		};

		previewWidget.updateSource = function () {
			const params = this.value?.params;
			if (!params?.filename) {
				this.videoEl.pause();
				this.videoEl.removeAttribute("src");
				this.videoEl.load();
				this.parentEl.hidden = true;
				fitNode(previewNode);
				return;
			}

			const viewParams = { ...params, timestamp: Date.now() };
			this.videoEl.pause();
			this.videoEl.removeAttribute("src");
			this.videoEl.load();
			this.videoEl.src = api.apiURL("/view?" + new URLSearchParams(viewParams));
			this.parentEl.hidden = false;
			this.videoEl.load();
			this.videoEl.play?.().catch(() => {});
			fitNode(previewNode);
		};

		previewWidget.videoEl.addEventListener("loadedmetadata", () => fitNode(previewNode));
		previewWidget.videoEl.addEventListener("loadeddata", () => {
			previewWidget.videoEl.play?.().catch(() => {});
			fitNode(previewNode);
		});
		previewWidget.videoEl.addEventListener("error", () => {
			previewWidget.parentEl.hidden = true;
			fitNode(previewNode);
		});

		this.updateParameters = (params, forceUpdate = false) => {
			if (!params?.filename) {
				previewWidget.value.params = {};
				previewWidget.updateSource();
				return;
			}

			previewWidget.value.hidden = false;
			previewWidget.value.params = { ...params };
			if (forceUpdate) {
				previewWidget.updateSource();
			}
		};
	});

	chainCallback(nodeType.prototype, "onExecuted", function (message) {
		this.updateParameters?.(getPreviewFromMessage(message), true);
	});
}

app.registerExtension({
	name: "AntiMatter.SaveVideoInFolder.Preview",
	init() {
		api.addEventListener("executed", ({ detail }) => {
			const preview = getPreviewFromMessage(detail);
			const node = getNodeById(detail?.display_node ?? detail?.node);
			if (preview !== undefined && isTargetNode(node)) {
				node.updateParameters?.(preview, true);
			}
		});
	},
	beforeRegisterNodeDef(nodeType, nodeData) {
		if (
			TARGET_NODES.has(nodeData?.name) ||
			TARGET_NODES.has(nodeData?.display_name) ||
			TARGET_NODES.has(nodeData?.displayName)
		) {
			addVideoPreview(nodeType);
		}
	},
});
