from .anti_aspect_ratio_master import AntiAspectRatioMaster
from .batch_loader_from_folder import BatchLoaderFromFolder

NODE_CLASS_MAPPINGS = {
    "Anti_aspect_ratio_master": AntiAspectRatioMaster,
    "Batch_Loader_From_Folder": BatchLoaderFromFolder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Anti_aspect_ratio_master": "Anti_aspect_ratio_master",
    "Batch_Loader_From_Folder": "Batch Loader from folder",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
