import torch
import numpy as np
import os
import folder_paths
from PIL import Image

try:
    import pytoshop
    from pytoshop.user import nested_layers
    from pytoshop.enums import ColorMode, Compression
    PYTOSHOP_AVAILABLE = True
except ImportError:
    PYTOSHOP_AVAILABLE = False

class ZHIHUISavePSD:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "🖼️ 图像列表": ("IMAGE", {"tooltip": "需要保存的图像批次或列表"}),
                "📄 文件名前缀": ("STRING", {"default": "zhihui_psd", "tooltip": "文件名前缀"}),
            },
            "optional": {
                "📂 自定义路径": ("STRING", {"default": "", "tooltip": "自定义保存路径，留空则使用默认路径"}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_psd"
    OUTPUT_NODE = True
    CATEGORY = "智绘灵箱/图片"
    INPUT_IS_LIST = True

    def save_psd(self, **kwargs):
        images = kwargs.get("🖼️ 图像列表")
        filename_prefix = kwargs.get("📄 文件名前缀", "zhihui_psd")
        custom_path_raw = kwargs.get("📂 自定义路径", "")

        # When INPUT_IS_LIST is True, all inputs are lists.
        # Ensure filename_prefix is a string.
        if isinstance(filename_prefix, list):
            filename_prefix = filename_prefix[0]

        # Ensure custom_path is a string
        custom_path = ""
        if isinstance(custom_path_raw, list):
            if len(custom_path_raw) > 0:
                custom_path = str(custom_path_raw[0]).strip()
        elif isinstance(custom_path_raw, str):
            custom_path = custom_path_raw.strip()

        if not PYTOSHOP_AVAILABLE:
            raise ImportError("智绘_保存PSD: pytoshop 模块未找到。请在 ComfyUI 的 Python 环境中运行 'pip install pytoshop'")

        if images is None:
            return {}

        # 1. Flatten images to PIL list
        pil_images = []

        # Helper function to process single item
        def process_item(item):
            if isinstance(item, torch.Tensor):
                 # Handle batch [B, H, W, C]
                if item.dim() == 4:
                    for i in range(item.shape[0]):
                        pil_images.append(self.tensor_to_pil(item[i]))
                # Handle single [H, W, C]
                elif item.dim() == 3:
                    pil_images.append(self.tensor_to_pil(item))

        # Check if input is a list (from INPUT_IS_LIST=True)
        if isinstance(images, list):
            for img_item in images:
                process_item(img_item)
        else:
            # Fallback if somehow it's not a list
            process_item(images)

        if not pil_images:
            print("智绘_保存PSD: 没有图像需要保存。")
            return {}

        # 2. Calculate canvas size (Max W, Max H)
        max_w = 0
        max_h = 0
        for img in pil_images:
            max_w = max(max_w, img.width)
            max_h = max(max_h, img.height)

        # 3. Create Layers
        layers_list = []
        for i, img in enumerate(pil_images):
            # Calculate centering offset
            x = (max_w - img.width) // 2
            y = (max_h - img.height) // 2

            # Split channels
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            r, g, b, a = img.split()
            channels = {
                0: np.array(r),
                1: np.array(g),
                2: np.array(b),
                -1: np.array(a)
            }

            layer = nested_layers.Image(
                name=f"图层 {i+1}",
                top=y, left=x,
                bottom=y+img.height, right=x+img.width,
                channels=channels
            )
            layers_list.append(layer)

        # 4. Prepare save path
        base_output_dir = self.output_dir
        if custom_path:
            try:
                # 转换为绝对路径，避免路径混合错误
                abs_custom_path = os.path.abspath(custom_path)
                os.makedirs(abs_custom_path, exist_ok=True)
                base_output_dir = abs_custom_path
            except Exception as e:
                print(f"创建自定义路径 '{custom_path}' 失败，使用默认路径。错误: {e}")

        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(filename_prefix, base_output_dir, max_w, max_h)

        file_name = f"{filename}_{counter:05}_.psd"
        file_path = os.path.join(full_output_folder, file_name)

        # 5. Create PSD structure
        # Note: size=(width, height) based on source code inspection
        # compression=Compression.raw to avoid 'packbits' dependency/bug in pytoshop 1.2.1
        psd = nested_layers.nested_layers_to_psd(
            layers_list,
            ColorMode.rgb,
            size=(max_w, max_h),
            compression=Compression.raw
        )

        # 6. Write file
        try:
            with open(file_path, "wb") as f:
                psd.write(f)
            print(f"智绘_保存PSD: 已保存 {file_path}")
        except Exception as e:
            print(f"智绘_保存PSD: 保存 PSD 文件时出错: {e}")
            raise e

        return {"ui": {"images": []}}

    def tensor_to_pil(self, tensor):
        return Image.fromarray(np.clip(255. * tensor.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_SavePSD": ZHIHUISavePSD
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_SavePSD": "💾 智绘_保存PSD"
}
