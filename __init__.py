from .nodes.text import NODE_CLASS_MAPPINGS as Text_Mappings
from .nodes.text import NODE_DISPLAY_NAME_MAPPINGS as Text_Names

from .nodes.image import NODE_CLASS_MAPPINGS as Image_Mappings
from .nodes.image import NODE_DISPLAY_NAME_MAPPINGS as Image_Names

from .nodes.api import NODE_CLASS_MAPPINGS as Api_Mappings
from .nodes.api import NODE_DISPLAY_NAME_MAPPINGS as Api_Names

from .nodes.tools import NODE_CLASS_MAPPINGS as Tools_Mappings
from .nodes.tools import NODE_DISPLAY_NAME_MAPPINGS as Tools_Names

from .nodes.video import NODE_CLASS_MAPPINGS as Video_Mappings
from .nodes.video import NODE_DISPLAY_NAME_MAPPINGS as Video_Names

NODE_CLASS_MAPPINGS = {
    **Text_Mappings,
    **Image_Mappings,
    **Api_Mappings,
    **Tools_Mappings,
    **Video_Mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **Text_Names,
    **Image_Names,
    **Api_Names,
    **Tools_Names,
    **Video_Names,
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']