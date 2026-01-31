"""
智绘灵箱 - 运行节点（图片网格复制器）

功能：将一张图片复制到网格的多个位置，输出批次
兼容 TTP 和其他批处理插件
参考自 lg_lock 的运行节点功能
"""
import torch
import numpy as np
from PIL import Image


class ZH_RunNode:
    """
    智绘运行节点
    将单张图片复制并放置到网格的多个位置
    输出完整批次，兼容多种插件
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": "画布图像（输入图片）"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "tooltip": "随机种子"
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    RETURN_TYPES = ("IMAGE", "*", "*", "*", "IMAGE")
    RETURN_NAMES = ("输出图片", "POSITIONS_1", "ORIGINAL_SIZE_2", "GRID_SIZE_3", "IMAGE_4")
    FUNCTION = "run_node"
    CATEGORY = "智绘灵箱/工具箱"

    @classmethod
    def IS_CHANGED(cls, image, seed):
        # 返回seed值，当seed改变时重新执行
        return seed

    def run_node(self, image, seed, prompt=None, extra_pnginfo=None):
        """执行网格排列"""

        # 固定网格大小为 4×4（16张图）
        grid_size = 4

        # 转换输入图片
        pil_img = self._tensor2pil(image)

        # 原图尺寸
        img_width = pil_img.width
        img_height = pil_img.height

        # 每个tile的尺寸 = 原图尺寸 / grid_size
        tile_width = img_width // grid_size
        tile_height = img_height // grid_size

        # 计算总 tile 数
        total_tiles = grid_size * grid_size

        # 最终拼接后的画布尺寸（与原图相同）
        original_image_size = (img_width, img_height)

        # 生成 positions LIST 并分割tiles
        positions = []
        tiles = []

        for row in range(grid_size):
            for col in range(grid_size):
                left = col * tile_width
                upper = row * tile_height
                right = left + tile_width
                lower = upper + tile_height
                positions.append((left, upper, right, lower))

                # 直接从原图裁剪（不放大）
                tile_img = pil_img.crop((left, upper, right, lower))
                tile_tensor = self._pil2tensor(tile_img)  # (1, tile_height, tile_width, 3)
                tiles.append(tile_tensor)

        # 合并成批次
        tiles_batch = torch.cat(tiles, dim=0)  # (16, tile_height, tile_width, 3)

        # 简化的日志输出
        print(f"✅ [智绘运行节点] 分割完成: {total_tiles}个tiles ({tile_width}×{tile_height})")

        # 返回:
        # 1. 输出图片: tiles批次 (16, tile_height, tile_width, 3) - 16个分割后的tiles
        # 2. POSITIONS_1: 位置列表
        # 3. ORIGINAL_SIZE_2: 原图尺寸
        # 4. GRID_SIZE_3: 网格大小 (4, 4)
        # 5. IMAGE_4: tiles批次 (16, tile_height, tile_width, 3)
        return (tiles_batch, positions, original_image_size, (grid_size, grid_size), tiles_batch)

    def _tensor2pil(self, image):
        """Tensor转PIL"""
        return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

    def _pil2tensor(self, image):
        """PIL转Tensor"""
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


NODE_CLASS_MAPPINGS = {
    "ZH_RunNode": ZH_RunNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_RunNode": "🔄 智绘_运行节点",
}
