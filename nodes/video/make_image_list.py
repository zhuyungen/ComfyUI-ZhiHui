import torch


class ZH_MakeImageList:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "skip_empty": ("BOOLEAN", {"default": True, "label_on": "跳过空槽", "label_off": "填充空槽"}),
            },
            "optional": {
                "image1":  ("IMAGE",),
                "image2":  ("IMAGE",),
                "image3":  ("IMAGE",),
                "image4":  ("IMAGE",),
                "image5":  ("IMAGE",),
                "image6":  ("IMAGE",),
                "image7":  ("IMAGE",),
                "image8":  ("IMAGE",),
                "image9":  ("IMAGE",),
                "image10": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "process"
    CATEGORY = "ZhiHui/video"

    def process(self, skip_empty=True, **kwargs):
        images = []
        for i in range(1, 11):
            v = kwargs.get(f"image{i}")
            if v is not None:
                images.append(v)
            elif not skip_empty:
                images.append(torch.zeros(1, 8, 8, 3, dtype=torch.float32))
        if not images:
            images.append(torch.zeros(1, 8, 8, 3, dtype=torch.float32))
        return (images,)


NODE_CLASS_MAPPINGS = {"ZH_MakeImageList": ZH_MakeImageList}
NODE_DISPLAY_NAME_MAPPINGS = {"ZH_MakeImageList": "🖼️ 图片列表合并 (Make Image List)"}
