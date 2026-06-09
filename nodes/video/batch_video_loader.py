import os
import torch
import numpy as np
import cv2
import math

# 尝试导入 av (PyAV)，这是 ComfyUI 环境标配的库，比 moviepy 更底层更稳
try:
    import av
    HAS_AV = True
except ImportError:
    HAS_AV = False
    print("⚠️ [智绘视频] 未检测到 av (PyAV) 库。这很不正常，ComfyUI 通常自带这个库。")

class ZH_BatchVideoLoader:
    """
    功能：智绘批量视频加载器 (V4 终极兼容版)
    引擎：画面使用 OpenCV (极速)，音频使用 PyAV (兼容性王道，仿VHS方案)
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # 基础参数
                "folder_path": ("STRING", {"default": "", "multiline": False, "placeholder": "视频文件夹路径"}),
                "video_index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1, "display": "number"}),
                
                # 抽帧与尺寸
                "force_rate": ("INT", {"default": 0, "min": 0, "max": 120, "step": 1, "tooltip": "0=原速。设置数值可强制改变输出FPS"}),
                "resize_width": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8, "tooltip": "0=原宽"}),
                "resize_height": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 8, "tooltip": "0=原高"}),
                
                # 截取控制
                "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "0=无限制"}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "frame_interval": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1, "tooltip": "间隔取帧"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "VIDEO_INFO", "STRING")
    RETURN_NAMES = ("images", "audio", "video_info", "filename_text")
    FUNCTION = "load_video"
    CATEGORY = "智绘灵箱/视频"

    def load_video(self, folder_path, video_index, force_rate, resize_width, resize_height, frame_load_cap, skip_first_frames, frame_interval):
        # 1. 路径检查
        if not folder_path or not os.path.exists(folder_path):
            print(f"❌ [智绘视频] 文件夹不存在: {folder_path}")
            return (self.get_empty_image(), None, {}, "error_path")

        # 2. 获取视频列表
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in video_extensions]
        files.sort()
        
        if not files:
            return (self.get_empty_image(), None, {}, "no_videos")

        # 3. 索引循环
        actual_index = video_index % len(files)
        target_file = files[actual_index]
        filename_no_ext = os.path.splitext(os.path.basename(target_file))[0]
        
        print(f"🎬 [智绘视频] 加载: {filename_no_ext}")

        # 4. 读取视频画面 (OpenCV - 保持高效)
        cap = cv2.VideoCapture(target_file)
        if not cap.isOpened():
            return (self.get_empty_image(), None, {}, "open_error")

        org_fps = cap.get(cv2.CAP_PROP_FPS)
        org_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        org_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        org_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = org_frame_count / org_fps if org_fps > 0 else 0

        final_fps = org_fps
        if force_rate > 0:
            final_fps = force_rate

        # 5. 读取帧
        frames = []
        current_pos = 0
        loaded_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret: break

            if current_pos < skip_first_frames:
                current_pos += 1
                continue

            if (current_pos - skip_first_frames) % frame_interval == 0:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize
                if resize_width > 0 or resize_height > 0:
                    h, w = frame.shape[:2]
                    new_w = resize_width if resize_width > 0 else int(w * (resize_height / h))
                    new_h = resize_height if resize_height > 0 else int(h * (resize_width / w))
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                frame = frame.astype(np.float32) / 255.0
                frames.append(frame)
                loaded_count += 1
                
                if frame_load_cap > 0 and loaded_count >= frame_load_cap:
                    break
            
            current_pos += 1

        cap.release()

        # 6. 读取音频 (PyAV - 兼容性王道)
        audio = None
        if HAS_AV:
            try:
                container = av.open(target_file)
                if len(container.streams.audio) > 0:
                    stream = container.streams.audio[0]
                    
                    # 强制重采样为 44100Hz, 立体声, 浮点数格式 (ComfyUI 标准)
                    target_sr = 44100
                    resampler = av.AudioResampler(format='fltp', layout='stereo', rate=target_sr)

                    audio_frames = []
                    for frame in container.decode(stream):
                        # 重采样
                        out_frames = resampler.resample(frame)
                        for out_frame in out_frames:
                            # 转换为 numpy
                            audio_frames.append(out_frame.to_ndarray())
                    
                    if audio_frames:
                        # 拼接所有帧: [Channels, Samples]
                        # PyAV fltp 格式出来的通常是 (2, samples)
                        audio_data = np.concatenate(audio_frames, axis=1)
                        
                        # 转 Tensor
                        waveform = torch.from_numpy(audio_data).float()
                        
                        # ComfyUI 要求格式: [Batch, Channels, Samples] -> [1, 2, Samples]
                        waveform = waveform.unsqueeze(0)
                        
                        audio = {"waveform": waveform, "sample_rate": target_sr}
                        print(f"🎵 [智绘视频] 音频加载成功 (PyAV): {target_sr}Hz")
                
                container.close()
            except Exception as e:
                print(f"⚠️ [智绘视频] PyAV 读取音频失败: {e}")
        else:
            print("⚠️ [智绘视频] 缺少 av 库，跳过音频加载")

        # 7. 打包 Video Info
        video_info = {
            "initial_fps": org_fps,
            "initial_frame_count": org_frame_count,
            "initial_width": org_width,
            "initial_height": org_height,
            "duration": duration,
            "loaded_fps": final_fps,
            "loaded_frame_count": len(frames),
            "filename": filename_no_ext
        }

        # 8. 输出
        if not frames:
            tensor_out = self.get_empty_image()
        else:
            tensor_out = torch.from_numpy(np.array(frames))

        return (tensor_out, audio, video_info, filename_no_ext)

    def get_empty_image(self):
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)

# ==============================================================================
# 视频信息提取器
# ==============================================================================
class ZH_VideoInfoExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_info": ("VIDEO_INFO",),
            }
        }

    RETURN_TYPES = ("FLOAT", "INT", "INT", "INT", "FLOAT", "FLOAT", "INT")
    RETURN_NAMES = ("初始FPS", "初始帧数", "初始宽度", "初始高度", "时长(秒)", "当前FPS", "当前帧数")
    FUNCTION = "unpack_info"
    CATEGORY = "智绘灵箱/视频"

    def unpack_info(self, video_info):
        return (
            float(video_info.get("initial_fps", 0)),
            int(video_info.get("initial_frame_count", 0)),
            int(video_info.get("initial_width", 0)),
            int(video_info.get("initial_height", 0)),
            float(video_info.get("duration", 0)),
            float(video_info.get("loaded_fps", 0)),
            int(video_info.get("loaded_frame_count", 0)),
        )

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_BatchVideoLoader": ZH_BatchVideoLoader,
    "ZH_VideoInfoExtractor": ZH_VideoInfoExtractor
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_BatchVideoLoader": "🎬 智绘_批量视频加载器",
    "ZH_VideoInfoExtractor": "ℹ️ 智绘_视频信息提取"
}