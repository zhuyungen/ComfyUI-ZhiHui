"""
智绘灵箱 - 制作批次节点

将多张图片合并成批次，支持自动尺寸匹配
适用于批量处理、批量生成等场景
"""

import torch
import torch.nn.functional as F

# 定义默认和最大输入数量
DEFAULT_IMAGES = 2  # 默认显示2个输入（前端会自动扩展）
MAX_IMAGES = 20     # 最多支持20个输入


class MakeImageBatchNode:
    """
    智绘制作批次节点 - 将多个图像合并成批次

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 批次合并：将多个单独图像合并成一个批次
    • 自动尺寸匹配：不同尺寸图像自动缩放到统一大小
    • 动态输入：支持最多20个图像输入
    • 批次输出：输出批次可直接用于批量处理
    • 数量统计：输出图像总数，便于后续节点使用

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本合并
       • 连接多张图片到"📸 图像1", "📸 图像2"... 端口
       • 执行节点，自动合并为批次
       • 从"🖼️ 图像批次"输出合并后的批次
       • 从"📊 图像数量"查看批次大小

    2️⃣ 动态扩展
       • 默认显示2个图像输入端口
       • 连接图像后，前端自动显示更多端口
       • 最多支持20个输入端口
       • 按需连接，无需全部使用

    3️⃣ 尺寸统一
       • 以第一张图像的尺寸为基准
       • 后续图像自动缩放到相同尺寸
       • 使用双线性插值（bilinear）保证质量
       • 无需手动调整尺寸

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 🖼️ 图像批次：合并后的图像批次（Tensor）
    • 📊 图像数量：批次中的图像总数（整数）

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 批量处理：合并多张图后批量应用滤镜/模型
    • 对比展示：将不同版本合并后统一处理
    • 节点集成：将多个图像源合并为单一流
    • 尺寸标准化：自动统一不同尺寸的图像
    • 数量控制：通过图像数量输出控制后续逻辑

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 至少需要输入一张图像
    • 所有图像会被缩放到第一张的尺寸
    • 缩放可能改变宽高比，建议输入相似尺寸的图
    • 批次大小会影响显存占用
    • 输入端口编号从1开始（📸 图像1, 📸 图像2...）
    • 最多支持20个输入

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 批量滤镜处理：
       合并多张图 → 应用滤镜 → 批量输出

    2. 版本对比：
       不同参数生成的多个版本 → 合并 → 统一展示

    3. 多源合并：
       从不同节点获取图像 → 合并为单一批次

    4. 网格预处理：
       合并图像 → 传入九宫格拼图节点

    5. 批量增强：
       合并多张图 → 批量放大/增强 → 统一保存

    🔗 常用工作流
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 智绘_制作批次 → 批量处理节点 → 智绘_九宫格拼图
    • 多个图像源 → 智绘_制作批次 → 统一保存
    • 智绘_多图片开关 × N → 智绘_制作批次 → 批量输出

    ═══════════════════════════════════════════════════
    """

    @classmethod
    def INPUT_TYPES(cls):
        """定义节点的输入端口"""
        inputs = {
            "required": {},
            "optional": {}
        }
        
        # 添加默认数量的图像输入（使用 image1, image2... 命名）
        for i in range(1, DEFAULT_IMAGES + 1):
            inputs["optional"][f"📸 图像{i}"] = ("IMAGE", {
                "tooltip": f"第{i}张图像（可选）"
            })
        
        return inputs
    
    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("🖼️ 图像批次", "📊 图像数量")
    FUNCTION = "make_batch"
    CATEGORY = "智绘灵箱"
    
    def make_batch(self, **kwargs):
        """
        将多个图像合并成批次
        
        功能说明：
        - 收集所有输入的图像
        - 按顺序合并成一个批次
        - 返回合并后的批次和图像数量
        """
        
        # 收集所有输入的图像（检查所有可能的输入端口）
        images = []
        for i in range(1, MAX_IMAGES + 1):
            img = kwargs.get(f"📸 图像{i}", None)
            if img is not None:
                images.append(img)
        
        # 如果没有任何图像，返回错误
        if len(images) == 0:
            raise ValueError("❌ 错误: 至少需要提供一张图像！")
            
        # 统一图像尺寸（以第一张图像为准）
        target_h = images[0].shape[1]
        target_w = images[0].shape[2]
        processed_images = []
        
        for img in images:
            # 如果尺寸不一致，进行缩放
            if img.shape[1] != target_h or img.shape[2] != target_w:
                # 调整维度顺序为 [batch, channels, height, width] 以便 interpolate 使用
                img = img.permute(0, 3, 1, 2)
                # 缩放
                img = F.interpolate(img, size=(target_h, target_w), mode='bilinear', align_corners=False)
                # 恢复维度顺序为 [batch, height, width, channels]
                img = img.permute(0, 2, 3, 1)
            processed_images.append(img)
        
        # 合并所有图像成一个批次
        # 每个图像的shape是 [batch, height, width, channels]
        # 我们需要将它们沿着batch维度连接
        batch_images = torch.cat(processed_images, dim=0)
        
        # 返回批次和图像数量
        image_count = batch_images.shape[0]
        
        return (batch_images, image_count)


# ========== 节点注册配置 ==========
NODE_CLASS_MAPPINGS = {
    "ZhihuiMakeImageBatchNode": MakeImageBatchNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZhihuiMakeImageBatchNode": "📦 智绘_制作批次"
}
