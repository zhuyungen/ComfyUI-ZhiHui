"""
智绘灵箱 - 图片计数器加载节点

功能：自动加载图片序列，内置计数器，支持循环和步进
适合批量处理、动画帧加载、序列测试
"""
import torch
import numpy as np
from PIL import Image
import os
from pathlib import Path
import folder_paths


class ZH_ImageLoaderWithCounter:
    """
    智绘图片计数器加载节点
    自动加载文件夹中的图片，支持计数器和序列控制
    """

    def __init__(self):
        self.counter = 0
        self.last_folder = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "图片文件夹路径（留空使用ComfyUI/input）"
                }),
                "counter_mode": ([
                    "顺序递增",
                    "顺序递减",
                    "循环递增",
                    "循环递减",
                    "随机选择",
                ], {
                    "default": "循环递增"
                }),
                "step": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "每次步进数量"
                }),
                "start_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 10000,
                    "step": 1,
                    "tooltip": "起始索引"
                }),
                "reset_counter": ("BOOLEAN", {
                    "default": False,
                    "label_on": "✅ 重置",
                    "label_off": "❌ 保持",
                    "tooltip": "重置计数器到起始位置"
                }),
            },
            "optional": {
                "file_filter": ("STRING", {
                    "default": "*.png,*.jpg,*.jpeg,*.webp",
                    "tooltip": "文件过滤器（用逗号分隔）"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("图像", "文件名", "当前索引")
    FUNCTION = "load_image_with_counter"
    CATEGORY = "智绘灵箱/工具箱"

    def load_image_with_counter(self, folder_path, counter_mode, step, start_index,
                                reset_counter, file_filter="*.png,*.jpg,*.jpeg,*.webp"):
        """使用计数器加载图片"""

        # 确定文件夹路径
        if not folder_path or folder_path.strip() == "":
            folder = Path(folder_paths.get_input_directory())
        else:
            folder = Path(folder_path)

        if not folder.exists():
            error_msg = f"文件夹不存在: {folder}"
            print(f"❌ [智绘计数器加载] {error_msg}")
            # 返回空白图片
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty_img, error_msg, -1)

        # 重置计数器或切换文件夹时
        if reset_counter or self.last_folder != str(folder):
            self.counter = start_index
            self.last_folder = str(folder)
            print(f"🔄 [智绘计数器加载] 计数器重置为 {start_index}")

        # 获取文件列表
        extensions = [ext.strip() for ext in file_filter.split(',')]
        all_files = []
        for ext in extensions:
            all_files.extend(folder.glob(ext))

        # 按文件名排序
        all_files = sorted(all_files, key=lambda x: x.name)

        if len(all_files) == 0:
            error_msg = f"文件夹中没有找到图片: {folder}"
            print(f"❌ [智绘计数器加载] {error_msg}")
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty_img, error_msg, -1)

        # 根据模式计算索引
        total_images = len(all_files)

        if counter_mode == "顺序递增":
            index = self.counter
            self.counter += step
            if index >= total_images:
                index = total_images - 1
                print(f"⚠️ [智绘计数器加载] 已到达末尾，停留在最后一张")

        elif counter_mode == "顺序递减":
            index = self.counter
            self.counter -= step
            if self.counter < 0:
                self.counter = 0
            if index >= total_images:
                index = total_images - 1

        elif counter_mode == "循环递增":
            index = self.counter % total_images
            self.counter += step

        elif counter_mode == "循环递减":
            index = self.counter % total_images
            self.counter -= step
            if self.counter < 0:
                self.counter = total_images - 1

        else:  # 随机选择
            import random
            index = random.randint(0, total_images - 1)

        # 加载图片
        image_path = all_files[index]
        try:
            pil_img = Image.open(image_path).convert('RGB')
            img_np = np.array(pil_img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_np).unsqueeze(0)

            print(f"✅ [智绘计数器加载] [{index+1}/{total_images}] {image_path.name}")
            return (img_tensor, image_path.name, index)

        except Exception as e:
            error_msg = f"加载图片失败: {e}"
            print(f"❌ [智绘计数器加载] {error_msg}")
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty_img, error_msg, -1)


class ZH_ImageSequenceLoader:
    """
    智绘图片序列批量加载节点
    一次性加载整个图片序列
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "图片文件夹路径（留空使用ComfyUI/input）"
                }),
                "start_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 10000,
                    "step": 1,
                    "tooltip": "起始索引"
                }),
                "max_images": ("INT", {
                    "default": 10,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "最大加载数量"
                }),
                "skip_frames": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "跳帧：1为全部，2为隔一帧"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("图像批次", "加载数量")
    FUNCTION = "load_sequence"
    CATEGORY = "智绘灵箱/工具箱"

    def load_sequence(self, folder_path, start_index, max_images, skip_frames):
        """批量加载图片序列"""

        # 确定文件夹路径
        if not folder_path or folder_path.strip() == "":
            folder = Path(folder_paths.get_input_directory())
        else:
            folder = Path(folder_path)

        if not folder.exists():
            error_msg = f"文件夹不存在: {folder}"
            print(f"❌ [智绘序列加载] {error_msg}")
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty_img, 0)

        # 获取文件列表
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
        all_files = sorted([
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in valid_extensions
        ])

        if len(all_files) == 0:
            error_msg = f"文件夹中没有找到图片: {folder}"
            print(f"❌ [智绘序列加载] {error_msg}")
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty_img, 0)

        # 应用起始索引和跳帧
        selected_files = all_files[start_index::skip_frames][:max_images]

        # 加载图片
        loaded_images = []
        for img_path in selected_files:
            try:
                pil_img = Image.open(img_path).convert('RGB')
                img_np = np.array(pil_img).astype(np.float32) / 255.0
                img_tensor = torch.from_numpy(img_np)
                loaded_images.append(img_tensor)
            except Exception as e:
                print(f"⚠️ [智绘序列加载] 跳过损坏图片: {img_path.name}, 错误: {e}")
                continue

        if len(loaded_images) == 0:
            print(f"❌ [智绘序列加载] 没有成功加载任何图片")
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (empty_img, 0)

        # 堆叠批次
        output = torch.stack(loaded_images)
        print(f"✅ [智绘序列加载] 成功加载 {len(loaded_images)} 张图片")
        return (output, len(loaded_images))


NODE_CLASS_MAPPINGS = {
    "ZH_ImageLoaderWithCounter": ZH_ImageLoaderWithCounter,
    "ZH_ImageSequenceLoader": ZH_ImageSequenceLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_ImageLoaderWithCounter": "🔢 智绘_计数器加载",
    "ZH_ImageSequenceLoader": "📸 智绘_序列批量加载",
}
