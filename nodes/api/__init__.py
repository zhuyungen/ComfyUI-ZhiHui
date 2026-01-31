# 1. 导入香蕉 (旧版/V15)
from .banana2xlyq_api import NODE_CLASS_MAPPINGS as Banana_Mappings
from .banana2xlyq_api import NODE_DISPLAY_NAME_MAPPINGS as Banana_Names

# 2. 导入豆包 (V20)
from .doubao_v20 import NODE_CLASS_MAPPINGS as Doubao_Mappings
from .doubao_v20 import NODE_DISPLAY_NAME_MAPPINGS as Doubao_Names

# 3. 导入智绘香蕉2 (新版)
# ⚠️ 请确保你的文件名为 banana_two.py
from .banana_two import NODE_CLASS_MAPPINGS as Tutu_Mappings
from .banana_two import NODE_DISPLAY_NAME_MAPPINGS as Tutu_Names

# 合并字典
NODE_CLASS_MAPPINGS = {
    **Banana_Mappings,
    **Doubao_Mappings,
    **Tutu_Mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **Banana_Names,
    **Doubao_Names,
    **Tutu_Names,
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']