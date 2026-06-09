# 1. 文件夹清理器
from .file_cleaner import NODE_CLASS_MAPPINGS as Cleaner_Mappings
from .file_cleaner import NODE_DISPLAY_NAME_MAPPINGS as Cleaner_Names

# 2. 图像遍历加载器 (旧版)
from .batch_loader import NODE_CLASS_MAPPINGS as Recursive_Mappings
from .batch_loader import NODE_DISPLAY_NAME_MAPPINGS as Recursive_Names

# 3. 高级保存
from .save_image_plus import NODE_CLASS_MAPPINGS as Save_Mappings
from .save_image_plus import NODE_DISPLAY_NAME_MAPPINGS as Save_Names

# 4. 九宫格拼图
from .grid_assembler import NODE_CLASS_MAPPINGS as Grid_Mappings
from .grid_assembler import NODE_DISPLAY_NAME_MAPPINGS as Grid_Names

# 5. 增强加载器 (防报错处理)
try:
    from .loader_plus import NODE_CLASS_MAPPINGS as LoaderPlus_Mappings
    from .loader_plus import NODE_DISPLAY_NAME_MAPPINGS as LoaderPlus_Names
except ImportError:
    LoaderPlus_Mappings, LoaderPlus_Names = {}, {}

# 6. 图像选择器 (防报错处理)
try:
    from .dt_image_selector import NODE_CLASS_MAPPINGS as Selector_Mappings
    from .dt_image_selector import NODE_DISPLAY_NAME_MAPPINGS as Selector_Names
except ImportError:
    Selector_Mappings, Selector_Names = {}, {}

# 7. 精确裁剪
try:
    from .image_cropper import NODE_CLASS_MAPPINGS as Cropper_Mappings
    from .image_cropper import NODE_DISPLAY_NAME_MAPPINGS as Cropper_Names
except ImportError:
    Cropper_Mappings, Cropper_Names = {}, {}

# 8. 安全批次加载器
from .safe_loader import NODE_CLASS_MAPPINGS as SafeLoader_Mappings
from .safe_loader import NODE_DISPLAY_NAME_MAPPINGS as SafeLoader_Names

# 9. 中文时间戳保存
from .save_image_with_time import NODE_CLASS_MAPPINGS as SaveTime_Mappings
from .save_image_with_time import NODE_DISPLAY_NAME_MAPPINGS as SaveTime_Names

# 10. 文件归档器
from .file_organizer import NODE_CLASS_MAPPINGS as Organizer_Mappings
from .file_organizer import NODE_DISPLAY_NAME_MAPPINGS as Organizer_Names

# 13. 子文件夹加载器 V3 (最新版)
from .subfolder_loader_v3 import NODE_CLASS_MAPPINGS as SubfolderV3_Mappings
from .subfolder_loader_v3 import NODE_DISPLAY_NAME_MAPPINGS as SubfolderV3_Names

# 14. 纯净图片加载器
from .image_batch_loader import NODE_CLASS_MAPPINGS as ImgLoader_Mappings
from .image_batch_loader import NODE_DISPLAY_NAME_MAPPINGS as ImgLoader_Names

# 15. 图片反推 (AI Caption)
from .image_captioning import NODE_CLASS_MAPPINGS as Caption_Mappings
from .image_captioning import NODE_DISPLAY_NAME_MAPPINGS as Caption_Names

# 16. 智能抠图 (Background Removal)
from .background_remover import NODE_CLASS_MAPPINGS as BgRemover_Mappings
from .background_remover import NODE_DISPLAY_NAME_MAPPINGS as BgRemover_Names

# 17. PSD 保存器 (Save PSD)
from .save_psd import NODE_CLASS_MAPPINGS as SavePSD_Mappings
from .save_psd import NODE_DISPLAY_NAME_MAPPINGS as SavePSD_Names

# 18. 画板
from .drawing_board import NODE_CLASS_MAPPINGS as DrawingBoard_Mappings
from .drawing_board import NODE_DISPLAY_NAME_MAPPINGS as DrawingBoard_Names

# 合并字典
NODE_CLASS_MAPPINGS = {
    **Cleaner_Mappings,
    **Recursive_Mappings,
    **Save_Mappings,
    **Grid_Mappings,
    **LoaderPlus_Mappings,
    **Selector_Mappings,
    **Cropper_Mappings,
    **SafeLoader_Mappings,
    **SaveTime_Mappings,
    **SubfolderV3_Mappings,
    **ImgLoader_Mappings,
    **Caption_Mappings,
    **BgRemover_Mappings,
    **SavePSD_Mappings,
    **Organizer_Mappings,
    **DrawingBoard_Mappings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **Cleaner_Names,
    **Recursive_Names,
    **Save_Names,
    **Grid_Names,
    **LoaderPlus_Names,
    **Selector_Names,
    **Cropper_Names,
    **SafeLoader_Names,
    **SaveTime_Names,
    **SubfolderV3_Names,
    **ImgLoader_Names,
    **Caption_Names,
    **BgRemover_Names,
    **SavePSD_Names,
    **Organizer_Names,
    **DrawingBoard_Names,
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']