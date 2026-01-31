import os
import json

class ZH_PresetLoader:
    """
    智绘预设文本管理节点 - 支持加载、保存、删除预设

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 加载预设：从预设库中选择并使用保存的提示词
    • 保存预设：将当前文本保存为新预设，方便复用
    • 删除预设：移除不需要的预设
    • 组合模式：灵活组合预设和自定义文本

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 使用预设
       • 从"预设选择"下拉菜单选择预设
       • 设置"组合模式"为"仅使用预设"
       • 执行节点，预设内容从"📄文本"端口输出
       • 在"👁️预设预览"端口查看完整内容

    2️⃣ 保存新预设
       • 在"文本内容"框输入要保存的文本
       • 打开"保存为新预设"开关 ✅
       • 在"新预设名称"输入框填写名称
       • 执行节点完成保存
       • ⚠️ 刷新浏览器(F5)后新预设才会出现在下拉菜单

    3️⃣ 删除预设
       • 从"预设选择"选择要删除的预设
       • 打开"删除选中预设"开关 ✅
       • 执行节点完成删除
       • ⚠️ 刷新浏览器(F5)后预设才会从下拉菜单消失

    🔄 组合模式说明
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 仅使用预设：只输出预设内容（默认）
    • 仅使用输入文本：只输出"文本内容"框的内容
    • 预设+输入文本：预设在前，自定义文本在后
    • 输入文本+预设：自定义文本在前，预设在后
    • 分隔符：组合时在中间插入的分隔符（默认换行）

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 📄文本：最终输出的文本内容，可连接到其他节点
    • 📋状态：操作状态信息（成功/失败/警告）
    • 👁️预设预览：实时显示选中预设的完整内容

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 预设文件位置：nodes/text/presets.json
    • 可直接编辑JSON文件批量管理预设
    • 组合模式可用于快速测试预设的变体
    • 使用有意义的预设名称，方便查找和管理
    • 定期备份presets.json文件

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 保存/删除操作后需要刷新浏览器才能看到更新
    • 这是ComfyUI的架构限制，所有节点都是如此
    • 不要使用"(不使用预设)"作为预设名称
    • 删除操作不可恢复，请谨慎操作

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
        这个函数决定了节点长什么样。
        我们在在这里读取 JSON 文件，这样每次刷新网页，下拉菜单都会更新。
        """
        # 1. 获取当前文件所在的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 2. 拼接出 json 文件的完整路径
        json_path = os.path.join(current_dir, "presets.json")

        # 3. 尝试读取文件
        preset_names = ["(不使用预设)"]  # 添加一个"不使用"选项
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 获取所有的 keys (就是你取的名字)
                    preset_names.extend(list(data.keys()))
            except Exception as e:
                print(f"[智绘警告] 读取预设文件失败: {e}")
                preset_names.append("读取失败_请检查JSON格式")
        else:
            preset_names.append("未找到presets.json文件")

        return {
            "required": {
                # 下拉菜单控件 (COMBO)
                "预设选择": (preset_names, {
                    "default": "(不使用预设)",
                    "tooltip": "选择要加载的预设（选中后会显示在预设预览中）"
                }),
                # 组合模式
                "组合模式": ([
                    "仅使用预设",
                    "仅使用输入文本",
                    "预设+输入文本",
                    "输入文本+预设",
                ], {
                    "default": "仅使用预设",
                    "tooltip": "如何组合预设和输入文本"
                }),
                # 分隔符（当需要组合时）
                "分隔符": ("STRING", {
                    "multiline": False,
                    "default": "\n",
                    "placeholder": "组合时的分隔符",
                    "tooltip": "组合预设和文本时使用的分隔符"
                }),
            },
            "optional": {
                # 文本输入框
                "文本内容": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "【可选】输入额外的文本内容，用于与预设组合",
                    "forceInput": False,
                    "tooltip": "可选输入，用于与预设组合或单独使用"
                }),
                # 保存选项
                "保存为新预设": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "💾 打开此开关可将当前文本保存为预设"
                }),
                "新预设名称": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "placeholder": "输入新预设的名称",
                    "tooltip": "保存时的预设名称（需要先打开保存开关）"
                }),
                # 删除选项
                "删除选中预设": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "🗑️ 打开此开关将删除上方选中的预设（危险操作）"
                }),
            }
        }

    # 输出类型：文本字符串 + 状态信息 + 预设内容预览
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    # 输出端口在界面上显示的名字
    RETURN_NAMES = ("📄文本", "📋状态", "👁️预设预览")
    # 节点逻辑处理函数
    FUNCTION = "process_preset"
    # 节点分类
    CATEGORY = "智绘灵箱/文本"
    # 标记为输出节点（显示状态信息）
    OUTPUT_NODE = True

    def process_preset(self, 预设选择, 组合模式, 分隔符, 文本内容="",
                       保存为新预设=False, 新预设名称="", 删除选中预设=False):
        """
        根据按钮状态处理预设

        参数说明：
        - 优先处理删除操作（破坏性操作）
        - 其次处理保存操作
        - 默认执行加载操作
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "presets.json")

        # ==================== 删除预设（优先级最高）====================
        if 删除选中预设:
            return self._delete_preset(json_path, 预设选择, 文本内容)

        # ==================== 保存预设 ====================
        elif 保存为新预设:
            return self._save_preset(json_path, 新预设名称, 文本内容)

        # ==================== 加载预设（默认）====================
        else:
            return self._load_preset(json_path, 预设选择, 文本内容, 组合模式, 分隔符)

    def _save_preset(self, json_path, preset_name, text):
        """保存预设到 JSON 文件"""
        # 检查预设名称
        if not preset_name or not preset_name.strip():
            status = "❌ 错误: 预设名称不能为空"
            print(f"[智绘预设] {status}")
            return (text, status, "")

        preset_name = preset_name.strip()

        # 禁止使用特殊名称
        if preset_name == "(不使用预设)":
            status = "❌ 错误: 不能使用系统保留名称"
            print(f"[智绘预设] {status}")
            return (text, status, "")

        try:
            # 读取现有预设
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}

            # 检查是否覆盖
            is_update = preset_name in data
            action = "更新" if is_update else "新建"

            # 添加或更新预设
            data[preset_name] = text

            # 写回文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            status = f"✅ 成功{action}预设: '{preset_name}' ({len(text)} 字符)"
            preview = f"【预设名称】\n{preset_name}\n\n【保存内容】\n{text[:200]}{'...' if len(text) > 200 else ''}"
            print(f"💾 [智绘预设] {status}")

            if is_update:
                print(f"⚠️  [智绘预设] 已覆盖同名预设")

            return (text, status, preview)

        except Exception as e:
            status = f"❌ 保存失败: {str(e)}"
            print(f"[智绘预设] {status}")
            return (text, status, "")

    def _delete_preset(self, json_path, preset_name, text):
        """删除指定预设"""
        # 检查预设名称
        if preset_name == "(不使用预设)" or not preset_name:
            status = "❌ 错误: 请选择要删除的预设"
            print(f"[智绘预设] {status}")
            return (text, status, "")

        try:
            # 读取现有预设
            if not os.path.exists(json_path):
                status = "❌ 错误: 预设文件不存在"
                print(f"[智绘预设] {status}")
                return (text, status, "")

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查预设是否存在
            if preset_name not in data:
                status = f"❌ 错误: 预设 '{preset_name}' 不存在"
                print(f"[智绘预设] {status}")
                return (text, status, "")

            # 删除预设
            deleted_content = data[preset_name]
            del data[preset_name]

            # 写回文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            status = f"✅ 成功删除预设: '{preset_name}' ({len(deleted_content)} 字符)"
            preview = f"【已删除预设】\n{preset_name}\n\n【删除内容】\n{deleted_content[:200]}{'...' if len(deleted_content) > 200 else ''}"
            print(f"🗑️  [智绘预设] {status}")

            return (text, status, preview)

        except Exception as e:
            status = f"❌ 删除失败: {str(e)}"
            print(f"[智绘预设] {status}")
            return (text, status, "")

    def _load_preset(self, json_path, preset, custom_text, mode, separator):
        """加载预设并根据模式组合文本"""
        preset_content = ""
        preset_found = False

        # 读取预设内容
        if preset != "(不使用预设)" and os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    preset_content = data.get(preset, "")
                    preset_found = preset in data
            except Exception as e:
                status = f"❌ 读取预设失败: {str(e)}"
                preview = ""
                print(f"[智绘预设] {status}")
                return (custom_text, status, preview)

        # 根据模式组合输出
        if mode == "仅使用预设":
            result = preset_content
        elif mode == "仅使用输入文本":
            result = custom_text
        elif mode == "预设+输入文本":
            if preset_content and custom_text:
                result = preset_content + separator + custom_text
            else:
                result = preset_content or custom_text
        elif mode == "输入文本+预设":
            if custom_text and preset_content:
                result = custom_text + separator + preset_content
            else:
                result = custom_text or preset_content
        else:
            result = preset_content or custom_text

        # 构建状态信息
        if preset == "(不使用预设)":
            status = f"✅ 未使用预设 | 模式: {mode} | 输出: {len(result)} 字符"
        elif preset_found:
            status = f"✅ 加载成功: {preset} | 模式: {mode} | 输出: {len(result)} 字符"
        else:
            status = f"⚠️ 预设 '{preset}' 不存在 | 使用输入文本 | 输出: {len(result)} 字符"

        # 构建预设预览
        if preset_found and preset_content:
            preview_text = preset_content[:300] + ('...' if len(preset_content) > 300 else '')
            preview = f"【预设名称】\n{preset}\n\n【预设内容】({len(preset_content)} 字符)\n{preview_text}\n\n【组合模式】\n{mode}"
        else:
            preview = f"【未使用预设】\n模式: {mode}\n输出: {len(result)} 字符"

        print(f"📖 [智绘预设] {status}")

        # 返回内容，必须包裹在元组里
        return (result, status, preview)

# 这一行是给分类下的 __init__.py 用的，方便识别
NODE_CLASS_MAPPINGS = {
    "ZH_PresetLoader": ZH_PresetLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_PresetLoader": "🎨 智绘_预设文本管理"
}
