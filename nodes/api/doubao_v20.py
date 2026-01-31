import torch
import numpy as np
import requests
import json
import base64
from PIL import Image
from io import BytesIO
import urllib3
import math

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

# ==============================================================================
# 豆包 (Doubao) 模型节点 - V21 高清增强版 (智能分辨率 + 全功能优化)
# ==============================================================================

print("\n" + "="*40)
print("🥟 智绘豆包 V21 (高清增强版) 已加载！")
print("="*40 + "\n")

class ZH_DoubaoImageGen:
    def __init__(self):
        # ★ 关键改进 1: Session 复用，提升性能
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "base_url": ("STRING", {"multiline": False, "default": "https://api.vectorengine.ai/v1"}),
                "api_key": ("STRING", {"multiline": False, "default": "", "placeholder": "填入 API Key"}),
                "model": (["doubao-seedream-4-5-251128", "doubao-seedream-4-0"], {"default": "doubao-seedream-4-5-251128"}),
                "prompt": ("STRING", {"multiline": True, "default": "Generate a cute 3D character"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "aspect_ratio": ([
                    "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9", "9:21"
                ], {"default": "1:1"}),
                # V21: 更清晰的说明
                "resolution": (["高清 (推荐)", "标清 (非融合模式)"], {"default": "高清 (推荐)"}),
                "generation_mode": ([
                    "多图融合/风格迁移 (disabled)",
                    "多图参考/故事模式 (auto)"
                ], {"default": "多图融合/风格迁移 (disabled)"}),
                # ★ 关键改进 5: 可调节图片质量
                "image_quality": ("INT", {"default": 95, "min": 60, "max": 100, "step": 5, "tooltip": "JPEG压缩质量 (60-100)"}),
            },
            "optional": {
                "ref_image1": ("IMAGE",),
                "ref_image2": ("IMAGE",),
                "ref_image3": ("IMAGE",),
            }
        }

    # ★ 关键改进 2: 返回详细信息和格式化显示
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("生成图片", "详细信息", "智绘显示")
    FUNCTION = "generate_doubao"
    CATEGORY = "智绘灵箱/API"
    OUTPUT_NODE = True  # 标记为输出节点

    def generate_doubao(self, base_url, api_key, model, prompt, seed, aspect_ratio, resolution, generation_mode, image_quality=95,
                       ref_image1=None, ref_image2=None, ref_image3=None):

        # ★ 关键改进 3: API Key 验证
        if not api_key or api_key.strip() == "":
            error_msg = "API Key 不能为空！请在 api_key 参数中填入您的密钥"
            print(f"❌ [智绘豆包] {error_msg}")
            error_img = Image.new('RGB', (512, 512), color=(128, 0, 0))
            error_display = f"""
╔══════════════════════════════════════════════════════════════
║ 🥟 智绘豆包 - 配置错误
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

        # 1. 地址处理
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/images/generations'):
            if base_url.endswith('/v1'):
                 endpoint = f"{base_url}/images/generations"
            else:
                 endpoint = f"{base_url}/v1/images/generations"
        else:
            endpoint = base_url

        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
        })

        # ★ 关键改进 6: 压缩统计
        total_size_before = 0
        total_size_after = 0

        # 2. 图片处理
        image_list = []
        def process_image(img_tensor):
            nonlocal total_size_before, total_size_after
            if img_tensor is not None:
                pil_img = tensor2pil(img_tensor)

                # 记录原始大小
                original_bytes = pil_img.size[0] * pil_img.size[1] * 3
                total_size_before += original_bytes

                if pil_img.mode != 'RGB': pil_img = pil_img.convert('RGB')

                max_side = 2048
                if max(pil_img.size) > max_side:
                    ratio = max_side / max(pil_img.size)
                    new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
                    pil_img = pil_img.resize(new_size, Image.LANCZOS)

                buffered = BytesIO()
                pil_img.save(buffered, format="JPEG", quality=image_quality)
                compressed_bytes = buffered.getvalue()
                total_size_after += len(compressed_bytes)

                img_str = base64.b64encode(compressed_bytes).decode("utf-8")
                return f"data:image/jpeg;base64,{img_str}"
            return None

        ref_images = [ref_image1, ref_image2, ref_image3]
        ref_count = 0
        for img in ref_images:
            processed = process_image(img)
            if processed:
                image_list.append(processed)
                ref_count += 1

        # 显示总压缩统计
        if total_size_before > 0:
            total_compression = (1 - total_size_after / total_size_before) * 100
            print(f"📊 [压缩统计] 总计: {total_size_before//1024}KB -> {total_size_after//1024}KB (节省 {total_compression:.1f}%)")

        # 3. 尺寸计算 (智能分辨率：确保 > 3.6M 像素以支持融合模式)
        size_map = {
            # 高清模式：所有尺寸 > 3.6M 像素，支持融合模式
            "高清 (推荐)": {
                "1:1":  "2048x2048", # 4.1M > 3.6M
                "16:9": "2688x1536", # 4.1M > 3.6M (加安全边距)
                "9:16": "1536x2688",
                "4:3":  "2304x1728", # 3.9M > 3.6M
                "3:4":  "1728x2304",
                "3:2":  "2496x1664", # 4.1M > 3.6M
                "2:3":  "1664x2496",
                "21:9": "2944x1280", # 3.7M > 3.6M
                "9:21": "1280x2944"
            },
            # 标清模式：仅供非融合模式使用
            "标清 (非融合模式)": {
                "1:1": "1024x1024", "16:9": "1536x864", "9:16": "864x1536",
                "4:3": "1280x960", "3:4": "960x1280", "3:2": "1280x853",
                "2:3": "853x1280", "21:9": "1792x768", "9:21": "768x1792"
            }
        }

        res_dict = size_map.get(resolution, size_map["高清 (推荐)"])
        final_size = res_dict.get(aspect_ratio, res_dict["1:1"])

        # 计算实际像素数
        w, h = map(int, final_size.split('x'))
        total_pixels = w * h
        pixels_m = total_pixels / 1_000_000

        print(f"🥟 [智绘豆包V21] 最终尺寸: {final_size} ({pixels_m:.1f}M像素)")

        # 4. 构造 Payload
        seq_mode = "disabled"
        seq_options = None
        if "auto" in generation_mode:
            seq_mode = "auto"
            seq_options = {"max_images": 3}

        # 种子安全限制
        safe_seed = seed % 2147483647

        payload = {
            "model": model,
            "prompt": prompt,
            "size": final_size,
            "sequential_image_generation": seq_mode,
            "response_format": "b64_json",
            "watermark": False,
            "seed": safe_seed
        }
        if seq_options: payload["sequential_image_generation_options"] = seq_options
        if image_list: payload["image"] = image_list

        error_type = "unknown"  # ★ 关键改进 4: 错误分类

        try:
            response = self.session.post(
                endpoint,
                data=json.dumps(payload),
                timeout=180,
                verify=False,
                proxies={"http": None, "https": None}
            )

            if response.status_code != 200:
                error_type = "api_error"
                print(f"❌ API 报错 ({response.status_code}): {response.text}")
                if response.status_code == 422 and "at least 3686400" in response.text:
                     print("💀 像素数不足！请使用'高清 (推荐)'模式")
                raise Exception(f"API Error {response.status_code}: {response.text[:200]}")

            result = response.json()
            output_tensors = []

            if 'data' in result and isinstance(result['data'], list):
                for item in result['data']:
                    b64_str = item.get('b64_json')
                    if b64_str:
                        if "," in b64_str[:50]: b64_str = b64_str.split(",", 1)[1]
                        try:
                            img_data = base64.b64decode(b64_str)
                            pil_img = Image.open(BytesIO(img_data))
                            output_tensors.append(pil2tensor(pil_img))
                        except Exception as e:
                            print(f"❌ 图片解码失败: {e}")

            if not output_tensors:
                error_type = "parse_error"
                raise Exception(f"API返回成功但无图片: {json.dumps(result)[:100]}")

            print(f"✅ [智绘豆包] 生成成功! 共 {len(output_tensors)} 张图片")

            # 生成详细信息
            compression_info = f"压缩率: {total_compression:.1f}%" if total_size_before > 0 else "无压缩"
            info_text = f"Model: {model}\nSize: {final_size} ({pixels_m:.1f}M像素)\nMode: {generation_mode}\n{compression_info}"

            # 生成智绘显示
            display_text = f"""
╔══════════════════════════════════════════════════════════════
║ 🥟 智绘豆包 - 生成完成
╠══════════════════════════════════════════════════════════════
║ 🎨 模型: {model}
║ 📐 尺寸: {final_size} ({pixels_m:.1f}M像素)
║ 📏 比例: {aspect_ratio}
║ 🎲 种子: {seed}
║ 🔄 生成模式: {generation_mode}
║ 📸 参考图片: {ref_count} 张
║ 🗜️  压缩质量: {image_quality}
║ 💾 压缩率: {total_compression:.1f}% ({total_size_before//1024}KB → {total_size_after//1024}KB)
║ 🖼️  输出: {len(output_tensors)} 张图片
╠══════════════════════════════════════════════════════════════
║ 📝 提示词:
║ {prompt[:150]}{'...' if len(prompt) > 150 else ''}
╠══════════════════════════════════════════════════════════════
║ ✅ 状态: 生成成功
║ 💡 提示: 使用'高清模式'支持所有功能
╚══════════════════════════════════════════════════════════════
"""

            # 返回结果
            if len(output_tensors) > 1:
                return (torch.cat(output_tensors, dim=0), info_text, display_text)
            else:
                return (output_tensors[0], info_text, display_text)

        except requests.exceptions.Timeout:
            error_type = "timeout"
            error_msg = "请求超时：服务器响应时间过长 (超过180秒)"
            print(f"⏱️  {error_msg}")

        except requests.exceptions.ConnectionError as e:
            error_type = "network"
            error_msg = f"网络连接错误: {str(e)[:100]}"
            print(f"🌐 {error_msg}")

        except Exception as e:
            if error_type == "unknown":
                error_type = "general"
            error_msg = str(e)
            print(f"❌ 运行异常: {e}")

        # ★ 根据错误类型提供针对性建议
        suggestions = {
            "timeout": """║ 💡 建议:
║ 1. 模型处理时间过长（已超过3分钟）
║ 2. 尝试减少参考图片数量
║ 3. 检查 vectorengine.ai 服务状态
║ 4. 降低分辨率设置""",
            "network": """║ 💡 建议:
║ 1. 检查网络连接是否正常
║ 2. 检查 base_url 地址是否正确
║ 3. 如在中国大陆，需配置代理访问
║ 4. 检查防火墙设置""",
            "api_error": """║ 💡 建议:
║ 1. 检查 API Key 是否正确且有效
║ 2. 检查账户余额是否充足
║ 3. 如提示像素不足，请使用'高清 (推荐)'模式
║ 4. 查看上方 HTTP 状态码获取详情
║ 5. 融合模式需要高清分辨率 (>3.6M像素)""",
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
║ 🥟 智绘豆包 - 生成失败
╠══════════════════════════════════════════════════════════════
║ ❌ 状态: 失败 (类型: {error_type})
╠══════════════════════════════════════════════════════════════
║ 📝 错误信息:
║ {error_msg[:200]}
╠══════════════════════════════════════════════════════════════
{suggestion_text}
╚══════════════════════════════════════════════════════════════
"""

        return (pil2tensor(error_img), error_info, error_display)

NODE_CLASS_MAPPINGS = { "ZH_DoubaoImageGen": ZH_DoubaoImageGen }
NODE_DISPLAY_NAME_MAPPINGS = { "ZH_DoubaoImageGen": "🥟 智绘_豆包 (高清增强版)" }
