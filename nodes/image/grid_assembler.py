import torch
import numpy as np
from PIL import Image

class ZH_GridImageAssembler:
    """
    智绘九宫格拼图节点 - 批次图片网格排列

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 网格拼接：将批次图片紧密拼接成网格大图
    • 自定义布局：自由设置行数和列数（1-20）
    • 尺寸优化：限制单张图片尺寸，节省显存
    • 无间距设计：图片之间无缝拼接
    • 背景选择：支持黑色/白色背景
    • 自动截断：超出容量的图片自动舍弃

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本拼接
       • 连接批次图片到"images"端口
       • 设置"columns"（列数）和"rows"（行数）
       • 执行节点，生成网格大图
       • 从"grid_image"输出拼接结果

    2️⃣ 调整布局
       • columns × rows = 网格容量
       • 例如：3列 × 3行 = 9张图
       • 范围：1-20（行和列）
       • 超出容量的图片会被截断

    3️⃣ 背景颜色
       • black：黑色背景（默认）
       • white：白色背景
       • 仅在图片未填满时可见

    4️⃣ 尺寸优化
       • max_cell_size：单张图片最大长边（像素）
       • 0：不限制，使用原始尺寸
       • >0：超过限制时等比缩小
       • 建议值：512、768、1024
       • 可大幅节省显存和渲染时间

    📐 布局计算
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 网格容量 = columns × rows
    • 画布宽度 = 单图宽度 × 列数
    • 画布高度 = 单图高度 × 行数
    • 图片按行优先排列（从左到右，从上到下）
    • 以第一张图的尺寸为基准，其他图自动缩放

    🎨 尺寸压缩示例
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 原图：2048x1536，max_cell_size=1024
      → 压缩为：1024x768（保持宽高比）

    • 原图：1024x1024，max_cell_size=512
      → 压缩为：512x512

    • 原图：800x600，max_cell_size=1024
      → 不压缩，保持800x600

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • grid_image：拼接完成的网格大图（单张图片）

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 对比展示：拼接不同参数生成的变体
    • 九宫格构图：3×3布局，经典九宫格效果
    • 联系图制作：多图并排对比效果
    • 缩略图集：压缩单图尺寸，快速预览批次
    • 打印排版：排列图片用于打印输出
    • 显存优化：大批量图片时降低max_cell_size

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 输入必须是批次图片（多张图的Tensor）
    • 以第一张图尺寸为基准，其他图自动缩放
    • 超出 columns × rows 的图片会被截断
    • max_cell_size=0 表示不限制尺寸
    • max_cell_size必须是64的倍数（如512、768、1024）
    • 大尺寸网格会消耗大量显存
    • 使用等比缩放（LANCZOS），保证质量

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 参数对比：
       批量生成不同参数的图 → 拼接为网格 → 对比效果

    2. 九宫格换装：
       生成9张不同服装 → 3×3拼接 → 展示效果

    3. 缩略图集：
       大量图片 → 压缩尺寸 → 网格排列 → 快速预览

    4. 打印排版：
       多张图片 → 网格排列 → 保存为单张 → 打印

    5. 联系图制作：
       前后对比图 → 2列排列 → 展示处理效果

    🔗 推荐工作流
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 批量生成 → 智绘_九宫格拼图 → 保存
      （批量图片拼接为一张）

    • 智绘_制作批次 → 智绘_九宫格拼图
      （多个单图合并拼接）

    • 智绘_纯净图片加载器 → 智绘_九宫格拼图
      （批量加载文件夹图片并拼接）

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",), # 输入必须是图片批次
                "columns": ("INT", {"default": 3, "min": 1, "max": 20, "step": 1}),
                "rows": ("INT", {"default": 3, "min": 1, "max": 20, "step": 1}),
                "background_color": (["black", "white"], {"default": "black"}), 
                # 你保留的优化想法：限制单张小图的最大长边，0表示不限制
                "max_cell_size": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 64, "display": "number"}), 
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grid_image",)
    FUNCTION = "assemble_grid"
    CATEGORY = "智绘灵箱/图片"

    def assemble_grid(self, images, columns, rows, background_color, max_cell_size):
        # images 是 Tensor [Batch, H, W, C]
        max_capacity = columns * rows
        
        # 1. 转换 Tensor 为 PIL List
        pil_images = []
        for img_tensor in images:
            # Tensor 转 Numpy (0-1) -> *255 -> uint8 -> PIL
            i = 255. * img_tensor.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            pil_images.append(img)
            
            # 如果达到上限，提前停止处理 (截断)
            if len(pil_images) >= max_capacity:
                break
        
        # 2. 获取并计算单格尺寸 (以第一张图为基准)
        if not pil_images:
            return (torch.zeros((1, 512, 512, 3)),)
            
        base_w, base_h = pil_images[0].size
        target_w, target_h = base_w, base_h

        # --- 尺寸压缩逻辑 ---
        if max_cell_size > 0:
            # 如果宽或高超过限制，计算缩放比例
            if base_w > max_cell_size or base_h > max_cell_size:
                scale = min(max_cell_size / base_w, max_cell_size / base_h)
                target_w = int(base_w * scale)
                target_h = int(base_h * scale)
                print(f"🪣 [九宫格] 触发压缩: 单图从 {base_w}x{base_h} -> {target_w}x{target_h}")

        # 3. 计算大画布尺寸 (紧密排列，无间距)
        canvas_w = target_w * columns
        canvas_h = target_h * rows
        
        # 创建画布
        bg_col = (0, 0, 0) if background_color == "black" else (255, 255, 255)
        canvas = Image.new("RGB", (canvas_w, canvas_h), color=bg_col)
        
        print(f"🪣 [九宫格] 创建紧密画布: {canvas_w}x{canvas_h}, 包含 {len(pil_images)} 张图")

        # 4. 循环粘贴
        for idx, img in enumerate(pil_images):
            # 计算当前是第几行第几列
            col_idx = idx % columns
            row_idx = idx // columns
            
            # 缩放处理 (如果有压缩需求，或者图片尺寸不统一)
            if img.size != (target_w, target_h):
                img = img.resize((target_w, target_h), Image.LANCZOS)
            
            # 计算坐标 (紧密排列)
            x = col_idx * target_w
            y = row_idx * target_h
            
            canvas.paste(img, (x, y))

        # 5. 转回 Tensor
        output_image = np.array(canvas).astype(np.float32) / 255.0
        output_image = torch.from_numpy(output_image)[None,]
        
        return (output_image,)

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_GridImageAssembler": ZH_GridImageAssembler
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_GridImageAssembler": "🪣 智绘_九宫格拼图"
}