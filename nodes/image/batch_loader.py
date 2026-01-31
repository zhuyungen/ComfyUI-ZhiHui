import os
import random
from pathlib import Path
from PIL import Image, ImageOps
import torch
import numpy as np

class ZH_BatchImageLoader:
    """
    智绘移植版 - 图像遍历加载器
    功能：支持递归扫描文件夹，打平所有图片文件，支持顺序/随机读取，支持分页加载。
    V2更新：新增无后缀文件名输出。
    """
    def __init__(self):
        # 缓存机制
        self.last_dir = ""
        self.last_recursive = False
        self.image_files = []

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:/path/to/your/images", "multiline": False}),
                "load_order": (["顺序 (Alphabetical)", "随机 (Random)"], {"default": "顺序 (Alphabetical)"}),
                "recursive_scan": ("BOOLEAN", {"default": False, "label_on": "开启递归 (Recursive)", "label_off": "仅当前目录 (Current)"}),
                "start_index": ("INT", {"default": 0, "min": 0, "step": 1}),
                "limit_count": ("INT", {"default": 10, "min": 1, "max": 1000, "step": 1}),
            }
        }

    # 修改点 1：增加了一个 STRING 类型
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    # 修改点 2：增加了一个输出口名字
    RETURN_NAMES = ("images_batch", "filename_text", "filename_no_ext")
    
    FUNCTION = "load_images"
    CATEGORY = "智绘灵箱/图片"

    def get_image_list(self, folder_path, recursive_scan, load_order):
        # 缓存检查
        if folder_path == self.last_dir and recursive_scan == self.last_recursive and self.image_files:
            return self.image_files

        image_files = []
        valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga')

        if recursive_scan:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(valid_exts):
                        image_files.append(os.path.join(root, file))
        else:
            if os.path.exists(folder_path):
                for file in os.listdir(folder_path):
                    full_path = os.path.join(folder_path, file)
                    if os.path.isfile(full_path) and file.lower().endswith(valid_exts):
                        image_files.append(full_path)

        if "顺序" in load_order:
            image_files.sort()
        elif "随机" in load_order:
            random.shuffle(image_files)

        self.last_dir = folder_path
        self.last_recursive = recursive_scan
        self.image_files = image_files
        
        return image_files

    def load_images(self, folder_path, load_order, recursive_scan, start_index, limit_count):
        if not folder_path or not os.path.exists(folder_path):
            print(f"⚠️ [智绘遍历] 路径不存在: {folder_path}")
            return (torch.zeros((1, 512, 512, 3)), "", "") # 这里的返回值也要对应增加空字符串

        image_list = self.get_image_list(folder_path, recursive_scan, load_order)
        total_files = len(image_list)
        
        print(f"📂 [智绘遍历] 找到 {total_files} 张图片。")

        if total_files == 0:
            return (torch.zeros((1, 512, 512, 3)), "", "")

        if start_index >= total_files:
            print(f"⚠️ [智绘遍历] 索引越界。")
            return (torch.zeros((1, 512, 512, 3)), "", "")

        end_index = start_index + limit_count
        target_files = image_list[start_index : min(end_index, total_files)]
        
        images = []
        filenames = []
        filenames_no_ext = [] # 新建列表存无后缀名
        
        ref_width = 0
        ref_height = 0

        for img_path in target_files:
            try:
                i = Image.open(img_path)
                i = ImageOps.exif_transpose(i)
                if i.mode != 'RGB':
                    i = i.convert("RGB")
                
                if len(images) == 0:
                    ref_width, ref_height = i.size
                else:
                    if i.size != (ref_width, ref_height):
                        i = i.resize((ref_width, ref_height), Image.LANCZOS)

                image = np.array(i).astype(np.float32) / 255.0
                image = torch.from_numpy(image)[None,]
                
                images.append(image)
                
                # --- 文件名处理逻辑 ---
                file_name_full = os.path.basename(img_path) # 例如 dog.png
                file_name_clean = os.path.splitext(file_name_full)[0] # 例如 dog
                
                filenames.append(file_name_full)
                filenames_no_ext.append(file_name_clean)
                
            except Exception as e:
                print(f"❌ [智绘遍历] 加载失败: {img_path}, 错误: {e}")
                continue

        if not images:
            return (torch.zeros((1, 512, 512, 3)), "", "")

        images_batch = torch.cat(images, dim=0)
        
        # 两个输出字符串
        output_names = ", ".join(filenames)
        output_names_no_ext = ", ".join(filenames_no_ext)
        
        print(f"✅ [智绘遍历] 加载成功 {len(images)} 张")
        
        # 返回三个值
        return (images_batch, output_names, output_names_no_ext)

NODE_CLASS_MAPPINGS = {
    "ZH_BatchImageLoader": ZH_BatchImageLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_BatchImageLoader": "🪣 智绘_图像遍历加载器"
}