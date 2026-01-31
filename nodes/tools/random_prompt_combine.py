"""
智绘灵箱 - 随机提示词组合节点

从多个文本源中随机抽取并组合成新的提示词
支持多种组合模式、种子控制、自定义分隔符等功能
"""
import random
import re
import secrets
import unicodedata


class ZHIHUIRandomPromptLineCombineNode:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        preprocess_options = [
            "不改变",
            "取数字",
            "取字母",
            "转大写",
            "转小写",
            "取中文",
            "去标点",
            "去换行",
            "去空行",
            "去空格",
            "去格式",
            "统计字数",
        ]

        inputs = {
            "required": {
                "🧰 字符串预处理": (preprocess_options, {"default": "不改变"}),
                "🔢 提取行数": ("INT", {"default": 1, "min": 1, "max": 9999, "step": 1}),
                "🎲 随机种子": ("INT", {"default": 0, "min": 0, "max": 0x7FFFFFFF, "step": 1}),
            },
            "optional": {},
        }

        for i in range(1, 11):
            inputs["optional"][f"📝 提示词行{i}"] = ("STRING", {"default": "", "multiline": True})

        return inputs

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("📝 提示词", "🔢 字数")
    OUTPUT_IS_LIST = (True, False)
    FUNCTION = "combine"
    CATEGORY = "智绘灵箱"

    def _remove_punctuation(self, text: str) -> str:
        return "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))

    def _count_nonspace_chars(self, text: str) -> int:
        return sum(1 for ch in text if not ch.isspace())

    def _apply_preprocess(self, text: str, option: str) -> str:
        if option == "不改变":
            return text
        if option == "取数字":
            return "".join(ch for ch in text if ch.isdigit() or ch == "\n")
        if option == "取字母":
            return "".join(ch for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ch == "\n")
        if option == "转大写":
            return text.upper()
        if option == "转小写":
            return text.lower()
        if option == "取中文":
            return "".join(ch for ch in text if ("\u4e00" <= ch <= "\u9fff") or ch == "\n")
        if option == "去标点":
            return self._remove_punctuation(text)
        if option == "去换行":
            return text.replace("\r\n", "").replace("\n", "").replace("\r", "")
        if option == "去空行":
            return "\n".join(ln for ln in text.splitlines() if ln.strip() != "")
        if option == "去空格":
            return "".join(ch for ch in text if (unicodedata.category(ch) != "Zs" and ch != "\t"))
        if option == "去格式":
            normalized_lines = []
            for ln in text.splitlines():
                normalized = re.sub(r"\s+", " ", ln.replace("\t", " ").replace("\r", " ")).strip()
                if normalized != "":
                    normalized_lines.append(normalized)
            return "\n".join(normalized_lines)
        return text

    def _pick_lines_in_order(self, rng: random.Random, lines: list[str], pick_count: int) -> list[str]:
        if not lines:
            return []

        if pick_count <= 1:
            indices = [rng.randrange(len(lines))]
        else:
            if pick_count <= len(lines):
                indices = rng.sample(range(len(lines)), k=pick_count)
            else:
                indices = list(range(len(lines)))
                remaining = pick_count - len(lines)
                indices.extend(rng.randrange(len(lines)) for _ in range(remaining))

        return [lines[i] for i in sorted(indices)]

    def _pick_one_line(self, rng: random.Random, lines: list[str]) -> str:
        if not lines:
            return ""
        return lines[rng.randrange(len(lines))]

    def combine(self, **kwargs):
        option = str(kwargs.get("🧰 字符串预处理", "不改变"))
        pick_count = int(kwargs.get("🔢 提取行数", 1))
        seed = int(kwargs.get("🎲 随机种子", 0))

        input_texts = []
        for i in range(1, 11):
            v = kwargs.get(f"📝 提示词行{i}", "")
            if v is None:
                continue
            s = str(v)
            if s.strip() != "":
                input_texts.append(s)

        if not input_texts:
            return ([], 0)

        rng = random.Random(seed if seed != 0 else secrets.randbelow(0x7FFFFFFF))

        input_lines_list = []
        if len(input_texts) == 1:
            lines = [ln for ln in input_texts[0].splitlines() if ln.strip() != ""]
            input_lines_list.append(lines)
        else:
            for text in input_texts:
                lines = [ln for ln in text.splitlines() if ln.strip() != ""]
                input_lines_list.append(lines)

        prompts = []
        if len(input_lines_list) == 1:
            picked = self._pick_lines_in_order(rng, input_lines_list[0], pick_count)
            for ln in picked:
                prompts.append(ln)
        else:
            active_inputs = [lines for lines in input_lines_list if len(lines) > 0]
            if not active_inputs:
                return ([], 0)

            for _ in range(pick_count):
                parts = []
                for lines in active_inputs:
                    parts.append(self._pick_one_line(rng, lines))
                prompts.append(", ".join(parts))

        if option == "统计字数":
            counts = [self._count_nonspace_chars(p) for p in prompts]
            total = sum(counts)
            return ([str(c) for c in counts], total)

        processed_prompts = [self._apply_preprocess(p, option) for p in prompts]
        total_chars = self._count_nonspace_chars("\n".join(processed_prompts))
        return (processed_prompts, total_chars)


NODE_CLASS_MAPPINGS = {
    "ZHIHUIRandomPromptLineCombineNode": ZHIHUIRandomPromptLineCombineNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZHIHUIRandomPromptLineCombineNode": "🎲 智绘_随机提示词组合",
}
