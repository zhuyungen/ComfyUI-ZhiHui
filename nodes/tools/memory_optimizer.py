"""
智绘灵箱 - 显存内存优化节点

智能管理显存和内存，防止溢出和性能下降
支持自动卸载模型、清空缓存、垃圾回收等优化操作
"""
import gc

import psutil
import torch
from comfy.comfy_types import IO


class ZHIHUISmartMemoryOptimizerNode:
    DESCRIPTION = "用途：显存/内存智能优化（预留显存、低内存/低显存时卸载模型、清空缓存、GC）。\n放置位置：建议放在工作流最前面；或在加载大模型/高分辨率采样前再放一个。\n直通用法：把“🔌 任意输入”接在你想触发的位置，输出端继续接回原流程，即可精确控制本节点何时执行。\n信息展示：运行后信息会直接显示在节点里（无需接信息输出端口）。\n参数说明：\n- 预留显存GB：写入 ComfyUI 的预留显存设置，给系统/其它程序留显存；越大越稳，但可用显存越少。\n- 内存安全余量GB：RAM 可用低于此值时触发“卸载全部模型 + 清理”。\n- 显存安全余量GB：VRAM 可用低于此值时触发“卸载部分模型占用 + 清理”。\n- 低内存时卸载全部模型：更激进，适合爆内存/频繁切图场景。\n- 运行时清空缓存：每次运行都做一次缓存清理，能缓解碎片但可能略慢。\n- 强制GC：强制 Python 垃圾回收，配合清理更彻底但可能卡一下。\n如何判断生效：看节点内显示的“动作=…”和“预留显存=…”，以及运行前后 RAM/VRAM 可用数值变化。"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "✅ 启用": ("BOOLEAN", {"default": True, "tooltip": "总开关；关闭时不做任何优化，仅输出状态"}),
                "🐙 预留显存GB": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 256.0, "step": 0.1, "tooltip": "预留给系统/其它程序的显存(GB)。越大越稳，但可用显存越少"}),
                "🧠 内存安全余量GB": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 512.0, "step": 0.5, "tooltip": "RAM可用低于此值(GB)时触发“卸载全部模型+清理”"}),
                "🧠 显存安全余量GB": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 256.0, "step": 0.1, "tooltip": "VRAM可用低于此值(GB)时触发“卸载部分模型占用+清理”；0表示不启用该规则"}),
                "🧹 低内存时卸载全部模型": ("BOOLEAN", {"default": True, "tooltip": "当RAM不足时卸载所有已加载模型，回收更彻底但会触发后续重新加载"}),
                "🧽 运行时清空缓存": ("BOOLEAN", {"default": True, "tooltip": "每次运行都清理一次缓存，缓解碎片，但可能略慢"}),
                "🧯 强制GC": ("BOOLEAN", {"default": True, "tooltip": "强制Python垃圾回收(gc.collect)，可能更彻底但会有短暂停顿"}),
            },
            "optional": {
                "🔌 任意输入": (IO.ANY, {"tooltip": "任意类型直通输入：把它接在你想触发优化的环节中间"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = (IO.ANY,)
    RETURN_NAMES = ("🔌 任意输出",)
    FUNCTION = "optimize"
    CATEGORY = "智绘灵箱"
    OUTPUT_NODE = True

    def _format_bytes(self, n: int) -> str:
        if n is None:
            return "0"
        if n >= 1024**3:
            return f"{n / (1024**3):.2f}GB"
        return f"{n / (1024**2):.0f}MB"

    def optimize(self, **kwargs):
        import comfy.model_management as model_management

        any_in = kwargs.get("🔌 任意输入", None)
        unique_id = kwargs.get("unique_id", kwargs.get("UNIQUE_ID", None))

        enabled = bool(kwargs.get("✅ 启用", True))
        reserve_vram_gb = float(kwargs.get("🐙 预留显存GB", 0.6))
        min_ram_gb = float(kwargs.get("🧠 内存安全余量GB", 4.0))
        min_vram_gb = float(kwargs.get("🧠 显存安全余量GB", 0.0))
        unload_on_low_ram = bool(kwargs.get("🧹 低内存时卸载全部模型", True))
        clear_cache = bool(kwargs.get("🧽 运行时清空缓存", True))
        force_gc = bool(kwargs.get("🧯 强制GC", True))

        dev = model_management.get_torch_device()
        vm = psutil.virtual_memory()
        ram_total = int(vm.total)
        ram_avail = int(vm.available)

        old_reserved = int(getattr(model_management, "EXTRA_RESERVED_VRAM", 0))

        actions = []
        if not enabled:
            info = (
                f"状态=关闭 | 设备={dev} | "
                f"RAM可用={self._format_bytes(ram_avail)}/{self._format_bytes(ram_total)} | "
                f"预留显存={self._format_bytes(old_reserved)}"
            )
            if unique_id is not None:
                from server import PromptServer
                PromptServer.instance.send_sync("dapao.memopt.info", {"node_id": int(unique_id), "info": info})
            return {"ui": {"dapao_info": info, "text": [info]}, "result": (any_in,)}

        model_management.EXTRA_RESERVED_VRAM = max(0, int(reserve_vram_gb * (1024**3)))
        if model_management.EXTRA_RESERVED_VRAM != old_reserved:
            actions.append(f"预留显存:{self._format_bytes(old_reserved)}→{self._format_bytes(model_management.EXTRA_RESERVED_VRAM)}")

        if clear_cache:
            model_management.soft_empty_cache()
            actions.append("清空缓存")

        if unload_on_low_ram and min_ram_gb > 0:
            threshold_ram = int(min_ram_gb * (1024**3))
            if ram_avail < threshold_ram:
                model_management.unload_all_models()
                model_management.free_memory(1e30, torch.device("cpu"))
                if force_gc:
                    gc.collect()
                model_management.soft_empty_cache()
                actions.append("低内存卸载模型")

        vram_total = 0
        vram_free = 0
        if hasattr(dev, "type") and dev.type not in ("cpu", "mps"):
            try:
                vram_total = int(model_management.get_total_memory(dev))
                vram_free = int(model_management.get_free_memory(dev))
            except Exception:
                vram_total = 0
                vram_free = 0

            if min_vram_gb > 0:
                need_free = int(min_vram_gb * (1024**3))
                if vram_free < need_free:
                    model_management.free_memory(need_free, dev)
                    model_management.soft_empty_cache()
                    actions.append("低显存卸载模型")

        if force_gc and not unload_on_low_ram:
            gc.collect()
            actions.append("GC")

        vm2 = psutil.virtual_memory()
        ram_avail2 = int(vm2.available)
        if hasattr(dev, "type") and dev.type not in ("cpu", "mps"):
            try:
                vram_free2 = int(model_management.get_free_memory(dev))
            except Exception:
                vram_free2 = 0
        else:
            vram_free2 = 0

        action_text = "；".join(actions) if actions else "无"
        info = (
            f"动作={action_text} | 设备={dev} | "
            f"RAM可用={self._format_bytes(ram_avail2)}/{self._format_bytes(ram_total)} | "
            f"VRAM可用={self._format_bytes(vram_free2)}/{self._format_bytes(vram_total)} | "
            f"预留显存={self._format_bytes(int(model_management.EXTRA_RESERVED_VRAM))}"
        )
        if unique_id is not None:
            from server import PromptServer
            PromptServer.instance.send_sync("dapao.memopt.info", {"node_id": int(unique_id), "info": info})
        return {"ui": {"dapao_info": info, "text": [info]}, "result": (any_in,)}


NODE_CLASS_MAPPINGS = {
    "ZHIHUISmartMemoryOptimizerNode": ZHIHUISmartMemoryOptimizerNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZHIHUISmartMemoryOptimizerNode": "🧠 智绘_显存内存优化",
}
