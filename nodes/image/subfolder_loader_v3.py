import os
import torch
import numpy as np
import random
from PIL import Image, ImageOps

class ZH_SubfolderLoader_V3:
    """
    功能：子文件夹批量加载器 (V3 终极版)
    特性：
    1. 智能尺寸：支持拉伸、裁剪、填充。
    2. 防缓存机制：引入 Seed 参数，彻底解决 ComfyUI 缓存导致的“不换图”问题。
    3. 多模式：支持“按索引顺序”和“随机抽取”两种模式。
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # 核心路径
                "folder_path": ("STRING", {"default": "", "multiline": False, "placeholder": "根目录路径"}),
                
                # ★★★ 新增：缓存粉碎机 & 随机控制 ★★★
                # 请右键点击 seed -> Convert to Widget -> Control after generate -> Increment/Randomize
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                
                # ★★★ 新增：加载模式 ★★★
                "load_mode": (["Index (按索引顺序)", "Random (随机抽取)"], {"default": "Index (按索引顺序)"}),

                # 索引控制 (仅在 Index 模式下生效)
                "start_index": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "label": "文件夹起始索引"}),
                "folder_limit": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1, "label": "加载文件夹数量"}),
                
                # 图片控制
                "image_start_index": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "label": "图片起始索引"}),
                "image_per_folder": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1, "label": "每文件夹加载张数"}),
                
                # 尺寸策略
                "resize_mode": (["Disabled (报错)", "Stretch (拉伸)", "Crop (裁剪)", "Pad (填充-推荐)"], {"default": "Pad (填充-推荐)"}),
                "target_width": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8, "tooltip": "0 = 跟随第一张图"}),
                "target_height": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8, "tooltip": "0 = 跟随第一张图"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images_batch", "folder_names")
    FUNCTION = "load_images"
    CATEGORY = "智绘灵箱/图片"

    def load_images(self, folder_path, seed, load_mode, start_index, folder_limit, image_start_index, image_per_folder, resize_mode, target_width, target_height):
        if not folder_path or not os.path.exists(folder_path):
            print(f"❌ [智绘V3] 路径不存在: {folder_path}")
            return (torch.zeros((1, 512, 512, 3)), "path_error")

        # 1. 扫描文件夹
        try:
            subfolders = [f.path for f in os.scandir(folder_path) if f.is_dir()]
        except Exception as e:
            print(f"❌ [智绘V3] 扫描失败: {e}")
            return (torch.zeros((1, 512, 512, 3)), "scan_error")
            
        if not subfolders:
             return (torch.zeros((1, 512, 512, 3)), "no_folders")

        # 2. 文件夹选择逻辑 (根据模式)
        selected_folders = []
        
        if load_mode == "Index (按索引顺序)":
            # 排序保证顺序一致
            subfolders.sort()
            
            # 使用 start_index
            if start_index >= len(subfolders):
                # 循环逻辑：如果索引超了，就取模循环，或者直接报错。这里为了批处理稳定，建议取模
                # 但根据用户习惯，通常是希望知道跑完了。这里先按标准逻辑：超了就没了。
                # 为了防止报错停止，我们做一个取模循环保护
                safe_index = start_index % len(subfolders)
                print(f"ℹ️ [智绘V3] 索引循环: {start_index} -> {safe_index}")
                start_index = safe_index
            
            selected_folders = subfolders[start_index : start_index + folder_limit]
            
        elif load_mode == "Random (随机抽取)":
            # 使用 seed 进行随机洗牌
            rng = random.Random(seed)
            # 从所有文件夹中随机选 folder_limit 个
            # 如果请求数量超过总数，就全选并乱序
            count = min(len(subfolders), folder_limit)
            selected_folders = rng.sample(subfolders, count)

        # 3. 读取图片
        all_images_pil = []
        loaded_folder_names = []

        for folder in selected_folders:
            folder_name = os.path.basename(folder)
            valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
            img_files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in valid_exts]
            img_files.sort()

            # 图片切片
            current_folder_imgs = img_files[image_start_index : image_start_index + image_per_folder]
            if not current_folder_imgs: continue

            for img_path in current_folder_imgs:
                try:
                    i = Image.open(img_path)
                    i = ImageOps.exif_transpose(i)
                    if i.mode != 'RGB': i = i.convert('RGB')
                    all_images_pil.append(i)
                except Exception as e:
                    print(f"❌ Load Error: {img_path}")

            loaded_folder_names.append(folder_name)

        if not all_images_pil:
            return (torch.zeros((1, 512, 512, 3)), "no_images")

        # 4. 尺寸处理 (Pad/Crop/Stretch)
        final_w = target_width if target_width > 0 else all_images_pil[0].width
        final_h = target_height if target_height > 0 else all_images_pil[0].height

        processed_tensors = []
        
        for img in all_images_pil:
            if img.size != (final_w, final_h):
                if resize_mode == "Disabled (报错)":
                    print(f"❌ 尺寸不匹配: {img.size}")
                    return (torch.zeros((1, 512, 512, 3)), "size_mismatch")
                elif resize_mode == "Stretch (拉伸)":
                    img = img.resize((final_w, final_h), Image.LANCZOS)
                elif resize_mode == "Crop (裁剪)":
                    ratio = max(final_w / img.width, final_h / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    left = (img.width - final_w) // 2
                    top = (img.height - final_h) // 2
                    img = img.crop((left, top, left + final_w, top + final_h))
                elif resize_mode == "Pad (填充-推荐)":
                    ratio = min(final_w / img.width, final_h / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    new_img = Image.new("RGB", (final_w, final_h), (0, 0, 0))
                    new_img.paste(img, ((final_w - new_size[0]) // 2, (final_h - new_size[1]) // 2))
                    img = new_img

            t = np.array(img).astype(np.float32) / 255.0
            processed_tensors.append(torch.from_numpy(t)[None,])

        # 5. 堆叠
        output_image = torch.cat(processed_tensors, dim=0)
        
        info_txt = f"Seed: {seed} | Mode: {load_mode} | Loaded: {len(processed_tensors)}"
        print(f"✅ [智绘V3] {info_txt}")
        
        return (output_image, ", ".join(loaded_folder_names))

NODE_CLASS_MAPPINGS = {
    "ZH_SubfolderLoader_V3": ZH_SubfolderLoader_V3
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_SubfolderLoader_V3": "📂 智绘_子文件夹批量加载 (V3 终极版)"
}