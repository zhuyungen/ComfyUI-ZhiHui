"""
智绘灵箱 - 图片排列节点

将多张图片按照指定布局排列成网格
支持自动布局、行列调整、间距控制等功能
"""
import torch
import numpy as np
from PIL import Image, ImageDraw
import math
import os
from pathlib import Path


class ImageLayoutNode:
    """
    图片排列节点 - 支持以基准图为中心的灵活布局排列

    核心功能：
    - 基准图：可来自单张输入或批次首张
    - 小图：可来自批次剩余图或文件夹加载
    - 排列方向：上下左右4个方向
    - 布局模式：自动/固定列数/固定行数
    - 缩放模式：适应/裁剪/拉伸
    - 自定义边框、背景色、间距
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "🔢 排列方向": (["左右", "上下", "左上", "右上"], {"default": "左右"}),
                "📏 基准图尺寸模式": (["默认（使用原图尺寸）", "自定义最长边"],),
                "📏 自定义最长边": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 64}),
                "🖼️  布局模式": (["自动", "固定列数", "固定行数"], {"default": "自动"}),
                "🔢 固定列数": ("INT", {"default": 3, "min": 1, "max": 20}),
                "🔢 固定行数": ("INT", {"default": 3, "min": 1, "max": 20}),
                "📐 小图尺寸": ("INT", {"default": 256, "min": 64, "max": 1024, "step": 64}),
                "🎨 缩放模式": (["适应（保持比例+填充）", "裁剪（保持比例+裁剪）", "拉伸（填满格子）"], {"default": "适应（保持比例+填充）"}),
                "🌈 背景颜色": (["黑色", "白色", "透明", "自定义"],),
                "🎨 自定义背景RGB": ("STRING", {"default": "255,255,255"}),
                "📏 边框宽度": ("INT", {"default": 2, "min": 0, "max": 20}),
                "🌈 边框颜色": (["黑色", "白色", "自定义"],),
                "🎨 自定义边框RGB": ("STRING", {"default": "0,0,0"}),
                "📏 小图间距": ("INT", {"default": 4, "min": 0, "max": 50}),
            },
            "optional": {
                "📸 基准图输入": ("IMAGE",),
                "📦 图片批次输入": ("IMAGE",),
                "📁 文件夹路径": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("🖼️  组合图",)
    FUNCTION = "layout_images"
    CATEGORY = "智绘灵箱"

    def layout_images(self,
                     排列方向="左右",
                     基准图尺寸模式="默认（使用原图尺寸）",
                     自定义最长边=1024,
                     布局模式="自动",
                     固定列数=3,
                     固定行数=3,
                     小图尺寸=256,
                     缩放模式="适应（保持比例+填充）",
                     背景颜色="黑色",
                     自定义背景RGB="255,255,255",
                     边框宽度=2,
                     边框颜色="黑色",
                     自定义边框RGB="0,0,0",
                     小图间距=4,
                     基准图输入=None,
                     图片批次输入=None,
                     文件夹路径=""):

        # 解析基准图
        if 基准图输入 is not None:
            base_image = 基准图输入[0]  # 取首张
            remaining_images = 图片批次输入 if 图片批次输入 is not None else None
        elif 图片批次输入 is not None and len(图片批次输入) > 0:
            base_image = 图片批次输入[0]
            remaining_images = 图片批次输入[1:] if len(图片批次输入) > 1 else None
        else:
            # 如果没有任何图像输入，返回空白图像
            empty = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty,)

        # 收集小图
        small_images_list = []

        # 从批次中收集剩余图
        if remaining_images is not None and len(remaining_images) > 0:
            for img in remaining_images:
                small_images_list.append(img)

        # 从文件夹加载图片
        if 文件夹路径 and os.path.exists(文件夹路径):
            folder = Path(文件夹路径)
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}

            image_files = sorted([
                f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in valid_extensions
            ])

            for img_path in image_files:
                try:
                    pil_img = Image.open(img_path).convert('RGB')
                    img_array = np.array(pil_img).astype(np.float32) / 255.0
                    img_tensor = torch.from_numpy(img_array)
                    small_images_list.append(img_tensor)
                except Exception as e:
                    print(f"[ImageLayout] 加载图片失败: {img_path}, 错误: {e}")
                    continue

        # 如果没有小图，只返回基准图
        if len(small_images_list) == 0:
            return (base_image.unsqueeze(0),)

        # 转换为PIL格式处理
        base_pil = self._tensor_to_pil(base_image)
        small_pils = [self._tensor_to_pil(img) for img in small_images_list]

        # 调整基准图尺寸
        if 基准图尺寸模式 == "自定义最长边":
            base_pil = self._resize_to_max_edge(base_pil, 自定义最长边)

        # 解析颜色
        bg_color = self._parse_color(背景颜色, 自定义背景RGB)
        border_color = self._parse_color(边框颜色, 自定义边框RGB, default_black=True)

        # 根据布局模式确定行列
        small_count = len(small_pils)
        if 布局模式 == "自动":
            cols = math.ceil(math.sqrt(small_count))
            rows = math.ceil(small_count / cols)
        elif 布局模式 == "固定列数":
            cols = 固定列数
            rows = math.ceil(small_count / cols)
        else:  # 固定行数
            rows = 固定行数
            cols = math.ceil(small_count / rows)

        # 缩放小图
        cell_size = 小图尺寸
        processed_smalls = []
        for img in small_pils:
            if 缩放模式 == "适应（保持比例+填充）":
                processed = self._resize_with_padding(img, cell_size, bg_color)
            elif 缩放模式 == "裁剪（保持比例+裁剪）":
                processed = self._resize_crop(img, cell_size)
            else:  # 拉伸
                processed = img.resize((cell_size, cell_size), Image.LANCZOS)
            processed_smalls.append(processed)

        # 生成网格
        grid_img = self._create_grid(
            processed_smalls, rows, cols, cell_size,
            bg_color, border_color, 边框宽度, 小图间距
        )

        # 合并基准图和网格
        result_pil = self._combine_base_and_grid(
            base_pil, grid_img, 排列方向, bg_color
        )

        # 转回tensor
        result_tensor = self._pil_to_tensor(result_pil)
        return (result_tensor,)

    def _tensor_to_pil(self, tensor):
        """将tensor转为PIL图像"""
        img_np = (tensor.cpu().numpy() * 255).astype(np.uint8)
        return Image.fromarray(img_np, mode='RGB')

    def _pil_to_tensor(self, pil_img):
        """将PIL图像转为tensor"""
        img_np = np.array(pil_img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(img_np)
        return tensor.unsqueeze(0)  # [1, H, W, C]

    def _resize_to_max_edge(self, img, max_edge):
        """按最长边缩放"""
        w, h = img.size
        if max(w, h) <= max_edge:
            return img
        ratio = max_edge / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        return img.resize(new_size, Image.LANCZOS)

    def _parse_color(self, color_name, custom_rgb, default_black=False):
        """解析颜色"""
        if color_name == "黑色":
            return (0, 0, 0)
        elif color_name == "白色":
            return (255, 255, 255)
        elif color_name == "透明":
            return (0, 0, 0, 0)  # RGBA透明
        else:  # 自定义
            try:
                parts = custom_rgb.split(',')
                r = int(parts[0].strip())
                g = int(parts[1].strip())
                b = int(parts[2].strip())
                return (r, g, b)
            except:
                return (0, 0, 0) if default_black else (255, 255, 255)

    def _resize_with_padding(self, img, size, bg_color):
        """保持比例缩放并填充"""
        w, h = img.size
        ratio = min(size / w, size / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        # 创建画布
        canvas = Image.new('RGB', (size, size), bg_color)
        paste_x = (size - new_w) // 2
        paste_y = (size - new_h) // 2
        canvas.paste(resized, (paste_x, paste_y))

        return canvas

    def _resize_crop(self, img, size):
        """保持比例裁剪"""
        w, h = img.size
        ratio = max(size / w, size / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        # 中心裁剪
        left = (new_w - size) // 2
        top = (new_h - size) // 2
        return resized.crop((left, top, left + size, top + size))

    def _create_grid(self, images, rows, cols, cell_size, bg_color, border_color, border_width, spacing):
        """创建网格"""
        total_width = cols * cell_size + (cols + 1) * spacing + 2 * border_width
        total_height = rows * cell_size + (rows + 1) * spacing + 2 * border_width

        grid = Image.new('RGB', (total_width, total_height), bg_color)
        draw = ImageDraw.Draw(grid)

        # 绘制网格边框（外框）
        if border_width > 0:
            for i in range(border_width):
                draw.rectangle(
                    [i, i, total_width - 1 - i, total_height - 1 - i],
                    outline=border_color
                )

        # 粘贴图片
        for idx, img in enumerate(images):
            if idx >= rows * cols:
                break

            row = idx // cols
            col = idx % cols

            x = border_width + spacing + col * (cell_size + spacing)
            y = border_width + spacing + row * (cell_size + spacing)

            grid.paste(img, (x, y))

            # 绘制单元格边框
            if border_width > 0:
                for i in range(border_width):
                    draw.rectangle(
                        [x - i - 1, y - i - 1, x + cell_size + i, y + cell_size + i],
                        outline=border_color
                    )

        return grid

    def _combine_base_and_grid(self, base_img, grid_img, direction, bg_color):
        """合并基准图和网格"""
        base_w, base_h = base_img.size
        grid_w, grid_h = grid_img.size

        if direction == "左右":
            result_w = base_w + grid_w
            result_h = max(base_h, grid_h)
            result = Image.new('RGB', (result_w, result_h), bg_color)
            result.paste(base_img, (0, 0))
            result.paste(grid_img, (base_w, 0))

        elif direction == "上下":
            result_w = max(base_w, grid_w)
            result_h = base_h + grid_h
            result = Image.new('RGB', (result_w, result_h), bg_color)
            result.paste(base_img, (0, 0))
            result.paste(grid_img, (0, base_h))

        elif direction == "左上":
            result_w = base_w + grid_w
            result_h = base_h + grid_h
            result = Image.new('RGB', (result_w, result_h), bg_color)
            result.paste(grid_img, (0, 0))
            result.paste(base_img, (grid_w, grid_h))

        else:  # 右上
            result_w = base_w + grid_w
            result_h = base_h + grid_h
            result = Image.new('RGB', (result_w, result_h), bg_color)
            result.paste(grid_img, (base_w, 0))
            result.paste(base_img, (0, grid_h))

        return result


NODE_CLASS_MAPPINGS = {
    "ImageLayoutNode": ImageLayoutNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageLayoutNode": "📐 图片排列"
}
