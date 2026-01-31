class ZH_TextSplitByDelimiter:
    """
    智绘文本按分隔符拆分节点 - 将长文本切分为批次

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 文本拆分：按分隔符将长文本切分为多个片段
    • 批次输出：输出列表触发ComfyUI批处理机制
    • 索引控制：从指定位置开始提取
    • 跳跃提取：支持间隔提取（每隔N个取一个）
    • 数量限制：控制最多输出多少个片段

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本拆分
       • 在"text"框输入长文本
       • "delimiter"设置分隔符（默认逗号）
       • "start_index"设为0（从开头开始）
       • "skip_count"设为0（不跳过）
       • "max_count"设置输出数量
       • 执行节点，文本被拆分为批次

    2️⃣ 常用分隔符
       • 逗号分隔：delimiter = ","
       • 换行分隔：delimiter = "\\n"
       • 空格分隔：delimiter = " "
       • 自定义：任意字符串作为分隔符

    3️⃣ 间隔提取
       • skip_count = 0：连续提取（1, 2, 3, 4...）
       • skip_count = 1：隔一个取一个（1, 3, 5...）
       • skip_count = 2：隔两个取一个（1, 4, 7...）
       • 步长公式：step = skip_count + 1

    4️⃣ 索引控制
       • start_index：从第几个片段开始（0为第一个）
       • 配合skip_count实现灵活提取
       • 超出范围时停止，不报错

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • string_list：拆分后的文本列表（触发批处理）

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 批量提示词：将多个提示词用逗号分隔，批量生成
    • 换行拆分：处理多行文本，每行单独处理
    • 选择性处理：使用skip_count跳过不需要的内容
    • 分批处理：用max_count控制每批数量
    • 自动去空：自动移除空白片段

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 输出是列表，会触发ComfyUI批处理机制
    • 后续节点会针对每个片段分别执行
    • 换行符使用"\\n"表示（两个字符）
    • 自动去除每个片段首尾空白
    • 空白片段会被过滤掉
    • 如果结果为空，返回单个空字符串

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 批量提示词生成：
       text = "猫, 狗, 鸟, 鱼"
       delimiter = ","
       → 生成4张不同主题的图

    2. 多行脚本处理：
       text = "第一行\\n第二行\\n第三行"
       delimiter = "\\n"
       → 逐行处理文本

    3. 选择性处理：
       start_index = 2, skip_count = 1
       → 从第3个开始，隔一个取一个

    4. 分批限制：
       max_count = 5
       → 最多处理前5个片段

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
                "delimiter": ("STRING", {"default": ",", "multiline": False}),
                "start_index": ("INT", {"default": 0, "min": 0, "step": 1, "display": "number"}),
                "skip_count": ("INT", {"default": 0, "min": 0, "step": 1, "display": "number"}), # 每隔多少个跳过
                "max_count": ("INT", {"default": 1, "min": 1, "max": 1000, "step": 1, "display": "number"}),
            }
        }

    # 返回 list 类型的 STRING，ComfyUI 会将其视为 Batch，从而触发多次运行
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string_list",)
    OUTPUT_IS_LIST = (True,) # 关键设置：告诉 ComfyUI 输出的是一个列表，而不是单个字符串
    
    FUNCTION = "split_text"
    CATEGORY = "智绘灵箱/文本"

    def split_text(self, text, delimiter, start_index, skip_count, max_count):
        # 1. 拆分
        if delimiter == "\\n":
            parts = text.split('\n')
        else:
            parts = text.split(delimiter)
        
        # 去除首尾空白
        parts = [p.strip() for p in parts if p.strip() != ""]
        
        total_len = len(parts)
        if total_len == 0:
            return ([""],)

        # 2. 计算切片逻辑
        # 步长 = 跳过数 + 1 (比如跳过0个，步长就是1，挨个取；跳过1个，步长是2，隔一个取一个)
        step = skip_count + 1
        
        result_list = []
        
        # 3. 循环提取
        current_idx = start_index
        count = 0
        
        while count < max_count and current_idx < total_len:
            result_list.append(parts[current_idx])
            current_idx += step
            count += 1
            
        # 如果结果为空（比如索引越界），返回空字符串防报错
        if not result_list:
            result_list = [""]

        print(f"🪣 [文本拆分] 原文{total_len}项 -> 输出{len(result_list)}项 (Start:{start_index}, Step:{step})")
        
        return (result_list,)


class ZH_RemoveEmptyLines:
    """
    智绘去除空行节点 - 清理文本中的空白行

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 去除空行：自动移除文本中的空白行
    • 保留格式：保持其他行的原有换行结构
    • 智能检测：空格、制表符等纯空白行也会被移除
    • 简单高效：单一功能，专注文本清理

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本使用
       • 在"text"框输入或连接文本
       • 执行节点即可
       • 所有空白行自动移除
       • 从"cleaned_text"输出清理后的文本

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • cleaned_text：去除空行后的干净文本

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 文本预处理：清理从API获取的文本
    • 提示词整理：移除多余空行，格式更整洁
    • 配合拆分：清理后再拆分，避免空白片段
    • 批处理：可用于批量文本清理

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 仅移除完全空白的行（包括空格、制表符等）
    • 包含任何可见字符的行都会保留
    • 不会修改非空行的内容
    • 行与行之间用换行符重新连接

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 清理API响应：
       原文本带有多余空行 → 清理后更整洁

    2. 提示词预处理：
       复制的提示词可能有空行 → 去除后更规范

    3. 文本拆分前处理：
       去除空行 → 拆分 → 避免产生空片段

    4. 日志清理：
       清理日志文本中的空白行

    ═══════════════════════════════════════════════════
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("cleaned_text",)
    
    FUNCTION = "remove_empty"
    CATEGORY = "智绘灵箱/文本"

    def remove_empty(self, text):
        if not text:
            return ("",)
            
        # 按行拆分
        lines = text.splitlines()
        
        # 过滤：只有当去除空白后长度大于0的行才保留
        non_empty_lines = [line for line in lines if line.strip()]
        
        # 重新拼接
        cleaned_text = "\n".join(non_empty_lines)
        
        print(f"🪣 [去除空行] 处理前 {len(lines)} 行 -> 处理后 {len(non_empty_lines)} 行")
        
        return (cleaned_text,)

# 注册映射
NODE_CLASS_MAPPINGS = {
    "ZH_TextSplitByDelimiter": ZH_TextSplitByDelimiter,
    "ZH_RemoveEmptyLines": ZH_RemoveEmptyLines
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_TextSplitByDelimiter": "🎨 智绘_文本按分隔符拆分",
    "ZH_RemoveEmptyLines": "🎨 智绘_去除空行"
}