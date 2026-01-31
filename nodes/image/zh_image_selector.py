import time
import torch
from server import PromptServer
from aiohttp import web
from nodes import PreviewImage
from threading import Event
import asyncio

# 自定义异常，用于中断执行
class ZH_ImageSelectorCancelled(Exception):
    pass

def get_selector_storage():
    """获取智绘选择器的共享存储空间 (独立命名空间)"""
    if not hasattr(PromptServer.instance, '_dt_selector_node_data'):
        PromptServer.instance._dt_selector_node_data = {}
    return PromptServer.instance._dt_selector_node_data

class 智绘_ImageSelector(PreviewImage):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "mode": (["always_pause", "keep_last_selection", "passthrough"], {"default": "always_pause"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("selected_images", "selected_indices")
    FUNCTION = "select_image"
    CATEGORY = "智绘灵箱/交互"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True, False)
    INPUT_IS_LIST = True
    
    @classmethod
    def IS_CHANGED(cls, images, **kwargs):
        return float(time.time())
    
    def select_image(self, images, mode, prompt=None, unique_id=None, extra_pnginfo=None):
        try:
            # 兼容列表或单值ID
            node_id = str(unique_id[0]) if isinstance(unique_id, list) else str(unique_id)
            actual_mode = mode[0] if isinstance(mode, list) else mode
            
            node_data = get_selector_storage()
            
            # 1. 整理图片列表 (兼容 Batch 和 List)
            image_list = []
            if isinstance(images, list):
                for img in images:
                    if isinstance(img, torch.Tensor):
                        if len(img.shape) == 4:
                            for i in range(img.shape[0]):
                                image_list.append(img[i:i+1])
                        elif len(img.shape) == 3:
                            image_list.append(img.unsqueeze(0))
            elif isinstance(images, torch.Tensor):
                if len(images.shape) == 4:
                    for i in range(images.shape[0]):
                        image_list.append(images[i:i+1])
                elif len(images.shape) == 3:
                    image_list.append(images.unsqueeze(0))
            
            # 2. 发送预览图到前端
            preview_images = []
            for i, img in enumerate(image_list):
                try:
                    # 使用父类 PreviewImage 的方法保存临时图
                    result = self.save_images(images=img, prompt=prompt)
                    if 'ui' in result and 'images' in result['ui']:
                        preview_images.extend(result['ui']['images'])
                except Exception as e:
                    print(f"[ZH_Selector] 预览生成失败: {e}")
                    continue
            
            # 通知前端更新图片
            PromptServer.instance.send_sync("dt_image_selector_update", {
                "id": node_id, 
                "urls": preview_images
            })
            
            # 3. 处理直通模式
            if actual_mode == "passthrough":
                self.cleanup_session_data(node_id)
                all_indices = ','.join(str(i) for i in range(len(image_list)))
                return {"result": (image_list, all_indices)}
            
            # 4. 处理保留上次选择模式
            if actual_mode == "keep_last_selection":
                if node_id in node_data and "last_selection" in node_data[node_id]:
                    last_selection = node_data[node_id]["last_selection"]
                    if last_selection and len(last_selection) > 0:
                        valid_indices = [idx for idx in last_selection if 0 <= idx < len(image_list)]
                        if valid_indices:
                            # 告诉前端恢复选中状态
                            PromptServer.instance.send_sync("dt_image_selector_selection", {
                                "id": node_id,
                                "selected_indices": valid_indices
                            })
                            self.cleanup_session_data(node_id)
                            indices_str = ','.join(str(i) for i in valid_indices)
                            return {"result": ([image_list[idx] for idx in valid_indices], indices_str)}
            
            # 5. 初始化等待会话
            if node_id in node_data:
                del node_data[node_id]
            
            event = Event()
            node_data[node_id] = {
                "event": event,
                "selected_indices": None,
                "images": image_list,
                "total_count": len(image_list),
                "cancelled": False
            }
            
            # 6. 阻塞等待前端信号
            print(f"⏳ [智绘选择器] 等待用户操作 (Node {node_id})...")
            while node_id in node_data:
                node_info = node_data[node_id]
                if node_info.get("cancelled", False):
                    self.cleanup_session_data(node_id)
                    raise ZH_ImageSelectorCancelled("用户取消选择")
                
                if "selected_indices" in node_info and node_info["selected_indices"] is not None:
                    break
                
                time.sleep(0.1) # 轮询等待

            # 7. 处理结果
            if node_id in node_data:
                node_info = node_data[node_id]
                selected_indices = node_info.get("selected_indices")
                
                if selected_indices is not None and len(selected_indices) > 0:
                    valid_indices = [idx for idx in selected_indices if 0 <= idx < len(image_list)]
                    if valid_indices:
                        selected_images = [image_list[idx] for idx in valid_indices]
                        
                        # 保存本次选择，供下次 keep_last_selection 使用
                        if node_id not in node_data: node_data[node_id] = {}
                        node_data[node_id]["last_selection"] = valid_indices
                        
                        self.cleanup_session_data(node_id)
                        indices_str = ','.join(str(i) for i in valid_indices)
                        return {"result": (selected_images, indices_str)}
                
                # 如果没选或无效，默认返回第一张，防报错
                self.cleanup_session_data(node_id)
                return {"result": ([image_list[0]] if len(image_list) > 0 else [], "0")}
            else:
                return {"result": ([image_list[0]] if len(image_list) > 0 else [], "0")}
            
        except DT_ImageSelectorCancelled:
            # 抛出中断异常，停止后续流程
            print("🚫 流程已取消")
            # 重新抛出给 ComfyUI 捕获
            raise Exception("用户在选择器取消了流程") 
        except Exception as e:
            print(f"❌ 选择器错误: {e}")
            return {"result": ([], "")}

    def cleanup_session_data(self, node_id):
        node_data = get_selector_storage()
        if node_id in node_data:
            # 只清理一次性的 key，保留 last_selection
            keys_to_remove = ["event", "selected_indices", "images", "total_count", "cancelled"]
            for key in keys_to_remove:
                if key in node_data[node_id]:
                    del node_data[node_id][key]

# 注册 API 路由 (注意 URL 加上 dt_ 前缀，防冲突)
@PromptServer.instance.routes.post("/dt_image_selector/select")
async def dt_select_image_handler(request):
    try:
        data = await request.json()
        node_id = data.get("node_id")
        selected_indices = data.get("selected_indices", [])
        action = data.get("action")
        
        node_data = get_selector_storage()
        
        if node_id not in node_data:
            return web.json_response({"success": False, "error": "节点数据已过期"})
        
        try:
            node_info = node_data[node_id]
            
            if "total_count" not in node_info:
                return web.json_response({"success": False, "error": "流程已结束"})
            
            if action == "cancel":
                node_info["cancelled"] = True
                node_info["selected_indices"] = []
            elif action == "select" and isinstance(selected_indices, list):
                # 校验索引有效性
                valid_indices = [idx for idx in selected_indices if isinstance(idx, int) and 0 <= idx < node_info["total_count"]]
                if valid_indices:
                    node_info["selected_indices"] = valid_indices
                    node_info["cancelled"] = False
                else:
                    return web.json_response({"success": False, "error": "未选择有效图片"})
            
            # 触发 Python 端的 Event，解除阻塞
            if "event" in node_info:
                node_info["event"].set()
                
            return web.json_response({"success": True})
            
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)})

    except Exception as e:
        return web.json_response({"success": False, "error": "请求无效"})

NODE_CLASS_MAPPINGS = {
    "ZH_ImageSelector": ZH_ImageSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ZH_ImageSelector": "👀 智绘_图像选择器 (交互式)",
}