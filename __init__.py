from .anti_aspect_ratio_master import AntiAspectRatioMaster
from .antimatter_text_file_appender import AntimatterTextFileAppender
from .batch_loader_from_folder import BatchLoaderFromFolder
from .lineprompt_masterload import LinePrompt_MasterLoad, LinePrompt_MasterLoad_JSON, LinePrompt_MasterLoad_JSON_Image
from .lmstudio_agents import LMStudioMultiInputSettingsAgent, LMStudioThreeImageAgent
from .ltx_director_x import (
    AntimatterLtxAudioTrackX,
    AntimatterLtxDirectorX,
    AntimatterLtxDirectorXOneNode,
    AntimatterLtxDirectorXPro,
    AntimatterLtxFragmentStitchX,
)
from .save_video_in_folder import AntiMatterVideoSavePopular, SaveVideoInFolder
from .text_filter import AntiMatterTextFilter
from .video_batch_loader import VideoBatchLoader

try:
    from comfy_api.latest import ComfyExtension, io
    from typing_extensions import override

    class AntiMatterExtension(ComfyExtension):
        @override
        async def get_node_list(self) -> list[type[io.ComfyNode]]:
            return [
                AntimatterLtxDirectorX,
                AntimatterLtxDirectorXPro,
                AntimatterLtxDirectorXOneNode,
                AntimatterLtxFragmentStitchX,
                AntimatterLtxAudioTrackX,
            ]

    async def comfy_entrypoint() -> AntiMatterExtension:
        return AntiMatterExtension()
except Exception:
    comfy_entrypoint = None

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "Anti_aspect_ratio_master": AntiAspectRatioMaster,
    "Antimatter_TextFileAppender": AntimatterTextFileAppender,
    "Batch_Loader_From_Folder": BatchLoaderFromFolder,
    "Antimetter_Video_Batch_Loader": VideoBatchLoader,
    "AntiMatter_Video_Save_Popular": AntiMatterVideoSavePopular,
    "AntiMatter_Save_Video_in_Folder": SaveVideoInFolder,
    "AntiMatter_TextFilter": AntiMatterTextFilter,
    "LinePrompt_MasterLoad": LinePrompt_MasterLoad,
    "LinePrompt_MasterLoad_JSON": LinePrompt_MasterLoad_JSON,
    "LinePrompt_MasterLoad_JSON_Image": LinePrompt_MasterLoad_JSON_Image,
    "LMStudioThreeImageAgent": LMStudioThreeImageAgent,
    "LMStudioMultiInputSettingsAgent": LMStudioMultiInputSettingsAgent,
    "AntimatterLtxDirectorX": AntimatterLtxDirectorX,
    "AntimatterLtxDirectorXPro": AntimatterLtxDirectorXPro,
    "AntimatterLtxDirectorXOneNode": AntimatterLtxDirectorXOneNode,
    "AntimatterLtxFragmentStitchX": AntimatterLtxFragmentStitchX,
    "AntimatterLtxAudioTrackX": AntimatterLtxAudioTrackX,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Anti_aspect_ratio_master": "Anti_aspect_ratio_master",
    "Antimatter_TextFileAppender": "Antimatter Text File Appender",
    "Batch_Loader_From_Folder": "Batch Loader from folder",
    "Antimetter_Video_Batch_Loader": "Video_Batch_Loader",
    "AntiMatter_Video_Save_Popular": "Video Save",
    "AntiMatter_Save_Video_in_Folder": "Save_Video_in_Folder",
    "AntiMatter_TextFilter": "AntiMatter Text Filter",
    "LinePrompt_MasterLoad": "LinePrompt_MasterLoad",
    "LinePrompt_MasterLoad_JSON": "LinePrompt_MasterLoad_JSON",
    "LinePrompt_MasterLoad_JSON_Image": "LinePrompt_MasterLoad_JSON_Image",
    "LMStudioThreeImageAgent": "LM Studio 3 Image Agent",
    "LMStudioMultiInputSettingsAgent": "LM Studio Multi Input Settings Agent",
    "AntimatterLtxDirectorX": "AntiMatter LTX Director X",
    "AntimatterLtxDirectorXPro": "AntiMatter LTX Director X Pro",
    "AntimatterLtxDirectorXOneNode": "AntiMatter LTX Director X One Node",
    "AntimatterLtxFragmentStitchX": "AntiMatter LTX Fragment Stitch X",
    "AntimatterLtxAudioTrackX": "AntiMatter LTX Audio Track X",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
