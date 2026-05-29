from .anti_aspect_ratio_master import AntiAspectRatioMaster
from .antimatter_text_file_appender import AntimatterTextFileAppender
from .batch_loader_from_folder import BatchLoaderFromFolder
from .lineprompt_masterload import LinePrompt_MasterLoad, LinePrompt_MasterLoad_JSON

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "Anti_aspect_ratio_master": AntiAspectRatioMaster,
    "Antimatter_TextFileAppender": AntimatterTextFileAppender,
    "Batch_Loader_From_Folder": BatchLoaderFromFolder,
    "LinePrompt_MasterLoad": LinePrompt_MasterLoad,
    "LinePrompt_MasterLoad_JSON": LinePrompt_MasterLoad_JSON,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Anti_aspect_ratio_master": "Anti_aspect_ratio_master",
    "Antimatter_TextFileAppender": "Antimatter Text File Appender",
    "Batch_Loader_From_Folder": "Batch Loader from folder",
    "LinePrompt_MasterLoad": "LinePrompt_MasterLoad",
    "LinePrompt_MasterLoad_JSON": "LinePrompt_MasterLoad_JSON",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
