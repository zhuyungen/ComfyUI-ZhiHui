import os
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths

class ZH_LoadImagePlus:
    """
    智绘增强图像加载器 - 加载图片并输出文件名信息

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 图片加载：从ComfyUI输入文件夹加载图片
    • 遮罩提取：自动提取Alpha通道作为遮罩
    • 文件名输出：同时输出带后缀和不带后缀的文件名
    • 自动旋转：处理EXIF旋转信息（手机拍照方向）
    • 格式转换：自动转换为RGB格式

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 加载图片
       • 从"image"下拉菜单选择图片文件
       • 支持上传新图片（右键点击可上传）
       • 执行节点完成加载
       • 图片来自ComfyUI的input文件夹

    2️⃣ 使用文件名
       • filename_text：完整文件名（example.png）
       • filename_stem：无后缀文件名（example）
       • 可连接到保存节点，实现文件名继承
       • 可用于条件判断、路径构建等

    3️⃣ 使用遮罩
       • 如果图片有Alpha通道，自动提取为遮罩
       • 如果图片无Alpha通道，输出64x64默认遮罩
       • 遮罩已反转：白色=保留，黑色=移除

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • image：加载的图片张量（RGB格式）
    • mask：提取的遮罩张量（如有Alpha通道）
    • filename_text：带扩展名的文件名（如：photo.png）
    • filename_stem：不带扩展名的文件名（如：photo）

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 文件名继承：将filename_stem连接到保存节点的前缀
    • 批处理：配合文本拆分节点实现批量加载
    • 条件判断：根据文件名决定处理流程
    • 路径构建：使用文件名构建子文件夹路径
    • 日志追踪：控制台会显示加载的文件名

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 图片必须在ComfyUI的input文件夹中
    • 手机拍照的图片会自动处理旋转（EXIF）
    • 所有图片统一转换为RGB格式
    • 如无Alpha通道，遮罩输出为默认的64x64黑色遮罩
    • 支持的格式：jpg、png、bmp、webp等常见格式

    🔗 典型工作流
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 智绘_增强加载器 → filename_stem → 智绘_高级图像保存
       （实现文件名继承，保持命名一致）

    2. 智绘_增强加载器 → image → 图像处理 → 智绘_高级图像保存
       （标准图像处理流程）

    3. 智绘_增强加载器 → mask → 遮罩处理 → 合成节点
       （使用提取的透明度遮罩）

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                # 调用 ComfyUI 原生的文件列表获取方法
                "image": (sorted(files), {"image_upload": True})
            }
        }

    # 输出：图片、遮罩、文件名(带后缀)、文件名(无后缀)
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "filename_text", "filename_stem")
    FUNCTION = "load_image"
    CATEGORY = "智绘灵箱/图片"

    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)
        
        # 1. 打开图片 (原生逻辑)
        i = Image.open(image_path)
        i = ImageOps.exif_transpose(i) # 处理手机拍照旋转问题
        image_pil = i.convert("RGB")
        
        # 2. 转 Tensor
        image_np = np.array(image_pil).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np)[None,]
        
        # 3. 处理遮罩
        if 'A' in i.getbands():
            mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")

        # 4. 提取文件名信息
        # image 变量本身就是文件名字符串 (例如 "example.png")
        filename_with_ext = image
        filename_no_ext = os.path.splitext(filename_with_ext)[0]

        print(f"📂 [智绘加载] 已加载: {filename_with_ext}")

        return (image_tensor, mask, filename_with_ext, filename_no_ext)

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_LoadImagePlus": ZH_LoadImagePlus
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_LoadImagePlus": "🪣 智绘_增强加载器 (带文件名)"
}