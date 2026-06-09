from .timeline_editor import NODE_CLASS_MAPPINGS as TimelineEditor_Mappings
from .timeline_editor import NODE_DISPLAY_NAME_MAPPINGS as TimelineEditor_Names

from .make_image_list import NODE_CLASS_MAPPINGS as MakeImageList_Mappings
from .make_image_list import NODE_DISPLAY_NAME_MAPPINGS as MakeImageList_Names

from .batch_video_loader import NODE_CLASS_MAPPINGS as VideoLoader_Mappings
from .batch_video_loader import NODE_DISPLAY_NAME_MAPPINGS as VideoLoader_Names

from .video_saver import NODE_CLASS_MAPPINGS as VideoSaver_Mappings
from .video_saver import NODE_DISPLAY_NAME_MAPPINGS as VideoSaver_Names

NODE_CLASS_MAPPINGS = {
    **TimelineEditor_Mappings,
    **MakeImageList_Mappings,
    **VideoLoader_Mappings,
    **VideoSaver_Mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **TimelineEditor_Names,
    **MakeImageList_Names,
    **VideoLoader_Names,
    **VideoSaver_Names,
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
