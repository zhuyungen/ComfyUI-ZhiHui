# 导入我们整理好的各个模块
from .nodes.text import NODE_CLASS_MAPPINGS as Text_Mappings
from .nodes.text import NODE_DISPLAY_NAME_MAPPINGS as Text_Names

from .nodes.image import NODE_CLASS_MAPPINGS as Image_Mappings
from .nodes.image import NODE_DISPLAY_NAME_MAPPINGS as Image_Names

from .nodes.api import NODE_CLASS_MAPPINGS as Api_Mappings
from .nodes.api import NODE_DISPLAY_NAME_MAPPINGS as Api_Names

from .nodes.tools import NODE_CLASS_MAPPINGS as Tools_Mappings
from .nodes.tools import NODE_DISPLAY_NAME_MAPPINGS as Tools_Names

# 合并所有节点的映射
NODE_CLASS_MAPPINGS = {
    **Text_Mappings,
    **Image_Mappings,
    **Api_Mappings,
    **Tools_Mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **Text_Names,
    **Image_Names,
    **Api_Names,
    **Tools_Names,
}

# --- 关键修改：告诉 ComfyUI 前端文件在哪里 ---
# "./js" 指的是当前插件根目录下的 js 文件夹
WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']