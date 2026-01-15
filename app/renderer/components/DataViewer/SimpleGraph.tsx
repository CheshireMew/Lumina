import React, { useEffect, useState, useRef } from 'react';

interface SimpleGraphProps {
    nodes: any[];
    edges: any[];
    onNodeSelect: (node: any) => void;
}

// 核心图谱引擎 (v2: 支持缩放/平移/物理稳定)
export const SimpleGraph: React.FC<SimpleGraphProps> = ({ nodes, edges, onNodeSelect }) => {
    const parentRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const simulationRef = useRef<any[]>([]);
    
    // Canvas Size Management
    const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });
    
    // Resize Observer
    useEffect(() => {
        if (!parentRef.current) return;
        
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                setCanvasSize({ width, height });
            }
        });
        
        resizeObserver.observe(parentRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    // 视口状态 (Viewport)
    const [transform, setTransform] = useState({ x: 0, y: 0, k: 0.8 }); // k is scale
    
    const [isDraggingCanvas, setIsDraggingCanvas] = useState(false);
    const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
    
    // 交互状态
    const [draggingNode, setDraggingNode] = useState<any>(null);
    const [hoverNode, setHoverNode] = useState<any>(null);

    // 物理引擎状态
    const alphaRef = useRef(1.0); // 模拟热度，随时间衰减

    // 初始化/更新节点
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        
        // 增量更新：保留已有节点的位置，只为新节点随机位置
        const newNodes = nodes.map(n => {
            const existing = simulationRef.current.find(en => en.id === n.id);
            if (existing) {
                // 更新属性但保留物理状态
                return { ...existing, ...n, radius: n.group === 'character' ? 20 : (n.group === 'implicit' ? 6 : 12) };
            } else {
                return {
                    ...n,
                    x: Math.random() * canvasSize.width, 
                    y: Math.random() * canvasSize.height,
                    vx: 0,
                    vy: 0,
                    radius: n.group === 'character' ? 20 : (n.group === 'implicit' ? 6 : 12)
                };
            }
        });
        
        simulationRef.current = newNodes;
        alphaRef.current = 1.0; // 数据更新时重置热度，重新布局
    }, [nodes, canvasSize]); // 依赖 nodes 和 canvasSize 变化

    // 动画与物理循环
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;

        const animate = () => {
            if (!canvas) return;
            
            // 物理计算步进 (当热度 alpha > 0.01 或 正在拖拽时计算)
            if (alphaRef.current > 0.01 || draggingNode) {
                simulationRef.current.forEach(node => {
                    if (node === draggingNode) return;

                    // 1. 向心力 (Centering) - 弱
                    const cx = canvasSize.width / 2;
                    const cy = canvasSize.height / 2;
                    node.vx += (cx - node.x) * 0.002 * alphaRef.current;
                    node.vy += (cy - node.y) * 0.002 * alphaRef.current;

                    // 2. 斥力 (Many-Body Repulsion) - 强
                    simulationRef.current.forEach(other => {
                        if (node === other) return;
                        const dx = node.x - other.x;
                        const dy = node.y - other.y;
                        let dist = Math.sqrt(dx*dx + dy*dy);
                        if (dist < 1) dist = 1; 
                        
                        // 距离越近斥力越大
                        if (dist < 300) {
                            const force = (200 * alphaRef.current) / (dist * 0.8);
                            node.vx += (dx / dist) * force;
                            node.vy += (dy / dist) * force;
                        }
                    });

                    // 3. 连接力 (Link Spring)
                    edges.forEach(edge => {
                         // 查找端点对象
                        const src = simulationRef.current.find(n => n.id === edge.from);
                        const dst = simulationRef.current.find(n => n.id === edge.to);
                        
                        if (src && dst) {
                            if (src === node) {
                                const dx = dst.x - node.x;
                                const dy = dst.y - node.y;
                                node.vx += dx * 0.015 * alphaRef.current;
                                node.vy += dy * 0.015 * alphaRef.current;
                            } else if (dst === node) {
                                const dx = src.x - node.x;
                                const dy = src.y - node.y;
                                node.vx += dx * 0.015 * alphaRef.current;
                                node.vy += dy * 0.015 * alphaRef.current;
                            }
                        }
                    });

                    // 速度限制与阻尼
                    node.vx *= 0.9 + (0.05 * (1 - alphaRef.current)); // 随着稳定阻尼增加
                    node.vy *= 0.9 + (0.05 * (1 - alphaRef.current));
                    
                    node.x += node.vx;
                    node.y += node.vy;
                });
                
                // 热度衰减
                if (!draggingNode) {
                    alphaRef.current *= 0.99; // 每一帧衰减
                } else {
                    alphaRef.current = 0.3; // 拖拽时保持一定热度以响应变化
                }
            }

            // --- 渲染阶段 ---
            ctx.save();
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 应用视口变换 (Pan/Zoom)
            ctx.translate(transform.x, transform.y);
            ctx.scale(transform.k, transform.k);

            // 绘制连线
            ctx.lineWidth = 1;
            edges.forEach(edge => {
                const src = simulationRef.current.find(n => n.id === edge.from);
                const dst = simulationRef.current.find(n => n.id === edge.to);
                if (src && dst) {
                    const isFocus = (src === hoverNode || dst === hoverNode);
                    
                    ctx.beginPath();
                    ctx.moveTo(src.x, src.y);
                    ctx.lineTo(dst.x, dst.y);
                    
                    // Neon lines
                    ctx.strokeStyle = isFocus ? '#fff' : 'rgba(139, 92, 246, 0.3)';
                    ctx.lineWidth = isFocus ? 2 / transform.k : 1 / transform.k;
                    ctx.stroke();

                     // 标签
                    if (isFocus || transform.k > 1.2) {
                        ctx.fillStyle = isFocus ? '#fff' : 'rgba(255,255,255,0.6)';
                        ctx.font = `${10/transform.k}px Arial`;
                        ctx.fillText(edge.label || '', (src.x + dst.x)/2, (src.y + dst.y)/2);
                    }
                }
            });

            // 绘制节点
            simulationRef.current.forEach(node => {
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
                
                // Neon Nodes
                let color = '#94a3b8';
                let glow = 'transparent';
                
                if (node.group === 'character') { color = '#f472b6'; glow = 'rgba(244, 114, 182, 0.5)'; }
                else if (node.group === 'knowledge') { color = '#60a5fa'; glow = 'rgba(96, 165, 250, 0.5)'; }
                else if (node.group === 'agent') { color = '#a78bfa'; glow = 'rgba(167, 139, 250, 0.5)'; }
                
                ctx.shadowBlur = 10;
                ctx.shadowColor = glow;
                ctx.fillStyle = color;
                ctx.fill();
                ctx.shadowBlur = 0; // reset
                
                if (node === hoverNode || node === draggingNode) {
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 2 / transform.k;
                    ctx.stroke();
                }

                if (transform.k > 0.6 || node.group === 'character') {
                     ctx.fillStyle = '#f1f5f9';
                     ctx.font = `${12/transform.k}px "Segoe UI", sans-serif`;
                     ctx.fillText(node.label || node.id, node.x + node.radius + 4, node.y + (4/transform.k));
                }
            });

            ctx.restore();
            animationFrameId = requestAnimationFrame(animate);
        };
        
        animate();
        return () => cancelAnimationFrame(animationFrameId);
    }, [nodes, edges, draggingNode, hoverNode, transform, canvasSize]);

    // --- 事件处理 (坐标映射逻辑) ---
    const toWorldPos = (clientX: number, clientY: number) => {
        if (!canvasRef.current) return {x:0,y:0};
        const rect = canvasRef.current.getBoundingClientRect();
        return {
            x: (clientX - rect.left - transform.x) / transform.k,
            y: (clientY - rect.top - transform.y) / transform.k
        };
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        const worldPos = toWorldPos(e.clientX, e.clientY);
        
        const clickedNode = simulationRef.current.find(node => {
            const dx = node.x - worldPos.x;
            const dy = node.y - worldPos.y;
            return Math.sqrt(dx*dx + dy*dy) < (node.radius + 5 / transform.k);
        });

        if (clickedNode) {
            setDraggingNode(clickedNode);
            onNodeSelect(clickedNode);
            alphaRef.current = 0.5;
        } else {
            setIsDraggingCanvas(true);
            setLastMousePos({ x: e.clientX, y: e.clientY });
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (draggingNode) {
             const worldPos = toWorldPos(e.clientX, e.clientY);
             draggingNode.x = worldPos.x;
             draggingNode.y = worldPos.y;
             draggingNode.vx = 0; 
             draggingNode.vy = 0;
             return;
        }
        if (isDraggingCanvas) {
            const dx = e.clientX - lastMousePos.x;
            const dy = e.clientY - lastMousePos.y;
            setTransform(t => ({ ...t, x: t.x + dx, y: t.y + dy }));
            setLastMousePos({ x: e.clientX, y: e.clientY });
            return;
        }
        const worldPos = toWorldPos(e.clientX, e.clientY);
        const hovered = simulationRef.current.find(node => {
            const dx = node.x - worldPos.x;
            const dy = node.y - worldPos.y;
            return Math.sqrt(dx*dx + dy*dy) < (node.radius + 5 / transform.k);
        });
        setHoverNode(hovered || null);
    };

    const handleMouseUp = () => {
        setDraggingNode(null);
        setIsDraggingCanvas(false);
    };

    const handleWheel = (e: React.WheelEvent) => {
        const zoomIntensity = 0.1;
        const delta = e.deltaY > 0 ? -zoomIntensity : zoomIntensity;
        let newK = transform.k * (1 + delta);
        if (newK < 0.1) newK = 0.1;
        if (newK > 5) newK = 5;
        setTransform(t => ({ ...t, k: newK }));
    };

    return (
        <div ref={parentRef} style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
            <canvas 
                ref={canvasRef} 
                width={canvasSize.width} 
                height={canvasSize.height}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onWheel={handleWheel}
                style={{ width: '100%', height: '100%', cursor: isDraggingCanvas ? 'grabbing' : (hoverNode ? 'pointer' : 'default') }}
            />
            <div style={{
                position: 'absolute', bottom: '15px', right: '15px',
                display: 'flex', gap: '10px'
            }}>
                 <button 
                    onClick={() => setTransform({ x: 0, y: 0, k: 0.8 })}
                    style={{
                        padding: '6px 12px', background: 'rgba(255,255,255,0.1)',
                        border: '1px solid rgba(255,255,255,0.2)', borderRadius: '20px',
                        color: '#fff', fontSize: '11px', cursor: 'pointer',
                        backdropFilter: 'blur(5px)'
                    }}
                >
                    Reset View
                </button>
            </div>
        </div>
    );
};
