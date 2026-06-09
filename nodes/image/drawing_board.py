import os
import torch
import numpy as np
import base64
from io import BytesIO
from PIL import Image
from aiohttp import web
from server import PromptServer
import folder_paths


# 注册直接输出接口，无需触发工作流
@PromptServer.instance.routes.post("/zh/drawing_board/output")
async def zh_drawing_board_direct_output(request):
    try:
        data = await request.json()
        image_data = data.get("image_data", "")
        node_id = str(data.get("node_id", "unknown"))
        if not image_data:
            return web.json_response({"error": "no image_data"}, status=400)
        raw = image_data.split(",", 1)[1] if "," in image_data else image_data
        img_bytes = base64.b64decode(raw)
        pil_img = Image.open(BytesIO(img_bytes)).convert("RGB")
        output_dir = folder_paths.get_output_directory()
        filename = f"drawing_board_{node_id}.png"
        pil_img.save(os.path.join(output_dir, filename))
        return web.json_response({"filename": filename, "subfolder": "", "type": "output"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


class ZH_DrawingBoard:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_data": ("STRING", {"default": ""}),
            },
            "optional": {
                "image": ("IMAGE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "process"
    CATEGORY = "ZhiHui/image"
    OUTPUT_NODE = False

    def process(self, image_data, image=None, unique_id=None):
        if image is not None and unique_id is not None:
            try:
                img_np = (image[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
                pil_img = Image.fromarray(img_np, "RGB")
                buf = BytesIO()
                pil_img.save(buf, format="PNG")
                b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                PromptServer.instance.send_sync("zh_drawing_board_input", {
                    "id": unique_id,
                    "url": b64,
                    "width": img_np.shape[1],
                    "height": img_np.shape[0],
                })
            except Exception as e:
                print(f"[ZH_DrawingBoard] 发送输入图片失败: {e}")

        if image_data and image_data.strip():
            try:
                data = image_data
                if "," in data:
                    data = data.split(",", 1)[1]
                img_bytes = base64.b64decode(data)
                pil_img = Image.open(BytesIO(img_bytes)).convert("RGB")
                img_array = np.array(pil_img).astype(np.float32) / 255.0
                tensor = torch.from_numpy(img_array).unsqueeze(0)
                return (tensor,)
            except Exception as e:
                print(f"[ZH_DrawingBoard] 解析画板图像失败: {e}")

        if image is not None:
            return (image,)

        blank = torch.ones((1, 512, 512, 3), dtype=torch.float32)
        return (blank,)


NODE_CLASS_MAPPINGS = {"ZH_DrawingBoard": ZH_DrawingBoard}
NODE_DISPLAY_NAME_MAPPINGS = {"ZH_DrawingBoard": "🎨 智绘_画板"}
