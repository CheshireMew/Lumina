import React from "react";
import { Brain, ScrollText, Workflow } from "lucide-react";

import { getTableViewMeta } from "./utils";

interface SidebarProps {
    selectedTable: string | null;
    onTableSelect: (tableName: string) => void;
}

const tableItems = [
    { table: "conversation_turns", icon: ScrollText },
    { table: "memory_items", icon: Brain },
    { table: "memory_consolidation_jobs", icon: Workflow },
];

export const Sidebar: React.FC<SidebarProps> = ({
    selectedTable,
    onTableSelect,
}) => {
    return (
        <div
            style={{
                width: "clamp(150px, 26vw, 240px)",
                backgroundColor: "rgba(20, 10, 30, 0.3)",
                borderRight: "1px solid rgba(255, 105, 180, 0.1)",
                display: "flex",
                flexDirection: "column",
                backdropFilter: "blur(10px)",
            }}
        >
            <div
                style={{
                    padding: "20px 20px 10px",
                    fontSize: "11px",
                    fontWeight: "800",
                    color: "#f472b6",
                    textTransform: "uppercase",
                    letterSpacing: "1px",
                }}
            >
                记忆流程
            </div>

            {tableItems.map(({ table, icon: Icon }) => {
                const active = selectedTable === table;
                const meta = getTableViewMeta(table);

                return (
                    <button
                        type="button"
                        key={table}
                        onClick={() => {
                            onTableSelect(table);
                        }}
                        style={{
                            padding: "12px 20px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                            background: active
                                ? "linear-gradient(90deg, rgba(236, 72, 153, 0.15), transparent)"
                                : "transparent",
                            color: active ? "#fff" : "rgba(255,255,255,0.6)",
                            borderLeft: active
                                ? "3px solid #ec4899"
                                : "3px solid transparent",
                            transition: "all 0.2s",
                            width: "100%",
                            borderTop: "none",
                            borderRight: "none",
                            borderBottom: "none",
                            textAlign: "left",
                        }}
                    >
                        <Icon size={18} style={{ flexShrink: 0 }} />
                        <div style={{ minWidth: 0 }}>
                            <div
                                style={{
                                    fontSize: "14px",
                                    fontWeight: active ? "600" : "400",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                }}
                            >
                                {meta.sidebarLabel}
                            </div>
                            <div
                                style={{
                                    fontSize: "11px",
                                    color: active
                                        ? "rgba(255,255,255,0.62)"
                                        : "rgba(255,255,255,0.38)",
                                    marginTop: "2px",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                }}
                            >
                                {meta.sidebarHint}
                            </div>
                        </div>
                    </button>
                );
            })}
        </div>
    );
};
