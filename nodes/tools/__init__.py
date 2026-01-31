# -*- coding: utf-8 -*-
"""
智绘灵箱 - 工具箱节点集成

提供图像处理、性能优化、提示词工具等多种实用节点
包含：显存优化、图片开关、批处理、颜色调整、噪波生成等功能
"""

# 导入节点类
from .memory_optimizer import ZHIHUISmartMemoryOptimizerNode
from .image_switch import ImageMultiSwitchNode
from .image_layout import ImageLayoutNode
from .make_batch import MakeImageBatchNode
from .load_folder import ZHIHUILoadFolderImages
from .random_prompt_extract import ZHIHUIRandomPromptLineExtractNode
from .random_prompt_combine import ZHIHUIRandomPromptLineCombineNode

# 导入新增的LG工具节点（开源版）
from .color_adjust import ZH_ColorAdjust, ZH_ColorAdjustAdvanced
from .image_counter_loader import ZH_ImageLoaderWithCounter, ZH_ImageSequenceLoader
from .noise import ZH_AddNoise, ZH_GenerateNoise

# 导入运行节点
from .run_node import ZH_RunNode

# 节点注册配置
NODE_CLASS_MAPPINGS = {
    # 性能优化
    "ZH_MemoryOptimizer": ZHIHUISmartMemoryOptimizerNode,

    # 图片处理
    "ZH_ImageSwitch": ImageMultiSwitchNode,
    "ZH_ImageLayout": ImageLayoutNode,
    "ZH_MakeBatch": MakeImageBatchNode,
    "ZH_LoadFolder": ZHIHUILoadFolderImages,

    # 提示词工具
    "ZH_RandomPromptExtract": ZHIHUIRandomPromptLineExtractNode,
    "ZH_RandomPromptCombine": ZHIHUIRandomPromptLineCombineNode,

    # LG工具集（开源版，无需密钥）
    "ZH_ColorAdjust": ZH_ColorAdjust,
    "ZH_ColorAdjustAdvanced": ZH_ColorAdjustAdvanced,
    "ZH_ImageLoaderWithCounter": ZH_ImageLoaderWithCounter,
    "ZH_ImageSequenceLoader": ZH_ImageSequenceLoader,
    "ZH_AddNoise": ZH_AddNoise,
    "ZH_GenerateNoise": ZH_GenerateNoise,

    # 运行节点
    "ZH_RunNode": ZH_RunNode,
}

# 节点显示名称映射（智绘系列）
NODE_DISPLAY_NAME_MAPPINGS = {
    # 性能优化
    "ZH_MemoryOptimizer": "🧠 智绘_显存内存优化",

    # 图片处理
    "ZH_ImageSwitch": "🔢 智绘_多图片开关",
    "ZH_ImageLayout": "📐 智绘_图片排列",
    "ZH_MakeBatch": "📦 智绘_制作批次",
    "ZH_LoadFolder": "📁 智绘_文件夹加载",

    # 提示词工具
    "ZH_RandomPromptExtract": "🎲 智绘_随机提示词提取",
    "ZH_RandomPromptCombine": "🎲 智绘_随机提示词组合",

    # LG工具集（开源版，无需密钥）
    "ZH_ColorAdjust": "🎨 智绘_颜色调整",
    "ZH_ColorAdjustAdvanced": "🎨 智绘_高级颜色调整",
    "ZH_ImageLoaderWithCounter": "🔢 智绘_计数器加载",
    "ZH_ImageSequenceLoader": "📸 智绘_序列批量加载",
    "ZH_AddNoise": "🌫️ 智绘_添加噪波",
    "ZH_GenerateNoise": "🌫️ 智绘_生成噪波",

    # 运行节点
    "ZH_RunNode": "🔄 智绘_运行节点",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
