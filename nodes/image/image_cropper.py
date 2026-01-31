import torch

class ZH_ImageCropper:
    """
    功能：精确图像裁剪
    支持像素级 (step=1) 和百分比级裁剪，解决原生节点步长过大的问题。
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "crop_mode": (["Pixels (像素)", "Percentage (百分比)"], {"default": "Pixels (像素)"}),
                # 设置 min=0, step=1 (像素) 或 step=0.1 (百分比)
                "top": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "bottom": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "left": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "right": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("cropped_image",)
    FUNCTION = "crop_image"
    CATEGORY = "智绘灵箱/图片"

    def crop_image(self, image, crop_mode, top, bottom, left, right):
        # image shape: [batch, height, width, channels]
        _, h, w, _ = image.shape
        
        crop_top = 0
        crop_bottom = 0
        crop_left = 0
        crop_right = 0
        
        # 1. 计算裁剪量
        if crop_mode == "Percentage (百分比)":
            # 百分比模式：把输入的整数当作百分比 (比如输入 10 代表 10%)
            # 这里限制最大 100，防止切没了
            top = min(top, 100)
            bottom = min(bottom, 100)
            left = min(left, 100)
            right = min(right, 100)
            
            crop_top = int(h * (top / 100.0))
            crop_bottom = int(h * (bottom / 100.0))
            crop_left = int(w * (left / 100.0))
            crop_right = int(w * (right / 100.0))
        else:
            # 像素模式：直接使用数值
            crop_top = top
            crop_bottom = bottom
            crop_left = left
            crop_right = right
            
        # 2. 边界安全检查 (防止裁剪过度导致报错)
        # 如果切得太多，至少保留 1 个像素
        if crop_top + crop_bottom >= h:
            print(f"⚠️ [智绘裁剪] 高度裁剪过度 (H:{h}, Cut:{crop_top}+{crop_bottom})，已自动保留1像素。")
            scale = (h - 1) / (crop_top + crop_bottom)
            crop_top = int(crop_top * scale)
            crop_bottom = int(crop_bottom * scale)
            
        if crop_left + crop_right >= w:
            print(f"⚠️ [智绘裁剪] 宽度裁剪过度 (W:{w}, Cut:{crop_left}+{crop_right})，已自动保留1像素。")
            scale = (w - 1) / (crop_left + crop_right)
            crop_left = int(crop_left * scale)
            crop_right = int(crop_right * scale)

        # 3. 执行裁剪
        # PyTorch 切片语法: [batch, y1:y2, x1:x2, channel]
        # y2 = h - crop_bottom
        # x2 = w - crop_right
        
        new_y1 = crop_top
        new_y2 = h - crop_bottom
        new_x1 = crop_left
        new_x2 = w - crop_right
        
        cropped = image[:, new_y1:new_y2, new_x1:new_x2, :]
        
        print(f"✂️ [智绘裁剪] {w}x{h} -> {new_x2-new_x1}x{new_y2-new_y1} (Mode: {crop_mode})")
        
        return (cropped,)

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_ImageCropper": ZH_ImageCropper
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_ImageCropper": "✂️ 智绘_精确图像裁剪"
}