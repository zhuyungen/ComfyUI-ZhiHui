"""
智绘灵箱 - 图片反推节点（增强版）

功能：使用 AI 模型分析图片内容，生成描述文本（提示词）
参考Qwen3VL-DP优化，支持多种先进模型和量化选项

新增功能：
- 量化支持：4-bit、8-bit、FP16
- 预设提示词：6种常用场景
- 多图输入：支持最多4张图片同时输入（Qwen模型）
- 视频输入：支持视频帧序列分析（Qwen模型）
- 设备选择：auto、cuda、cpu、mps
- TF32加速：支持Ampere及以上架构GPU
- 种子控制：随机、固定、递增模式
- Qwen3VL额外选项：支持连接Qwen3VL额外选项节点
- 参数命名与Qwen3VL-DP保持一致
"""
import torch
import numpy as np
from PIL import Image
import os
import sys
import logging
import json
import time
import random
import folder_paths
from pathlib import Path
from enum import Enum

# 尝试导入transformers
try:
    from transformers import (
        BlipProcessor, BlipForConditionalGeneration,
        Blip2Processor, Blip2ForConditionalGeneration,
        AutoModelForImageTextToText, AutoProcessor, AutoTokenizer,
        BitsAndBytesConfig
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ [智绘反推] transformers 库未安装，请运行: pip install transformers")

# 尝试导入HuggingFace Hub
try:
    from huggingface_hub import snapshot_download as hf_snapshot_download
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    print("⚠️ [智绘反推] huggingface_hub 未安装，无法自动下载模型")

# 尝试导入ModelScope
try:
    from modelscope.hub.snapshot_download import snapshot_download as ms_snapshot_download
    MODELSCOPE_AVAILABLE = True
except ImportError:
    ms_snapshot_download = None
    MODELSCOPE_AVAILABLE = False


# ==================== 量化选项 ====================

class Quantization(str, Enum):
    """量化选项枚举"""
    Q4_BIT = "4-bit (节省显存)"
    Q8_BIT = "8-bit (平衡)"
    NONE = "None (FP16)"

    @classmethod
    def get_values(cls):
        return [item.value for item in cls]


# ==================== 日志控制 ====================

class SuppressTransformersLogs:
    """上下文管理器：抑制transformers下载模型时的冗余日志"""

    def __enter__(self):
        # 保存原始输出
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # 抑制特定库的日志
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.WARNING)
        logging.getLogger('huggingface_hub').setLevel(logging.WARNING)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始输出
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        return False


# ==================== 辅助函数 ====================

def tensor2pil(image):
    """将 ComfyUI 的 tensor 转为 PIL Image"""
    if image.dim() == 4:
        image = image[0]
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def get_models_base_path():
    """获取模型基础路径 - 统一使用 ComfyUI/models/prompt_generator/ 目录"""
    try:
        models_dir = Path(folder_paths.models_dir) / "prompt_generator"
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir
    except Exception as e:
        print(f"⚠️ [智绘反推] 无法创建模型目录: {e}")
        # 回退到用户主目录
        fallback = Path.home() / ".cache" / "huggingface" / "hub"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def ensure_model_available(repo_id, source='huggingface'):
    """
    确保模型可用，支持HuggingFace和ModelScope两种来源

    Args:
        repo_id: 模型仓库ID
        source: 'huggingface' 或 'modelscope'

    Returns:
        模型路径（字符串）
    """
    models_base = get_models_base_path()
    model_folder_name = repo_id.split('/')[-1]
    model_path = models_base / model_folder_name

    # 检查模型是否已完整下载
    config_file = model_path / "config.json"
    model_file = model_path / "model.safetensors"
    model_index = model_path / "model.safetensors.index.json"

    if model_path.exists() and config_file.exists():
        if model_file.exists() or model_index.exists():
            print(f"✅ [智绘反推] 检测到已存在模型: {model_folder_name}")
            print(f"📁 [智绘反推] 模型路径: {model_path}")
            return str(model_path)
        else:
            print(f"⚠️ [智绘反推] 模型目录存在但文件不完整，将重新下载...")

    # 检查ModelScope是否可用
    if source == 'modelscope' and not MODELSCOPE_AVAILABLE:
        raise RuntimeError(
            f"模型来自 ModelScope，但 ModelScope 库未安装。\n"
            f"请运行: pip install modelscope\n"
            f"或手动下载模型到: {model_path}"
        )

    print(f"📥 [智绘反推] 正在从 {source.upper()} 下载模型到 {model_path}...")
    print("⏳ 首次下载可能需要较长时间，请耐心等待...")

    # 创建模型目录
    model_path.mkdir(parents=True, exist_ok=True)

    # 根据来源选择下载函数
    try:
        if source == 'modelscope':
            downloaded_path = ms_snapshot_download(
                model_id=repo_id,
                cache_dir=str(model_path.parent),
                local_dir=str(model_path),
            )
        else:
            downloaded_path = hf_snapshot_download(
                repo_id=repo_id,
                local_dir=str(model_path),
                local_dir_use_symlinks=False,
                ignore_patterns=["*.md", "*.txt", ".gitattributes"],
                resume_download=True,
                max_workers=4
            )
        print(f"✅ [智绘反推] 模型下载完成！路径: {model_path}")
        return str(model_path)
    except Exception as e:
        error_msg = f"模型下载失败: {str(e)}\n"
        if source == 'modelscope':
            error_msg += f"建议：手动从 https://modelscope.cn/models/{repo_id} 下载到: {model_path}"
        else:
            error_msg += f"建议：设置 HF_ENDPOINT 环境变量或手动从 https://huggingface.co/{repo_id} 下载到: {model_path}"
        raise RuntimeError(error_msg)


# ==================== 模型配置 ====================

# 预设提示词（与Qwen3VL-DP保持一致）
PRESET_PROMPTS = {
    "提示词风格 - 标签": "你的任务是为文生图AI生成一个简洁的逗号分隔标签列表，仅基于图像中的视觉信息。限制输出最多50个唯一标签。严格描述视觉元素，如主体、服装、环境、颜色、光照和构图。不要包含抽象概念、解释、营销术语或技术术语。目标是一个简洁的视觉描述符列表。避免重复标签。",
    "提示词风格 - 简单": "分析图像并生成一个简单的单句文生图提示词。简洁地描述主要主体和场景。",
    "提示词风格 - 详细": "基于图像生成一个详细的艺术性文生图提示词。将主体、动作、环境、光照和整体氛围组合成一个连贯的段落，约2-3句话。关注关键视觉细节。",
    "提示词风格 - 极致详细": "从图像生成一个极其详细和描述性的文生图提示词。创建一个丰富的段落，详细阐述主体的外观、服装纹理、具体背景元素、光线的质量和颜色、阴影以及整体氛围。追求高度描述性和沉浸式的提示词。",
    "提示词风格 - 电影感": "作为一个大师级提示词工程师。为图像生成AI创建一个高度详细和富有感染力的提示词。描述主体、姿势、环境、光照、情绪和艺术风格（如照片写实、电影感、绘画风格）。将所有元素编织成一个自然语言段落，专注于视觉冲击力。",
}

# ==================== 模型扫描和配置 ====================

def scan_local_models():
    """
    扫描本地 prompt_generator 目录中的模型
    自动识别模型类型并生成配置
    """
    models_base = get_models_base_path()
    local_models = {}

    if not models_base.exists():
        return local_models

    print(f"[智绘反推] 扫描模型目录: {models_base}")

    # 遍历目录中的所有子文件夹
    for model_dir in models_base.iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name
        config_file = model_dir / "config.json"

        # 检查是否有config.json
        if not config_file.exists():
            continue

        try:
            # 读取config.json识别模型类型
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            model_type = None
            architectures = config.get("architectures", [])

            # 根据架构识别模型类型
            if architectures:
                arch = architectures[0].lower()
                if "blip2" in arch:
                    model_type = "blip2"
                elif "blip" in arch:
                    model_type = "blip"
                elif "qwen2vl" in arch or "qwen3vl" in arch:
                    model_type = "qwen"

            # 如果无法从架构识别，尝试从模型名称识别
            if not model_type:
                name_lower = model_name.lower()
                if "blip2" in name_lower or "blip-2" in name_lower:
                    model_type = "blip2"
                elif "blip" in name_lower:
                    model_type = "blip"
                elif "qwen" in name_lower:
                    model_type = "qwen"

            if model_type:
                # 直接使用模型名称作为显示名称
                display_name = model_name

                local_models[f"LOCAL_{model_name}"] = {
                    "display_name": display_name,
                    "repo_id": str(model_dir),  # 使用本地路径
                    "model_type": model_type,
                    "vram": "~?GB",
                    "source": "local",
                }
                print(f"   ✅ 发现本地模型: {model_name} (类型: {model_type})")

        except Exception as e:
            print(f"   ⚠️ 跳过 {model_name}: {e}")
            continue

    if local_models:
        print(f"[智绘反推] 找到 {len(local_models)} 个本地模型")

    return local_models


# 预定义的模型配置（用于下载）
PREDEFINED_MODEL_CONFIGS = {
    "ZH_BLIP_Large": {
        "display_name": "BLIP-Large (推荐-精度高)",
        "repo_id": "Salesforce/blip-image-captioning-large",
        "model_type": "blip",
        "vram": "~2GB",
        "source": "huggingface",
    },
    "ZH_BLIP_Base": {
        "display_name": "BLIP-Base (快速-精度中)",
        "repo_id": "Salesforce/blip-image-captioning-base",
        "model_type": "blip",
        "vram": "~1GB",
        "source": "huggingface",
    },
    "ZH_BLIP2_2.7B": {
        "display_name": "BLIP2-2.7B (强-显存需3GB+)",
        "repo_id": "Salesforce/blip2-opt-2.7b",
        "model_type": "blip2",
        "vram": "~5GB",
        "source": "huggingface",
    },
    "ZH_Qwen2VL_2B": {
        "display_name": "Qwen2-VL-2B (高性能)",
        "repo_id": "Qwen/Qwen2-VL-2B-Instruct",
        "model_type": "qwen",
        "vram": "~4GB",
        "source": "huggingface",
    },
    "ZH_Qwen2VL_7B": {
        "display_name": "Qwen2-VL-7B (超强理解)",
        "repo_id": "Qwen/Qwen2-VL-7B-Instruct",
        "model_type": "qwen",
        "vram": "~14GB",
        "source": "huggingface",
    },
}

# 合并本地模型和预定义模型
def get_all_models():
    """获取所有可用模型（本地+预定义）"""
    all_models = {}

    # 先加载本地模型
    local_models = scan_local_models()
    all_models.update(local_models)

    # 再加载预定义模型
    all_models.update(PREDEFINED_MODEL_CONFIGS)

    return all_models

# 初始化模型配置
MODEL_CONFIGS = get_all_models()


# ==================== 主节点 ====================

class ZH_ImageCaptioning:
    """
    智绘图片反推节点（增强版）

    支持功能：
    - 多种模型：BLIP、BLIP2、Qwen2-VL系列
    - 量化支持：4-bit、8-bit、FP16
    - 预设提示词：6种常用场景
    - 多图输入：支持最多4张图片同时输入（Qwen模型）
    - 视频输入：支持视频帧序列分析（Qwen模型）
    - 自定义参数：温度、束搜索、最大长度等
    - 种子控制：随机、固定、递增模式
    - 设备选择：auto、cuda、cpu、mps
    - TF32加速：支持Ampere及以上架构GPU加速
    - Qwen3VL额外选项：支持连接Qwen3VL额外选项节点

    参数名称与Qwen3VL-DP保持一致

    模型存储：ComfyUI/models/prompt_generator/

    注意事项：
    - BLIP/BLIP2模型只支持单张图片输入
    - Qwen模型支持多图和视频输入
    - 至少需要输入一张图片或视频
    """

    def __init__(self):
        self.processor = None
        self.model = None
        self.tokenizer = None
        self.current_model_id = None
        self.current_quantization = None
        self.current_device = None
        self.last_seed = -1

    @classmethod
    def INPUT_TYPES(cls):
        model_names = [cfg["display_name"] for cfg in MODEL_CONFIGS.values()]
        preset_names = list(PRESET_PROMPTS.keys())

        return {
            "required": {
                "🤖 模型选择": (model_names, {
                    "default": "BLIP-Large (推荐-精度高)",
                    "tooltip": "选择图片理解模型"
                }),
                "⚙️ 量化级别": (list(Quantization.get_values()), {
                    "default": Quantization.NONE,
                    "tooltip": "量化级别，降低显存占用"
                }),
                "💭 预设提示词": (preset_names, {
                    "default": "提示词风格 - 详细",
                    "tooltip": "选择预设的提示词模板"
                }),
                "✏️ 自定义提示词": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "【可选】输入自定义提示词，留空则使用预设提示词"
                }),
                "🔢 最大令牌数": ("INT", {
                    "default": 1234,
                    "min": 64,
                    "max": 4096,
                    "step": 16,
                    "tooltip": "生成文本的最大令牌数"
                }),
                "🌡️ 采样温度": ("FLOAT", {
                    "default": 0.6,
                    "min": 0.1,
                    "max": 1.0,
                    "step": 0.1,
                    "tooltip": "创造性控制，值越高越随机"
                }),
                "🎯 核采样参数": ("FLOAT", {
                    "default": 0.9,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "核采样参数"
                }),
                "🔍 束搜索数量": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "tooltip": "束搜索数量，值越大越准确但越慢"
                }),
                "🚫 重复惩罚": ("FLOAT", {
                    "default": 1.2,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.01,
                    "tooltip": "重复惩罚，防止生成重复内容"
                }),
                "🎬 视频帧数": ("INT", {
                    "default": 16,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "tooltip": "视频帧数（用于视频输入的采样）"
                }),
                "💻 设备选择": (["auto", "cuda", "cpu", "mps"], {
                    "default": "auto",
                    "tooltip": "设备选择"
                }),
                "🚀 开启TF32加速": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "启用TF32加速（仅支持Ampere及以上架构显卡，如30/40/50系，能显著提升速度）"
                }),
                "🔄 保持模型加载": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否保持模型加载（推荐开启）"
                }),
                "🎲 随机种子": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff,
                    "tooltip": "随机种子，-1为随机"
                }),
                "🎯 种子控制": (["随机", "固定", "递增"], {
                    "default": "随机",
                    "tooltip": "种子控制模式"
                }),
            },
            "optional": {
                "🖼️ 图像1": ("IMAGE", {
                    "tooltip": "输入图片1"
                }),
                "🖼️ 图像2": ("IMAGE", {
                    "tooltip": "输入图片2"
                }),
                "🖼️ 图像3": ("IMAGE", {
                    "tooltip": "输入图片3"
                }),
                "🖼️ 图像4": ("IMAGE", {
                    "tooltip": "输入图片4"
                }),
                "🎥 视频": ("IMAGE", {
                    "tooltip": "视频输入（作为图像序列）"
                }),
                "🎯 Qwen3VL额外选项": ("QWEN3VL_EXTRA_OPTIONS", {
                    "tooltip": "可选的Qwen3VL额外选项，连接Qwen3VL额外选项节点"
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("描述文本",)
    FUNCTION = "generate_caption"
    CATEGORY = "智绘灵箱/图片"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        seed_control = kwargs.get("🎯 种子控制", "随机")
        seed = kwargs.get("🎲 随机种子", -1)

        # 随机和递增模式下，强制更新
        if seed_control in ["随机", "递增"]:
            return float("nan")

        # 固定模式下，仅当种子值变化时更新
        return seed

    def generate_caption(self, **kwargs):
        """生成图片描述 - 使用kwargs处理带emoji的参数名"""

        start_time = time.time()

        # 提取参数（兼容带emoji的参数名）
        模型选择 = kwargs.get("🤖 模型选择")
        量化级别 = kwargs.get("⚙️ 量化级别")
        预设提示词 = kwargs.get("💭 预设提示词")
        自定义提示词 = kwargs.get("✏️ 自定义提示词", "")
        最大令牌数 = kwargs.get("🔢 最大令牌数")
        采样温度 = kwargs.get("🌡️ 采样温度")
        核采样参数 = kwargs.get("🎯 核采样参数")
        束搜索数量 = kwargs.get("🔍 束搜索数量")
        重复惩罚 = kwargs.get("🚫 重复惩罚")
        视频帧数 = kwargs.get("🎬 视频帧数", 16)
        设备选择 = kwargs.get("💻 设备选择", "auto")
        开启TF32加速 = kwargs.get("🚀 开启TF32加速", False)
        保持模型加载 = kwargs.get("🔄 保持模型加载", True)
        随机种子 = kwargs.get("🎲 随机种子", -1)
        种子控制 = kwargs.get("🎯 种子控制", "随机")

        # 可选输入
        图像1 = kwargs.get("🖼️ 图像1")
        图像2 = kwargs.get("🖼️ 图像2")
        图像3 = kwargs.get("🖼️ 图像3")
        图像4 = kwargs.get("🖼️ 图像4")
        视频 = kwargs.get("🎥 视频")
        extra_options = kwargs.get("🎯 Qwen3VL额外选项")

        if not TRANSFORMERS_AVAILABLE:
            error_msg = "❌ transformers 库未安装\n请运行: pip install transformers accelerate"
            print(error_msg)
            return (error_msg,)

        # 检查是否有输入
        input_images = [图像1, 图像2, 图像3, 图像4]
        has_images = any(img is not None for img in input_images)
        has_video = 视频 is not None

        if not has_images and not has_video:
            error_msg = "❌ 请至少输入一张图片或视频"
            print(error_msg)
            return (error_msg,)

        # 设置 TF32 加速
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = 开启TF32加速
            torch.backends.cudnn.allow_tf32 = 开启TF32加速
            if 开启TF32加速:
                print("🚀 [智绘反推] 已开启 TF32 加速模式")

        # 处理种子
        if 种子控制 == "固定":
            effective_seed = 随机种子 if 随机种子 != -1 else random.randint(0, 2147483647)
        elif 种子控制 == "随机":
            effective_seed = random.randint(0, 2147483647)
        elif 种子控制 == "递增":
            if self.last_seed == -1:
                effective_seed = 随机种子 if 随机种子 != -1 else random.randint(0, 2147483647)
            else:
                effective_seed = self.last_seed + 1
        else:
            effective_seed = random.randint(0, 2147483647)

        self.last_seed = effective_seed
        print(f"🎲 [智绘反推] 使用随机种子: {effective_seed} (模式: {种子控制})")
        torch.manual_seed(effective_seed)

        # 查找模型配置
        model_config = None
        model_id = None
        for mid, cfg in MODEL_CONFIGS.items():
            if cfg["display_name"] == 模型选择:
                model_config = cfg
                model_id = mid
                break

        if not model_config:
            return (f"❌ 未找到模型配置: {模型选择}",)

        try:
            # 检查是否需要加载新模型
            if (self.model is None or
                self.current_model_id != model_id or
                self.current_quantization != 量化级别 or
                self.current_device != 设备选择):

                models_base = get_models_base_path()
                print(f"📦 [智绘反推] 模型存储路径: {models_base}")
                print(f"🔄 [智绘反推] 加载模型: {模型选择}")
                print(f"   量化级别: {量化级别}")
                print(f"   设备选择: {设备选择}")
                print(f"   显存需求: {model_config['vram']}")
                print(f"   首次使用将自动下载，请稍候...")

                load_start = time.time()
                with SuppressTransformersLogs():
                    self._load_model(model_config, 量化级别, models_base, 设备选择)
                load_time = time.time() - load_start

                self.current_model_id = model_id
                self.current_quantization = 量化级别
                self.current_device = 设备选择
                print(f"✅ [智绘反推] 模型加载成功，耗时: {load_time:.2f}秒")

            # 确定使用的提示词
            if 自定义提示词 and 自定义提示词.strip():
                prompt_text = 自定义提示词.strip()
                print(f"💭 [智绘反推] 使用自定义提示词")
            else:
                prompt_text = PRESET_PROMPTS.get(预设提示词, PRESET_PROMPTS["提示词风格 - 详细"])
                print(f"💭 [智绘反推] 使用预设提示词: {预设提示词}")

            # 应用Qwen3VL额外选项增强提示词（如果有的话）
            if extra_options:
                try:
                    import qwen3vl_extra_options
                    prompt_text = qwen3vl_extra_options.Qwen3VL_ExtraOptions.build_enhanced_prompt(prompt_text, extra_options)
                    print(f"✅ [智绘反推] 已应用Qwen3VL额外选项增强提示词")
                except (ImportError, AttributeError) as e:
                    print(f"⚠️ [智绘反推] 警告: 无法导入Qwen3VL额外选项模块 ({e})，使用基础提示词")

            # 根据模型类型处理
            model_type = model_config["model_type"]

            if model_type in ["blip", "blip2"]:
                # BLIP系列只支持单张图片，取第一张非空图片
                first_image = None
                for img in input_images:
                    if img is not None:
                        # 如果是批次，取第一张
                        first_image = img[0] if img.shape[0] > 1 else img
                        break

                if first_image is None and has_video:
                    # 如果没有图片但有视频，取视频第一帧
                    first_image = 视频[0] if 视频.shape[0] > 1 else 视频

                if first_image is None:
                    return ("❌ BLIP模型需要至少一张图片输入",)

                pil_image = tensor2pil(first_image)
                caption = self._process_blip(
                    pil_image, prompt_text, 最大令牌数, 束搜索数量,
                    采样温度, 重复惩罚
                )
                print(f"✅ [智绘反推] 处理完成")
                final_output = caption

            elif model_type == "qwen":
                # Qwen模型支持多图和视频
                caption = self._process_qwen_multi(
                    input_images, 视频, prompt_text, 最大令牌数,
                    采样温度, 核采样参数, 重复惩罚, 视频帧数
                )
                print(f"✅ [智绘反推] 处理完成")
                final_output = caption

            else:
                final_output = "不支持的模型类型"

            total_time = time.time() - start_time
            print(f"🎉 [智绘反推] 总耗时: {total_time:.2f}秒")

            # 根据设置决定是否卸载模型
            if not 保持模型加载:
                self._unload_model()

            return (final_output,)

        except Exception as e:
            error_msg = f"❌ [智绘反推] 处理失败: {str(e)}\n\n可能原因:\n1. 模型未下载完成\n2. 显存不足\n3. 网络连接问题"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return (error_msg,)

    def _load_model(self, model_config, quantization, models_base, device_choice="auto"):
        """加载模型 - 支持量化和设备选择"""
        model_type = model_config["model_type"]
        repo_id = model_config["repo_id"]
        source = model_config.get("source", "huggingface")

        # 设备选择逻辑
        if device_choice == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        else:
            device = device_choice

        print(f"💻 [智绘反推] 使用设备: {device}")

        # 确保模型可用
        model_path = ensure_model_available(repo_id, source)

        # 配置量化
        quant_config = None
        load_dtype = torch.float16 if device == "cuda" else torch.float32

        if device == "cuda":
            if quantization == Quantization.Q4_BIT:
                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
                load_dtype = None
            elif quantization == Quantization.Q8_BIT:
                quant_config = BitsAndBytesConfig(load_in_8bit=True)
                load_dtype = None

        # 加载模型
        if model_type == "blip":
            self.processor = BlipProcessor.from_pretrained(model_path)
            if quant_config:
                self.model = BlipForConditionalGeneration.from_pretrained(
                    model_path,
                    quantization_config=quant_config,
                    device_map="auto"
                )
            else:
                self.model = BlipForConditionalGeneration.from_pretrained(
                    model_path,
                    torch_dtype=load_dtype
                ).to(device)

        elif model_type == "blip2":
            self.processor = Blip2Processor.from_pretrained(model_path)
            if quant_config:
                self.model = Blip2ForConditionalGeneration.from_pretrained(
                    model_path,
                    quantization_config=quant_config,
                    device_map="auto"
                )
            else:
                self.model = Blip2ForConditionalGeneration.from_pretrained(
                    model_path,
                    torch_dtype=load_dtype
                ).to(device)

        elif model_type == "qwen":
            if not HUGGINGFACE_AVAILABLE:
                raise RuntimeError("Qwen模型需要安装: pip install huggingface_hub")

            self.processor = AutoProcessor.from_pretrained(
                model_path,
                trust_remote_code=True
            )

            load_kwargs = {
                "torch_dtype": load_dtype,
                "trust_remote_code": True
            }

            if quant_config:
                load_kwargs["quantization_config"] = quant_config
                load_kwargs["device_map"] = "auto"

            self.model = AutoModelForImageTextToText.from_pretrained(
                model_path,
                **load_kwargs
            )

            if not quant_config:
                self.model.to(device)

            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
            except:
                self.tokenizer = None

        self.model.eval()
        print(f"✅ 模型已加载到设备: {device if not quant_config else 'auto(量化)'}")

    def _unload_model(self):
        """卸载模型以释放显存"""
        print("🗑️  [智绘反推] 释放模型资源...")
        if self.model is not None:
            del self.model
            self.model = None
        if self.processor is not None:
            del self.processor
            self.processor = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        self.current_model_id = None
        self.current_quantization = None
        self.current_device = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _process_blip(self, pil_image, prompt_text, max_tokens, num_beams,
                     temperature, repetition_penalty):
        """处理BLIP/BLIP2模型"""
        device = next(self.model.parameters()).device

        # 处理输入
        inputs = self.processor(pil_image, text=prompt_text, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # 生成描述
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_tokens,
                num_beams=num_beams,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                do_sample=temperature > 1.0,
            )

        caption = self.processor.decode(outputs[0], skip_special_tokens=True)
        return caption

    def _process_qwen(self, pil_image, prompt_text, max_tokens, temperature,
                     top_p, repetition_penalty):
        """处理Qwen模型（单图）"""
        device = next(self.model.parameters()).device

        # 构建对话
        conversation = [{
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image},
                {"type": "text", "text": prompt_text}
            ]
        }]

        # 应用聊天模板
        text_prompt = self.processor.apply_chat_template(
            conversation,
            tokenize=False,
            add_generation_prompt=True
        )

        # 处理输入
        inputs = self.processor(
            text=text_prompt,
            images=[pil_image],
            return_tensors="pt"
        )

        inputs = {k: v.to(device) for k, v in inputs.items() if torch.is_tensor(v)}

        # 设置停止标记
        stop_tokens = []
        if self.tokenizer:
            stop_tokens = [self.tokenizer.eos_token_id]
            if hasattr(self.tokenizer, 'eot_id'):
                stop_tokens.append(self.tokenizer.eot_id)

        # 生成文本
        with torch.no_grad():
            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "do_sample": True,
            }

            if stop_tokens:
                gen_kwargs["eos_token_id"] = stop_tokens

            outputs = self.model.generate(**inputs, **gen_kwargs)

        input_len = inputs["input_ids"].shape[1]
        caption = self.processor.decode(outputs[0, input_len:], skip_special_tokens=True)
        return caption

    def _process_qwen_multi(self, input_images, video, prompt_text, max_tokens,
                           temperature, top_p, repetition_penalty, video_frames):
        """处理Qwen模型（多图/视频）"""
        device = next(self.model.parameters()).device

        # 构建对话内容
        conversation = [{"role": "user", "content": []}]

        # 添加多个图像
        pil_images = []
        for i, image in enumerate(input_images, 1):
            if image is not None:
                # 如果是批次，取第一张
                img_tensor = image[0] if image.shape[0] > 1 else image
                pil_img = tensor2pil(img_tensor)
                pil_images.append(pil_img)
                conversation[0]["content"].append({
                    "type": "image",
                    "image": pil_img
                })
                print(f"   - 添加图像{i}")

        # 添加视频（作为多帧图像序列）
        if video is not None:
            video_frames_list = [
                Image.fromarray((frame.cpu().numpy() * 255).astype(np.uint8))
                for frame in video
            ]

            # 采样视频帧
            if len(video_frames_list) > video_frames:
                indices = np.linspace(0, len(video_frames_list) - 1, video_frames, dtype=int)
                sampled_frames = [video_frames_list[i] for i in indices]
            else:
                sampled_frames = video_frames_list

            # 确保至少有2帧（Qwen3-VL 要求）
            if sampled_frames and len(sampled_frames) == 1:
                sampled_frames.append(sampled_frames[0])

            if sampled_frames:
                conversation[0]["content"].append({
                    "type": "video",
                    "video": sampled_frames
                })
                print(f"   - 添加视频（{len(sampled_frames)}帧）")

        # 添加文本提示
        conversation[0]["content"].append({
            "type": "text",
            "text": prompt_text
        })

        # 应用聊天模板
        text_prompt = self.processor.apply_chat_template(
            conversation,
            tokenize=False,
            add_generation_prompt=True
        )

        # 提取图像和视频用于处理器
        video_frames_list = []
        for item in conversation[0]['content']:
            if item['type'] == 'video':
                video_frames_list = item['video']
                break
        videos_arg = [video_frames_list] if video_frames_list else None

        # 处理输入
        inputs = self.processor(
            text=text_prompt,
            images=pil_images if pil_images else None,
            videos=videos_arg,
            return_tensors="pt"
        )

        # 将输入移到设备
        inputs = {k: v.to(device) for k, v in inputs.items() if torch.is_tensor(v)}

        # 设置停止标记
        stop_tokens = []
        if self.tokenizer:
            stop_tokens = [self.tokenizer.eos_token_id]
            if hasattr(self.tokenizer, 'eot_id'):
                stop_tokens.append(self.tokenizer.eot_id)

        # 生成文本
        with torch.no_grad():
            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "do_sample": True,
            }

            if stop_tokens:
                gen_kwargs["eos_token_id"] = stop_tokens

            outputs = self.model.generate(**inputs, **gen_kwargs)

        input_len = inputs["input_ids"].shape[1]
        caption = self.processor.decode(outputs[0, input_len:], skip_special_tokens=True)
        return caption


# 注册节点
NODE_CLASS_MAPPINGS = {
    "ZH_ImageCaptioning": ZH_ImageCaptioning,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_ImageCaptioning": "🎨 智绘_图片反推",
}
