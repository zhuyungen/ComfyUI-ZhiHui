"""
智绘灵箱 - 多图片开关节点

支持多图片输入，通过索引选择输出指定图片
适用于条件分支、图片切换等场景
"""

# 定义默认和最大输入数量
DEFAULT_IMAGES = 2  # 默认显示2个输入（前端会自动扩展）
MAX_IMAGES = 20     # 最多支持20个输入

class ImageMultiSwitchNode:
    """
    智绘多图片开关节点 - 灵活切换多个图片输入

    ═══════════════════════════════════════════════════
    📖 使用说明
    ═══════════════════════════════════════════════════

    🎯 核心功能
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 多图输入：支持最多20张图片输入
    • 编号选择：使用数字编号快速切换图片
    • 智能跳过：自动跳过空图片，选择下一张有效图
    • 循环模式：索引超出时自动循环到第一张
    • 动态端口：默认2个输入，连接后自动扩展
    • 实时信息：显示选中图片、总数等状态信息

    📝 基础操作
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1️⃣ 基本切换
       • 连接多张图片到 image1, image2... 端口
       • 设置"🎯 编号"为要输出的图片编号（1-20）
       • 执行节点，输出对应编号的图片
       • 从"ℹ️ 信息"端口查看选择状态

    2️⃣ 跳过空图片
       • "⏭️ 跳过空图片"开关打开（默认启用）
       • 如果选中的编号没有图片，自动使用下一张
       • 确保始终输出有效图片
       • 适合动态输入场景

    3️⃣ 循环模式
       • "🔄 循环模式"开关打开
       • 编号超出范围时，自动循环
       • 例如：总共3张图，选择4号 → 输出1号
       • 适合需要重复使用图片的场景

    4️⃣ 动态扩展
       • 默认显示2个图片输入端口
       • 连接图片后，前端自动显示更多端口
       • 最多支持20个输入端口
       • 只连接需要的端口即可

    🔄 模式对比
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 默认模式（跳过空图片:关, 循环:关）：
      - 编号不存在时，使用边界图片
      - 小于最小编号 → 第一张
      - 大于最大编号 → 最后一张

    • 跳过空图片模式：
      - 如果选中编号为空，寻找下一张有效图
      - 保证输出始终是有效图片
      - 适合动态/稀疏输入

    • 循环模式：
      - 编号超出时，取模循环
      - 例如：3张图，选7号 → (7-1)%3 = 0 → 第1张
      - 适合重复利用图片

    📊 输出端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 🖼️ 图像：选中的图片输出
    • ℹ️ 信息：状态信息（选中编号、总数、模式等）
    • 🔢 索引：实际选中的图片编号（整数）
    • 📊 总数：输入的图片总数

    💡 使用技巧
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 条件分支：根据不同条件选择不同图片
    • A/B测试：快速切换不同版本对比效果
    • 动态输入：配合编号控制实现图片切换动画
    • 批量处理：编号自动递增实现逐图处理
    • 空位跳过：输入不连续时自动跳过空位
    • 索引输出：将索引连接到其他节点实现联动

    ⚠️ 注意事项
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    • 编号从1开始（image1, image2...），不是从0
    • 输入端口不需要连续（可以只连接1、3、5）
    • 跳过空图片模式下，空编号会查找下一张
    • 循环模式下，编号会映射到实际存在的图片
    • 最多支持20个输入端口
    • 没有输入图片时会返回错误信息

    🎯 典型应用场景
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. 条件图片选择：
       根据参数值选择不同的base图

    2. 版本快速切换：
       连接多个版本的图，编号切换快速对比

    3. 动态图片序列：
       编号自动递增，生成图片序列动画

    4. 多路输入合并：
       从多个来源收集图片，统一选择输出

    5. 备选方案切换：
       主图失败时，自动切换到备用图

    ═══════════════════════════════════════════════════
    """

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """节点每次都重新计算"""
        return float("NaN")
    
    @classmethod
    def INPUT_TYPES(cls):
        """定义节点的输入端口"""
        inputs = {
            "required": {
                # 🎯 编号选择器
                "🎯 编号": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": MAX_IMAGES,
                    "step": 1,
                    "tooltip": "选择要输出的图片编号（1-20）"
                }),
            },
            "optional": {
                # 🎨 功能选项
                "⏭️ 跳过空图片": ("BOOLEAN", {
                    "default": True,
                    "label_on": "启用 ✓",
                    "label_off": "禁用 ✗",
                    "tooltip": "如果选中的图片为空，自动使用下一张有效图片"
                }),
                "🔄 循环模式": ("BOOLEAN", {
                    "default": False,
                    "label_on": "启用 ✓",
                    "label_off": "禁用 ✗",
                    "tooltip": "当索引超出范围时，循环回到第一张图片"
                }),
            }
        }
        
        # 只添加默认数量的图片输入端口
        # 使用 image1, image2... 命名（从1开始）
        for i in range(1, DEFAULT_IMAGES + 1):
            inputs["optional"][f"image{i}"] = ("IMAGE", {
                "tooltip": f"第{i}张输入图片（可选）"
            })
        
        return inputs
    
    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT")
    RETURN_NAMES = ("🖼️ 图像", "ℹ️ 信息", "🔢 索引", "📊 总数")
    FUNCTION = "switch_image"
    CATEGORY = "智绘灵箱"
    
    def switch_image(self, **kwargs):
        """
        多图片切换的主要逻辑函数
        
        参数说明：
        - kwargs: 包含所有输入参数的字典
        
        返回值：
        - 选中的图片
        - 信息文本
        - 实际选中的索引号（整数，从0开始）
        - 总图片数量
        """
        
        # 获取控制参数
        select_index = kwargs.get("🎯 编号", 1)
        skip_empty = kwargs.get("⏭️ 跳过空图片", True)
        loop_mode = kwargs.get("🔄 循环模式", False)
        
        # 收集所有输入的图片（检查所有可能的输入端口）
        images = []
        for i in range(1, MAX_IMAGES + 1):
            img = kwargs.get(f"image{i}", None)
            if img is not None:
                images.append((i, img))  # 保存编号和图片
        
        # 如果没有任何图片输入，返回错误信息
        if not images:
            error_msg = "❌ 错误: 没有输入任何图片！"
            return (None, error_msg, 0, 0)
        
        total_images = len(images)
        
        # 直接使用编号查找对应的图片
        selected_image = kwargs.get(f"image{select_index}", None)
        selected_idx = select_index
        
        # 如果选中的图片不存在，需要处理
        if selected_image is None:
            if loop_mode and total_images > 0:
                # 循环模式：使用取模找到有效的图片
                # 将编号映射到实际存在的图片列表
                index = ((select_index - 1) % total_images)
                selected_idx, selected_image = images[index]
            else:
                # 非循环模式：使用边界限制
                if select_index < images[0][0]:
                    # 小于最小编号，使用第一张
                    selected_idx, selected_image = images[0]
                else:
                    # 大于最大编号，使用最后一张
                    selected_idx, selected_image = images[-1]
        
        # 如果启用了跳过空图片功能
        if selected_image is None and skip_empty and total_images > 0:
            # 找到第一张有效的图片
            for idx, img in images:
                if img is not None:
                    selected_idx, selected_image = idx, img
                    break
        
        # 生成信息文本
        info_lines = [
            f"✅ 输出: image{selected_idx}",
            f"📊 总数: {total_images}",
            f"🎯 请求: {select_index}",
        ]
        
        if loop_mode:
            info_lines.append("🔄 循环: 开")
        
        if skip_empty:
            info_lines.append("⏭️ 跳过: 开")
        
        info_text = " | ".join(info_lines)
        
        # 返回结果
        return (selected_image, info_text, selected_idx, total_images)


# ========== 节点注册配置 ==========
# 这部分代码告诉ComfyUI有哪些节点可以使用

# 节点类映射：将节点的内部名称映射到类
NODE_CLASS_MAPPINGS = {
    "ZhihuiImageMultiSwitchNode": ImageMultiSwitchNode, # 多图片开关节点
}

# 节点显示名称映射：定义节点在ComfyUI界面上显示的名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "ZhihuiImageMultiSwitchNode": "🔢 智绘_多图片开关",
}
