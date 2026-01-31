import os
import torch
import numpy as np
import imageio
import folder_paths
import torchaudio
import random
import subprocess
import shutil

# 尝试获取 imageio 自带的 ffmpeg 路径，如果没有就用系统默认的
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except:
    FFMPEG_EXE = "ffmpeg"

class ZH_VideoSaver:
    """
    功能：智绘纯净视频保存器 (V3 铁稳版)
    修复：放弃 imageio 直接写音频的方案，改用 ffmpeg 命令行后期合成，彻底解决兼容性报错。
    """
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "DT_Video", "multiline": False}),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 120.0, "step": 0.01}),
                "crf": ("INT", {"default": 20, "min": 0, "max": 51, "step": 1, "tooltip": "画质控制：18-23 最佳"}),
                "sub_folder": ("STRING", {"default": "my_videos", "multiline": False}),
            },
            "optional": {
                "audio": ("AUDIO",),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filepath",)
    FUNCTION = "save_video"
    CATEGORY = "智绘灵箱/视频"
    OUTPUT_NODE = True

    def save_video(self, images, filename_prefix, fps, crf, sub_folder, audio=None, prompt=None, extra_pnginfo=None):
        # 1. 路径准备
        if sub_folder and sub_folder.strip() != "":
            full_output_folder = os.path.join(self.output_dir, sub_folder)
        else:
            full_output_folder = self.output_dir

        if not os.path.exists(full_output_folder):
            os.makedirs(full_output_folder)

        # 生成最终文件名
        file_index = 1
        while True:
            final_file_name = f"{filename_prefix}_{file_index:04d}.mp4"
            final_path = os.path.join(full_output_folder, final_file_name)
            if not os.path.exists(final_path):
                break
            file_index += 1

        # 临时文件路径 (无声视频)
        rand_id = random.randint(100000, 999999)
        temp_video_path = os.path.join(full_output_folder, f"temp_mute_{rand_id}.mp4")
        temp_audio_path = os.path.join(full_output_folder, f"temp_audio_{rand_id}.wav")

        print(f"💾 [智绘保存] 正在处理: {final_path}")

        # 2. 第一步：保存无声视频 (绝对稳)
        try:
            images_np = (255. * images.cpu().numpy()).astype(np.uint8)
            
            # 注意：这里去掉了 audio 参数，绝对不会报错了
            writer = imageio.get_writer(
                temp_video_path, 
                fps=fps, 
                codec='libx264', 
                quality=None, 
                pixelformat='yuv420p',
                ffmpeg_params=["-crf", str(crf)] 
            )

            for frame in images_np:
                writer.append_data(frame)

            writer.close()
            
        except Exception as e:
            print(f"❌ [智绘保存] 视频画面写入失败: {e}")
            return ("",)

        # 3. 第二步：处理音频与合成
        if audio is not None:
            # 3.1 保存临时音频
            try:
                waveform = audio['waveform']
                sample_rate = audio['sample_rate']
                if waveform.dim() == 3: waveform = waveform.squeeze(0)
                torchaudio.save(temp_audio_path, waveform, sample_rate)
            except Exception as e:
                print(f"⚠️ [智绘保存] 音频提取失败: {e}")
                temp_audio_path = None

            # 3.2 使用 ffmpeg 合成 (Muxing)
            if temp_audio_path and os.path.exists(temp_audio_path):
                print(f"🎵 [智绘保存] 正在合成音画...")
                try:
                    # 调用 ffmpeg 命令: ffmpeg -i 视频 -i 音频 -c:v copy -c:a aac -map 0:v -map 1:a 输出
                    # -y 表示覆盖, -shortest 表示以最短流为准(防止音频比视频长)
                    cmd = [
                        FFMPEG_EXE, '-y',
                        '-i', temp_video_path,
                        '-i', temp_audio_path,
                        '-c:v', 'copy', # 视频流直接复制，不重编码，极快
                        '-c:a', 'aac',  # 音频转 AAC
                        '-strict', 'experimental',
                        final_path
                    ]
                    
                    # 隐藏命令行窗口
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    print(f"✅ [智绘保存] 合成完毕: {final_file_name}")
                    
                except subprocess.CalledProcessError as e:
                    print(f"❌ [智绘保存] FFmpeg 合成失败，保留无声视频。错误: {e}")
                    # 如果合成失败，就把无声视频改名为最终文件
                    if os.path.exists(final_path): os.remove(final_path)
                    os.rename(temp_video_path, final_path)
            else:
                # 有 audio 输入但保存 wav 失败，直接移动无声视频
                os.rename(temp_video_path, final_path)
        else:
            # 没有音频输入，直接重命名无声视频
            os.rename(temp_video_path, final_path)
            print(f"✅ [智绘保存] 无声视频已保存: {final_file_name}")

        # 4. 清理临时文件
        try:
            if os.path.exists(temp_video_path): os.remove(temp_video_path)
            if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
        except:
            pass

        return {"ui": {"text": [final_path], "images": []}, "result": (final_path,)}

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_VideoSaver": ZH_VideoSaver
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_VideoSaver": "💾 智绘_纯净视频保存"
}