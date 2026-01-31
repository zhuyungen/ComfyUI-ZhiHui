"""
智绘灵箱 - 噪波节点

功能：为图片添加各种噪波效果
支持高斯噪波、椒盐噪波、柏林噪波等
适合图片预处理、风格化、测试
"""
import torch
import numpy as np
from PIL import Image


class ZH_AddNoise:
    """
    智绘噪波添加节点
    支持多种噪波类型和强度控制
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "noise_type": ([
                    "高斯噪波",
                    "椒盐噪波",
                    "均匀噪波",
                    "泊松噪波",
                    "混合噪波",
                ], {
                    "default": "高斯噪波"
                }),
                "intensity": ("FLOAT", {
                    "default": 0.1,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "噪波强度：0为无噪波，1为最大噪波"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "tooltip": "随机种子（0为随机）"
                }),
                "monochrome": ("BOOLEAN", {
                    "default": False,
                    "label_on": "✅ 单色",
                    "label_off": "❌ 彩色",
                    "tooltip": "单色噪波（灰度）或彩色噪波"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("噪波图像",)
    FUNCTION = "add_noise"
    CATEGORY = "智绘灵箱/工具箱"

    def add_noise(self, images, noise_type, intensity, seed, monochrome):
        """添加噪波到图片"""

        # 设置随机种子
        if seed > 0:
            np.random.seed(seed)

        result_images = []

        for img_tensor in images:
            # 获取图片数据
            img_np = img_tensor.cpu().numpy().copy()
            height, width, channels = img_np.shape

            # 生成噪波
            if noise_type == "高斯噪波":
                # 高斯噪波：均值0，标准差intensity
                if monochrome:
                    noise = np.random.normal(0, intensity, (height, width, 1))
                    noise = np.repeat(noise, channels, axis=2)
                else:
                    noise = np.random.normal(0, intensity, (height, width, channels))

            elif noise_type == "椒盐噪波":
                # 椒盐噪波：随机黑白点
                noise = np.zeros((height, width, channels))
                mask = np.random.random((height, width, channels)) < intensity
                noise[mask] = np.random.choice([0, 1], size=np.sum(mask))
                noise = noise - img_np * mask  # 只在mask位置应用

            elif noise_type == "均匀噪波":
                # 均匀噪波：[-intensity, intensity]
                if monochrome:
                    noise = np.random.uniform(-intensity, intensity, (height, width, 1))
                    noise = np.repeat(noise, channels, axis=2)
                else:
                    noise = np.random.uniform(-intensity, intensity, (height, width, channels))

            elif noise_type == "泊松噪波":
                # 泊松噪波：模拟光子计数噪声
                lam = 1.0 / (intensity + 0.01)  # 避免除零
                if monochrome:
                    noise_val = np.random.poisson(lam, (height, width, 1)) / lam - 1
                    noise = np.repeat(noise_val, channels, axis=2) * intensity
                else:
                    noise = (np.random.poisson(lam, (height, width, channels)) / lam - 1) * intensity

            else:  # 混合噪波
                # 混合多种噪波
                gaussian = np.random.normal(0, intensity * 0.5, (height, width, channels))
                uniform = np.random.uniform(-intensity * 0.3, intensity * 0.3, (height, width, channels))
                noise = gaussian + uniform

            # 应用噪波
            noisy_img = img_np + noise

            # 限制范围
            noisy_img = np.clip(noisy_img, 0, 1)

            # 转回tensor
            noisy_tensor = torch.from_numpy(noisy_img.astype(np.float32))
            result_images.append(noisy_tensor)

        # 堆叠批次
        output = torch.stack(result_images)
        print(f"✅ [智绘噪波] 完成 {len(images)} 张图片 {noise_type} (强度:{intensity:.2f})")
        return (output,)


class ZH_GenerateNoise:
    """
    智绘噪波生成节点
    生成纯噪波图像
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 8192,
                    "step": 8,
                    "tooltip": "图片宽度"
                }),
                "height": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 8192,
                    "step": 8,
                    "tooltip": "图片高度"
                }),
                "noise_type": ([
                    "白噪声",
                    "柏林噪声",
                    "分形噪声",
                    "梯度噪声",
                    "云朵噪声",
                ], {
                    "default": "白噪声"
                }),
                "scale": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 10.0,
                    "step": 0.1,
                    "tooltip": "噪声缩放（影响细节大小）"
                }),
                "octaves": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 8,
                    "step": 1,
                    "tooltip": "八度数（影响细节层次）"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "tooltip": "随机种子"
                }),
                "batch_size": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "tooltip": "批次大小"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("噪波图像",)
    FUNCTION = "generate_noise"
    CATEGORY = "智绘灵箱/工具箱"

    def generate_noise(self, width, height, noise_type, scale, octaves, seed, batch_size):
        """生成噪波图像"""

        # 设置随机种子
        if seed > 0:
            np.random.seed(seed)

        result_images = []

        for batch_idx in range(batch_size):
            if noise_type == "白噪声":
                # 纯随机噪声
                noise_img = np.random.rand(height, width, 3).astype(np.float32)

            elif noise_type == "柏林噪声":
                # 简化的柏林噪声实现
                noise_img = self._generate_perlin_noise(width, height, scale, octaves)

            elif noise_type == "分形噪声":
                # 分形布朗运动
                noise_img = self._generate_fractal_noise(width, height, scale, octaves)

            elif noise_type == "梯度噪声":
                # 梯度噪声
                noise_img = self._generate_gradient_noise(width, height, scale)

            else:  # 云朵噪声
                # 云朵效果噪声
                noise_img = self._generate_cloud_noise(width, height, scale, octaves)

            # 转换为tensor
            noise_tensor = torch.from_numpy(noise_img)
            result_images.append(noise_tensor)

        # 堆叠批次
        output = torch.stack(result_images)
        print(f"✅ [智绘噪波生成] 生成 {batch_size} 张 {width}x{height} {noise_type}")
        return (output,)

    def _generate_perlin_noise(self, width, height, scale, octaves):
        """简化的柏林噪声"""
        noise = np.zeros((height, width, 3), dtype=np.float32)
        frequency = scale
        amplitude = 1.0

        for _ in range(octaves):
            # 生成随机梯度场
            grid_width = int(width / frequency) + 2
            grid_height = int(height / frequency) + 2
            gradients = np.random.rand(grid_height, grid_width, 2) * 2 - 1

            # 插值生成噪声
            for y in range(height):
                for x in range(width):
                    gx = x / frequency
                    gy = y / frequency
                    ix = int(gx)
                    iy = int(gy)
                    fx = gx - ix
                    fy = gy - iy

                    # 简单双线性插值
                    v00 = np.dot(gradients[iy, ix], [fx, fy])
                    v10 = np.dot(gradients[iy, ix + 1], [fx - 1, fy])
                    v01 = np.dot(gradients[iy + 1, ix], [fx, fy - 1])
                    v11 = np.dot(gradients[iy + 1, ix + 1], [fx - 1, fy - 1])

                    v0 = v00 * (1 - fx) + v10 * fx
                    v1 = v01 * (1 - fx) + v11 * fx
                    value = v0 * (1 - fy) + v1 * fy

                    noise[y, x] += value * amplitude

            frequency *= 2
            amplitude *= 0.5

        # 归一化到 [0, 1]
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
        return noise

    def _generate_fractal_noise(self, width, height, scale, octaves):
        """分形噪声"""
        noise = np.zeros((height, width, 3), dtype=np.float32)
        frequency = scale
        amplitude = 1.0

        for _ in range(octaves):
            # 生成一层噪声
            layer = np.random.rand(
                int(height / frequency) + 1,
                int(width / frequency) + 1,
                3
            )
            # 放大到目标尺寸
            from scipy.ndimage import zoom
            layer_upscaled = zoom(layer, [frequency, frequency, 1], order=1)
            layer_upscaled = layer_upscaled[:height, :width, :]

            noise += layer_upscaled * amplitude

            frequency *= 2
            amplitude *= 0.5

        # 归一化
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
        return noise

    def _generate_gradient_noise(self, width, height, scale):
        """梯度噪声"""
        x = np.linspace(0, scale, width)
        y = np.linspace(0, scale, height)
        xx, yy = np.meshgrid(x, y)

        noise = np.sin(xx * 2 * np.pi) * np.cos(yy * 2 * np.pi)
        noise = (noise + 1) / 2  # 归一化到 [0, 1]
        noise = np.stack([noise, noise, noise], axis=2).astype(np.float32)
        return noise

    def _generate_cloud_noise(self, width, height, scale, octaves):
        """云朵噪声"""
        try:
            from scipy.ndimage import zoom
        except ImportError:
            # 如果没有scipy，回退到简单噪声
            return np.random.rand(height, width, 3).astype(np.float32)

        noise = np.zeros((height, width), dtype=np.float32)
        frequency = scale
        amplitude = 1.0

        for _ in range(octaves):
            layer_size = max(2, int(height / frequency))
            layer = np.random.rand(layer_size, layer_size)
            layer_upscaled = zoom(layer, frequency, order=3)
            layer_upscaled = layer_upscaled[:height, :width]

            noise += layer_upscaled * amplitude

            frequency *= 2
            amplitude *= 0.5

        # 归一化并应用云朵效果（非线性变换）
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
        noise = np.power(noise, 0.5)  # 增强明亮区域
        noise = np.stack([noise, noise, noise], axis=2).astype(np.float32)
        return noise


NODE_CLASS_MAPPINGS = {
    "ZH_AddNoise": ZH_AddNoise,
    "ZH_GenerateNoise": ZH_GenerateNoise,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_AddNoise": "🌫️ 智绘_添加噪波",
    "ZH_GenerateNoise": "🌫️ 智绘_生成噪波",
}
