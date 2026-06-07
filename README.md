# ComfyUI-ZHIHUI (智绘灵箱)

一个功能丰富的 ComfyUI 自定义节点插件，提供图像处理、文本操作、批处理等多种实用功能。

A feature-rich ComfyUI custom node plugin providing image processing, text operations, batch processing and various utility functions.

## 🚀 安装方法 / Installation

### 方法一：Git 安装 (推荐) / Method 1: Git Installation (Recommended)

在 ComfyUI 的 `custom_nodes` 目录下运行：
Run in your ComfyUI's `custom_nodes` directory:

```bash
git clone https://github.com/zhuyungen/ComfyUI-ZhiHui.git
```

然后重启 ComfyUI 或使用 ComfyUI Manager 重新加载节点。
Then restart ComfyUI or reload nodes using ComfyUI Manager.

### 方法二：手动安装 / Method 2: Manual Installation

1. 下载本项目的 ZIP 文件
2. 解压到 ComfyUI 的 `custom_nodes` 目录
3. 安装依赖：`pip install -r requirements.txt`
4. 重启 ComfyUI

### 方法三：ComfyUI Manager 安装 / Method 3: ComfyUI Manager

如果本插件已被 ComfyUI Manager 收录，可直接在 Manager 中搜索 "智绘灵箱" 或 "ZHIHUI" 进行安装。

## 📋 依赖要求 / Requirements

```
torch
numpy
Pillow
pytoshop
```

安装依赖：
```bash
pip install -r requirements.txt
```

## 🎯 主要功能 / Main Features

### 🖼️ 图像处理 / Image Processing
- **🎨 画板 (Drawing Board)**: 内置画板节点，支持多图层绘画、抠图、图形编辑
- **智绘_九宫格拼图**: 批次图片网格排列拼接
- **智绘_图片切换器**: 多图像智能切换选择
- **智绘_制作批次**: 单图转批次处理
- **智绘_纯净图片加载器**: 增强版图片加载器
- **智绘_批量图片加载器**: 文件夹批量图片加载
- **智绘_高级保存图片**: 增强版图片保存功能
- **智绘_带时间保存图片**: 自动时间戳图片保存
- **智绘_保存PSD**: 多图层PSD文件生成

### 📝 文本处理 / Text Processing
- **智绘_文本分割器**: 按分隔符分割文本
- **智绘_去空行**: 清理文本空行
- **智绘_随机提示词提取**: 随机提取文本行作为提示词

### 🛠️ 实用工具 / Utilities
- **智绘_文件清理器**: 自动清理临时文件
- **智绘_预设加载器**: 预设参数快速加载

## 📚 节点列表 / Node List

### 图像类节点 / Image Nodes
| 节点名称 | 英文名称 | 功能描述 |
|---------|---------|---------|
| 🎨 画板 | Drawing Board | 多图层画板，支持画笔/橡皮/文字/图形/抠图，可接收上游图片输入 |
| 🪣 智绘_九宫格拼图 | Grid Image Assembler | 批次图片网格排列拼接 |
| 🔄 智绘_图片切换器 | Image Multi Switch | 多图像智能切换选择 |
| 📦 智绘_制作批次 | Make Image Batch | 单图转批次处理 |
| 🖼️ 智绘_纯净图片加载器 | Image Loader Plus | 增强版图片加载器 |
| 📁 智绘_批量图片加载器 | Image Batch Loader | 文件夹批量图片加载 |
| 💾 智绘_高级保存图片 | Advanced Save Image | 增强版图片保存功能 |
| ⏰ 智绘_带时间保存图片 | Save Image With Time | 自动时间戳图片保存 |
| 💾 智绘_保存PSD | Save PSD | 多图层PSD文件生成 |

### 文本类节点 / Text Nodes
| 节点名称 | 英文名称 | 功能描述 |
|---------|---------|---------|
| ✂️ 智绘_文本分割器 | Text Split By Delimiter | 按分隔符分割文本 |
| 🧹 智绘_去空行 | Remove Empty Lines | 清理文本空行 |
| 🎲 智绘_随机提示词提取 | Random Prompt Extract | 随机提取文本行作为提示词 |

### 工具类节点 / Utility Nodes
| 节点名称 | 英文名称 | 功能描述 |
|---------|---------|---------|
| 🗑️ 智绘_文件清理器 | File Cleaner | 自动清理临时文件 |
| ⚙️ 智绘_预设加载器 | Preset Loader | 预设参数快速加载 |

## 📖 使用说明 / Usage Guide

详细的使用说明请参考 [DATONG_GUIDE.md](DATONG_GUIDE.md) 文档，包含：

- 每个节点的详细功能介绍
- 参数配置说明
- 使用技巧和注意事项
- 典型应用场景示例
- 工作流推荐

For detailed usage instructions, please refer to [DATONG_GUIDE.md](DATONG_GUIDE.md), which includes:

- Detailed function introduction for each node
- Parameter configuration instructions
- Usage tips and precautions
- Typical application scenarios
- Recommended workflows

## 🔧 开发信息 / Development Info

- **版本**: 1.0.0
- **兼容性**: ComfyUI
- **Python版本**: 3.8+
- **许可证**: MIT License

## 🤝 贡献 / Contributing

欢迎提交 Issue 和 Pull Request 来改进这个项目！

Welcome to submit Issues and Pull Requests to improve this project!

## 📄 许可证 / License

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 致谢 / Acknowledgments

感谢 ComfyUI 社区的支持和贡献！

Thanks to the ComfyUI community for their support and contributions!

---

**注意**: 如果在使用过程中遇到问题，请检查是否正确安装了所有依赖项。

**Note**: If you encounter issues during use, please check if all dependencies are properly installed.