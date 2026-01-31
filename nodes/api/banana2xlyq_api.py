import torch
import numpy as np
import requests
import json
import base64
from PIL import Image
from io import BytesIO
import urllib3
import math
import time

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

# ==============================================================================
# Gemini 3 Pro (香蕉) - V17 增强版 (Session复用 + 详细输出 + 错误分类)
# ==============================================================================

class ZH_BananaVectorAPI:
    def __init__(self):
        # ★ 关键改进 1: Session 复用
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "base_url": ("STRING", {"multiline": False, "default": "https://api.vectorengine.ai"}),
                "api_key": ("STRING", {"multiline": False, "default": "", "placeholder": "填入 API Key"}),
                "prompt": ("STRING", {"multiline": True, "default": "A cute futuristic cat, 8k resolution, cinematic lighting"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "aspect_ratio": ([
                    "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "Auto (From Image)"
                ], {"default": "1:1"}),
                "resolution": (["1K (Default)", "2K", "4K"], {"default": "1K (Default)"}),
                # ★ 关键改进 5: 可调节图片质量
                "image_quality": ("INT", {"default": 90, "min": 60, "max": 100, "step": 5, "tooltip": "JPEG压缩质量 (60-100)"}),
            },
            "optional": {
                "ref_image1": ("IMAGE",),
                "ref_image2": ("IMAGE",),
                "ref_image3": ("IMAGE",),
                "ref_image4": ("IMAGE",),
            }
        }

    # ★ 关键改进 2: 返回详细信息和格式化显示
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("生成图片", "详细信息", "智绘显示")
    FUNCTION = "generate_image"
    CATEGORY = "智绘灵箱/API"
    OUTPUT_NODE = True  # 标记为输出节点

    def generate_image(self, base_url, api_key, prompt, seed, aspect_ratio, resolution, image_quality=90,
                      ref_image1=None, ref_image2=None, ref_image3=None, ref_image4=None):

        # ★ 关键改进 3: API Key 验证
        if not api_key or api_key.strip() == "":
            error_msg = "API Key 不能为空！请在 api_key 参数中填入您的密钥"
            print(f"❌ [智绘向量引擎] {error_msg}")
            error_img = Image.new('RGB', (512, 512), color=(128, 0, 0))
            error_display = f"""
╔══════════════════════════════════════════════════════════════
║ 🍌 智绘向量引擎 - 配置错误
╠══════════════════════════════════════════════════════════════
║ ❌ 状态: API Key 缺失
╠══════════════════════════════════════════════════════════════
║ 💡 解决方法:
║ 1. 在节点的 api_key 参数中填入您的密钥
║ 2. 请从 vectorengine.ai 获取有效密钥
║ 3. 确保密钥有足够余额
╚══════════════════════════════════════════════════════════════
"""
            return (pil2tensor(error_img), error_msg, error_display)

        # --- 1. 参数准备 ---
        base_url = base_url.rstrip('/')
        endpoint = f"{base_url}/v1beta/models/gemini-3-pro-image-preview:generateContent"

        # ★★★ 关键点 1: 强制短连接 (Connection: close) ★★★
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Connection': 'close'
        })

        # 自动比例逻辑
        final_aspect_ratio = aspect_ratio
        if aspect_ratio == "Auto (From Image)":
            if ref_image1 is not None:
                h = ref_image1.shape[1]
                w = ref_image1.shape[2]
                ratio = w / h
                ratios = {"1:1": 1.0, "16:9": 1.777, "9:16": 0.562, "4:3": 1.333, "3:4": 0.75, "3:2": 1.5, "2:3": 0.666}
                final_aspect_ratio = min(ratios.keys(), key=lambda x: abs(ratios[x] - ratio))
            else:
                final_aspect_ratio = "1:1"

        # ★ 关键改进 6: 压缩统计
        total_size_before = 0
        total_size_after = 0

        def process_image(img_tensor):
            nonlocal total_size_before, total_size_after
            if img_tensor is not None:
                pil_img = tensor2pil(img_tensor)

                # 记录原始大小
                original_bytes = pil_img.size[0] * pil_img.size[1] * 3
                total_size_before += original_bytes

                buffered = BytesIO()
                pil_img.save(buffered, format="JPEG", quality=image_quality)
                compressed_bytes = buffered.getvalue()
                total_size_after += len(compressed_bytes)

                img_str = base64.b64encode(compressed_bytes).decode("utf-8")
                return {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}
            return None

        parts = [{"text": prompt}]
        ref_images = [ref_image1, ref_image2, ref_image3, ref_image4]
        ref_count = 0
        for img in ref_images:
            processed = process_image(img)
            if processed:
                parts.append(processed)
                ref_count += 1

        # 显示总压缩统计
        if total_size_before > 0:
            total_compression = (1 - total_size_after / total_size_before) * 100
            print(f"📊 [压缩统计] 总计: {total_size_before//1024}KB -> {total_size_after//1024}KB (节省 {total_compression:.1f}%)")

        image_config = {"aspectRatio": final_aspect_ratio}
        if resolution == "4K": image_config["imageSize"] = "4K"
        elif resolution == "2K": image_config["imageSize"] = "2K"

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": image_config
            }
        }

        print(f"🍌 [智绘向量引擎] 发送请求... (超时: 300秒, 参考图: {ref_count}张)")

        error_type = "unknown"  # ★ 关键改进 4: 错误分类

        try:
            # ★★★ 关键点 2: 移除代理限制 + 超长超时 ★★★
            response = self.session.post(
                f"{endpoint}?key={api_key}",
                data=json.dumps(payload),
                timeout=300,
                verify=False
            )

            if response.status_code != 200:
                error_type = "api_error"
                raise Exception(f"HTTP Error {response.status_code}: {response.text[:200]}")

            # 解析逻辑
            result = response.json()
            img_data = None

            # 策略 A: Gemini 格式
            try:
                candidates = result.get('candidates', [])
                if candidates:
                    parts_list = candidates[0].get('content', {}).get('parts', [])
                    for part in parts_list:
                        data_obj = part.get('inline_data') or part.get('inlineData')
                        if data_obj and 'data' in data_obj:
                            img_data = base64.b64decode(data_obj['data'])
                            break
            except: pass

            # 策略 B: OpenAI 格式
            if not img_data:
                if 'data' in result and isinstance(result['data'], list):
                    item = result['data'][0]
                    if 'b64_json' in item:
                        b64_str = item['b64_json']
                        if "," in b64_str[:50]: b64_str = b64_str.split(",", 1)[1]
                        img_data = base64.b64decode(b64_str)

            # 策略 C: URL 格式
            if not img_data:
                url = None
                if 'data' in result and isinstance(result['data'], list) and 'url' in result['data'][0]:
                    url = result['data'][0]['url']
                if url:
                    print(f"🔗 下载 URL: {url}")
                    img_data = self.session.get(url, timeout=60, verify=False).content

            if not img_data:
                error_type = "parse_error"
                raise Exception("解析图片失败，API可能返回了纯文本错误或JSON结构变更")

            output_image = Image.open(BytesIO(img_data))
            print(f"✅ 生成成功! 尺寸: {output_image.size}")

            # 生成详细信息
            compression_info = f"压缩率: {total_compression:.1f}%" if total_size_before > 0 else "无压缩"
            info_text = f"Prompt: {prompt[:100]}...\nResolution: {resolution}\nAspect Ratio: {final_aspect_ratio}\n{compression_info}"

            # 生成智绘显示
            display_text = f"""
╔══════════════════════════════════════════════════════════════
║ 🍌 智绘向量引擎 - 生成完成
╠══════════════════════════════════════════════════════════════
║ 🎨 模型: gemini-3-pro-image-preview
║ 📐 分辨率: {resolution}
║ 📏 比例: {final_aspect_ratio}
║ 🎲 种子: {seed}
║ 🖼️  输出: {output_image.size[0]} x {output_image.size[1]} px
║ 📸 参考图片: {ref_count} 张
║ 🗜️  压缩质量: {image_quality}
║ 💾 压缩率: {total_compression:.1f}% ({total_size_before//1024}KB → {total_size_after//1024}KB)
╠══════════════════════════════════════════════════════════════
║ 📝 提示词:
║ {prompt[:150]}{'...' if len(prompt) > 150 else ''}
╠══════════════════════════════════════════════════════════════
║ ✅ 状态: 生成成功
║ 💰 提示: 无重试机制，仅一次计费
╚══════════════════════════════════════════════════════════════
"""

            return (pil2tensor(output_image), info_text, display_text)

        except requests.exceptions.Timeout:
            error_type = "timeout"
            error_msg = "请求超时：服务器响应时间过长 (超过300秒)"
            print(f"⏱️  {error_msg}")

        except requests.exceptions.ConnectionError as e:
            error_type = "network"
            error_msg = f"网络连接错误: {str(e)[:100]}"
            print(f"🌐 {error_msg}")

        except Exception as e:
            if error_type == "unknown":
                error_type = "general"
            error_msg = str(e)
            print(f"❌ 请求失败: {e}")

        # ★ 根据错误类型提供针对性建议
        print("💀 为防止重复计费，已停止重试。请检查网络或代理设置。")

        suggestions = {
            "timeout": """║ 💡 建议:
║ 1. 模型处理时间过长（已超过5分钟）
║ 2. 尝试减少参考图片数量
║ 3. 检查 vectorengine.ai 服务状态
║ 4. 降低分辨率设置（4K→2K→1K）""",
            "network": """║ 💡 建议:
║ 1. 检查网络连接是否正常
║ 2. 检查 base_url 地址是否正确
║ 3. 如在中国大陆，需配置代理访问
║ 4. 检查防火墙设置""",
            "api_error": """║ 💡 建议:
║ 1. 检查 API Key 是否正确且有效
║ 2. 检查账户余额是否充足
║ 3. 检查 base_url 是否正确
║ 4. 查看上方 HTTP 状态码获取详情""",
            "parse_error": """║ 💡 建议:
║ 1. API 返回了异常数据格式
║ 2. vectorengine.ai 可能更新了接口
║ 3. 查看控制台完整错误日志
║ 4. 联系 API 提供商确认接口格式""",
            "general": """║ 💡 建议:
║ 1. 查看控制台完整错误日志
║ 2. 检查输入参数是否正确
║ 3. 尝试使用默认参数重新运行
║ 4. 如果问题持续，请报告此错误"""
        }

        suggestion_text = suggestions.get(error_type, suggestions["general"])

        # ★ 关键改进 7: 红色错误图片，更易识别
        error_img = Image.new('RGB', (512, 512), color=(128, 0, 0))
        error_info = f"Error ({error_type}): {error_msg}"

        error_display = f"""
╔══════════════════════════════════════════════════════════════
║ 🍌 智绘向量引擎 - 生成失败
╠══════════════════════════════════════════════════════════════
║ ❌ 状态: 失败 (类型: {error_type})
║ 🔄 重试: 已禁用（防止重复计费）
╠══════════════════════════════════════════════════════════════
║ 📝 错误信息:
║ {error_msg[:200]}
╠══════════════════════════════════════════════════════════════
{suggestion_text}
╚══════════════════════════════════════════════════════════════
"""

        return (pil2tensor(error_img), error_info, error_display)

NODE_CLASS_MAPPINGS = {
    "ZH_BananaVectorAPI": ZH_BananaVectorAPI
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_BananaVectorAPI": "🍌 智绘_banana2_向量引擎api (增强版)"
}
