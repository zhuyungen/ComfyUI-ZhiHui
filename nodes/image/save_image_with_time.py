import os
import torch
import numpy as np
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import folder_paths
from datetime import datetime

class ZH_SaveImageWithDateTime:
    """
    智绘中文时间戳保存节点 - 使用中文时间戳命名

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 中文时间戳：使用中文格式的日期时间命名
    • 自定义后缀：添加描述性文字，方便识别
    • 子文件夹：自动创建指定的子文件夹路径
    • 格式选择：完整时间、仅日期、仅时间三种格式
    • 覆盖模式：选择是否覆盖同名文件
    • 元数据保存：自动保存工作流信息到PNG

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本保存
       • 连接图片到"images"端口
       • 设置"custom_suffix"为描述性后缀（如：智绘作品）
       • 设置"path_subfolder"为子文件夹名
       • 执行节点，图片保存到output/子文件夹/

    2️⃣ 时间戳格式
       • "年-月-日-时-分-秒"（默认）：
         示例：2025年01月28日14时30分45秒_智绘作品_00.png
       • "仅日期"：
         示例：2025年01月28日_智绘作品_00.png
       • "仅时间"：
         示例：14时30分45秒_智绘作品_00.png

    3️⃣ 覆盖模式
       • 关闭（默认）：文件名带序号，不覆盖
         - 批次中的多张图：_00, _01, _02...
         - 每次执行都生成新文件
       • 开启：文件名不带序号，覆盖同名文件
         - 批次中多张图会相互覆盖，只保留最后一张
         - 适合需要固定文件名的场景

    4️⃣ 子文件夹
       • 相对于ComfyUI的output文件夹
       • 默认：ZHIHUI_Output
       • 支持多级：project/version1/final
       • 不存在时自动创建

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 无直接输出（OUTPUT_NODE = True）
    • 图片保存到磁盘指定路径
    • 在ComfyUI界面可预览保存结果

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 项目分类：用子文件夹区分不同项目
    • 时间追踪：通过文件名追溯创建时间
    • 批次标识：后缀添加批次信息
    • 固定命名：开启覆盖模式，每次保存相同文件名
    • 快速定位：中文时间戳便于人工识别
    • 版本管理：配合子文件夹实现版本分类

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 保存位置固定为ComfyUI的output文件夹
    • 批次图片关闭覆盖模式时带序号（_00, _01...）
    • 开启覆盖模式时，批次中只保留最后一张
    • PNG格式自动保存工作流元数据
    • 压缩级别固定为4（平衡速度和大小）
    • 文件名使用中文，Windows/Linux均兼容
    • 同一秒内多次执行会覆盖（时间戳相同）

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 项目归档：
       path_subfolder = "项目A/2025年1月"
       按项目和月份归档作品

    2. 版本管理：
       path_subfolder = "角色设计/版本1"
       custom_suffix = "正式版"
       清晰的版本分类

    3. 测试迭代：
       覆盖模式开启
       每次测试覆盖上一次，保持文件夹整洁

    4. 批量生成：
       覆盖模式关闭
       批次图片自动编号，便于整理

    5. 时间追踪：
       使用完整时间戳格式
       通过文件名追踪创建时间

    🔗 推荐工作流
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • VAE Decode → 智绘_中文时间戳保存
      （标准图像生成流程）

    • 智绘_纯净图片加载器 → 处理 → 智绘_中文时间戳保存
      （批量处理带时间戳）

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "custom_suffix": ("STRING", {"default": "智绘作品", "multiline": False}),
                "path_subfolder": ("STRING", {"default": "ZHIHUI_Output", "multiline": False}),
                "timestamp_format": (["年-月-日-时-分-秒", "仅日期", "仅时间"], {"default": "年-月-日-时-分-秒"}),
                # 新增：覆盖模式开关
                "overwrite_mode": ("BOOLEAN", {"default": False, "label_on": "开启覆盖 (不带序号)", "label_off": "关闭覆盖 (自动序号)"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "智绘灵箱/图片"

    def save_images(self, images, custom_suffix, path_subfolder, timestamp_format, overwrite_mode, prompt=None, extra_pnginfo=None):
        # 1. 时间格式化
        now = datetime.now()
        if timestamp_format == "仅日期":
            time_str = now.strftime("%Y年%m月%d日")
        elif timestamp_format == "仅时间":
            time_str = now.strftime("%H时%M分%S秒")
        else:
            time_str = now.strftime("%Y年%m月%d日%H时%M分%S秒")

        filename_base = f"{time_str}_{custom_suffix}"
        
        full_output_folder = os.path.join(self.output_dir, path_subfolder)
        if not os.path.exists(full_output_folder):
            os.makedirs(full_output_folder)

        results = list()
        for batch_number, image in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # 元数据处理
            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            # --- 核心修改：根据开关决定文件名 ---
            if overwrite_mode:
                # 开启覆盖：不加 batch_number
                file = f"{filename_base}.png"
            else:
                # 关闭覆盖：保留 _00 这种序号
                file = f"{filename_base}_{batch_number:02d}.png"
            
            save_path = os.path.join(full_output_folder, file)
            
            img.save(save_path, pnginfo=metadata, compress_level=4)
            results.append({
                "filename": file,
                "subfolder": path_subfolder,
                "type": self.type
            })

        print(f"✅ [智绘保存] 已存入: {full_output_folder}/{filename_base} (覆盖模式:{overwrite_mode})")
        return {"ui": {"images": results}}

NODE_CLASS_MAPPINGS = {
    "ZH_SaveImageWithDateTime": ZH_SaveImageWithDateTime
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_SaveImageWithDateTime": "💾 智绘_中文时间戳保存"
}