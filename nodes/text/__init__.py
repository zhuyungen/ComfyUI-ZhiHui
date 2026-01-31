# 1. 导入预设管理节点
from .preset_loader import NODE_CLASS_MAPPINGS as Preset_Mappings
from .preset_loader import NODE_DISPLAY_NAME_MAPPINGS as Preset_Names

# 2. 导入文本操作符 (Text Operators)
from .text_operators import NODE_CLASS_MAPPINGS as Operator_Mappings
from .text_operators import NODE_DISPLAY_NAME_MAPPINGS as Operator_Names

# 合并字典
NODE_CLASS_MAPPINGS = {
    **Preset_Mappings,
    **Operator_Mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **Preset_Names,
    **Operator_Names,
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']