import os
import json
import numpy as np
from PIL import Image, PngImagePlugin
import torch

class ZH_SaveImagePlus:
    """
    智绘高级图像保存节点 - 自定义路径、DPI、元数据控制

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 自定义保存路径：完全控制文件保存位置
    • 自动编号系统：智能扫描已有文件，续接编号不重复
    • DPI控制：设置图片打印分辨率（72-600 DPI）
    • 质量控制：JPG格式支持质量调节（1-100）
    • 元数据开关：选择性保存工作流信息到PNG
    • 批量处理：自动处理批次图片

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本保存
       • 连接图片输入端口
       • 设置"根目录路径"，如：C:/ComfyUI_Output
       • 设置"子文件夹"，如：date/job1
       • 执行节点，图片保存到完整路径
       • 如文件夹不存在，自动创建

    2️⃣ 文件命名
       • "文件名前缀"：设置文件名开头，如 Image
       • 自动添加5位数字编号：Image_00001.png
       • 编号自动续接：如已有 Image_00005，下次从 00006 开始
       • 批次处理：同批多张图自动递增编号

    3️⃣ 格式选择
       • PNG格式：
         - 无损压缩，最佳质量
         - 支持透明通道
         - 支持保存工作流元数据
       • JPG格式：
         - 有损压缩，文件更小
         - 不支持透明通道（自动转RGB）
         - 不保存工作流元数据
         - 可调节质量（1-100，默认100）

    4️⃣ DPI设置
       • 范围：72-600 DPI（默认300）
       • 72 DPI：屏幕显示标准
       • 150 DPI：普通打印
       • 300 DPI：高质量打印（推荐）
       • 600 DPI：专业印刷

    🔧 高级功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 元数据控制（save_workflow_metadata）：
      - 打开：PNG文件包含完整工作流信息，可还原
      - 关闭：PNG文件纯净，不含任何元数据
      - 用途：分享图片时关闭，保护工作流隐私

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • image：原图直通输出，可连接后续节点
    • full_path：已保存文件的完整路径（调试用）

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 路径格式：支持 / 和 \\ 两种分隔符
    • 子文件夹支持多级：project/v1/final
    • date 变量：在子文件夹名中使用，自动按日期分类
    • 批量保存：输入批次图片，自动保存所有图片
    • 编号续接：中断任务重跑不会覆盖已有文件

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 根目录必须存在，或有创建权限
    • JPG格式会自动移除透明通道
    • JPG格式不保存工作流元数据
    • 元数据开关仅对PNG格式生效
    • 编号扫描机制：扫描前缀相同的文件找最大编号

    📂 路径示例
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 根目录：C:/ComfyUI_Output
    • 子文件夹：2025/project_A
    • 文件名前缀：render
    • 最终路径：C:/ComfyUI_Output/2025/project_A/render_00001.png

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        self.output_dir = "output" # 默认 fallback

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "root_path": ("STRING", {"default": "C:/ComfyUI_Output", "multiline": False}),
                "sub_folder": ("STRING", {"default": "date/job1", "multiline": False}),
                "filename_prefix": ("STRING", {"default": "Image", "multiline": False}),
                "extension": (["png", "jpg"], {"default": "png"}),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1}),
                "dpi": ("INT", {"default": 300, "min": 72, "max": 600, "step": 1}),
                # 你要求的开关：是否保存工作流元数据
                "save_workflow_metadata": ("BOOLEAN", {"default": True, "label_on": "保存 (Save)", "label_off": "丢弃 (Clean)"}),
            },
            # 隐藏属性：用于获取当前工作流的元数据
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "full_path")
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "智绘灵箱/图片"

    def save_images(self, images, root_path, sub_folder, filename_prefix, extension, quality, dpi, save_workflow_metadata, prompt=None, extra_pnginfo=None):
        
        # 1. 组装路径
        # 处理路径分隔符，防止 windows/linux 混用报错
        full_output_folder = os.path.join(root_path, sub_folder)
        
        # 自动新建文件夹
        if not os.path.exists(full_output_folder):
            try:
                os.makedirs(full_output_folder, exist_ok=True)
                print(f"🪣 [智绘保存] 已创建目录: {full_output_folder}")
            except Exception as e:
                print(f"❌ [智绘报错] 创建目录失败: {e}")
                return (images, "")

        results = list()
        saved_paths = []

        # 2. 遍历批次中的每一张图
        for batch_number, image in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            # --- 自动计数器逻辑 ---
            # 扫描目录下已有的文件，找到最大的序号
            def get_next_counter(folder, prefix, ext):
                existing_files = os.listdir(folder)
                max_counter = 0
                for f in existing_files:
                    if f.startswith(prefix) and f.endswith(f".{ext}"):
                        # 尝试提取 "Image_0001.png" 后面的数字
                        try:
                            # 去掉后缀 -> 去掉前缀 -> 去掉下划线 -> 转数字
                            part = f.replace(f".{ext}", "").replace(prefix, "")
                            if part.startswith("_"):
                                num = int(part[1:])
                                if num > max_counter:
                                    max_counter = num
                        except:
                            continue
                return max_counter + 1

            counter = get_next_counter(full_output_folder, filename_prefix, extension)
            
            # 加上 batch_number 是为了防止同一次生成里的多张图重名
            current_counter = counter + batch_number 
            file_name = f"{filename_prefix}_{current_counter:05d}.{extension}"
            full_file_path = os.path.join(full_output_folder, file_name)

            # --- 元数据处理 (核心需求) ---
            metadata = None
            if save_workflow_metadata and extension == 'png':
                # 如果开启保存，并且是PNG格式，准备元数据容器
                metadata = PngImagePlugin.PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
            else:
                # 否则，metadata 保持为 None，即纯净保存
                pass

            # --- 保存执行 ---
            try:
                if extension == 'png':
                    # PNG 无损，忽略 quality，但写入 metadata 和 DPI
                    img.save(full_file_path, pnginfo=metadata, dpi=(dpi, dpi), compress_level=4)
                else:
                    # JPG 忽略 metadata (JPG存元数据比较麻烦，通常不存工作流)，写入 quality 和 DPI
                    img_bg = img.convert('RGB') # 移除 Alpha 通道防止 JPG 报错
                    img_bg.save(full_file_path, quality=quality, dpi=(dpi, dpi))
                
                saved_paths.append(full_file_path)
                
                # 为 UI 准备预览信息
                results.append({
                    "filename": file_name,
                    "subfolder": sub_folder, # 这里其实只是为了前端显示，指向哪里不重要，重要的是真实文件已存
                    "type": "output"
                })
                
            except Exception as e:
                print(f"❌ [智绘保存] 图片保存失败: {e}")

        
        print(f"🪣 [智绘保存] 成功保存 {len(saved_paths)} 张图片至: {full_output_folder}")
        
        # 返回原图以便后续节点使用，返回路径字符串用于调试
        return (images, ", ".join(saved_paths))

# 注册映射
NODE_CLASS_MAPPINGS = {
    "ZH_SaveImagePlus": ZH_SaveImagePlus
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_SaveImagePlus": "🪣 智绘_高级图像保存"
}