import os
import torch
import numpy as np
import random
from PIL import Image, ImageOps

class ZH_ImageBatchLoader:
    """
    智绘纯净批量图片加载器 - 无状态、可控、智能尺寸统一

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 批量加载：一次加载多张图片
    • 无状态设计：每次严格从指定索引开始，无记忆
    • 顺序/随机模式：支持按索引或随机抽取
    • 智能尺寸统一：自动处理不同尺寸图片（拉伸/裁剪/填充）
    • 自定义路径：直接指定文件夹路径
    • 批次控制：精确控制起始点和加载数量

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本加载
       • 设置"directory_path"为图片文件夹路径
       • "start_index"设为0（从第一张开始）
       • "batch_size"设置要加载的数量
       • "load_mode"选择"Index (按顺序)"
       • 执行节点，按顺序加载图片

    2️⃣ 自动递增加载
       • 右键点击"start_index"数字框
       • 选择"Convert to Widget"
       • 选择"Control after generate" → "Increment"
       • 每次执行后start_index自动+1
       • 实现逐张处理整个文件夹

    3️⃣ 随机抽取模式
       • "load_mode"选择"Random (随机抽取)"
       • 设置"seed"控制随机结果
       • 每次随机抽取batch_size张图片
       • 相同seed产生相同随机序列

    4️⃣ 尺寸统一处理
       • 默认模式：跟随第一张图的尺寸
       • 自定义尺寸：设置target_width和target_height
       • resize_mode选择处理策略：
         - Disabled (报错)：尺寸不同直接报错
         - Stretch (拉伸)：强制拉伸到目标尺寸
         - Crop (裁剪)：等比缩放后裁剪中心区域
         - Pad (填充-推荐)：等比缩放后填充黑边

    🔄 加载模式详解
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • Index (按顺序)：
      - 文件夹内图片按文件名排序
      - 从start_index开始，连续读取batch_size张
      - 索引越界时停止（不循环）
      - 适合批处理整个文件夹

    • Random (随机抽取)：
      - 从文件夹中随机抽取batch_size张
      - 不会重复抽取（使用sample方法）
      - seed控制随机性，相同seed结果相同
      - 适合数据增强、样本测试

    📐 尺寸处理策略对比
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • Disabled (报错)：
      - 严格模式，尺寸必须完全一致
      - 用于确保数据集规范性

    • Stretch (拉伸)：
      - 直接拉伸到目标尺寸
      - 会改变图片宽高比
      - 速度最快，但可能变形

    • Crop (裁剪)：
      - 等比缩放后裁剪中心区域
      - 保持宽高比，但会丢失边缘内容
      - 适合需要保持比例的场景

    • Pad (填充-推荐)：
      - 等比缩放后用黑色填充空白
      - 保持宽高比，不丢失内容
      - 最安全的统一方案

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • images：批量图片张量（自动堆叠为batch）
    • filename_text：文件名列表（逗号分隔）
    • directory：输入的文件夹路径

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 自动递增：配合"Control after generate"实现自动化
    • 循环处理：start_index从0到文件总数-1
    • 尺寸预设：target设为0时跟随第一张图
    • 尺寸标准化：设置为512/1024等标准尺寸
    • 随机增强：使用Random模式训练模型
    • 批次大小：根据显存调整batch_size

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 无状态设计：每次从start_index开始，不记忆上次位置
    • 如需记忆位置，请使用ComfyUI原生Batch Loader
    • 索引越界时停止，不会循环或报错
    • 文件夹必须存在且有读取权限
    • 支持格式：jpg、jpeg、png、bmp、webp、tiff
    • target_width和height必须是8的倍数（如512、1024）
    • Random模式下seed相同结果相同

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 批量处理工作流：
       start_index自动递增 + batch_size=1
       逐张处理整个文件夹

    2. 批次训练/测试：
       batch_size=8 + Pad模式
       一次处理8张不同尺寸图片

    3. 随机数据增强：
       Random模式 + 变化的seed
       每次随机抽取不同图片

    4. 固定样本测试：
       Index模式 + 固定start_index
       始终测试相同的图片组

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "", "multiline": False, "placeholder": "图片文件夹路径"}),
                
                # 核心控制：你要从第几张开始？
                # 如果想自动递增，请在界面上右键点击此数字 -> Convert to Widget -> Control after generate -> Increment
                "start_index": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1, "label": "起始索引 (Start Index)"}),
                
                # 批次大小：一次读几张？
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1, "label": "加载数量 (Batch Size)"}),
                
                # 模式选择
                "load_mode": (["Index (按顺序)", "Random (随机抽取)"], {"default": "Index (按顺序)"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "label": "随机种子"}),

                # 尺寸策略 (直接集成 V3 的好功能)
                "resize_mode": (["Disabled (报错)", "Stretch (拉伸)", "Crop (裁剪)", "Pad (填充-推荐)"], {"default": "Pad (填充-推荐)"}),
                "target_width": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8, "tooltip": "0 = 跟随第一张图"}),
                "target_height": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8, "tooltip": "0 = 跟随第一张图"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "filename_text", "directory")
    FUNCTION = "load_batch_images"
    CATEGORY = "智绘灵箱/图片"

    def load_batch_images(self, directory_path, start_index, batch_size, load_mode, seed, resize_mode, target_width, target_height):
        if not directory_path or not os.path.exists(directory_path):
            print(f"❌ [智绘加载] 路径不存在: {directory_path}")
            return (torch.zeros((1, 512, 512, 3)), "error", "")

        # 1. 扫描文件
        valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
        try:
            files = [
                os.path.join(directory_path, f) for f in os.listdir(directory_path) 
                if os.path.isfile(os.path.join(directory_path, f)) and os.path.splitext(f)[1].lower() in valid_exts
            ]
        except Exception as e:
            print(f"❌ [智绘加载] 扫描失败: {e}")
            return (torch.zeros((1, 512, 512, 3)), "scan_error", directory_path)
            
        if not files:
            print(f"⚠️ [智绘加载] 文件夹为空: {directory_path}")
            return (torch.zeros((1, 512, 512, 3)), "empty_folder", directory_path)

        # 2. 挑选文件 (无状态逻辑的核心)
        selected_files = []
        
        if load_mode == "Index (按顺序)":
            files.sort() # 必须排序，保证索引对应固定文件
            
            # 索引保护：如果超了，就循环 (取模)，或者你可以选择报错
            # 这里做成取模循环，保证永远能取到图，不会崩
            total_files = len(files)
            
            # 计算实际要取的片段
            for i in range(batch_size):
                # idx = (start_index + i) % total_files # 循环模式
                idx = start_index + i # 严格模式：超了就没了
                
                if idx < total_files:
                    selected_files.append(files[idx])
                else:
                    # 如果不需要循环，这里就停止
                    break 
                    
        elif load_mode == "Random (随机抽取)":
            rng = random.Random(seed)
            # 随机抽 batch_size 张，可能会重复，也可能不重复，看你怎么选
            # 这里用 sample (不重复)
            count = min(len(files), batch_size)
            selected_files = rng.sample(files, count)

        if not selected_files:
            print("⚠️ [智绘加载] 索引越界或无文件选中")
            return (torch.zeros((1, 512, 512, 3)), "index_error", directory_path)

        # 3. 读取并处理图片
        all_images_pil = []
        filenames = []
        
        for file_path in selected_files:
            try:
                i = Image.open(file_path)
                i = ImageOps.exif_transpose(i)
                if i.mode != 'RGB': i = i.convert('RGB')
                all_images_pil.append(i)
                filenames.append(os.path.basename(file_path))
            except Exception as e:
                print(f"❌ Load Error: {file_path}")

        if not all_images_pil:
            return (torch.zeros((1, 512, 512, 3)), "load_error", directory_path)

        # 4. 统一尺寸 (Pad/Crop/Stretch)
        # 这一步是为了防止 batch 堆叠时报错
        final_w = target_width if target_width > 0 else all_images_pil[0].width
        final_h = target_height if target_height > 0 else all_images_pil[0].height

        processed_tensors = []
        
        for img in all_images_pil:
            if img.size != (final_w, final_h):
                if resize_mode == "Disabled (报错)":
                    print(f"❌ 尺寸不匹配: {img.size} vs {(final_w, final_h)}")
                    return (torch.zeros((1, 512, 512, 3)), "size_mismatch", directory_path)
                
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

        # 5. 堆叠输出
        output_image = torch.cat(processed_tensors, dim=0)
        
        print(f"✅ [智绘加载] 成功加载 {len(processed_tensors)} 张 | 起点: {start_index}")
        return (output_image, ", ".join(filenames), directory_path)

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_ImageBatchLoader": ZH_ImageBatchLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_ImageBatchLoader": "🖼️ 智绘_纯净图片加载器"
}