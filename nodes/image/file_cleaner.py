import os

class ZH_FileCleaner:
    """
    智绘文件夹清理器 - 图片流专用清理工具

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 图片流集成：直接接入图像处理流程
    • 选择性删除：通过开关控制是否执行删除
    • 多格式支持：支持指定多个文件扩展名
    • 安全模式：默认关闭删除，避免误操作
    • 图片直通：不中断图像流，原样传递
    • 批量清理：一次删除整个文件夹的目标文件

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本使用
       • 将此节点插入图像处理流程中
       • 连接上游节点的图片输出到"image"端口
       • 设置"folder_path"为要清理的文件夹路径
       • 设置"file_extensions"为要删除的文件类型
       • "enable_delete"开关打开后执行删除

    2️⃣ 配置路径
       • folder_path：绝对路径或相对路径
       • 默认："./output"（当前目录的output文件夹）
       • 示例：C:/ComfyUI_Output/temp
       • 路径必须存在，否则跳过删除

    3️⃣ 指定文件类型
       • file_extensions：用逗号分隔多个扩展名
       • 默认："jpg, png, txt"
       • 自动处理空格和点号
       • 例如："jpg, png" 或 ".jpg, .png" 都可以

    4️⃣ 安全开关
       • enable_delete：默认关闭（Disable）
       • 关闭时：不执行删除，仅传递图片
       • 打开时：执行删除操作
       • 防止误操作删除重要文件

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • image：原样传递的图片（不会修改）

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 工作流清理：在保存新图片前清理旧文件
    • 临时文件管理：定期清理临时文件夹
    • 批量替换：删除旧图后生成新图
    • 日志清理：清理处理过程中的临时日志
    • 测试模式：先关闭开关测试工作流，再打开执行
    • 选择性清理：只清理特定格式，保留其他文件

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 删除操作不可恢复，请谨慎使用
    • 默认关闭删除开关，需手动打开
    • 只删除指定扩展名的文件
    • 不会删除子文件夹中的文件
    • 不会删除文件夹本身
    • 被占用的文件会跳过（不会报错）
    • 路径不存在时跳过删除，不会报错
    • 图片会原样传递，不影响后续节点

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 生成前清理：
       VAE Decode → 智绘_文件夹清理器 → 智绘_高级图像保存
       每次生成前清空输出文件夹

    2. 临时文件清理：
       清理中间处理文件，保持文件夹整洁

    3. 版本替换：
       删除旧版本图片，保存新版本

    4. 测试迭代：
       快速清理测试图片，重新生成

    5. 格式转换：
       删除原格式，保存新格式

    🔗 推荐工作流
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • VAE Decode → 智绘_文件夹清理器 → 保存节点
      （生成图片后自动清理临时文件）

    • 加载器 → 处理 → 智绘_文件夹清理器 → 保存
      （处理完成后清理原文件）

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # 强制要求输入图片，接在 VAE Decode 之后最合适，起到“触发器”的作用
                "image": ("IMAGE",),
                
                "folder_path": ("STRING", {"default": "./output", "multiline": False}),
                "file_extensions": ("STRING", {"default": "jpg, png, txt", "multiline": False}),
                "enable_delete": ("BOOLEAN", {"default": False, "label_on": "开启删除 (Enable)", "label_off": "关闭 (Disable)"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    
    FUNCTION = "clean_files"
    CATEGORY = "智绘灵箱/图片"

    def clean_files(self, image, folder_path, file_extensions, enable_delete):
        # 逻辑：不管删不删，先保证图片能传下去，不报错
        if enable_delete:
            if os.path.exists(folder_path):
                # 处理后缀：把 "jpg, png" 变成 ["jpg", "png"]
                target_exts = [ext.strip().lower().replace(".", "") for ext in file_extensions.split(",")]
                
                print(f"🗑️ [智绘清理] 准备扫描目录: {folder_path}，目标后缀: {target_exts}")

                try:
                    deleted_count = 0
                    for filename in os.listdir(folder_path):
                        if "." in filename:
                            file_ext = filename.split(".")[-1].lower()
                            if file_ext in target_exts:
                                full_file_path = os.path.join(folder_path, filename)
                                try:
                                    os.remove(full_file_path)
                                    deleted_count += 1
                                    # print(f"已删除: {filename}") # 避免刷屏，只统计总数
                                except Exception:
                                    pass # 忽略占用错误
                    
                    if deleted_count > 0:
                        print(f"🗑️ [智绘清理] 共删除 {deleted_count} 个文件。")
                    else:
                        print("🗑️ [智绘清理] 目录干净，未发现目标文件。")

                except Exception as e:
                    print(f"❌ [智绘清理] 扫描错误: {e}")
            else:
                print(f"⚠️ [智绘清理] 路径不存在: {folder_path}")

        # 原样返回图片，不打断工作流
        return (image,)

# 注册映射
NODE_CLASS_MAPPINGS = {
    "ZH_FileCleaner": ZH_FileCleaner
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_FileCleaner": "🗑️ 智绘_文件夹清理器 (图片流)"
}