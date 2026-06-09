import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ============================================================
// 几何工具
// ============================================================
function hypot(a, b) { return Math.sqrt(a.x * b.x + a.y * b.y); }
function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

function simplify(pts, tol) {
    if (pts.length <= 2) return pts;
    const a = pts[0], b = pts[pts.length - 1];
    let maxD = -1, idx = -1;
    for (let i = 1; i < pts.length - 1; i++) {
        const dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.abs(dy * pts[i].x - dx * pts[i].y + b.x * a.y - b.y * a.x) / Math.hypot(dx, dy);
        if (d > maxD) { maxD = d; idx = i; }
    }
    if (maxD <= tol || idx < 0) return [a, b];
    return [...simplify(pts.slice(0, idx + 1), tol).slice(0, -1), ...simplify(pts.slice(idx), tol)];
}

function shoelace(pts) {
    let s = 0;
    for (let i = 0; i < pts.length - 1; i++) s += pts[i].x * pts[i+1].y - pts[i+1].x * pts[i].y;
    return Math.abs(s / 2);
}

function uid(pfx) { return `${pfx}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`; }

function pointInPolygon(pt, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const xi = poly[i].x, yi = poly[i].y, xj = poly[j].x, yj = poly[j].y;
        if (((yi > pt.y) !== (yj > pt.y)) && (pt.x < (xj - xi) * (pt.y - yi) / (yj - yi) + xi)) inside = !inside;
    }
    return inside;
}

function elementInLasso(el, lasso) {
    if (el.kind === "path") {
        const step = Math.max(1, Math.floor(el.points.length / 20));
        for (let i = 0; i < el.points.length; i += step) {
            if (pointInPolygon(el.points[i], lasso)) return true;
        }
        return false;
    }
    const b = elBounds(el);
    return pointInPolygon({ x: b.x + b.w / 2, y: b.y + b.h / 2 }, lasso);
}

function newLayer(n) { return { id: uid("layer"), name: `图层 ${n}`, hidden: false, locked: false, elements: [] }; }

function elBounds(el) {
    if (el.kind === "path") {
        const xs = el.points.map(p => p.x), ys = el.points.map(p => p.y);
        const pad = Math.max(8, el.size);
        return { x: Math.min(...xs) - pad, y: Math.min(...ys) - pad, w: Math.max(...xs) - Math.min(...xs) + pad * 2, h: Math.max(...ys) - Math.min(...ys) + pad * 2 };
    }
    if (el.kind === "text") return { x: el.x, y: el.y - el.size, w: Math.max(80, el.text.length * el.size * 0.6), h: el.size * 1.4 };
    return { x: Math.min(el.x, el.x + el.w), y: Math.min(el.y, el.y + el.h), w: Math.abs(el.w), h: Math.abs(el.h) };
}

function hitTest(pt, el, pad = 0) {
    const b = elBounds(el);
    return pt.x >= b.x - pad && pt.x <= b.x + b.w + pad && pt.y >= b.y - pad && pt.y <= b.y + b.h + pad;
}

// ============================================================
// 渲染器
// ============================================================
function drawElement(ctx, el, selected) {
    ctx.save();
    if (el.kind === "image") {
        const img = el._img;
        if (img && img.complete) {
            ctx.globalAlpha = el.opacity ?? 1;
            const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
            ctx.translate(cx, cy);
            ctx.rotate((el.rotation || 0) * Math.PI / 180);
            ctx.drawImage(img, -el.w / 2, -el.h / 2, el.w, el.h);
        }
    } else if (el.kind === "path") {
        ctx.strokeStyle = el.color; ctx.lineWidth = el.size;
        ctx.lineCap = "round"; ctx.lineJoin = "round";
        ctx.beginPath();
        el.points.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
        ctx.stroke();
    } else if (el.kind === "text") {
        ctx.fillStyle = el.color;
        ctx.font = `600 ${el.size}px "Microsoft YaHei", sans-serif`;
        el.text.split("\n").forEach((line, i) => ctx.fillText(line, el.x, el.y + i * el.size * 1.28));
    } else if (el.kind === "rect") {
        ctx.strokeStyle = el.color; ctx.lineWidth = el.size;
        const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
        ctx.translate(cx, cy); ctx.rotate((el.rotation || 0) * Math.PI / 180);
        ctx.strokeRect(-el.w / 2, -el.h / 2, el.w, el.h);
    } else if (el.kind === "circle") {
        ctx.strokeStyle = el.color; ctx.lineWidth = el.size;
        const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
        ctx.translate(cx, cy); ctx.rotate((el.rotation || 0) * Math.PI / 180);
        ctx.beginPath(); ctx.ellipse(0, 0, Math.abs(el.w / 2), Math.abs(el.h / 2), 0, 0, Math.PI * 2); ctx.stroke();
    } else if (el.kind === "arrow") {
        ctx.strokeStyle = el.color; ctx.lineWidth = el.size; ctx.lineCap = "round";
        const ex = el.x + el.w, ey = el.y + el.h;
        ctx.beginPath(); ctx.moveTo(el.x, el.y); ctx.lineTo(ex, ey); ctx.stroke();
        const ang = Math.atan2(ey - el.y, ex - el.x), f = Math.max(12, el.size * 4);
        ctx.beginPath();
        ctx.moveTo(ex, ey); ctx.lineTo(ex - f * Math.cos(ang - Math.PI / 6), ey - f * Math.sin(ang - Math.PI / 6));
        ctx.moveTo(ex, ey); ctx.lineTo(ex - f * Math.cos(ang + Math.PI / 6), ey - f * Math.sin(ang + Math.PI / 6));
        ctx.stroke();
    }
    if (selected) {
        ctx.restore(); ctx.save();
        const b = elBounds(el);
        ctx.strokeStyle = "#22d3ee"; ctx.lineWidth = 2; ctx.setLineDash([8, 6]);
        ctx.strokeRect(b.x, b.y, b.w, b.h); ctx.setLineDash([]);
        // 缩放手柄（仅图片/矩形/圆形/箭头）
        if (["image","rect","circle","arrow"].includes(el.kind)) {
            const handles = [{x:b.x,y:b.y},{x:b.x+b.w,y:b.y},{x:b.x,y:b.y+b.h},{x:b.x+b.w,y:b.y+b.h}];
            ctx.fillStyle = "#22d3ee";
            for (const h of handles) { ctx.fillRect(h.x - 6, h.y - 6, 12, 12); }
        }
    }
    ctx.restore();
}

function renderBoard(canvas, layers, bw, bh, selId, lassoPath) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(bw * dpr) || canvas.height !== Math.round(bh * dpr)) {
        canvas.width = Math.round(bw * dpr); canvas.height = Math.round(bh * dpr);
        canvas.style.width = bw + "px"; canvas.style.height = bh + "px";
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, bw, bh);
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, bw, bh);
    ctx.save(); ctx.strokeStyle = "rgba(148,163,184,.18)"; ctx.lineWidth = 1;
    for (let x = 60; x < bw; x += 60) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, bh); ctx.stroke(); }
    for (let y = 60; y < bh; y += 60) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(bw, y); ctx.stroke(); }
    ctx.restore();
    for (const layer of layers) {
        if (layer.hidden) continue;
        for (const el of layer.elements) drawElement(ctx, el, el.id === selId);
    }
    if (lassoPath && lassoPath.length >= 2) {
        ctx.save(); ctx.strokeStyle = "#fb923c"; ctx.lineWidth = 2; ctx.setLineDash([7, 5]);
        ctx.fillStyle = "rgba(34,211,238,.12)";
        ctx.beginPath();
        lassoPath.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
        if (lassoPath.closed) { ctx.closePath(); ctx.fill(); }
        ctx.stroke(); ctx.setLineDash([]); ctx.restore();
    }
    // 尺寸标签
    const label = `${bw} × ${bh}`;
    ctx.save();
    ctx.font = "bold 12px monospace";
    const lw = ctx.measureText(label).width;
    ctx.fillStyle = "rgba(0,0,0,.45)";
    ctx.fillRect(bw - lw - 14, bh - 26, lw + 10, 20);
    ctx.fillStyle = "#fff";
    ctx.textAlign = "left";
    ctx.fillText(label, bw - lw - 9, bh - 11);
    ctx.restore();
}

// ============================================================
// ComfyUI 节点
// ============================================================
app.registerExtension({
    name: "ComfyUI-ZHIHUI.DrawingBoard",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ZH_DrawingBoard") return;

        nodeType.prototype.onNodeCreated = function () {
            this.size = [240, 80];
            // 隐藏 image_data widget
            const w = this.widgets?.find(x => x.name === "image_data");
            if (w) { w.type = "hidden"; w.computeSize = () => [0, -4]; }

            this._boardState = {
                layers: [newLayer(1)],
                activeLayerId: null,
                selId: null,
                bw: 960, bh: 540,
                color: "#111827", strokeSize: 5,
                tool: "pen",
                undoStack: [], redoStack: [],
                lasso: null,
                lassoConfirming: false,
                imageCache: new Map(),
            };
            this._boardState.activeLayerId = this._boardState.layers[0].id;

            // 监听上游图片传入
            const self = this;
            self._ignoreNextInput = false;
            api.addEventListener("zh_drawing_board_input", (event) => {
                const { id, url, width, height } = event.detail;
                if (String(id) !== String(self.id)) return;
                if (self._ignoreNextInput) { self._ignoreNextInput = false; return; }
                const img = new Image(); img.src = url;
                img.onload = () => {
                    const state = self._boardState;
                    const scale = Math.min(state.bw / width, state.bh / height, 1);
                    const dw = Math.round(width * scale);
                    const dh = Math.round(height * scale);
                    const el = { id: uid("image"), kind: "image", url, _img: img, x: 0, y: 0, w: dw, h: dh, rotation: 0, opacity: 1, _isInput: true };
                    // 优先复用已指定的输入图层
                    if (self._inputLayerId) {
                        const existing = state.layers.find(l => l.id === self._inputLayerId);
                        if (existing) {
                            // 替换该层中的输入图片元素（保留用户绘制的其他元素）
                            const hasInput = existing.elements.some(e => e._isInput);
                            if (hasInput) {
                                existing.elements = existing.elements.map(e => e._isInput ? el : e);
                            } else {
                                existing.elements.unshift(el);
                            }
                            return;
                        }
                    }
                    // 输入图层不存在时，始终使用 firstLayer，不新建图层
                    const firstLayer = state.layers[0];
                    const hasInput = firstLayer.elements.some(e => e._isInput);
                    if (hasInput) {
                        firstLayer.elements = firstLayer.elements.map(e => e._isInput ? el : e);
                    } else {
                        firstLayer.elements.unshift(el);
                    }
                    state.activeLayerId = firstLayer.id;
                    self._inputLayerId = firstLayer.id;
                };
            });

            // 监听队列执行，画板空时清空 image_data 让 Python 透传上游图片
            const onExec = () => {
                const hasContent = self._boardState.layers.some(l => l.elements.length > 0);
                if (!hasContent) {
                    const imgWidget = self.widgets?.find(x => x.name === "image_data");
                    if (imgWidget) imgWidget.value = "";
                    if (self.widgets_values) self.widgets_values[0] = "";
                }
            };
            api.addEventListener("executing", onExec);

            this.addWidget("button", "🎨 打开画板", null, () => this._openBoard());
        };

        nodeType.prototype.onConfigure = function() {
            const w = this.widgets?.find(x => x.name === "image_data");
            if (w) w.value = "";
            if (this.widgets_values) this.widgets_values[0] = "";
        };

        nodeType.prototype._getCanvas = function () { return this._boardCanvas; };

        nodeType.prototype._openBoard = function () {
            // 已经打开就聚焦
            if (this._boardPanel && document.body.contains(this._boardPanel)) {
                this._boardPanel.style.zIndex = 10000;
                return;
            }
            const state = this._boardState;

            // 浮动窗口，不遮挡背景
            const panel = document.createElement("div");
            panel.style.cssText = "position:fixed;top:60px;left:60px;z-index:9998;background:#1e293b;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;width:min(1200px,90vw);height:min(820px,88vh);box-shadow:0 24px 80px rgba(0,0,0,.6);border:1px solid rgba(148,163,184,.18);resize:both;";
            this._boardPanel = panel;

            // ---- 顶栏 ----
            const header = document.createElement("div");
            header.style.cssText = "display:flex;align-items:center;gap:8px;padding:10px 14px;background:#0f172a;border-bottom:1px solid rgba(148,163,184,.18);flex-shrink:0;flex-wrap:wrap;";

            const title = document.createElement("span");
            title.textContent = "🎨 画板";
            title.style.cssText = "font-weight:700;font-size:15px;color:#f1f5f9;margin-right:8px;";
            header.appendChild(title);

            // 工具按钮
            const tools = [
                { id: "select", label: "选择" }, { id: "pen", label: "画笔" },
                { id: "eraser", label: "橡皮" }, { id: "text", label: "文字" },
                { id: "rect", label: "矩形" }, { id: "circle", label: "圆形" },
                { id: "arrow", label: "箭头" }, { id: "lasso", label: "套索" },
            ];
            const toolBtns = {};
            for (const t of tools) {
                const btn = document.createElement("button");
                btn.textContent = t.label; btn.dataset.tool = t.id;
                btn.style.cssText = "padding:4px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#cbd5e1;cursor:pointer;font-size:12px;";
                btn.onclick = () => { state.tool = t.id; refreshToolBtns(); };
                toolBtns[t.id] = btn;
                header.appendChild(btn);
            }

            // 颜色 + 笔刷
            const colorInput = document.createElement("input");
            colorInput.type = "color"; colorInput.value = state.color;
            colorInput.style.cssText = "width:32px;height:28px;border:none;background:none;cursor:pointer;";
            colorInput.oninput = () => { state.color = colorInput.value; };
            header.appendChild(colorInput);

            const sizeInput = document.createElement("input");
            sizeInput.type = "range"; sizeInput.min = 1; sizeInput.max = 28; sizeInput.value = state.strokeSize;
            sizeInput.style.cssText = "width:80px;accent-color:#fb923c;";
            sizeInput.oninput = () => { state.strokeSize = Number(sizeInput.value); };
            header.appendChild(sizeInput);

            // 撤销/重做
            const undoBtn = document.createElement("button");
            undoBtn.textContent = "↩ 撤销";
            undoBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#cbd5e1;cursor:pointer;font-size:12px;margin-left:4px;";
            undoBtn.onclick = () => { if (state.undoStack.length) { state.redoStack.push(JSON.stringify(state.layers)); state.layers = JSON.parse(state.undoStack.pop()); reloadImgs(); redraw(); } };
            header.appendChild(undoBtn);

            const redoBtn = document.createElement("button");
            redoBtn.textContent = "↪ 重做";
            redoBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#cbd5e1;cursor:pointer;font-size:12px;";
            redoBtn.onclick = () => { if (state.redoStack.length) { state.undoStack.push(JSON.stringify(state.layers)); state.layers = JSON.parse(state.redoStack.pop()); reloadImgs(); redraw(); } };
            header.appendChild(redoBtn);

            // 尺寸选择
            // 比例下拉 + 尺寸输入
            const sizePresets = {"16:9":[960,540],"1:1":[900,900],"9:16":[540,960],"4:3":[960,720],"3:4":[720,960]};
            const ratioSel = document.createElement("select");
            ratioSel.style.cssText = "padding:4px 8px;border-radius:6px;background:#1e293b;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:12px;cursor:pointer;";
            for (const lbl of ["16:9","1:1","9:16","4:3","3:4","自由尺寸"]) {
                const o = document.createElement("option"); o.value = lbl; o.textContent = lbl; ratioSel.appendChild(o);
            }
            header.appendChild(ratioSel);

            const wInput = document.createElement("input");
            wInput.type = "number"; wInput.min = 64; wInput.max = 4096; wInput.value = state.bw;
            wInput.style.cssText = "width:56px;padding:3px 5px;border-radius:6px;background:#1e293b;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:11px;";
            const xLbl = document.createElement("span"); xLbl.textContent = "×"; xLbl.style.cssText = "color:#64748b;font-size:12px;padding:0 2px;";
            const hInput = document.createElement("input");
            hInput.type = "number"; hInput.min = 64; hInput.max = 4096; hInput.value = state.bh;
            hInput.style.cssText = "width:56px;padding:3px 5px;border-radius:6px;background:#1e293b;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:11px;";
            header.appendChild(wInput); header.appendChild(xLbl); header.appendChild(hInput);

            ratioSel.onchange = () => {
                const preset = sizePresets[ratioSel.value];
                if (preset) {
                    wInput.value = preset[0]; hInput.value = preset[1];
                    wInput.readOnly = true; hInput.readOnly = true;
                    wInput.style.opacity = "0.6"; hInput.style.opacity = "0.6";
                    state.bw = preset[0]; state.bh = preset[1]; redraw();
                } else {
                    wInput.readOnly = false; hInput.readOnly = false;
                    wInput.style.opacity = "1"; hInput.style.opacity = "1";
                }
            };
            // 初始状态锁定（默认16:9）
            wInput.readOnly = true; hInput.readOnly = true;
            wInput.style.opacity = "0.6"; hInput.style.opacity = "0.6";

            const applySize = () => {
                const w = Math.max(64, Math.min(4096, parseInt(wInput.value) || state.bw));
                const h = Math.max(64, Math.min(4096, parseInt(hInput.value) || state.bh));
                state.bw = w; state.bh = h; redraw();
            };
            wInput.onchange = applySize; hInput.onchange = applySize;

            // 载入图片
            const fileInput = document.createElement("input");
            fileInput.type = "file"; fileInput.accept = "image/*"; fileInput.multiple = true; fileInput.style.display = "none";
            fileInput.onchange = async () => {
                for (const f of fileInput.files) {
                    const url = await new Promise(res => { const r = new FileReader(); r.onload = e => res(e.target.result); r.readAsDataURL(f); });
                    const img = new Image(); img.src = url;
                    await new Promise(res => { img.onload = res; img.onerror = res; });
                    pushUndo();
                    const el = { id: uid("image"), kind: "image", url, _img: img, x: 20, y: 20, w: Math.min(img.naturalWidth, state.bw - 40), h: Math.min(img.naturalHeight, state.bh - 40), rotation: 0, opacity: 1 };
                    // 当前激活图层为空则复用，否则新建图层
                    const active = activeLayer();
                    if (active && !active.locked && active.elements.length === 0) {
                        active.elements.push(el);
                        state.activeLayerId = active.id;
                    } else {
                        const layer = newLayer(state.layers.filter(l => l.kind !== "group").length + 1);
                        layer.elements.push(el);
                        state.layers.push(layer);
                        state.activeLayerId = layer.id;
                    }
                    redraw(); refreshLayers();
                }
                fileInput.value = "";
            };
            const loadImgBtn = document.createElement("button");
            loadImgBtn.textContent = "📂 载入图片";
            loadImgBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#cbd5e1;cursor:pointer;font-size:12px;margin-left:4px;";
            loadImgBtn.onclick = () => fileInput.click();
            header.appendChild(loadImgBtn);
            header.appendChild(fileInput);

            // 清空
            const clearBtn = document.createElement("button");
            clearBtn.textContent = "🗑 清空";
            clearBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#cbd5e1;cursor:pointer;font-size:12px;";
            clearBtn.onclick = () => { if (!confirm("清空画板？")) return; pushUndo(); state.layers = [newLayer(1)]; state.activeLayerId = state.layers[0].id; state.selId = null; redraw(); refreshLayers(); };
            header.appendChild(clearBtn);

            // spacer + 关闭
            const spacer = document.createElement("div"); spacer.style.flex = "1";
            header.appendChild(spacer);
            const closeBtn = document.createElement("button");
            closeBtn.textContent = "✕";
            closeBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:none;background:transparent;color:#94a3b8;cursor:pointer;font-size:16px;";
            closeBtn.onclick = () => { dismissLassoActions(); document.body.removeChild(panel); };
            header.appendChild(closeBtn);

            // 拖动逻辑
            header.style.cursor = "move";
            header.onpointerdown = e => {
                if (e.target === closeBtn || e.target.closest("button,input,select")) return;
                e.preventDefault();
                const startX = e.clientX - panel.offsetLeft;
                const startY = e.clientY - panel.offsetTop;
                const onMove = ev => {
                    panel.style.left = Math.max(0, ev.clientX - startX) + "px";
                    panel.style.top = Math.max(0, ev.clientY - startY) + "px";
                };
                const onUp = () => {
                    document.removeEventListener("pointermove", onMove);
                    document.removeEventListener("pointerup", onUp);
                };
                document.addEventListener("pointermove", onMove);
                document.addEventListener("pointerup", onUp);
            };

            // ---- 主体 ----
            const body = document.createElement("div");
            body.style.cssText = "display:flex;flex:1;min-height:0;overflow:hidden;";

            // 图层面板
            const sidebar = document.createElement("div");
            sidebar.style.cssText = "width:180px;flex-shrink:0;background:#0f172a;border-right:1px solid rgba(148,163,184,.12);display:flex;flex-direction:column;overflow:hidden;";

            const layerTitle = document.createElement("div");
            layerTitle.style.cssText = "padding:8px 10px;font-size:12px;font-weight:600;color:#94a3b8;border-bottom:1px solid rgba(148,163,184,.1);display:flex;align-items:center;gap:6px;";
            layerTitle.innerHTML = "图层";
            const addLayerBtn = document.createElement("button");
            addLayerBtn.textContent = "+ 新建";
            addLayerBtn.style.cssText = "margin-left:auto;padding:2px 7px;border-radius:4px;border:1px solid rgba(148,163,184,.25);background:transparent;color:#94a3b8;cursor:pointer;font-size:11px;";
            addLayerBtn.onclick = () => { pushUndo(); const l = newLayer(state.layers.length + 1); state.layers.push(l); state.activeLayerId = l.id; redraw(); refreshLayers(); };
            layerTitle.appendChild(addLayerBtn);
            sidebar.appendChild(layerTitle);

            const layerList = document.createElement("div");
            layerList.style.cssText = "flex:1;overflow-y:auto;padding:4px;";
            sidebar.appendChild(layerList);

            // 属性面板底部
            const propPanel = document.createElement("div");
            propPanel.style.cssText = "padding:8px;border-top:1px solid rgba(148,163,184,.1);font-size:11px;color:#64748b;";
            propPanel.textContent = "点击图层激活";
            sidebar.appendChild(propPanel);

            // 画布区
            const canvasWrap = document.createElement("div");
            canvasWrap.style.cssText = "flex:1;min-width:0;display:flex;align-items:center;justify-content:center;overflow:auto;background:repeating-conic-gradient(rgba(148,163,184,.12) 0% 25%,transparent 0% 50%) 50%/20px 20px;padding:20px;";

            const canvas = document.createElement("canvas");
            canvas.style.cssText = "cursor:crosshair;box-shadow:0 8px 32px rgba(0,0,0,.5);";
            canvasWrap.appendChild(canvas);

            // ---- 底栏 ----
            const footer = document.createElement("div");
            footer.style.cssText = "display:flex;align-items:center;gap:10px;padding:10px 14px;background:#0f172a;border-top:1px solid rgba(148,163,184,.18);flex-shrink:0;";

            const statusTxt = document.createElement("span");
            statusTxt.style.cssText = "font-size:11px;color:#64748b;flex:1;";
            statusTxt.textContent = "就绪";
            footer.appendChild(statusTxt);

            const nodeRef = this;
            const runBtn = document.createElement("button");
            runBtn.textContent = "✅ 输出图像";
            runBtn.style.cssText = "padding:8px 20px;border-radius:8px;border:none;background:#fb923c;color:#fff;cursor:pointer;font-weight:600;font-size:13px;";
            runBtn.onclick = async () => {
                runBtn.disabled = true; runBtn.textContent = "输出中...";
                try {
                    const offscreen = document.createElement("canvas");
                    offscreen.width = state.bw; offscreen.height = state.bh;
                    const octx = offscreen.getContext("2d");
                    octx.fillStyle = "#ffffff";
                    octx.fillRect(0, 0, state.bw, state.bh);
                    for (const layer of state.layers) {
                        if (layer.hidden) continue;
                        for (const el of layer.elements) drawElement(octx, el, false);
                    }
                    const dataUrl = offscreen.toDataURL("image/png");
                    // 直接 POST 保存文件，刷新节点预览
                    const resp = await fetch("/zh/drawing_board/output", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ image_data: dataUrl, node_id: nodeRef.id }),
                    });
                    const result = await resp.json();
                    if (result.error) throw new Error(result.error);
                    const imgUrl = `/view?filename=${encodeURIComponent(result.filename)}&subfolder=${result.subfolder}&type=${result.type}&t=${Date.now()}`;
                    const previewImg = new Image();
                    previewImg.src = imgUrl;
                    nodeRef.imgs = [previewImg];
                    nodeRef.setSizeForImage?.();
                    nodeRef.graph?.setDirtyCanvas(true, false);
                    // 写入 image_data，只触发画板节点及下游
                    const imgWidget = nodeRef.widgets?.find(x => x.name === "image_data");
                    if (imgWidget) imgWidget.value = dataUrl;
                    if (!nodeRef.widgets_values) nodeRef.widgets_values = [];
                    nodeRef.widgets_values[0] = dataUrl;
                    nodeRef._ignoreNextInput = true;
                    // 构建只包含画板节点及其下游的最小 prompt，不重跑上游
                    const fullPrompt = await app.graphToPrompt();
                    const allOutput = fullPrompt.output;
                    const nodeId = String(nodeRef.id);
                    // 找出所有下游节点（BFS）
                    const toRun = new Set([nodeId]);
                    let changed = true;
                    while (changed) {
                        changed = false;
                        for (const [id, node] of Object.entries(allOutput)) {
                            if (toRun.has(id)) continue;
                            for (const v of Object.values(node.inputs || {})) {
                                if (Array.isArray(v) && toRun.has(String(v[0]))) {
                                    toRun.add(id); changed = true; break;
                                }
                            }
                        }
                    }
                    const minimalOutput = {};
                    for (const id of toRun) {
                        if (!allOutput[id]) continue;
                        const node = allOutput[id];
                        const newInputs = {};
                        for (const [key, val] of Object.entries(node.inputs || {})) {
                            // 删除指向不在执行集合内的上游节点的连接
                            if (Array.isArray(val) && !toRun.has(String(val[0]))) continue;
                            newInputs[key] = val;
                        }
                        minimalOutput[id] = { ...node, inputs: newInputs };
                    }
                    await api.fetchApi("/prompt", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ client_id: api.clientId, prompt: minimalOutput, extra_data: { extra_pnginfo: {} } }),
                    });
                    statusTxt.textContent = "输出完成";
                    setTimeout(() => { statusTxt.textContent = "就绪"; }, 2000);
                } catch(e) {
                    statusTxt.textContent = "输出失败: " + e.message;
                } finally {
                    runBtn.disabled = false;
                    runBtn.textContent = "✅ 输出图像";
                    const clearWidget = nodeRef.widgets?.find(x => x.name === "image_data");
                    if (clearWidget) clearWidget.value = "";
                    if (nodeRef.widgets_values) nodeRef.widgets_values[0] = "";
                }
            };
            const delSelBtn = document.createElement("button");
            delSelBtn.textContent = "🗑 删除选中";
            delSelBtn.style.cssText = "padding:8px 14px;border-radius:8px;border:1px solid rgba(239,68,68,.5);background:transparent;color:#ef4444;cursor:pointer;font-size:13px;";
            delSelBtn.onclick = () => {
                if (!state.selId) return;
                pushUndo();
                for (const layer of state.layers) layer.elements = layer.elements.filter(x => x.id !== state.selId);
                state.selId = null; redraw(); refreshLayers();
            };
            footer.appendChild(delSelBtn);
            footer.appendChild(runBtn);

            // ---- 组装 ----
            body.appendChild(sidebar);
            body.appendChild(canvasWrap);
            panel.appendChild(header);
            panel.appendChild(body);
            panel.appendChild(footer);
            document.body.appendChild(panel);

            // ---- 辅助函数 ----
            function refreshToolBtns() {
                for (const [id, btn] of Object.entries(toolBtns)) {
                    btn.style.background = id === state.tool ? "#fb923c" : "transparent";
                    btn.style.color = id === state.tool ? "#fff" : "#cbd5e1";
                }
            }
            refreshToolBtns();

            function refreshLayers() {
                layerList.innerHTML = "";
                [...state.layers].reverse().forEach(layer => {
                    const row = document.createElement("div");
                    row.style.cssText = `display:flex;align-items:center;gap:4px;padding:5px 6px;border-radius:5px;cursor:pointer;font-size:11px;color:#cbd5e1;border:1px solid ${layer.id === state.activeLayerId ? "#fb923c" : "transparent"};margin-bottom:2px;`;
                    row.onclick = () => { state.activeLayerId = layer.id; refreshLayers(); };

                    const vis = document.createElement("button");
                    vis.textContent = layer.hidden ? "🙈" : "👁";
                    vis.style.cssText = "background:none;border:none;cursor:pointer;padding:0;font-size:12px;";
                    vis.onclick = e => { e.stopPropagation(); layer.hidden = !layer.hidden; redraw(); refreshLayers(); };

                    const lock = document.createElement("button");
                    lock.textContent = layer.locked ? "🔒" : "🔓";
                    lock.style.cssText = "background:none;border:none;cursor:pointer;padding:0;font-size:12px;";
                    lock.onclick = e => { e.stopPropagation(); layer.locked = !layer.locked; refreshLayers(); };

                    const name = document.createElement("span");
                    name.style.cssText = "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;";
                    name.textContent = layer.name;

                    const delBtn = document.createElement("button");
                    delBtn.textContent = "✕";
                    delBtn.style.cssText = "background:none;border:none;cursor:pointer;color:#ef4444;font-size:11px;padding:0 2px;";
                    delBtn.onclick = e => {
                        e.stopPropagation();
                        const layerIdx = state.layers.findIndex(l => l.id === layer.id);
                        if (layerIdx === 0) {
                            // 图层1不能删除，但可以清空内容
                            if (layer.elements.length === 0) return;
                            pushUndo();
                            layer.elements = [];
                            redraw(); refreshLayers();
                            return;
                        }
                        pushUndo();
                        state.layers = state.layers.filter(l => l.id !== layer.id);
                        if (state.activeLayerId === layer.id) state.activeLayerId = state.layers[state.layers.length - 1].id;
                        redraw(); refreshLayers();
                    };

                    row.appendChild(vis); row.appendChild(lock); row.appendChild(name); row.appendChild(delBtn);
                    layerList.appendChild(row);
                });
            }
            refreshLayers();

            function pushUndo() {
                state.undoStack.push(JSON.stringify(state.layers.map(l => ({...l, elements: l.elements.map(e => ({...e, _img: undefined}))}))));
                if (state.undoStack.length > 60) state.undoStack.shift();
                state.redoStack = [];
            }

            function reloadImgs() {
                for (const layer of state.layers) {
                    for (const el of layer.elements) {
                        if (el.kind === "image" && el.url && !el._img) {
                            const img = state.imageCache.get(el.url) || new Image();
                            img.src = el.url; el._img = img;
                            state.imageCache.set(el.url, img);
                        }
                    }
                }
            }

            function redraw() {
                renderBoard(canvas, state.layers, state.bw, state.bh, state.selId, state.lasso);
            }
            redraw();

            // ---- 画布交互 ----
            let drawing = false, drag = null;
            let _lassoBar = null;

            function dismissLassoActions() {
                if (_lassoBar && _lassoBar.parentNode) _lassoBar.parentNode.removeChild(_lassoBar);
                _lassoBar = null;
                state.lasso = null;
                state.lassoConfirming = false;
                redraw();
            }

            // 将 lasso 多边形从图片元素中抠掉（destination-out 合成）
            function cutLassoFromImage(el, lasso) {
                const img = el._img;
                if (!img || !img.complete) return el;
                const offscreen = document.createElement("canvas");
                offscreen.width = Math.round(Math.abs(el.w));
                offscreen.height = Math.round(Math.abs(el.h));
                const octx = offscreen.getContext("2d");
                // 先画原图
                octx.save();
                if (el.rotation) {
                    octx.translate(offscreen.width / 2, offscreen.height / 2);
                    octx.rotate(el.rotation * Math.PI / 180);
                    octx.drawImage(img, -offscreen.width / 2, -offscreen.height / 2, offscreen.width, offscreen.height);
                } else {
                    octx.drawImage(img, 0, 0, offscreen.width, offscreen.height);
                }
                octx.restore();
                // 将套索坐标转换为图片局部坐标
                const scaleX = offscreen.width / Math.abs(el.w);
                const scaleY = offscreen.height / Math.abs(el.h);
                const ox = Math.min(el.x, el.x + el.w);
                const oy = Math.min(el.y, el.y + el.h);
                octx.globalCompositeOperation = "destination-out";
                octx.beginPath();
                for (let i = 0; i < lasso.length; i++) {
                    const lx = (lasso[i].x - ox) * scaleX;
                    const ly = (lasso[i].y - oy) * scaleY;
                    if (i === 0) octx.moveTo(lx, ly); else octx.lineTo(lx, ly);
                }
                octx.closePath();
                octx.fill();
                const newUrl = offscreen.toDataURL("image/png");
                const newImg = new Image();
                newImg.onload = () => redraw();
                newImg.src = newUrl;
                return { ...el, url: newUrl, _img: newImg };
            }

            function applyLasso() {
                const lasso = state.lasso;
                if (!lasso || lasso.length < 3) { dismissLassoActions(); return; }
                pushUndo();
                for (const layer of state.layers) {
                    if (layer.hidden || layer.locked) continue;
                    layer.elements = layer.elements.map(el => {
                        if (!elementInLasso(el, lasso)) return el;
                        if (el.kind === "image") return cutLassoFromImage(el, lasso);
                        return null; // 路径/形状直接删除
                    }).filter(Boolean);
                }
                dismissLassoActions();
                refreshLayers();
            }

            function showLassoActions() {
                if (_lassoBar) dismissLassoActions();
                // 计算套索在屏幕上的中心，浮于画布上方
                const r = canvas.getBoundingClientRect();
                const xs = state.lasso.map(p => p.x), ys = state.lasso.map(p => p.y);
                const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
                const cy = Math.min(...ys);
                const scaleX = r.width / state.bw, scaleY = r.height / state.bh;
                const screenX = r.left + cx * scaleX;
                const screenY = r.top + cy * scaleY - 48;

                const bar = document.createElement("div");
                bar.style.cssText = `position:fixed;z-index:10001;display:flex;gap:8px;padding:7px 12px;background:#0f172a;border:1px solid rgba(148,163,184,.3);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.5);left:${screenX}px;top:${Math.max(4, screenY)}px;transform:translateX(-50%);`;
                const hint = document.createElement("span");
                hint.textContent = "套索选区";
                hint.style.cssText = "font-size:12px;color:#94a3b8;line-height:28px;";
                bar.appendChild(hint);

                const applyBtn = document.createElement("button");
                applyBtn.textContent = "✂️ 删除选中区域";
                applyBtn.style.cssText = "padding:5px 13px;border-radius:6px;border:none;background:#ef4444;color:#fff;cursor:pointer;font-size:12px;font-weight:600;";
                applyBtn.onclick = () => applyLasso();
                bar.appendChild(applyBtn);

                const cancelBtn = document.createElement("button");
                cancelBtn.textContent = "取消";
                cancelBtn.style.cssText = "padding:5px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#94a3b8;cursor:pointer;font-size:12px;";
                cancelBtn.onclick = () => dismissLassoActions();
                bar.appendChild(cancelBtn);

                document.body.appendChild(bar);
                _lassoBar = bar;
            }

            function canvasPos(e) {
                const r = canvas.getBoundingClientRect();
                return { x: (e.clientX - r.left) / r.width * state.bw, y: (e.clientY - r.top) / r.height * state.bh };
            }

            function activeLayer() { return state.layers.find(l => l.id === state.activeLayerId); }

            canvas.onpointerdown = e => {
                if (e.button !== 0) return;
                e.preventDefault(); canvas.setPointerCapture(e.pointerId);
                const pt = canvasPos(e);
                const tool = state.tool;

                if (tool === "select") {
                    // 先检查是否点到已选中元素的缩放手柄
                    if (state.selId) {
                        for (let li = state.layers.length - 1; li >= 0; li--) {
                            const layer = state.layers[li];
                            if (layer.hidden || layer.locked) continue;
                            const el = layer.elements.find(x => x.id === state.selId);
                            if (!el || !["image","rect","circle","arrow"].includes(el.kind)) break;
                            const b = elBounds(el);
                            const handles = { nw:{x:b.x,y:b.y}, ne:{x:b.x+b.w,y:b.y}, sw:{x:b.x,y:b.y+b.h}, se:{x:b.x+b.w,y:b.y+b.h} };
                            for (const [corner, hp] of Object.entries(handles)) {
                                if (Math.abs(pt.x - hp.x) <= 10 && Math.abs(pt.y - hp.y) <= 10) {
                                    drag = { type: "resize", layerId: layer.id, elId: el.id, corner, origEl: {...el}, startPt: pt };
                                    return;
                                }
                            }
                            break;
                        }
                    }
                    state.selId = null;
                    for (let li = state.layers.length - 1; li >= 0; li--) {
                        const layer = state.layers[li];
                        if (layer.hidden || layer.locked) continue;
                        for (let ei = layer.elements.length - 1; ei >= 0; ei--) {
                            if (hitTest(pt, layer.elements[ei], 6)) {
                                state.selId = layer.elements[ei].id;
                                drag = { type: "move", layerId: layer.id, elId: layer.elements[ei].id, startPt: pt, originals: layer.elements.map(x => ({...x, points: x.points ? x.points.map(p=>({...p})) : undefined})) };
                                break;
                            }
                        }
                        if (drag) break;
                    }
                    redraw(); return;
                }

                if (tool === "lasso") {
                    if (state.lassoConfirming) return;
                    state.lasso = [pt]; drawing = true; redraw(); return;
                }

                const layer = activeLayer();
                if (!layer || layer.locked) return;
                pushUndo();
                drawing = true;

                if (tool === "text") {
                    const txt = prompt("输入文字", "文字") || "";
                    if (!txt) { drawing = false; return; }
                    layer.elements.push({ id: uid("text"), kind: "text", text: txt, x: pt.x, y: pt.y, color: state.color, size: Math.max(16, state.strokeSize * 7) });
                    drawing = false; redraw(); return;
                }

                if (tool === "pen" || tool === "eraser") {
                    const el = { id: uid("path"), kind: "path", points: [pt], color: tool === "eraser" ? "#ffffff" : state.color, size: tool === "eraser" ? state.strokeSize * 4 : state.strokeSize };
                    layer.elements.push(el);
                    drag = { type: "draw", layerId: layer.id, elId: el.id };
                    redraw(); return;
                }

                const el = { id: uid(tool), kind: tool, x: pt.x, y: pt.y, w: 1, h: 1, color: state.color, size: state.strokeSize, rotation: 0 };
                layer.elements.push(el);
                drag = { type: "shape", layerId: layer.id, elId: el.id, startPt: pt };
                redraw();
            };

            canvas.onpointermove = e => {
                if (!drag && !drawing) return;
                const pt = canvasPos(e);
                if (state.tool === "lasso" && drawing) {
                    state.lasso.push(pt); redraw(); return;
                }
                if (!drag) return;
                if (drag.type === "draw") {
                    const layer = state.layers.find(l => l.id === drag.layerId);
                    const el = layer?.elements.find(x => x.id === drag.elId);
                    if (el && el.kind === "path") { el.points.push(pt); redraw(); }
                } else if (drag.type === "shape") {
                    const layer = state.layers.find(l => l.id === drag.layerId);
                    const el = layer?.elements.find(x => x.id === drag.elId);
                    if (el) { el.w = pt.x - el.x; el.h = pt.y - el.y; redraw(); }
                } else if (drag.type === "move") {
                    const layer = state.layers.find(l => l.id === drag.layerId);
                    if (!layer) return;
                    const dx = pt.x - drag.startPt.x, dy = pt.y - drag.startPt.y;
                    layer.elements = layer.elements.map(el => {
                        const orig = drag.originals.find(o => o.id === el.id);
                        if (!orig || el.id !== drag.elId) return el;
                        if (el.kind === "path") return { ...el, points: orig.points.map(p => ({ x: p.x + dx, y: p.y + dy })) };
                        return { ...el, x: orig.x + dx, y: orig.y + dy };
                    });
                    redraw();
                } else if (drag.type === "resize") {
                    const layer = state.layers.find(l => l.id === drag.layerId);
                    const el = layer?.elements.find(x => x.id === drag.elId);
                    if (!el) return;
                    const o = drag.origEl;
                    const dx = pt.x - drag.startPt.x, dy = pt.y - drag.startPt.y;
                    const MIN = 20;
                    const c = drag.corner;
                    let nx = o.x, ny = o.y, nw = o.w, nh = o.h;
                    if (c.includes("e")) nw = Math.max(MIN, o.w + dx);
                    if (c.includes("s")) nh = Math.max(MIN, o.h + dy);
                    if (c.includes("w")) { nx = Math.min(o.x + o.w - MIN, o.x + dx); nw = o.w - (nx - o.x); }
                    if (c.includes("n")) { ny = Math.min(o.y + o.h - MIN, o.y + dy); nh = o.h - (ny - o.y); }
                    el.x = nx; el.y = ny; el.w = nw; el.h = nh;
                    redraw();
                }
            };

            canvas.onpointerup = e => {
                if (state.tool === "lasso" && drawing && state.lasso?.length >= 3) {
                    state.lasso = simplify(state.lasso, 2);
                    state.lasso.closed = true;
                    if (shoelace(state.lasso) >= 16) {
                        drawing = false; drag = null;
                        state.lassoConfirming = true;
                        redraw();
                        showLassoActions();
                        return;
                    }
                    state.lasso = null;
                    state.lassoConfirming = false;
                }
                drawing = false; drag = null; redraw();
            };

            canvas.onpointercancel = () => {
                if (state.lassoConfirming) return;
                state.lasso = null;
                drawing = false; drag = null; redraw();
            };

            // 键盘监听挂在 document 上，避免焦点问题
            const onKeyDown = e => {
                // 只在画板窗口存在时处理
                if (!document.body.contains(panel)) { document.removeEventListener("keydown", onKeyDown); return; }
                // 输入框里不处理
                if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
                if (e.key === "Escape") { dismissLassoActions(); document.body.removeChild(panel); document.removeEventListener("keydown", onKeyDown); return; }
                if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) { undoBtn.onclick(); return; }
                if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) { redoBtn.onclick(); return; }
                if ((e.key === "Delete" || e.key === "Backspace") && state.selId) {
                    e.preventDefault();
                    pushUndo();
                    for (const layer of state.layers) layer.elements = layer.elements.filter(x => x.id !== state.selId);
                    state.selId = null; redraw(); refreshLayers();
                }
                const keyMap = { s:"select", b:"pen", e:"eraser", t:"text", r:"circle", a:"arrow", l:"lasso" };
                if (!e.ctrlKey && !e.metaKey && keyMap[e.key]) { state.tool = keyMap[e.key]; refreshToolBtns(); }
            };
            document.addEventListener("keydown", onKeyDown);
        };
    }
});
