/**
 * DataViewer - 通用数据可视化组件 (Refactored)
 * 包含：表浏览、数据查看、查询控制台
 */
import React, { useState } from "react";
import { Database, X, RefreshCw, Network } from "lucide-react";

import { Sidebar } from "./Sidebar";
import { TableSection } from "./TableSection";
import { SimpleGraph } from "./SimpleGraph";
import { RecordEditor } from "./RecordEditor";
import { EdgeDetailModal } from "./EdgeDetailModal";
import { useDataViewerGraph } from "./useDataViewerGraph";
import { useDataViewerTables } from "./useDataViewerTables";
import type { DataViewerProps } from "./types";

const DataViewer: React.FC<DataViewerProps> = ({
    isOpen,
    onClose,
    activeCharacterId,
}) => {
    const [activeTab, setActiveTab] = useState<
        "tables" | "query" | "stats" | "graph"
    >("tables");

    const graph = useDataViewerGraph({
        isOpen,
        activeTab,
        activeCharacterId,
    });

    const tables = useDataViewerTables({
        isOpen,
        activeCharacterId,
        refreshGraph: graph.loadGraph,
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
                style={{
                    background:
                        "linear-gradient(145deg, rgba(30, 20, 40, 0.95), rgba(45, 20, 60, 0.98))",
                    borderRadius: "24px",
                    width: "900px",
                    height: "650px",
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
                                Memory Core
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
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
                        activeTab={activeTab}
                        selectedTable={tables.selectedTable}
                        onTabChange={setActiveTab}
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
                        {activeTab === "tables" && (
                            <TableSection
                                selectedTable={tables.selectedTable}
                                tableData={tables.tableData}
                                loading={tables.loading || graph.loading}
                                graphData={graph.graphData}
                                onRefreshTable={tables.refreshTable}
                                onRefreshGraph={() => {
                                    void graph.loadGraph();
                                }}
                                onCreateRecord={tables.handleCreateRecord}
                                onEditRecord={tables.handleEditRecord}
                                onDeleteRecord={tables.handleDeleteRecord}
                                onEdgeClick={graph.setDetailEdge}
                            />
                        )}

                        {activeTab === "graph" && (
                            <div
                                style={{
                                    height: "100%",
                                    display: "flex",
                                    position: "relative",
                                }}
                            >
                                <div
                                    style={{
                                        flex: 1,
                                        display: "flex",
                                        flexDirection: "column",
                                    }}
                                >
                                    <div
                                        style={{
                                            padding: "15px 25px",
                                            display: "flex",
                                            justifyContent: "space-between",
                                            alignItems: "center",
                                            background: "rgba(0,0,0,0.1)",
                                        }}
                                    >
                                        <h3
                                            style={{
                                                display: "flex",
                                                alignItems: "center",
                                                gap: "10px",
                                                margin: 0,
                                                color: "#c084fc",
                                            }}
                                        >
                                            <Network size={20} /> Knowledge Graph
                                        </h3>
                                        <div style={{ display: "flex", gap: "15px" }}>
                                            <button
                                                onClick={() => {
                                                    void graph.loadGraph();
                                                }}
                                                style={{
                                                    padding: "6px 14px",
                                                    backgroundColor:
                                                        "rgba(139, 92, 246, 0.2)",
                                                    color: "#ddd6fe",
                                                    border:
                                                        "1px solid rgba(139, 92, 246, 0.4)",
                                                    borderRadius: "6px",
                                                    cursor: "pointer",
                                                }}
                                            >
                                                <RefreshCw size={12} /> Refresh
                                            </button>
                                        </div>
                                    </div>
                                    <div
                                        style={{
                                            flex: 1,
                                            position: "relative",
                                            overflow: "hidden",
                                            backgroundColor: "rgba(15, 23, 42, 0.4)",
                                        }}
                                    >
                                        <SimpleGraph
                                            nodes={graph.graphData?.nodes || []}
                                            edges={graph.graphData?.edges || []}
                                            onNodeSelect={graph.setSelectedNode}
                                        />
                                    </div>
                                </div>
                                {graph.selectedNode && (
                                    <div
                                        style={{
                                            width: "280px",
                                            borderLeft:
                                                "1px solid rgba(255, 105, 180, 0.1)",
                                            backgroundColor:
                                                "rgba(20, 10, 30, 0.6)",
                                            display: "flex",
                                            flexDirection: "column",
                                            padding: "20px",
                                            backdropFilter: "blur(15px)",
                                        }}
                                    >
                                        <div
                                            style={{
                                                display: "flex",
                                                justifyContent: "space-between",
                                                marginBottom: "20px",
                                            }}
                                        >
                                            <h3 style={{ margin: 0, color: "#fff" }}>
                                                {graph.selectedNode.label}
                                            </h3>
                                            <button
                                                onClick={() => graph.setSelectedNode(null)}
                                                style={{
                                                    background: "none",
                                                    border: "none",
                                                    color: "rgba(255,255,255,0.5)",
                                                    cursor: "pointer",
                                                }}
                                            >
                                                <X size={18} />
                                            </button>
                                        </div>
                                        <div
                                            style={{
                                                fontSize: "11px",
                                                color: "rgba(255,255,255,0.4)",
                                            }}
                                        >
                                            ID: {graph.selectedNode.id}
                                        </div>
                                        <div
                                            style={{
                                                fontSize: "12px",
                                                color: "#f472b6",
                                                fontWeight: "600",
                                            }}
                                        >
                                            Type: {graph.selectedNode.group}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                <RecordEditor
                    editingRecord={tables.editingRecord}
                    isCreating={tables.isCreating}
                    editorForm={tables.editorForm}
                    setEditorForm={tables.setEditorForm}
                    onCancel={tables.closeEditor}
                    onSave={() => {
                        void tables.handleSaveRecord();
                    }}
                />

                <EdgeDetailModal
                    detailEdge={graph.detailEdge}
                    onClose={() => graph.setDetailEdge(null)}
                />
            </div>
        </div>
    );
};

export default DataViewer;
