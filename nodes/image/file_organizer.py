import os
import shutil

class ZH_FileOrganizer:
    """
    功能：智能文件归档
    逻辑：扫描源文件夹的文件，如果目标文件夹中有同名子文件夹，则移动/复制过去。
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_path": ("STRING", {"default": "", "multiline": False, "placeholder": "源文件夹 (文件在这里)"}),
                "dest_path": ("STRING", {"default": "", "multiline": False, "placeholder": "目标文件夹 (文件夹在这里)"}),
                "operation": (["Dry Run (仅模拟测试)", "Copy (复制)", "Move (移动-慎用)"], {"default": "Dry Run (仅模拟测试)"}),
            },
            "optional": {
                # 作为一个触发器，随便连个东西激活它，或者点击运行
                "trigger_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("log_info",)
    FUNCTION = "organize_files"
    CATEGORY = "智绘灵箱/文件管理"
    OUTPUT_NODE = True

    def organize_files(self, source_path, dest_path, operation, trigger_image=None):
        if not source_path or not os.path.exists(source_path):
            return (f"❌ 源路径不存在: {source_path}",)
        if not dest_path or not os.path.exists(dest_path):
            return (f"❌ 目标路径不存在: {dest_path}",)

        log = []
        log.append(f"📂 开始整理: {source_path} -> {dest_path}")
        log.append(f"⚙️ 模式: {operation}")
        log.append("-" * 30)

        moved_count = 0
        skipped_count = 0
        
        # 获取源文件夹所有文件
        files = os.listdir(source_path)
        
        for filename in files:
            source_file = os.path.join(source_path, filename)
            
            # 只处理文件，不处理文件夹
            if not os.path.isfile(source_file):
                continue

            # 获取文件名（不带后缀），例如 "视频A.mp4" -> "视频A"
            name_no_ext = os.path.splitext(filename)[0]
            
            # 构造目标子文件夹路径
            target_folder = os.path.join(dest_path, name_no_ext)
            
            # 检查目标是否存在对应的文件夹
            if os.path.exists(target_folder) and os.path.isdir(target_folder):
                target_file = os.path.join(target_folder, filename)
                
                msg = f"✅ 匹配成功: [{filename}] -> 文件夹 [{name_no_ext}]"
                
                try:
                    if operation == "Move (移动-慎用)":
                        shutil.move(source_file, target_file)
                        msg += " [已移动]"
                        moved_count += 1
                    elif operation == "Copy (复制)":
                        shutil.copy2(source_file, target_file)
                        msg += " [已复制]"
                        moved_count += 1
                    else:
                        msg += " [模拟-未执行]"
                        moved_count += 1
                except Exception as e:
                    msg = f"❌ 操作失败: {filename} - {str(e)}"
                
                print(f"[大桶归档] {msg}")
                log.append(msg)
            else:
                # log.append(f"⚪ 跳过: {filename} (目标无对应文件夹)")
                skipped_count += 1

        summary = f"\n📊 统计: 成功匹配并操作 {moved_count} 个文件，跳过 {skipped_count} 个无对应文件夹的文件。"
        print(summary)
        log.append(summary)
        
        return ("\n".join(log),)

# 注册
NODE_CLASS_MAPPINGS = {
    "ZH_FileOrganizer": ZH_FileOrganizer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_FileOrganizer": "🗂️ 智绘_智能文件归档"
}