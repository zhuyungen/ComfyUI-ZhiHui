import { app } from "../../scripts/app.js";

// 为智绘运行节点添加seed控制功能
app.registerExtension({
    name: "ZHIHUI.SeedControl",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "ZH_RunNode") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // 找到seed widget
                const seedWidget = this.widgets?.find((w) => w.name === "seed");
                if (seedWidget) {
                    // 保存原始的callback
                    const originalCallback = seedWidget.callback;

                    // 设置随机化函数
                    seedWidget.afterQueued = function() {
                        const randomSeed = Math.floor(Math.random() * 1125899906842624);
                        seedWidget.value = randomSeed;
                        if (originalCallback) {
                            originalCallback(randomSeed);
                        }
                    };
                }

                return r;
            };

            // 监听执行完成事件
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                const r = onExecuted ? onExecuted.apply(this, arguments) : undefined;

                // 找到seed widget并更新值
                const seedWidget = this.widgets?.find((w) => w.name === "seed");
                if (seedWidget && seedWidget.afterQueued) {
                    seedWidget.afterQueued();
                }

                return r;
            };
        }
    },
});
