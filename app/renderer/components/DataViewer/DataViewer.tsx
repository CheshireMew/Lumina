/**
 * DataViewer - 通用数据可视化组件 (Refactored)
 * 包含：表浏览、数据查看、查询控制台
 */
import React from "react";
import { Database, X } from "lucide-react";

import { useDialogAccessibility } from "../../hooks/useDialogAccessibility";
import { Sidebar } from "./Sidebar";
import { TableSection } from "./TableSection";
import { useDataViewerTables } from "./useDataViewerTables";
import type { DataViewerProps } from "./types";

const DataViewer: React.FC<DataViewerProps> = ({
    isOpen,
    onClose,
    activeCharacterId,
    apiBaseUrl,
}) => {
    const dialogRef = useDialogAccessibility<HTMLDivElement>(isOpen, onClose);
    const tables = useDataViewerTables({
        isOpen,
        activeCharacterId,
        apiBaseUrl,
    });

    if (!isOpen) return null;

    return (
        <div
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(20, 10, 30, 0.4)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                zIndex: 1001,
                backdropFilter: "blur(8px)",
                transition: "all 0.3s ease",
            }}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="memory-viewer-title"
                tabIndex={-1}
                style={{
                    background:
                        "linear-gradient(145deg, rgba(30, 20, 40, 0.95), rgba(45, 20, 60, 0.98))",
                    borderRadius: "24px",
                    width: "min(900px, calc(100vw - 32px))",
                    height: "min(650px, calc(100vh - 32px))",
                    boxShadow:
                        "0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(255, 105, 180, 0.1)",
                    display: "flex",
                    flexDirection: "column",
                    fontFamily: '"Outfit", "Segoe UI", sans-serif',
                    color: "#e0e0e0",
                    overflow: "hidden",
                }}
            >
                <div
                    style={{
                        padding: "15px 25px",
                        background: "rgba(255, 105, 180, 0.05)",
                        borderBottom: "1px solid rgba(255, 105, 180, 0.15)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        height: "60px",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div
                            style={{
                                width: "36px",
                                height: "36px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                background: "linear-gradient(135deg, #ec4899, #8b5cf6)",
                                borderRadius: "10px",
                            }}
                        >
                            <Database size={20} color="white" />
                        </div>
                        <div>
                            <span
                                style={{
                                    fontWeight: "700",
                                    fontSize: "18px",
                                    color: "#fff",
                                }}
                            >
                                <span id="memory-viewer-title">记忆数据</span>
                            </span>
                            <div
                                style={{
                                    color: "rgba(255,255,255,0.5)",
                                    fontSize: "12px",
                                    marginTop: "2px",
                                }}
                            >
                                对话历史与长期记忆
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="关闭记忆数据"
                        style={{
                            background: "none",
                            border: "none",
                            color: "#f472b6",
                            cursor: "pointer",
                        }}
                    >
                        <X size={24} />
                    </button>
                </div>

                <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
                    <Sidebar
                        selectedTable={tables.selectedTable}
                        onTableSelect={tables.loadTableData}
                    />

                    <div
                        style={{
                            flex: 1,
                            overflow: "hidden",
                            display: "flex",
                            flexDirection: "column",
                            backgroundColor: "rgba(0,0,0,0.2)",
                        }}
                    >
                        <TableSection
                            selectedTable={tables.selectedTable}
                            tableData={tables.tableData}
                            loading={tables.loading}
                            onRefreshTable={tables.refreshTable}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DataViewer;
