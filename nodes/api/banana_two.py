import torch
import numpy as np
import requests
import json
import base64
from PIL import Image
from io import BytesIO
import urllib3
import time
import random
import re

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

# ==============================================================================
# 香蕉 (Banana) - V18 极速性能版 (Session复用 + 输入验证 + 增强错误处理)
# ==============================================================================

class ZH_BananaTutuPort:
    def __init__(self):
        # ★ 关键改进 1: Session 复用，提升性能
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "base_url": ("STRING", {"multiline": False, "default": "https://ai.t8star.cn/v1/images/generations"}),
                "api_key": ("STRING", {"multiline": False, "default": "", "placeholder": "填入 sk-xxx..."}),
                "model": (["nano-banana-2", "gemini-3-pro-image-preview"], {"default": "nano-banana-2"}),

                "prompt": ("STRING", {"multiline": True, "default": "A cute futuristic cat"}),

                "aspect_ratio": (
                    ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                    {"default": "1:1"}
                ),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                # ★ 关键改进 5: 可调节图片质量
                "image_quality": ("INT", {"default": 85, "min": 60, "max": 100, "step": 5, "tooltip": "JPEG压缩质量 (60-100)"}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("生成图片", "详细信息", "智绘显示")
    FUNCTION = "generate"
    CATEGORY = "智绘灵箱/API"
    OUTPUT_NODE = True  # 标记为输出节点，便于显示

    def generate(self, base_url, api_key, model, prompt, aspect_ratio, image_size, seed, image_quality=85,
                 image_1=None, image_2=None, image_3=None, image_4=None):

        # ★ 关键改进 2: API Key 验证
        if not api_key or api_key.strip() == "":
            error_msg = "API Key 不能为空！请在 api_key 参数中填入您的密钥（格式：sk-xxx...）"
            print(f"❌ [智绘香蕉2] {error_msg}")
            error_img = Image.new('RGB', (512, 512), color=(128, 0, 0))
            error_display = f"""
╔══════════════════════════════════════════════════════════════
║ 🍌 智绘香蕉2 - 配置错误
╠══════════════════════════════════════════════════════════════
║ ❌ 状态: API Key 缺失
╠══════════════════════════════════════════════════════════════
║ 💡 解决方法:
║ 1. 在节点的 api_key 参数中填入您的密钥
║ 2. 密钥格式通常为: sk-xxxxxxxxxxxxxxxx
║ 3. 请从API提供商处获取有效密钥
╚══════════════════════════════════════════════════════════════
"""
            return (pil2tensor(error_img), error_msg, error_display)

        # 1. 整理图片
        input_images_raw = [image_1, image_2, image_3, image_4]

        # 2. 提示词处理
        rng = random.Random(seed)
        random_id = rng.randint(10000, 99999)
        varied_prompt = f"{prompt} --v {random_id}"

        # 映射逻辑 (图3 -> 图1)
        port_to_array_map = {}
        valid_images = []
        array_idx = 0

        for port_idx, img in enumerate(input_images_raw, 1):
            if img is not None:
                array_idx += 1
                port_to_array_map[port_idx] = array_idx
                valid_images.append(img)

        final_prompt = varied_prompt
        for port_num, array_num in port_to_array_map.items():
            patterns = [
                (rf'图{port_num}(?![0-9])', f'图{array_num}'),
                (rf'图片{port_num}(?![0-9])', f'图片{array_num}'),
                (rf'第{port_num}张图', f'第{array_num}张图'),
            ]
            for pattern, replacement in patterns:
                final_prompt = re.sub(pattern, replacement, final_prompt)

        print(f"🍌 [智绘极速版] 有效图片: {len(valid_images)} 张")

        # ★ 关键改进 3: 压缩统计
        total_size_before = 0
        total_size_after = 0

        # 3. 图片极限压缩 (JPEG + Resize)
        image_payload_list = []
        for img_idx, img_tensor in enumerate(valid_images, 1):
            pil_img = tensor2pil(img_tensor)

            # 记录原始大小
            original_bytes = pil_img.size[0] * pil_img.size[1] * 3  # RGB估算
            total_size_before += original_bytes

            # --- 提速关键点 A: 强制转 RGB (JPEG不支持透明) ---
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')

            # --- 提速关键点 B: 限制最大尺寸 (防止上传巨图) ---
            max_side = 1536 # 限制长边最大 1536px，足够AI看清了
            if max(pil_img.size) > max_side:
                ratio = max_side / max(pil_img.size)
                new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
                pil_img = pil_img.resize(new_size, Image.LANCZOS)
                print(f"   📉 图片 {img_idx} 过大，已压缩至: {new_size}")

            buffered = BytesIO()
            # --- 提速关键点 C: 使用 JPEG 格式，可调质量 ---
            # PNG 编码慢且体积大，JPEG 极快且体积小
            pil_img.save(buffered, format="JPEG", quality=image_quality)
            compressed_bytes = buffered.getvalue()
            total_size_after += len(compressed_bytes)

            b64 = base64.b64encode(compressed_bytes).decode('utf-8')

            # 注意：MIME 类型改成 image/jpeg
            image_payload_list.append(f"data:image/jpeg;base64,{b64}")

            # 显示压缩率
            compression_ratio = (1 - len(compressed_bytes) / original_bytes) * 100 if original_bytes > 0 else 0
            print(f"   💾 图片 {img_idx}: {original_bytes//1024}KB -> {len(compressed_bytes)//1024}KB (压缩 {compression_ratio:.1f}%)")

        # 显示总压缩统计
        if total_size_before > 0:
            total_compression = (1 - total_size_after / total_size_before) * 100
            print(f"📊 [压缩统计] 总计: {total_size_before//1024}KB -> {total_size_after//1024}KB (节省 {total_compression:.1f}%)")

        # 4. 构建请求
        payload = {
            "model": model,
            "prompt": final_prompt,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "response_format": "b64_json",
        }
        if image_payload_list:
            payload["image"] = image_payload_list

        # --- 提速关键点 D: 使用 Session 实例变量（已在 __init__ 中创建） ---
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
        })

        base_url = base_url.rstrip('/')
        max_retries = 3
        last_error = None
        error_type = "unknown"  # ★ 关键改进 4: 错误分类

        for attempt in range(max_retries):
            try:
                print(f"🚀 [智绘极速版] 发送请求 ({attempt+1}/{max_retries})...")

                # 稍微增加 Timeout 到 180s，防止大模型处理慢
                response = self.session.post(
                    base_url,
                    json=payload,
                    timeout=180,
                    verify=False
                )

                if response.status_code != 200:
                    error_type = "api_error"
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

                result = response.json()

                # 解析结果
                img_data = None
                if 'data' in result and isinstance(result['data'], list):
                    item = result['data'][0]
                    if 'b64_json' in item:
                        b64_str = item['b64_json']
                        if "," in b64_str[:50]: b64_str = b64_str.split(",", 1)[1]
                        img_data = base64.b64decode(b64_str)
                    elif 'url' in item:
                        img_url = item['url']
                        print(f"🔗 下载 URL: {img_url}")
                        dl_resp = self.session.get(img_url, timeout=60, verify=False)
                        img_data = dl_resp.content

                if not img_data:
                    error_type = "parse_error"
                    raise Exception(f"无图片数据: {json.dumps(result)[:100]}")

                output_image = Image.open(BytesIO(img_data))
                print(f"✅ 生成完毕: {output_image.size}")

                # 生成详细信息
                compression_info = f"压缩率: {total_compression:.1f}%" if total_size_before > 0 else "无压缩"
                info_text = f"Prompt: {final_prompt}\nSize: {image_size} ({aspect_ratio})\n{compression_info}"

                # 生成智绘显示（格式化显示）
                display_text = f"""
╔══════════════════════════════════════════════════════════════
║ 🍌 智绘香蕉2 - 生成完成
╠══════════════════════════════════════════════════════════════
║ 🎨 模型: {model}
║ 📐 尺寸: {image_size} (比例: {aspect_ratio})
║ 🎲 种子: {seed}
║ 🖼️  输出: {output_image.size[0]} x {output_image.size[1]} px
║ 📸 输入图片: {len(valid_images)} 张
║ 🗜️  压缩质量: {image_quality}
║ 💾 压缩率: {total_compression:.1f}% ({total_size_before//1024}KB → {total_size_after//1024}KB)
╠══════════════════════════════════════════════════════════════
║ 📝 提示词:
║ {final_prompt}
╠══════════════════════════════════════════════════════════════
║ ✅ 状态: 生成成功
║ ⏱️  耗时: 第 {attempt+1} 次尝试成功
╚══════════════════════════════════════════════════════════════
"""

                return (pil2tensor(output_image), info_text, display_text)

            except requests.exceptions.Timeout:
                error_type = "timeout"
                last_error = "请求超时：服务器响应时间过长"
                print(f"⏱️  超时 ({attempt+1}): {last_error}")

            except requests.exceptions.ConnectionError as e:
                error_type = "network"
                last_error = f"网络连接错误: {str(e)[:100]}"
                print(f"🌐 网络错误 ({attempt+1}): {last_error}")

            except Exception as e:
                if error_type == "unknown":
                    error_type = "general"
                last_error = e
                print(f"❌ 失败 ({attempt+1}): {e}")

            # 只有在非常严重的网络错误下才重试，避免无效等待
            if attempt < max_retries - 1:
                time.sleep(1)

        print(f"💀 最终失败: {last_error}")
        error_img = Image.new('RGB', (512, 512), color=(128, 0, 0))

        # 错误信息
        error_info = f"Error ({error_type}): {last_error}"

        # ★ 根据错误类型提供针对性建议
        suggestions = {
            "timeout": """║ 💡 建议:
║ 1. 服务器处理时间过长，请稍后重试
║ 2. 尝试减少输入图片数量或降低图片质量
║ 3. 检查服务器状态是否正常""",
            "network": """║ 💡 建议:
║ 1. 检查网络连接是否正常
║ 2. 检查 base_url 地址是否正确
║ 3. 尝试使用 VPN 或更换网络环境
║ 4. 检查防火墙设置""",
            "api_error": """║ 💡 建议:
║ 1. 检查 API Key 是否正确且有效
║ 2. 检查账户余额是否充足
║ 3. 检查 base_url 是否正确
║ 4. 查看上方错误信息中的 HTTP 状态码""",
            "parse_error": """║ 💡 建议:
║ 1. API 返回了异常数据格式
║ 2. 检查模型名称是否正确
║ 3. 查看控制台完整错误日志
║ 4. 联系 API 提供商确认接口格式""",
            "general": """║ 💡 建议:
║ 1. 查看控制台完整错误日志
║ 2. 检查输入参数是否正确
║ 3. 尝试使用默认参数重新运行
║ 4. 如果问题持续，请报告此错误"""
        }

        suggestion_text = suggestions.get(error_type, suggestions["general"])

        # 错误显示
        error_display = f"""
╔══════════════════════════════════════════════════════════════
║ 🍌 智绘香蕉2 - 生成失败
╠══════════════════════════════════════════════════════════════
║ ❌ 状态: 失败 (类型: {error_type})
║ 🔄 尝试次数: {max_retries}
╠══════════════════════════════════════════════════════════════
║ 📝 错误信息:
║ {str(last_error)[:200]}
╠══════════════════════════════════════════════════════════════
{suggestion_text}
╚══════════════════════════════════════════════════════════════
"""

        return (pil2tensor(error_img), error_info, error_display)

NODE_CLASS_MAPPINGS = {
    "ZH_BananaTutuPort": ZH_BananaTutuPort
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_BananaTutuPort": "🍌 智绘香蕉2 (极速版)"
}
