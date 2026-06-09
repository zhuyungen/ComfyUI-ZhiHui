import torch
import numpy as np
import json
import base64
from io import BytesIO
from PIL import Image
from server import PromptServer

ZH_TIMELINE_INFO = "ZH_TIMELINE_INFO"


class ZH_TimelineEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timeline_data": ("STRING", {"default": ""}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
                "total_frames": ("INT", {"default": 121, "min": 2, "max": 9999}),
            },
            "optional": {
                "prompt_override": ("STRING", {"forceInput": True}),
                "image": ("IMAGE",),
                "audio": ("AUDIO",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = (ZH_TIMELINE_INFO, "IMAGE", "AUDIO")
    RETURN_NAMES = ("timeline_info", "images", "audio")
    FUNCTION = "process"
    CATEGORY = "ZhiHui/video"
    OUTPUT_NODE = False

    def process(self, timeline_data, fps, total_frames, prompt_override=None, image=None, audio=None, unique_id=None):
        # 把 batch 所有帧的缩略图推送到前端面板
        if unique_id is not None and image is not None:
            thumbnails = []
            for i in range(image.shape[0]):
                try:
                    img_np = (image[i].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
                    pil_img = Image.fromarray(img_np, "RGB")
                    pil_img.thumbnail((120, 90), Image.LANCZOS)
                    buf = BytesIO()
                    pil_img.save(buf, format="PNG")
                    b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                    thumbnails.append({"index": i, "url": b64})
                except Exception:
                    thumbnails.append({"index": i, "url": None})
            PromptServer.instance.send_sync("zh_timeline_editor_images", {
                "id": unique_id, "thumbnails": thumbnails,
            })

        blank_image = torch.ones((1, 512, 512, 3), dtype=torch.float32)
        blank_audio = {"waveform": torch.zeros(1, 1, 1), "sample_rate": 44100}

        segments = []
        if timeline_data and timeline_data.strip():
            try:
                data = json.loads(timeline_data)
                segments = data.get("segments", [])
                total_frames = data.get("total_frames", total_frames)
                fps = data.get("fps", fps)
            except json.JSONDecodeError:
                pass

        # prompt_override 用 | 分隔，逐段覆盖提示词
        if prompt_override and prompt_override.strip():
            overrides = [p.strip() for p in prompt_override.split("|")]
            for i, seg in enumerate(segments):
                if i < len(overrides) and overrides[i]:
                    seg["prompt"] = overrides[i]

        # 收集每段图像、帧索引、段类型
        out_images, frame_indexes, seg_types = [], [], []
        for seg in segments:
            img_idx = seg.get("image_index")
            if img_idx is not None and image is not None and img_idx < image.shape[0]:
                out_images.append(image[img_idx:img_idx + 1])
                frame_indexes.append(str(seg.get("start", 0)))
                seg_types.append(seg.get("type", "flf"))

        images_out = torch.cat(out_images, dim=0) if out_images else blank_image

        prompt_str = " | ".join(s.get("prompt", "").strip() for s in segments if s.get("prompt", "").strip())

        timeline_info = {
            "segments": segments,
            "total_frames": total_frames,
            "fps": fps,
            "prompt": prompt_str,
            "frame_indexes": ",".join(frame_indexes),
            "segment_types": ",".join(seg_types),
            "segment_count": len(segments),
        }

        return (timeline_info, images_out, audio if audio is not None else blank_audio)


NODE_CLASS_MAPPINGS = {"ZH_TimelineEditor": ZH_TimelineEditor}
NODE_DISPLAY_NAME_MAPPINGS = {"ZH_TimelineEditor": "🎬 时间轴编辑器 (Timeline Editor)"}
