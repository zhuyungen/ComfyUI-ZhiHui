import os
import torch
import numpy as np
from PIL import Image, ImageOps
import glob

class ZH_SafeBatchLoader:
    """
    功能：安全批次加载器 (Safe Batch Loader)
    解决了原生批次加载在文件数量不匹配时报错的问题。
    支持：循环读取、保持最后、输出空黑图等策略。
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "path": ("STRING", {"default": "", "multiline": False, "placeholder": "文件夹路径 (例如 D:/images)"}),
                "pattern": ("STRING", {"default": "*", "multiline": False}),
                # 核心控制参数，对应 WAS 的 seed，其实就是索引
                "index_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                
                # --- 大桶独家：安全策略 ---
                "out_of_bounds_behavior": ([
                    "return_empty_black (越界发黑图)", 
                    "loop_sequence (循环播放)", 
                    "hold_last (保持最后一张)"
                ], {"default": "return_empty_black (越界发黑图)"}),
                
                "mode": (["single_image", "incremental_image", "randomize"], {"default": "single_image"}),
                "allow_RGBA": ("BOOLEAN", {"default": False}),
                "filename_text_extension": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "filename_text")
    FUNCTION = "load_batch_images"
    CATEGORY = "智绘灵箱/图片"

    def load_batch_images(self, path, pattern, index_seed, out_of_bounds_behavior, mode, allow_RGBA, filename_text_extension):
        # 1. 路径检查
        if not path or not os.path.exists(path):
            print(f"⚠️ [智绘加载] 路径不存在: {path}")
            return (self.generate_black_image(), "error_path_not_found")

        # 2. 获取文件列表
        # 支持递归吗？WAS 默认好像不递归，我们也保持简单，只读当前层
        search_path = os.path.join(path, pattern)
        files = glob.glob(search_path)
        # 过滤非图片文件 (简单过滤)
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
        files = [f for f in files if os.path.splitext(f)[1].lower() in image_extensions]
        files.sort() # 确保顺序一致

        total_count = len(files)
        if total_count == 0:
            print(f"⚠️ [智绘加载] 文件夹为空: {path}")
            return (self.generate_black_image(), "empty_folder")

        # 3. 计算目标索引 (Index Logic)
        target_index = index_seed
        
        # 处理不同的模式 (Mode)
        # WAS 的 incremental 逻辑比较复杂，需要存储状态。
        # 这里为了简化且更符合 ComfyUI 原生逻辑，我们主要把 index_seed 当作绝对索引。
        # 如果选了 randomize，我们就用 seed 做个随机数
        if mode == "randomize":
            import random
            random.seed(index_seed)
            target_index = random.randint(0, total_count - 1)

        # 4. 越界处理逻辑 (核心!)
        if target_index >= total_count:
            behavior = out_of_bounds_behavior.split(" ")[0] # 提取英文部分
            
            if behavior == "return_empty_black":
                print(f"🛑 [智绘加载] 索引 {target_index} 超出范围 (总数{total_count}) -> 发送黑图")
                return (self.generate_black_image(), "out_of_bounds")
            
            elif behavior == "loop_sequence":
                new_index = target_index % total_count
                print(f"🔄 [智绘加载] 索引 {target_index} -> 循环至 {new_index} (总数{total_count})")
                target_index = new_index
                
            elif behavior == "hold_last":
                new_index = total_count - 1
                print(f"✋ [智绘加载] 索引 {target_index} -> 保持最后 {new_index} (总数{total_count})")
                target_index = new_index

        # 5. 加载图片
        try:
            image_path = files[target_index]
            i = Image.open(image_path)
            i = ImageOps.exif_transpose(i) # 修正手机照片方向

            # 处理颜色通道
            if not allow_RGBA and 'A' in i.getbands():
                # 如果不许 RGBA，但图是 RGBA，则转 RGB (黑色背景)
                i = i.convert("RGB")
            elif allow_RGBA:
                # 允许 RGBA，保持原样 (但要确保 ComfyUI 能吃)
                pass
            else:
                i = i.convert("RGB")

            # 转 Tensor
            image_np = np.array(i).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_np)[None,]

            # 处理文件名
            filename = os.path.basename(image_path)
            if not filename_text_extension:
                filename = os.path.splitext(filename)[0]

            print(f"📂 [智绘加载] 成功加载: {filename} (Index: {target_index})")
            return (image_tensor, filename)

        except Exception as e:
            print(f"❌ [智绘加载] 读取文件失败: {e}")
            return (self.generate_black_image(), "read_error")

    def generate_black_image(self):
        # 生成一张 512x512 的全黑图
        black_tensor = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
        return black_tensor

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_SafeBatchLoader": ZH_SafeBatchLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_SafeBatchLoader": "🛡️ 智绘_安全批次加载器"
}