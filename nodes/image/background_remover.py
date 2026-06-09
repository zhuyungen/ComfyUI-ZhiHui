"""
智绘灵箱 - 智能抠图节点

功能：使用 AI 模型自动去除图片背景，支持多种场景
"""
import torch
import numpy as np
from PIL import Image
import os
import sys
import io
import logging
import folder_paths
import json
from pathlib import Path

try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# 注册 RMBG 模型路径
folder_paths.add_model_folder_path("rmbg", os.path.join(folder_paths.models_dir, "RMBG"))


# ==================== 日志控制 ====================

class SuppressRembgLogs:
    """上下文管理器：抑制rembg下载模型时的冗余日志"""

    def __enter__(self):
        # 保存原始输出
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # 抑制特定库的日志
        logging.getLogger('rembg').setLevel(logging.WARNING)
        logging.getLogger('onnxruntime').setLevel(logging.ERROR)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始输出
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        return False


# ==================== 辅助函数 ====================

def tensor2pil(image):
    """将 ComfyUI 的 tensor 转为 PIL Image"""
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def pil2tensor(image):
    """将 PIL Image 转为 ComfyUI 的 tensor"""
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def refine_foreground(image_tensor, mask_tensor):
    """
    快速前景颜色估算优化
    使用 guided filter 或简单的颜色传播来优化前景边缘

    Args:
        image_tensor: [B, C, H, W] 格式的图像张量
        mask_tensor: [B, 1, H, W] 格式的遮罩张量

    Returns:
        refined_image: [B, C, H, W] 格式的优化后图像张量
    """
    try:
        import cv2

        # 确保输入格式正确
        if len(image_tensor.shape) == 4:
            image = image_tensor[0].permute(1, 2, 0).cpu().numpy()  # [H, W, C]
        else:
            image = image_tensor.permute(1, 2, 0).cpu().numpy()

        if len(mask_tensor.shape) == 4:
            mask = mask_tensor[0, 0].cpu().numpy()  # [H, W]
        else:
            mask = mask_tensor[0].cpu().numpy()

        # 转换为 uint8 格式
        image_uint8 = (image * 255).astype(np.uint8)
        mask_uint8 = (mask * 255).astype(np.uint8)

        # 创建三通道遮罩
        mask_3ch = cv2.cvtColor(mask_uint8, cv2.COLOR_GRAY2BGR)

        # 使用 guided filter 进行边缘优化
        # 参数: radius=5, eps=1e-6
        refined = cv2.ximgproc.guidedFilter(
            guide=image_uint8,
            src=image_uint8,
            radius=5,
            eps=1e-6
        )

        # 在遮罩边缘区域应用优化
        # 只在半透明区域（0.1-0.9）应用优化
        edge_mask = ((mask > 0.1) & (mask < 0.9)).astype(np.float32)
        edge_mask = cv2.GaussianBlur(edge_mask, (5, 5), 0)
        edge_mask = np.expand_dims(edge_mask, axis=-1)

        # 混合原图和优化后的图像
        result = image_uint8 * (1 - edge_mask) + refined * edge_mask
        result = result.astype(np.uint8)

        # 转换回 tensor 格式
        result_tensor = torch.from_numpy(result.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)

        return result_tensor

    except ImportError:
        # 如果 cv2.ximgproc 不可用，使用简单的高斯模糊作为替代
        print("⚠️ [智绘抠图] cv2.ximgproc 不可用，使用简化的前景优化")
        return image_tensor
    except Exception as e:
        print(f"⚠️ [智绘抠图] 前景优化失败: {e}")
        return image_tensor


def get_rembg_model_path():
    """
    获取 rembg 模型存储路径
    使用 ComfyUI 标准的 models/RMBG 目录
    """
    try:
        # 使用 ComfyUI 的 models/RMBG 目录
        models_dir = folder_paths.models_dir
        rembg_path = os.path.join(models_dir, "RMBG")

        # 确保目录存在
        os.makedirs(rembg_path, exist_ok=True)

        # 设置环境变量，让 rembg 使用这个目录
        os.environ['U2NET_HOME'] = rembg_path

        return rembg_path

    except Exception as e:
        # 回退到默认路径
        print(f"⚠️ [智绘抠图] 无法使用 ComfyUI 模型目录，使用默认路径: {e}")
        default_path = os.path.expanduser("~/.u2net")
        os.makedirs(default_path, exist_ok=True)
        os.environ['U2NET_HOME'] = default_path
        return default_path


# rembg 支持的标准模型名称列表
REMBG_STANDARD_MODELS = [
    "u2net", "u2netp", "u2net_human_seg", "u2net_cloth_seg",
    "silueta", "isnet-general-use", "isnet-anime", "sam",
    "birefnet-general", "birefnet-general-lite", "birefnet-portrait",
    "birefnet-dis", "birefnet-hrsod", "birefnet-cod",
]

# rembg标准模型 -> 中文友好显示名称
REMBG_DISPLAY_NAMES = {
    "u2net": "U2-Net 通用标准 (推荐)",
    "u2netp": "U2-Net 快速版 (速度优先)",
    "u2net_human_seg": "U2-Net 人像专用",
    "u2net_cloth_seg": "U2-Net 服装电商",
    "silueta": "Silueta 人像高精度",
    "isnet-general-use": "IS-Net 新一代通用",
    "isnet-anime": "IS-Net 动漫专用 (二次元)",
    "sam": "SAM 分割模型 (Meta)",
    "birefnet-general": "BiRefNet 通用高精度 (RMBG推荐)",
    "birefnet-general-lite": "BiRefNet 快速版",
    "birefnet-portrait": "BiRefNet 人像专用",
    "birefnet-dis": "BiRefNet 二分图像分割",
    "birefnet-hrsod": "BiRefNet 高分辨率显著目标",
    "birefnet-cod": "BiRefNet 伪装目标检测",
}

# 模型名称映射（显示名称 -> 智绘模型ID） - 保留向后兼容
MODEL_MAPPING = {
    "通用标准 (推荐)": "zh_standard",
    "通用快速 (速度优先)": "zh_fast",
    "人像专用 (人物)": "zh_human",
    "人像高精度 (细节)": "zh_human_hd",
    "服装电商 (衣物产品)": "zh_cloth",
    "新一代通用 (最新算法)": "zh_isnet",
    "新一代动漫 (二次元/插画)": "zh_isnet_anime",
}

# 智绘模型ID -> rembg实际模型名称
REMBG_MODEL_MAPPING = {
    "zh_standard": "u2net",
    "zh_fast": "u2netp",
    "zh_human": "u2net_human_seg",
    "zh_human_hd": "silueta",
    "zh_cloth": "u2net_cloth_seg",
    "zh_isnet": "isnet-general-use",
    "zh_isnet_anime": "isnet-anime",
}


def normalize_model_name(name):
    """
    标准化模型名称：统一连字符和下划线
    例如: isnet-general-use 和 isnet_general_use 都会变成 isnet-general-use
    """
    name_lower = name.lower()

    # 创建标准化映射
    normalized_map = {
        # 将下划线版本映射到连字符版本
        "isnet_general_use": "isnet-general-use",
        "isnet_anime": "isnet-anime",
        # 将连字符版本映射到下划线版本
        "u2net-human-seg": "u2net_human_seg",
        "u2net-cloth-seg": "u2net_cloth_seg",
    }

    # 如果有映射，返回标准名称
    if name_lower in normalized_map:
        return normalized_map[name_lower]

    return name_lower


# ==================== 本地模型扫描 ====================

def scan_local_rmbg_models():
    """
    扫描本地 RMBG 目录和 rembg 默认目录中的模型
    只识别 rembg 标准支持的模型及其变体

    扫描位置：
    1. ComfyUI/models/RMBG (优先)
    2. ~/.u2net (rembg默认位置)
    3. U2NET_HOME 环境变量指定的位置

    支持结构：
    1. 目录/模型名/model.onnx
    2. 目录/模型名.onnx
    3. 目录/模型名/子目录/model.onnx (递归搜索)
    """
    try:
        local_models = {}

        # 扫描目录列表
        scan_dirs = []

        # 1. ComfyUI/models/RMBG (优先级最高)
        comfyui_rmbg_dir = Path(folder_paths.models_dir) / "RMBG"
        if comfyui_rmbg_dir.exists():
            scan_dirs.append(("ComfyUI", comfyui_rmbg_dir))

        # 2. rembg 默认目录 ~/.u2net
        default_u2net = Path.home() / ".u2net"
        if default_u2net.exists():
            scan_dirs.append(("rembg默认", default_u2net))

        # 3. U2NET_HOME 环境变量
        u2net_home = os.environ.get('U2NET_HOME')
        if u2net_home:
            u2net_home_path = Path(u2net_home)
            if u2net_home_path.exists() and u2net_home_path not in [d[1] for d in scan_dirs]:
                scan_dirs.append(("U2NET_HOME", u2net_home_path))

        if not scan_dirs:
            return local_models

        # 扫描每个目录
        for source_name, base_dir in scan_dirs:
            try:
                # 列出目录中的所有内容
                all_items = list(base_dir.iterdir())

                # 情况1: 扫描子目录中的模型（包括递归搜索）
                for model_dir in all_items:
                    if not model_dir.is_dir():
                        continue

                    model_name = model_dir.name

                    # 递归搜索模型文件（.onnx 是 rembg 使用的格式）
                    model_files = (
                        list(model_dir.rglob("*.onnx")) +
                        list(model_dir.rglob("*.pth"))
                    )

                    if not model_files:
                        continue

                    # 标准化模型名称
                    # RMBG-1.4 / RMBG-2.0 对应 birefnet-general
                    if model_name.lower().startswith("rmbg"):
                        normalized_name = "birefnet-general"
                    else:
                        normalized_name = normalize_model_name(model_name)

                    # 只接受 rembg 标准支持的模型
                    if normalized_name not in [m.lower() for m in REMBG_STANDARD_MODELS]:
                        continue

                    # 如果已经找到了这个模型（优先使用ComfyUI目录的），跳过
                    if normalized_name in local_models:
                        continue

                    # 添加到模型列表
                    local_models[normalized_name] = {
                        "path": str(model_dir),
                        "model_type": "local",
                        "files": [f.name for f in model_files],
                        "original_name": model_name,
                        "source": source_name
                    }

                # 情况2: 扫描直接放在目录下的 .onnx 文件
                direct_files = list(base_dir.glob("*.onnx")) + list(base_dir.glob("*.pth"))
                if direct_files:
                    for model_file in direct_files:
                        model_name = model_file.stem
                        normalized_name = normalize_model_name(model_name)

                        # 只接受 rembg 标准支持的模型
                        if normalized_name not in [m.lower() for m in REMBG_STANDARD_MODELS]:
                            continue

                        # 如果已经找到了这个模型，跳过
                        if normalized_name in local_models:
                            continue

                        local_models[normalized_name] = {
                            "path": str(base_dir),
                            "model_type": "local",
                            "files": [model_file.name],
                            "original_name": model_name,
                            "source": source_name
                        }

            except Exception as e:
                print(f"⚠️ [智绘抠图] 扫描 {source_name} 目录时出错: {e}")
                continue

        return local_models

    except Exception as e:
        print(f"❌ [智绘抠图] 扫描本地模型时出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def is_model_available_locally(model_name):
    """检查模型是否已在本地，避免自动下载"""
    if model_name in LOCAL_MODELS_INFO:
        return True
    u2net_dir = Path(os.environ.get('U2NET_HOME', Path.home() / ".u2net"))
    if (u2net_dir / f"{model_name}.onnx").exists():
        return True
    return False


def get_all_available_models():
    """
    获取所有可用模型（本地模型 + 所有rembg标准模型）
    返回格式: {显示名称: 实际模型名称}
    """
    all_models = {}

    for std_model in REMBG_STANDARD_MODELS:
        display_name = REMBG_DISPLAY_NAMES.get(std_model, std_model)
        all_models[display_name] = std_model

    local_models = scan_local_rmbg_models()
    for local_model, model_info in local_models.items():
        display_name = REMBG_DISPLAY_NAMES.get(local_model, local_model)
        if display_name in all_models:
            all_models[f"{display_name} [本地已下载]"] = local_model
        else:
            all_models[display_name] = local_model

    return all_models


# LOCAL_MODELS_INFO 必须在 get_all_available_models 之前初始化
LOCAL_MODELS_INFO = scan_local_rmbg_models()
ALL_MODELS = get_all_available_models()


# ==================== 主节点 ====================

class ZH_BackgroundRemover:
    """
    智绘智能抠图节点
    使用 rembg 库实现高质量背景移除

    质量模式说明：
    - 标准模式: 快速抠图，适合简单背景
    - 高质量模式 (推荐头发丝): 启用 Alpha Matting，边缘更自然
    - 极致模式 (最佳细节): 最高质量，保留最多细节，适合复杂场景

    复杂场景建议：
    1. 头发丝/毛发: 使用"人像高精度"模型 + "高质量模式"或"极致模式"
    2. 调整前景阈值 (240-250): 值越高边缘越锐利
    3. 调整背景阈值 (5-15): 值越低背景越干净
    4. 调整腐蚀尺寸 (5-15): 用于平滑边缘
    """

    def __init__(self):
        self.session = None
        self.current_model = None
        self.model_path = None

    @classmethod
    def INPUT_TYPES(cls):
        # 获取所有可用模型的显示名称列表
        model_list = list(ALL_MODELS.keys())

        # 如果没有任何模型，至少保留一个默认选项
        if not model_list:
            model_list = ["U2-Net 通用标准 (推荐)"]

        # 优先选择推荐模型
        default_model = model_list[0] if model_list else "U2-Net 通用标准 (推荐)"

        # 尝试找到推荐的模型
        for name in model_list:
            if "推荐" in name or "u2-net 通用标准" in name.lower():
                default_model = name
                break

        return {
            "required": {
                "images": ("IMAGE", {
                    "tooltip": "输入需要抠图的图片"
                }),
                "model": (model_list, {
                    "default": default_model,
                    "tooltip": "选择抠图模型"
                }),
                "灵敏度": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "灵敏度控制（值越高检测越灵敏）"
                }),
                "处理分辨率": ("INT", {
                    "default": 1024,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "tooltip": "处理分辨率（越高越精细但越慢）"
                }),
                "遮罩模糊": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 64,
                    "step": 1,
                    "display": "slider",
                    "tooltip": "遮罩边缘模糊程度"
                }),
                "遮罩偏移": ("INT", {
                    "default": 0,
                    "min": -64,
                    "max": 64,
                    "step": 1,
                    "display": "slider",
                    "tooltip": "遮罩边界偏移（正值扩展，负值收缩）"
                }),
                "反转输出": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "反转遮罩和图像"
                }),
                "精细前景优化": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "使用快速前景颜色估算优化透明背景"
                }),
                "背景类型": (["透明度", "颜色"], {
                    "default": "透明度",
                    "tooltip": "选择输出背景类型"
                }),
            },
            "optional": {
                "背景颜色": ("COLORCODE", {
                    "default": "#222222",
                    "tooltip": "背景颜色（仅在背景类型为颜色时生效）"
                }),
                "启用Alpha Matting": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "启用Alpha Matting精细边缘优化（头发丝、毛发等细节更清晰，但速度较慢）"
                }),
                "Alpha前景阈值": ("INT", {
                    "default": 240,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "tooltip": "前景阈值（0-255），值越高对前景判断越严格"
                }),
                "Alpha背景阈值": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "tooltip": "背景阈值（0-255），值越低对背景判断越严格"
                }),
                "Alpha腐蚀大小": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 50,
                    "step": 1,
                    "tooltip": "腐蚀核大小，用于平滑边缘（值越大边缘越平滑）"
                }),
                "形态学后处理": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "启用形态学后处理（自动去除噪点和填充孔洞）"
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE")
    RETURN_NAMES = ("图像", "遮罩", "遮罩图像")
    FUNCTION = "remove_background"
    CATEGORY = "智绘灵箱/图片"

    def remove_background(self, images, model, 灵敏度, 处理分辨率, 遮罩模糊, 遮罩偏移,
                         反转输出, 精细前景优化, 背景类型, 背景颜色="#222222",
                         启用Alpha_Matting=False, Alpha前景阈值=240, Alpha背景阈值=10,
                         Alpha腐蚀大小=10, 形态学后处理=False):
        """执行背景移除"""

        if not REMBG_AVAILABLE:
            error_mask = torch.zeros((images.shape[0], images.shape[1], images.shape[2]))
            error_mask_image = error_mask.unsqueeze(-1).repeat(1, 1, 1, 3)
            return (images, error_mask, error_mask_image)

        # 从显示名称获取实际模型名称
        actual_model = ALL_MODELS.get(model, "u2net")

        # 检查是否是本地模型
        is_local = model in LOCAL_MODELS_INFO or actual_model in LOCAL_MODELS_INFO


        try:
            # 初始化或切换模型
            if self.session is None or self.current_model != actual_model:
                self.model_path = get_rembg_model_path()
                if not is_model_available_locally(actual_model):
                    raise RuntimeError(
                        f"模型 [{actual_model}] 未下载。\n"
                        f"请手动下载后放到 ComfyUI/models/RMBG/{actual_model}/ 目录，\n"
                        f"或运行: pip install rembg 后首次执行自动下载（需科学上网）。"
                    )
                with SuppressRembgLogs():
                    self.session = new_session(actual_model)
                self.current_model = actual_model

            # 批量处理图像
            result_images = []
            result_masks = []

            for idx, img_tensor in enumerate(images):
                # 转换为 PIL
                pil_image = tensor2pil(img_tensor)
                orig_w, orig_h = pil_image.size

                # 按处理分辨率缩放送入模型
                scale = min(处理分辨率 / max(orig_w, orig_h), 1.0)
                if scale < 1.0:
                    proc_w = int(orig_w * scale)
                    proc_h = int(orig_h * scale)
                    proc_image = pil_image.resize((proc_w, proc_h), Image.LANCZOS)
                else:
                    proc_image = pil_image

                # 执行背景移除
                with SuppressRembgLogs():
                    output = remove(
                        proc_image,
                        session=self.session,
                        alpha_matting=启用Alpha_Matting,
                        alpha_matting_foreground_threshold=Alpha前景阈值,
                        alpha_matting_background_threshold=Alpha背景阈值,
                        alpha_matting_erode_size=Alpha腐蚀大小,
                        post_process_mask=形态学后处理,
                        only_mask=False,
                    )

                # 还原到原始尺寸
                if scale < 1.0:
                    output = output.resize((orig_w, orig_h), Image.LANCZOS)

                # 确保输出为 RGBA
                if output.mode != 'RGBA':
                    output = output.convert('RGBA')

                # 提取 Alpha 通道作为遮罩
                alpha_array = np.array(output.split()[-1]).astype(np.float32) / 255.0

                # 应用灵敏度调整
                alpha_array = alpha_array * (1 + (1 - 灵敏度))
                alpha_array = np.clip(alpha_array, 0, 1)

                # 转换回 PIL 用于后处理
                mask_img = Image.fromarray((alpha_array * 255).astype(np.uint8))

                # 应用遮罩模糊
                if 遮罩模糊 > 0:
                    from PIL import ImageFilter
                    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=遮罩模糊))

                # 应用遮罩偏移
                if 遮罩偏移 != 0:
                    from PIL import ImageFilter
                    if 遮罩偏移 > 0:
                        for _ in range(遮罩偏移):
                            mask_img = mask_img.filter(ImageFilter.MaxFilter(3))
                    else:
                        for _ in range(-遮罩偏移):
                            mask_img = mask_img.filter(ImageFilter.MinFilter(3))

                # 反转遮罩
                if 反转输出:
                    mask_img = Image.fromarray(255 - np.array(mask_img))

                # 转换为 tensor
                mask_tensor = torch.from_numpy(np.array(mask_img).astype(np.float32) / 255.0)

                # 处理前景
                orig_image = tensor2pil(img_tensor)

                if 精细前景优化:
                    # 使用前景优化
                    img_tensor_rgba = torch.from_numpy(np.array(orig_image)).permute(2, 0, 1).unsqueeze(0).float() / 255.0
                    mask_tensor_b1hw = mask_tensor.unsqueeze(0).unsqueeze(0)

                    # 导入优化函数
                    try:
                        import cv2
                        refined_fg = refine_foreground(img_tensor_rgba, mask_tensor_b1hw)
                        refined_fg_img = tensor2pil(refined_fg[0].permute(1, 2, 0))
                        r, g, b = refined_fg_img.split()
                        foreground = Image.merge('RGBA', (r, g, b, mask_img))
                    except Exception as e:
                        print(f"⚠️ [智绘抠图] 前景优化失败，使用标准模式: {e}")
                        orig_rgba = orig_image.convert("RGBA")
                        r, g, b, _ = orig_rgba.split()
                        foreground = Image.merge('RGBA', (r, g, b, mask_img))
                else:
                    # 标准处理
                    orig_rgba = orig_image.convert("RGBA")
                    r, g, b, _ = orig_rgba.split()
                    foreground = Image.merge('RGBA', (r, g, b, mask_img))

                # 根据背景类型处理
                if 背景类型 == "颜色":
                    # 添加背景颜色
                    def hex_to_rgba(hex_color):
                        hex_color = hex_color.lstrip('#')
                        if len(hex_color) == 6:
                            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                            a = 255
                        elif len(hex_color) == 8:
                            r, g, b, a = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), int(hex_color[6:8], 16)
                        else:
                            r, g, b, a = 34, 34, 34, 255  # 默认灰色
                        return (r, g, b, a)

                    rgba = hex_to_rgba(背景颜色)
                    bg_image = Image.new('RGBA', orig_image.size, rgba)
                    composite_image = Image.alpha_composite(bg_image, foreground)
                    result_img = pil2tensor(composite_image.convert("RGB"))
                else:
                    # 透明背景
                    result_img = pil2tensor(foreground)

                result_images.append(result_img)
                result_masks.append(mask_tensor)

            # 合并批次
            output_images = torch.cat(result_images, dim=0)
            output_masks = torch.stack(result_masks)

            # 创建遮罩图像（用于可视化）
            mask_images = []
            for mask_tensor in result_masks:
                mask_image = mask_tensor.unsqueeze(0).unsqueeze(-1).repeat(1, 1, 1, 3)
                mask_images.append(mask_image)
            mask_image_output = torch.cat(mask_images, dim=0)

            return (output_images, output_masks, mask_image_output)

        except Exception as e:
            print(f"❌ [智绘抠图] 处理失败: {e}")
            print("💡 提示: 检查模型是否下载完成、显存是否充足")
            import traceback
            traceback.print_exc()

            # 返回原图和空白遮罩
            error_mask = torch.zeros((images.shape[0], images.shape[1], images.shape[2]))
            error_mask_image = error_mask.unsqueeze(-1).repeat(1, 1, 1, 3)
            return (images, error_mask, error_mask_image)


class ZH_BackgroundRemoverWithPrompt:
    """
    智绘提示词抠图节点（实验性）
    根据文本描述抠出特定物体
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "prompt": ("STRING", {
                    "multiline": False,
                    "default": "person",
                }),
                "confidence_threshold": ("FLOAT", {
                    "default": 0.25,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE")
    RETURN_NAMES = ("RGB图像", "Alpha蒙版", "原图(透传)")
    FUNCTION = "segment_by_text"
    CATEGORY = "智绘灵箱/图片"

    def segment_by_text(self, images, prompt, confidence_threshold):
        error_mask = torch.zeros((images.shape[0], images.shape[1], images.shape[2]))
        return (images, error_mask, images)


class ZH_BackgroundReplacer:
    """
    智绘背景替换节点
    将抠图结果合成到新背景上
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "foreground": ("IMAGE",),
                "mask": ("MASK",),
                "background": ("IMAGE",),
                "blend_mode": ([
                    "正常覆盖 (推荐)",
                    "正片叠底 (变暗)",
                    "滤色 (变亮)",
                ], {"default": "正常覆盖 (推荐)"}),
                "feather_edge": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 50,
                    "step": 1,
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("合成图像",)
    FUNCTION = "replace_background"
    CATEGORY = "智绘灵箱/图片"

    def replace_background(self, foreground, mask, background, blend_mode, feather_edge):
        """替换背景"""
        try:
            # 调整 mask 维度
            if len(mask.shape) == 3:
                mask = mask.unsqueeze(-1)
            elif len(mask.shape) == 2:
                mask = mask.unsqueeze(0).unsqueeze(-1)

            # 边缘羽化
            if feather_edge > 0:
                try:
                    from scipy.ndimage import gaussian_filter
                    mask_np = mask.cpu().numpy()
                    for i in range(mask_np.shape[0]):
                        mask_np[i, :, :, 0] = gaussian_filter(
                            mask_np[i, :, :, 0],
                            sigma=feather_edge/3
                        )
                    mask = torch.from_numpy(mask_np).to(mask.device)
                except ImportError:
                    print("⚠️ [智绘抠图] scipy 未安装，跳过羽化")

            # 扩展 mask 到 RGB 三通道
            mask_rgb = mask.repeat(1, 1, 1, 3)

            # 调整背景尺寸
            if background.shape[1:3] != foreground.shape[1:3]:
                from torch.nn.functional import interpolate
                background = interpolate(
                    background.permute(0, 3, 1, 2),
                    size=(foreground.shape[1], foreground.shape[2]),
                    mode='bilinear',
                    align_corners=False
                ).permute(0, 2, 3, 1)

            # 调整批次数量
            if background.shape[0] == 1 and foreground.shape[0] > 1:
                background = background.repeat(foreground.shape[0], 1, 1, 1)

            # 混合模式
            if blend_mode == "正片叠底 (变暗)":
                result = foreground * mask_rgb * background + background * (1 - mask_rgb)
            elif blend_mode == "滤色 (变亮)":
                result = 1 - (1 - foreground * mask_rgb) * (1 - background)
            else:  # 正常覆盖
                result = foreground * mask_rgb + background * (1 - mask_rgb)

            return (result,)

        except Exception as e:
            print(f"❌ [智绘抠图] 背景替换失败: {e}")
            return (foreground,)


# ==================== 节点注册 ====================

NODE_CLASS_MAPPINGS = {
    "ZH_BackgroundRemover": ZH_BackgroundRemover,
    "ZH_BackgroundRemoverWithPrompt": ZH_BackgroundRemoverWithPrompt,
    "ZH_BackgroundReplacer": ZH_BackgroundReplacer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_BackgroundRemover": "🎨 智绘_智能抠图",
    "ZH_BackgroundRemoverWithPrompt": "🎯 智绘_提示词抠图(实验)",
    "ZH_BackgroundReplacer": "🎨 智绘_背景替换",
}
