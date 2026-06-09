import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function uid(p) { return `${p}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`; }

app.registerExtension({
    name: "ComfyUI-ZHIHUI.TimelineEditor",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ZH_TimelineEditor") return;

        nodeType.prototype.onNodeCreated = function () {
            this.size = [280, 80];

            const wTimeline = this.widgets?.find(x => x.name === "timeline_data");
            if (wTimeline) { wTimeline.type = "hidden"; wTimeline.computeSize = () => [0, -4]; }

            this._tlState = {
                segments: [
                    { id: uid("s"), start: 0, end: 60, prompt: "", image_index: null, type: "flf" },
                    { id: uid("s"), start: 60, end: 121, prompt: "", image_index: null, type: "flf" },
                ],
                total_frames: 121,
                fps: 24,
                thumbnails: [],  // [{index, url}, ...]
                selId: null,
            };

            api.addEventListener("zh_timeline_editor_images", (e) => {
                const { id, thumbnails } = e.detail;
                if (String(id) !== String(this.id)) return;
                this._tlState.thumbnails = thumbnails;
                if (this._refreshEditPanel) this._refreshEditPanel();
            });

            // 从上游节点预览图直接读取缩略图（无需运行工作流）
            this._getUpstreamThumbnails = function() {
                const imageInput = this.inputs?.find(i => i.name === "image");
                if (!imageInput || imageInput.link == null) return [];
                const link = app.graph.links[imageInput.link];
                if (!link) return [];
                const sourceNode = app.graph.getNodeById(link.origin_id);
                if (!sourceNode?.imgs?.length) return [];
                return sourceNode.imgs.map((img, i) => ({
                    index: i,
                    url: img.currentSrc || img.src || null,
                }));
            };

            this.addWidget("button", "🎬 打开时间轴", null, () => this._openTimeline());
        };

        nodeType.prototype._saveToWidget = function () {
            const state = this._tlState;
            const data = {
                total_frames: state.total_frames,
                fps: state.fps,
                segments: state.segments.map(s => ({
                    id: s.id, start: s.start, end: s.end,
                    prompt: s.prompt, image_index: s.image_index, type: s.type || "flf",
                })),
            };
            const w = this.widgets?.find(x => x.name === "timeline_data");
            if (w) w.value = JSON.stringify(data);
            if (!this.widgets_values) this.widgets_values = [];
            this.widgets_values[0] = JSON.stringify(data);
        };

        nodeType.prototype._openTimeline = function () {
            if (this._tlPanel && document.body.contains(this._tlPanel)) {
                this._tlPanel.style.zIndex = 10001; return;
            }
            const state = this._tlState;
            const nodeRef = this;

            const wFps = this.widgets?.find(x => x.name === "fps");
            const wFrames = this.widgets?.find(x => x.name === "total_frames");
            if (wFps) state.fps = wFps.value;
            if (wFrames) state.total_frames = wFrames.value;

            // 打开时立即从上游节点预览图填充缩略图
            const upstream = nodeRef._getUpstreamThumbnails?.() || [];
            if (upstream.length) state.thumbnails = upstream;

            const panel = document.createElement("div");
            panel.style.cssText = "position:fixed;top:60px;left:80px;z-index:9999;background:#1e293b;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;width:min(1100px,92vw);height:min(680px,86vh);box-shadow:0 24px 80px rgba(0,0,0,.65);border:1px solid rgba(148,163,184,.18);resize:both;";
            this._tlPanel = panel;

            // ── header ──
            const header = document.createElement("div");
            header.style.cssText = "display:flex;align-items:center;gap:8px;padding:10px 14px;background:#0f172a;border-bottom:1px solid rgba(148,163,184,.18);flex-shrink:0;cursor:move;flex-wrap:wrap;";

            const title = document.createElement("span");
            title.textContent = "🎬 时间轴编辑器";
            title.style.cssText = "font-weight:700;font-size:15px;color:#f1f5f9;margin-right:4px;";
            header.appendChild(title);

            const fpsLbl = document.createElement("span"); fpsLbl.textContent = "FPS:"; fpsLbl.style.cssText = "color:#94a3b8;font-size:12px;";
            const fpsInput = document.createElement("input");
            fpsInput.type = "number"; fpsInput.min = 1; fpsInput.max = 120; fpsInput.value = state.fps;
            fpsInput.style.cssText = "width:50px;padding:3px 5px;border-radius:5px;background:#1e293b;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:12px;";
            fpsInput.onchange = () => { state.fps = Math.max(1, parseInt(fpsInput.value) || 24); };
            header.appendChild(fpsLbl); header.appendChild(fpsInput);

            const frLbl = document.createElement("span"); frLbl.textContent = "总帧:"; frLbl.style.cssText = "color:#94a3b8;font-size:12px;";
            const frInput = document.createElement("input");
            frInput.type = "number"; frInput.min = 2; frInput.max = 9999; frInput.value = state.total_frames;
            frInput.style.cssText = "width:64px;padding:3px 5px;border-radius:5px;background:#1e293b;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:12px;";
            frInput.onchange = () => {
                const nf = Math.max(2, parseInt(frInput.value) || 121);
                state.total_frames = nf;
                if (state.segments.length > 0) state.segments[state.segments.length - 1].end = nf;
                redrawTimeline();
            };
            header.appendChild(frLbl); header.appendChild(frInput);

            const addBtn = document.createElement("button");
            addBtn.textContent = "+ 添加段";
            addBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:1px solid rgba(148,163,184,.3);background:transparent;color:#cbd5e1;cursor:pointer;font-size:12px;";
            addBtn.onclick = () => {
                const segs = state.segments;
                if (!segs.length) {
                    segs.push({ id: uid("s"), start: 0, end: state.total_frames, prompt: "", image_index: null, type: "flf" });
                } else {
                    const last = segs[segs.length - 1];
                    const mid = Math.round((last.start + last.end) / 2);
                    if (mid <= last.start) return;
                    const newSeg = { id: uid("s"), start: mid, end: last.end, prompt: "", image_index: null, type: "flf" };
                    last.end = mid;
                    segs.push(newSeg);
                    state.selId = newSeg.id;
                }
                redrawTimeline(); refreshEdit();
            };
            header.appendChild(addBtn);

            const spacer = document.createElement("div"); spacer.style.flex = "1";
            header.appendChild(spacer);

            const closeBtn = document.createElement("button");
            closeBtn.textContent = "✕";
            closeBtn.style.cssText = "padding:4px 10px;border-radius:6px;border:none;background:transparent;color:#94a3b8;cursor:pointer;font-size:16px;";
            closeBtn.onclick = () => document.body.removeChild(panel);
            header.appendChild(closeBtn);

            header.onpointerdown = e => {
                if (e.target.closest("button,input,select")) return;
                e.preventDefault();
                const sx = e.clientX - panel.offsetLeft, sy = e.clientY - panel.offsetTop;
                const mv = ev => { panel.style.left = Math.max(0,ev.clientX-sx)+"px"; panel.style.top = Math.max(0,ev.clientY-sy)+"px"; };
                const up = () => { document.removeEventListener("pointermove",mv); document.removeEventListener("pointerup",up); };
                document.addEventListener("pointermove",mv); document.addEventListener("pointerup",up);
            };

            // ── body ──
            const body = document.createElement("div");
            body.style.cssText = "display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden;";

            const tlArea = document.createElement("div");
            tlArea.style.cssText = "flex-shrink:0;padding:14px 16px 8px;background:#0f172a;border-bottom:1px solid rgba(148,163,184,.12);";

            const trackWrap = document.createElement("div");
            trackWrap.style.cssText = "position:relative;user-select:none;";

            const rulerCanvas = document.createElement("canvas");
            rulerCanvas.height = 22;
            rulerCanvas.style.cssText = "display:block;width:100%;border-radius:4px 4px 0 0;background:#0f172a;";

            const trackCanvas = document.createElement("canvas");
            trackCanvas.height = 52;
            trackCanvas.style.cssText = "display:block;width:100%;cursor:pointer;border-radius:0 0 4px 4px;background:#1e293b;";

            trackWrap.appendChild(rulerCanvas);
            trackWrap.appendChild(trackCanvas);
            tlArea.appendChild(trackWrap);
            body.appendChild(tlArea);

            // image strip（上游 batch 中所有图片的缩略图横排）
            const stripArea = document.createElement("div");
            stripArea.style.cssText = "flex-shrink:0;padding:8px 16px;background:#0f172a;border-bottom:1px solid rgba(148,163,184,.12);display:flex;align-items:center;gap:8px;overflow-x:auto;min-height:68px;";
            const stripLabel = document.createElement("span");
            stripLabel.textContent = "输入图片:";
            stripLabel.style.cssText = "color:#64748b;font-size:11px;flex-shrink:0;";
            stripArea.appendChild(stripLabel);
            body.appendChild(stripArea);

            const editArea = document.createElement("div");
            editArea.style.cssText = "flex:1;min-height:0;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:10px;";
            body.appendChild(editArea);

            // footer
            const footer = document.createElement("div");
            footer.style.cssText = "display:flex;align-items:center;justify-content:flex-end;gap:10px;padding:10px 14px;background:#0f172a;border-top:1px solid rgba(148,163,184,.18);flex-shrink:0;";

            const delBtn = document.createElement("button");
            delBtn.textContent = "🗑 删除选中段";
            delBtn.style.cssText = "padding:7px 14px;border-radius:7px;border:1px solid rgba(239,68,68,.5);background:transparent;color:#ef4444;cursor:pointer;font-size:13px;";
            delBtn.onclick = () => {
                if (!state.selId || state.segments.length <= 1) return;
                const idx = state.segments.findIndex(s => s.id === state.selId);
                if (idx < 0) return;
                const removed = state.segments.splice(idx, 1)[0];
                if (idx > 0) state.segments[idx-1].end = removed.end;
                else if (state.segments.length > 0) state.segments[0].start = removed.start;
                state.selId = state.segments[idx] ? state.segments[idx].id : state.segments[state.segments.length-1].id;
                redrawTimeline(); refreshEdit();
            };
            footer.appendChild(delBtn);

            const confirmBtn = document.createElement("button");
            confirmBtn.textContent = "✅ 确认输出";
            confirmBtn.style.cssText = "padding:8px 22px;border-radius:8px;border:none;background:#fb923c;color:#fff;cursor:pointer;font-weight:600;font-size:13px;";
            confirmBtn.onclick = () => { nodeRef._saveToWidget(); document.body.removeChild(panel); };
            footer.appendChild(confirmBtn);

            panel.appendChild(header);
            panel.appendChild(body);
            panel.appendChild(footer);
            document.body.appendChild(panel);

            // ── image strip 渲染 ──
            function buildStrip() {
                // 移除旧缩略图（保留 label）
                while (stripArea.children.length > 1) stripArea.removeChild(stripArea.lastChild);
                if (!state.thumbnails.length) {
                    const hint = document.createElement("span");
                    hint.textContent = "连接 image 输入并执行一次后显示缩略图";
                    hint.style.cssText = "color:#475569;font-size:11px;";
                    stripArea.appendChild(hint);
                    return;
                }
                state.thumbnails.forEach(t => {
                    const wrap = document.createElement("div");
                    wrap.style.cssText = "position:relative;flex-shrink:0;width:60px;height:52px;border-radius:5px;overflow:hidden;background:#1e293b;border:2px solid transparent;cursor:pointer;";
                    wrap.title = `图片 ${t.index}`;
                    if (t.url) {
                        const img = document.createElement("img");
                        img.src = t.url;
                        img.style.cssText = "width:100%;height:100%;object-fit:cover;";
                        wrap.appendChild(img);
                    }
                    const lbl = document.createElement("div");
                    lbl.textContent = t.index;
                    lbl.style.cssText = "position:absolute;bottom:1px;right:3px;font-size:10px;color:#e2e8f0;text-shadow:0 1px 2px #000;";
                    wrap.appendChild(lbl);
                    stripArea.appendChild(wrap);
                });
            }

            // ── timeline draw ──
            function tlWidth() { return trackCanvas.clientWidth || trackCanvas.offsetWidth || 800; }
            function frameToX(f) { return (f / state.total_frames) * tlWidth(); }
            function xToFrame(x) { return Math.round((x / tlWidth()) * state.total_frames); }

            const COLORS = ["#fb923c","#34d399","#60a5fa","#f472b6","#a78bfa","#facc15","#4ade80","#f87171"];

            function drawRuler() {
                const dpr = window.devicePixelRatio || 1;
                const w = tlWidth(), h = 22;
                rulerCanvas.width = Math.round(w * dpr); rulerCanvas.height = Math.round(h * dpr);
                rulerCanvas.style.width = w + "px"; rulerCanvas.style.height = h + "px";
                const ctx = rulerCanvas.getContext("2d");
                ctx.setTransform(dpr,0,0,dpr,0,0);
                ctx.fillStyle = "#0f172a"; ctx.fillRect(0,0,w,h);
                const step = state.total_frames <= 60 ? 5 : state.total_frames <= 200 ? 10 : state.total_frames <= 500 ? 25 : 50;
                for (let f = 0; f <= state.total_frames; f += step) {
                    const x = frameToX(f);
                    ctx.fillStyle = "#334155"; ctx.fillRect(x, 14, 1, 8);
                    ctx.fillStyle = "#64748b"; ctx.font = "10px monospace"; ctx.textAlign = "center";
                    ctx.fillText(f, x, 12);
                }
            }

            function drawTrack() {
                const dpr = window.devicePixelRatio || 1;
                const w = tlWidth(), h = 52;
                trackCanvas.width = Math.round(w * dpr); trackCanvas.height = Math.round(h * dpr);
                trackCanvas.style.width = w + "px"; trackCanvas.style.height = h + "px";
                const ctx = trackCanvas.getContext("2d");
                ctx.setTransform(dpr,0,0,dpr,0,0);
                ctx.fillStyle = "#1e293b"; ctx.fillRect(0,0,w,h);

                state.segments.forEach((seg, i) => {
                    const x1 = frameToX(seg.start), x2 = frameToX(seg.end);
                    const bw = Math.max(2, x2 - x1 - 2);
                    const col = COLORS[i % COLORS.length];
                    const sel = seg.id === state.selId;
                    ctx.fillStyle = sel ? col : col + "88";
                    ctx.beginPath(); ctx.roundRect(x1+1, 4, bw, 44, 5); ctx.fill();
                    if (sel) { ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.stroke(); }

                    if (seg.image_index !== null && seg.image_index !== undefined) {
                        ctx.fillStyle = sel ? "rgba(0,0,0,.5)" : "rgba(0,0,0,.35)";
                        ctx.font = "bold 10px sans-serif"; ctx.textAlign = "left";
                        ctx.fillText(`🖼${seg.image_index} [${seg.type||"flf"}]`, x1+6, 20);
                    } else {
                        ctx.fillStyle = "rgba(255,255,255,.45)";
                        ctx.font = "bold 10px sans-serif"; ctx.textAlign = "left";
                        ctx.fillText(seg.type || "flf", x1+6, 20);
                    }
                    const txt = seg.prompt || "(无提示词)";
                    ctx.fillStyle = sel ? "#fff" : "rgba(255,255,255,.7)";
                    ctx.font = "11px sans-serif"; ctx.textAlign = "left";
                    const maxW = bw - 12;
                    let display = txt;
                    while (ctx.measureText(display).width > maxW && display.length > 1) display = display.slice(0,-1);
                    if (display !== txt) display = display.slice(0,-1) + "…";
                    ctx.fillText(display, x1+6, (seg.image_index !== null && seg.image_index !== undefined) ? 38 : 30);

                    if (i < state.segments.length - 1) {
                        const hx = frameToX(seg.end);
                        ctx.fillStyle = "rgba(255,255,255,.6)"; ctx.fillRect(hx-2, 0, 4, h);
                    }
                });
            }

            function redrawTimeline() { drawRuler(); drawTrack(); }

            // ── track interaction ──
            let dragHandle = null;

            trackCanvas.onpointerdown = e => {
                const rect = trackCanvas.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width * tlWidth();
                for (let i = 0; i < state.segments.length - 1; i++) {
                    const hx = frameToX(state.segments[i].end);
                    if (Math.abs(x - hx) <= 6) {
                        dragHandle = { idx: i, startX: e.clientX, origEnd: state.segments[i].end };
                        trackCanvas.setPointerCapture(e.pointerId);
                        e.preventDefault(); return;
                    }
                }
                const f = xToFrame(x);
                const hit = state.segments.find(s => f >= s.start && f < s.end);
                if (hit) { state.selId = hit.id; redrawTimeline(); refreshEdit(); }
            };

            trackCanvas.onpointermove = e => {
                if (!dragHandle) return;
                const dx = e.clientX - dragHandle.startX;
                const df = Math.round(dx / tlWidth() * state.total_frames);
                const seg = state.segments[dragHandle.idx];
                const next = state.segments[dragHandle.idx + 1];
                const newEnd = Math.max(seg.start + 1, Math.min(next.end - 1, dragHandle.origEnd + df));
                seg.end = newEnd; next.start = newEnd;
                redrawTimeline();
            };

            trackCanvas.onpointerup = () => { dragHandle = null; };
            trackCanvas.onpointercancel = () => { dragHandle = null; };

            trackCanvas.onmousemove = e => {
                const rect = trackCanvas.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width * tlWidth();
                let onHandle = false;
                for (let i = 0; i < state.segments.length - 1; i++) {
                    if (Math.abs(x - frameToX(state.segments[i].end)) <= 6) { onHandle = true; break; }
                }
                trackCanvas.style.cursor = onHandle ? "ew-resize" : "pointer";
            };

            // ── edit panel ──
            function refreshEdit() {
                editArea.innerHTML = "";
                const seg = state.segments.find(s => s.id === state.selId);
                if (!seg) {
                    const hint = document.createElement("div");
                    hint.style.cssText = "color:#64748b;font-size:13px;margin-top:20px;text-align:center;";
                    hint.textContent = "点击时间轴上的段进行编辑";
                    editArea.appendChild(hint); return;
                }

                const idx = state.segments.indexOf(seg);
                const col = COLORS[idx % COLORS.length];

                const segTitle = document.createElement("div");
                segTitle.style.cssText = `font-size:13px;font-weight:700;color:${col};padding-bottom:4px;border-bottom:1px solid rgba(148,163,184,.1);`;
                segTitle.textContent = `段 ${idx+1}  ·  帧 ${seg.start} → ${seg.end}  (共 ${seg.end - seg.start} 帧)`;
                editArea.appendChild(segTitle);

                const promptLbl = document.createElement("div");
                promptLbl.textContent = "提示词"; promptLbl.style.cssText = "font-size:12px;color:#94a3b8;margin-top:4px;";
                editArea.appendChild(promptLbl);

                const promptTA = document.createElement("textarea");
                promptTA.value = seg.prompt;
                promptTA.placeholder = "输入这段的提示词...";
                promptTA.style.cssText = "width:100%;box-sizing:border-box;min-height:90px;padding:8px;border-radius:7px;background:#0f172a;color:#e2e8f0;border:1px solid rgba(148,163,184,.25);font-size:13px;resize:vertical;outline:none;";
                promptTA.oninput = () => { seg.prompt = promptTA.value; redrawTimeline(); };
                editArea.appendChild(promptTA);

                // 图片选择：从 thumbnails 中点选
                const imgLbl = document.createElement("div");
                imgLbl.textContent = "参考图（点击选择，再次点击取消）";
                imgLbl.style.cssText = "font-size:12px;color:#94a3b8;margin-top:8px;";
                editArea.appendChild(imgLbl);

                const thumbRow = document.createElement("div");
                thumbRow.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;";

                function buildThumbRow() {
                    thumbRow.innerHTML = "";
                    if (!state.thumbnails.length) {
                        const hint = document.createElement("span");
                        hint.textContent = "连接 image 输入并执行一次后显示";
                        hint.style.cssText = "color:#475569;font-size:11px;";
                        thumbRow.appendChild(hint);
                        return;
                    }
                    state.thumbnails.forEach(t => {
                        const wrap = document.createElement("div");
                        const selected = seg.image_index === t.index;
                        wrap.style.cssText = `position:relative;width:72px;height:56px;border-radius:6px;overflow:hidden;background:#0f172a;border:2px solid ${selected ? "#fb923c" : "rgba(148,163,184,.2)"};cursor:pointer;transition:border-color .15s;`;
                        if (t.url) {
                            const img = document.createElement("img");
                            img.src = t.url;
                            img.style.cssText = "width:100%;height:100%;object-fit:cover;";
                            wrap.appendChild(img);
                        }
                        const lbl = document.createElement("div");
                        lbl.textContent = t.index;
                        lbl.style.cssText = "position:absolute;bottom:1px;right:3px;font-size:10px;color:#e2e8f0;text-shadow:0 1px 2px #000;background:rgba(0,0,0,.4);padding:0 2px;border-radius:2px;";
                        wrap.appendChild(lbl);
                        if (selected) {
                            const check = document.createElement("div");
                            check.textContent = "✓";
                            check.style.cssText = "position:absolute;top:1px;left:3px;font-size:12px;color:#fb923c;text-shadow:0 1px 2px #000;";
                            wrap.appendChild(check);
                        }
                        wrap.onclick = () => {
                            seg.image_index = selected ? null : t.index;
                            buildThumbRow();
                            redrawTimeline();
                        };
                        thumbRow.appendChild(wrap);
                    });
                }
                buildThumbRow();
                editArea.appendChild(thumbRow);

                // 注册刷新回调（收到后端推送时刷新缩略图）
                nodeRef._refreshEditPanel = () => { buildStrip(); buildThumbRow(); };

                // 段类型选择
                const typeLbl = document.createElement("div");
                typeLbl.textContent = "图像帧类型";
                typeLbl.style.cssText = "font-size:12px;color:#94a3b8;margin-top:10px;";
                editArea.appendChild(typeLbl);

                const typeRow = document.createElement("div");
                typeRow.style.cssText = "display:flex;gap:6px;margin-top:4px;";
                const typeDescs = { flf: "首尾帧 (First/Last)", fmlf: "首中尾帧 (F/M/L)", ref: "参考帧 (Reference)" };
                for (const [t, desc] of Object.entries(typeDescs)) {
                    const btn = document.createElement("button");
                    btn.textContent = t;
                    btn.title = desc;
                    const active = (seg.type || "flf") === t;
                    btn.style.cssText = `padding:4px 12px;border-radius:5px;border:1px solid ${active ? "#fb923c" : "rgba(148,163,184,.3)"};background:${active ? "rgba(251,146,60,.15)" : "transparent"};color:${active ? "#fb923c" : "#94a3b8"};cursor:pointer;font-size:12px;font-weight:${active ? "700" : "400"};`;
                    btn.onclick = () => {
                        seg.type = t;
                        // 刷新所有按钮样式
                        typeRow.querySelectorAll("button").forEach(b => {
                            const isActive = b.textContent === t;
                            b.style.borderColor = isActive ? "#fb923c" : "rgba(148,163,184,.3)";
                            b.style.background = isActive ? "rgba(251,146,60,.15)" : "transparent";
                            b.style.color = isActive ? "#fb923c" : "#94a3b8";
                            b.style.fontWeight = isActive ? "700" : "400";
                        });
                        redrawTimeline();
                    };
                    typeRow.appendChild(btn);
                }
                editArea.appendChild(typeRow);

                // 帧范围
                const rangeRow = document.createElement("div");
                rangeRow.style.cssText = "display:flex;align-items:center;gap:8px;margin-top:10px;";
                const mkLbl = t => { const l = document.createElement("span"); l.textContent = t; l.style.cssText = "color:#64748b;font-size:12px;"; return l; };

                const startInput = document.createElement("input");
                startInput.type = "number"; startInput.min = 0; startInput.max = seg.end - 1; startInput.value = seg.start;
                startInput.style.cssText = "width:72px;padding:4px 6px;border-radius:5px;background:#0f172a;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:12px;";

                const endInput = document.createElement("input");
                endInput.type = "number"; endInput.min = seg.start + 1; endInput.max = state.total_frames; endInput.value = seg.end;
                endInput.style.cssText = "width:72px;padding:4px 6px;border-radius:5px;background:#0f172a;color:#cbd5e1;border:1px solid rgba(148,163,184,.3);font-size:12px;";

                const applyRange = () => {
                    const ns = Math.max(0, Math.min(parseInt(startInput.value)||0, seg.end-1));
                    const ne = Math.max(ns+1, Math.min(parseInt(endInput.value)||seg.end, state.total_frames));
                    if (ns !== seg.start && idx > 0) state.segments[idx-1].end = ns;
                    if (ne !== seg.end && idx < state.segments.length-1) state.segments[idx+1].start = ne;
                    seg.start = ns; seg.end = ne;
                    segTitle.textContent = `段 ${idx+1}  ·  帧 ${seg.start} → ${seg.end}  (共 ${seg.end - seg.start} 帧)`;
                    redrawTimeline();
                };
                startInput.onchange = applyRange; endInput.onchange = applyRange;

                rangeRow.appendChild(mkLbl("起始帧:")); rangeRow.appendChild(startInput);
                rangeRow.appendChild(mkLbl("结束帧:")); rangeRow.appendChild(endInput);
                editArea.appendChild(rangeRow);
            }

            buildStrip();
            redrawTimeline();
            if (state.segments.length) {
                if (!state.selId) state.selId = state.segments[0].id;
                refreshEdit();
            }

            const ro = new ResizeObserver(() => redrawTimeline());
            ro.observe(trackCanvas);
        };
    }
});
