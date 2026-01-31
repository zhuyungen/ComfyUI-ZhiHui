import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "ComfyUI-DATONG.ImageSelector",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ZH_ImageSelector") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                this.selected_images = new Set();
                this.isWaitingSelection = false;
                this.imageData = [];
                this.imageRects = [];
                
                // === 布局常量配置 (V3 极简版) ===
                // 顶部高度大幅减小：只留 标题(30) + Mode选项(30) + 间隙(10)
                this.TOP_HEADER_HEIGHT = 70;   
                this.BOTTOM_BUTTON_HEIGHT = 60; // 底部增高一点点，方便点击
                this.MIN_NODE_HEIGHT = 300;     

                // ★★★ 核心改变：删除了原来的两个 Widget 按钮 ★★★
                // 既然都要画在 canvas 上，就不需要原生控件占地方了

                // 强制设定初始大小
                this.setSize([Math.max(this.size[0], 350), Math.max(this.size[1], this.MIN_NODE_HEIGHT)]);

                return result;
            };

            // --- 尺寸限制 ---
            nodeType.prototype.onResize = function(size) {
                if (size[0] < 250) size[0] = 250;
                if (size[1] < this.MIN_NODE_HEIGHT) size[1] = this.MIN_NODE_HEIGHT;
                this.calculateImageLayout(); 
            };

            // --- 布局计算 (因为顶部变矮了，图片区域会自动上移) ---
            nodeType.prototype.calculateImageLayout = function() {
                if (!this.imgs || this.imgs.length === 0) {
                    this.imageRects = [];
                    return;
                }
                
                const margin = 10;
                const sidePadding = 10;
                const availableW = this.size[0] - sidePadding * 2;
                let availableH = this.size[1] - this.TOP_HEADER_HEIGHT - this.BOTTOM_BUTTON_HEIGHT;
                
                if (availableH < 10) availableH = 10;

                const count = this.imgs.length;
                const cols = Math.ceil(Math.sqrt(count));
                const rows = Math.ceil(count / cols);
                
                const cellW = availableW / cols;
                const cellH = availableH / rows;
                
                this.imageRects = [];
                for(let i=0; i<count; i++) {
                    const col = i % cols;
                    const row = Math.floor(i / cols);
                    
                    const x = sidePadding + col * cellW + margin/2;
                    // Y坐标从 70px 开始，不再浪费空间
                    const y = this.TOP_HEADER_HEIGHT + row * cellH + margin/2;
                    const w = cellW - margin;
                    const h = cellH - margin;
                    
                    this.imageRects.push([x, y, w, h]);
                }
            };

            // --- 绘制背景 ---
            nodeType.prototype.onDrawBackground = function(ctx) {
                if (!this.imgs || this.imgs.length === 0) return;
                
                if (this.imageRects.length !== this.imgs.length) this.calculateImageLayout();

                // 绘制深灰背景框
                const bgY = this.TOP_HEADER_HEIGHT - 5;
                const bgH = this.size[1] - this.TOP_HEADER_HEIGHT - this.BOTTOM_BUTTON_HEIGHT + 10;
                ctx.fillStyle = "#222"; 
                ctx.fillRect(5, bgY, this.size[0]-10, bgH);

                for (let i = 0; i < this.imgs.length; i++) {
                    if (i >= this.imageRects.length) break;
                    const [x, y, w, h] = this.imageRects[i];
                    const img = this.imgs[i];
                    
                    ctx.fillStyle = "#111"; 
                    ctx.fillRect(x, y, w, h);
                    
                    if (img && img.complete && img.naturalWidth > 0) {
                        const scale = Math.min(w / img.naturalWidth, h / img.naturalHeight);
                        const drawW = img.naturalWidth * scale;
                        const drawH = img.naturalHeight * scale;
                        const drawX = x + (w - drawW) / 2;
                        const drawY = y + (h - drawH) / 2;
                        ctx.drawImage(img, drawX, drawY, drawW, drawH);
                    }
                }
            };

            // --- 绘制前景 (选中框 + 底部双按钮) ---
            nodeType.prototype.onDrawForeground = function(ctx) {
                if (!this.imgs || this.imgs.length === 0) return;
                
                // 1. 选中框
                this.selected_images.forEach(index => {
                    if (index < this.imageRects.length) {
                        const [x, y, w, h] = this.imageRects[index];
                        ctx.lineWidth = 3;
                        ctx.strokeStyle = "#4CAF50"; 
                        ctx.strokeRect(x, y, w, h);
                        ctx.fillStyle = "#4CAF50";
                        ctx.fillRect(x, y, 24, 24);
                        ctx.fillStyle = "white";
                        ctx.font = "bold 14px Arial";
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillText((index + 1).toString(), x + 12, y + 12);
                    }
                });
                
                // 2. 底部控制条 (状态机)
                const y = this.size[1] - this.BOTTOM_BUTTON_HEIGHT;
                const w = this.size[0];
                const h = this.BOTTOM_BUTTON_HEIGHT;

                if (this.isWaitingSelection) {
                    // === 激活状态：画两个按钮 ===
                    
                    // 左侧：取消按钮 (红色/深红)
                    ctx.fillStyle = "#c62828"; 
                    ctx.fillRect(0, y, w/2, h);
                    ctx.fillStyle = "white";
                    ctx.font = "bold 16px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("✖ 取消", w/4, y + h/2);

                    // 右侧：确认按钮 (绿色)
                    // 如果没选图，给个暗绿色提示
                    const canSubmit = this.selected_images.size > 0;
                    ctx.fillStyle = canSubmit ? "#2e7d32" : "#1b5e20"; 
                    ctx.fillRect(w/2, y, w/2, h);
                    
                    ctx.fillStyle = canSubmit ? "white" : "#aaa";
                    const confirmText = canSubmit ? `✔ 提交 (${this.selected_images.size})` : "请选择图片";
                    ctx.fillText(confirmText, w*0.75, y + h/2);

                    // 中间分割线
                    ctx.fillStyle = "rgba(0,0,0,0.2)";
                    ctx.fillRect(w/2 - 1, y, 2, h);

                } else {
                    // === 非激活状态：灰色条 (就是你要的“灰色的”) ===
                    ctx.fillStyle = "#333";
                    ctx.fillRect(0, y, w, h);
                    ctx.fillStyle = "#666";
                    ctx.font = "italic 14px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("等待上游输入...", w/2, y + h/2);
                }
            };

            // --- 交互逻辑 (支持双按钮点击) ---
            const onMouseDown = nodeType.prototype.onMouseDown;
            nodeType.prototype.onMouseDown = function(event, localPos, graphCanvas) {
                if (!this.imgs || this.imgs.length === 0) return onMouseDown?.apply(this, arguments);

                // 1. 检测底部区域
                if (this.isWaitingSelection && localPos[1] > this.size[1] - this.BOTTOM_BUTTON_HEIGHT) {
                    const halfW = this.size[0] / 2;
                    
                    if (localPos[0] < halfW) {
                        // 点击了左边 -> 取消
                        this.cancelSelection();
                        return true;
                    } else {
                        // 点击了右边 -> 确认
                        if (this.selected_images.size > 0) {
                            this.executeSelection();
                            return true;
                        }
                    }
                }

                // 2. 检测图片点击
                const index = this.getImageIndexFromClick(localPos);
                if (index >= 0) {
                    this.toggleImageSelection(index);
                    return true; 
                }
                return onMouseDown?.apply(this, arguments);
            };

            nodeType.prototype.getImageIndexFromClick = function(pos) {
                if (!this.imageRects) return -1;
                for (let i = 0; i < this.imageRects.length; i++) {
                    const [x, y, w, h] = this.imageRects[i];
                    if (pos[0] >= x && pos[0] <= x + w && pos[1] >= y && pos[1] <= y + h) return i;
                }
                return -1;
            };
            
            nodeType.prototype.toggleImageSelection = function(index) {
                if (this.selected_images.has(index)) this.selected_images.delete(index);
                else this.selected_images.add(index);
                this.setDirtyCanvas(true, true); 
            };

            nodeType.prototype.executeSelection = function() {
                if (!this.isWaitingSelection) return;
                const selectedIndices = Array.from(this.selected_images);
                fetch('/dt_image_selector/select', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ node_id: this.id.toString(), action: 'select', selected_indices: selectedIndices })
                });
                this.isWaitingSelection = false; this.setDirtyCanvas(true, true);
            };
            
            nodeType.prototype.cancelSelection = function() {
                fetch('/dt_image_selector/select', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ node_id: this.id.toString(), action: 'cancel' })
                });
                this.isWaitingSelection = false;
            };

            // 注意：原来的 updateWidgets 函数已经删除了，因为没有 Widget 了
        }
    },
    
    setup() {
        api.addEventListener("zh_image_selector_update", (event) => {
            const data = event.detail;
            const node = app.graph._nodes_by_id[data.id];
            if (!node || node.type !== "ZH_ImageSelector") return;
            
            const imageData = data.urls.map(url => ({ filename: url.filename, subfolder: url.subfolder, type: url.type }));
            node.imgs = []; let loadedCount = 0; node.imageData = imageData; node.selected_images.clear(); node.isWaitingSelection = true;
            
            imageData.forEach((imgData) => {
                const img = new Image();
                img.onload = () => { loadedCount++; if (loadedCount === imageData.length) { node.calculateImageLayout(); app.graph.setDirtyCanvas(true); } };
                img.src = api.apiURL(`/view?filename=${encodeURIComponent(imgData.filename)}&type=${imgData.type}&subfolder=${imgData.subfolder}`);
                node.imgs.push(img);
            });
        });
        
        api.addEventListener("dt_image_selector_selection", (event) => {
            const data = event.detail;
            const node = app.graph._nodes_by_id[data.id];
            if (node && node.type === "ZH_ImageSelector") {
                node.isWaitingSelection = false; node.selected_images.clear();
                if (data.selected_indices) data.selected_indices.forEach(i => node.selected_images.add(i));
                app.graph.setDirtyCanvas(true);
            }
        });
    }
});