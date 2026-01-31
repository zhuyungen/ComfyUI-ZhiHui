"""
智绘灵箱 - 颜色调整节点

功能：调整图片的亮度、对比度、饱和度、色调
支持批量处理和实时预览
"""
import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


class ZH_ColorAdjust:
    """
    智绘颜色调整节点
    支持亮度、对比度、饱和度、锐度调整
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "brightness": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "亮度：1.0为原图，>1增亮，<1变暗"
                }),
                "contrast": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "对比度：1.0为原图，>1增强，<1减弱"
                }),
                "saturation": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "饱和度：1.0为原图，0为灰度，>1增强"
                }),
                "sharpness": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "锐度：1.0为原图，>1增强，<1模糊"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("调整后图像",)
    FUNCTION = "adjust_color"
    CATEGORY = "智绘灵箱/工具箱"

    def adjust_color(self, images, brightness, contrast, saturation, sharpness):
        """执行颜色调整"""
        result_images = []

        for img_tensor in images:
            # 转换为PIL图像
            img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np, mode='RGB')

            # 应用亮度调整
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(pil_img)
                pil_img = enhancer.enhance(brightness)

            # 应用对比度调整
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer.enhance(contrast)

            # 应用饱和度调整
            if saturation != 1.0:
                enhancer = ImageEnhance.Color(pil_img)
                pil_img = enhancer.enhance(saturation)

            # 应用锐度调整
            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(pil_img)
                pil_img = enhancer.enhance(sharpness)

            # 转回tensor
            adjusted_np = np.array(pil_img).astype(np.float32) / 255.0
            adjusted_tensor = torch.from_numpy(adjusted_np)
            result_images.append(adjusted_tensor)

        # 堆叠批次
        output = torch.stack(result_images)
        print(f"✅ [智绘颜色调整] 完成 {len(images)} 张图片调整")
        return (output,)


class ZH_ColorAdjustAdvanced:
    """
    智绘高级颜色调整节点
    支持色温、色调、曲线调整
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "temperature": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 1.0,
                    "display": "slider",
                    "tooltip": "色温：负值偏冷（蓝色），正值偏暖（黄色）"
                }),
                "tint": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 1.0,
                    "display": "slider",
                    "tooltip": "色调：负值偏绿，正值偏品红"
                }),
                "exposure": ("FLOAT", {
                    "default": 0.0,
                    "min": -2.0,
                    "max": 2.0,
                    "step": 0.1,
                    "display": "slider",
                    "tooltip": "曝光：调整整体亮度（EV值）"
                }),
                "highlights": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 1.0,
                    "display": "slider",
                    "tooltip": "高光：调整亮部细节"
                }),
                "shadows": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 1.0,
                    "display": "slider",
                    "tooltip": "阴影：调整暗部细节"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("调整后图像",)
    FUNCTION = "adjust_advanced"
    CATEGORY = "智绘灵箱/工具箱"

    def adjust_advanced(self, images, temperature, tint, exposure, highlights, shadows):
        """高级颜色调整"""
        result_images = []

        for img_tensor in images:
            # 转换为numpy数组（float32）
            img_np = img_tensor.cpu().numpy()

            # 应用曝光调整
            if exposure != 0.0:
                img_np = img_np * (2 ** exposure)

            # 应用色温调整
            if temperature != 0.0:
                temp_factor = temperature / 100.0
                # 冷色（蓝色）或暖色（黄色）
                img_np[:, :, 0] = np.clip(img_np[:, :, 0] + temp_factor * 0.1, 0, 1)  # R
                img_np[:, :, 2] = np.clip(img_np[:, :, 2] - temp_factor * 0.1, 0, 1)  # B

            # 应用色调调整
            if tint != 0.0:
                tint_factor = tint / 100.0
                # 绿色或品红
                img_np[:, :, 1] = np.clip(img_np[:, :, 1] - tint_factor * 0.1, 0, 1)  # G
                img_np[:, :, 0] = np.clip(img_np[:, :, 0] + tint_factor * 0.05, 0, 1)  # R
                img_np[:, :, 2] = np.clip(img_np[:, :, 2] + tint_factor * 0.05, 0, 1)  # B

            # 应用高光调整
            if highlights != 0.0:
                hl_factor = highlights / 100.0
                # 仅影响亮部（>0.5）
                bright_mask = img_np > 0.5
                adjustment = (img_np - 0.5) * hl_factor * 0.5
                img_np = np.where(bright_mask, img_np + adjustment, img_np)

            # 应用阴影调整
            if shadows != 0.0:
                sh_factor = shadows / 100.0
                # 仅影响暗部（<0.5）
                dark_mask = img_np < 0.5
                adjustment = (0.5 - img_np) * sh_factor * 0.5
                img_np = np.where(dark_mask, img_np + adjustment, img_np)

            # 限制范围
            img_np = np.clip(img_np, 0, 1)

            # 转回tensor
            adjusted_tensor = torch.from_numpy(img_np.astype(np.float32))
            result_images.append(adjusted_tensor)

        # 堆叠批次
        output = torch.stack(result_images)
        print(f"✅ [智绘高级颜色调整] 完成 {len(images)} 张图片调整")
        return (output,)


NODE_CLASS_MAPPINGS = {
    "ZH_ColorAdjust": ZH_ColorAdjust,
    "ZH_ColorAdjustAdvanced": ZH_ColorAdjustAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_ColorAdjust": "🎨 智绘_颜色调整",
    "ZH_ColorAdjustAdvanced": "🎨 智绘_高级颜色调整",
}
