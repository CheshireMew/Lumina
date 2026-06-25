import React from "react";
import { Edit, Plus, RefreshCw, Table as TableIcon, Trash2 } from "lucide-react";

import {
    formatCellValue,
    getColumnLabel,
    getOrderedColumns,
    getTableViewMeta,
} from "./utils";

interface TableSectionProps {
    selectedTable: string | null;
    tableData: any[];
    loading: boolean;
    onRefreshTable: () => void;
    onCreateRecord: () => void;
    onEditRecord: (row: any) => void;
    onDeleteRecord: (id: any) => void;
}

export const TableSection: React.FC<TableSectionProps> = ({
    selectedTable,
    tableData,
    loading,
    onRefreshTable,
    onCreateRecord,
    onEditRecord,
    onDeleteRecord,
}) => {
    const meta = getTableViewMeta(selectedTable);
    const columns = getOrderedColumns(tableData, selectedTable);

    return (
        <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div
                style={{
                    padding: "15px 25px",
                    borderBottom: "1px solid rgba(255, 105, 180, 0.1)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "rgba(0,0,0,0.1)",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
                    <TableIcon size={18} color="#f472b6" />
                    <div style={{ minWidth: 0 }}>
                        <div
                            style={{
                                fontWeight: "700",
                                color: "#fff",
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                fontSize: "16px",
                                flexWrap: "wrap",
                            }}
                        >
                            <span>{meta.title}</span>
                            <span
                                style={{
                                    color: "#f9a8d4",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    background: "rgba(236, 72, 153, 0.12)",
                                    border: "1px solid rgba(236, 72, 153, 0.25)",
                                    borderRadius: "999px",
                                    padding: "2px 8px",
                                }}
                            >
                                {tableData.length} {meta.countLabel}
                            </span>
                            <span
                                style={{
                                    color: "rgba(255,255,255,0.42)",
                                    fontSize: "11px",
                                    fontFamily: "monospace",
                                    fontWeight: 500,
                                }}
                            >
                                {meta.technicalName}
                            </span>
                        </div>
                        <div
                            style={{
                                color: "rgba(255,255,255,0.55)",
                                fontSize: "12px",
                                marginTop: "3px",
                                whiteSpace: "nowrap",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                            }}
                        >
                            {meta.subtitle}
                        </div>
                    </div>
                </div>
                <div style={{ display: "flex", gap: "10px" }}>
                    <button
                        onClick={onRefreshTable}
                        style={{
                            cursor: "pointer",
                            background: "none",
                            border: "none",
                            color: "#f472b6",
                        }}
                        title="Refresh"
                    >
                        <RefreshCw size={18} />
                    </button>
                    <button
                        onClick={onCreateRecord}
                        style={{
                            cursor: "pointer",
                            background: "linear-gradient(135deg, #ec4899, #8b5cf6)",
                            border: "none",
                            color: "white",
                            padding: "6px 12px",
                            borderRadius: "6px",
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            fontSize: "12px",
                                    fontWeight: "600",
                        }}
                    >
                        <Plus size={14} /> New
                    </button>
                </div>
            </div>
            <div style={{ flex: 1, overflow: "auto" }}>
                {loading ? (
                    <div
                        style={{
                            padding: "30px",
                            color: "#f472b6",
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                            fontSize: "14px",
                        }}
                    >
                        <RefreshCw className="spin" size={20} /> Loading data from Core...
                    </div>
                ) : (
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                        <thead>
                            <tr
                                style={{
                                    textAlign: "left",
                                    backgroundColor: "rgba(0,0,0,0.2)",
                                    color: "#a5b4fc",
                                    position: "sticky",
                                    top: 0,
                                    zIndex: 1,
                                    backdropFilter: "blur(4px)",
                                }}
                            >
                                <th style={{ padding: "12px 15px", width: "40px", textAlign: "center" }}>
                                    #
                                </th>
                                <th style={{ padding: "12px 15px", width: "90px" }}>Action</th>
                                {columns.map((col) => (
                                    <th
                                        key={col}
                                        style={{
                                            padding: "12px 15px",
                                            whiteSpace: "nowrap",
                                            fontWeight: "600",
                                        }}
                                    >
                                        {getColumnLabel(col)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {tableData.map((row, i) => (
                                <tr
                                    key={i}
                                    style={{
                                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                                        backgroundColor:
                                            i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
                                    }}
                                >
                                    <td
                                        style={{
                                            padding: "12px 15px",
                                            color: "#e2e8f0",
                                            verticalAlign: "top",
                                            textAlign: "center",
                                            opacity: 0.5,
                                            fontFamily: "monospace",
                                        }}
                                    >
                                        {i + 1}
                                    </td>
                                    <td
                                        style={{
                                            padding: "12px 15px",
                                            verticalAlign: "top",
                                            width: "90px",
                                            display: "flex",
                                            gap: "5px",
                                        }}
                                    >
                                        <button
                                            onClick={() => onEditRecord(row)}
                                            style={{
                                                background: "rgba(255, 255, 255, 0.1)",
                                                border: "1px solid rgba(255, 255, 255, 0.2)",
                                                color: "#f472b6",
                                                borderRadius: "6px",
                                                padding: "6px",
                                                cursor: "pointer",
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                            }}
                                            title="Edit Record"
                                        >
                                            <Edit size={14} />
                                        </button>
                                        <button
                                            onClick={() => onDeleteRecord(row.id)}
                                            style={{
                                                background: "rgba(239, 68, 68, 0.1)",
                                                border: "1px solid rgba(239, 68, 68, 0.2)",
                                                color: "#f87171",
                                                borderRadius: "6px",
                                                padding: "6px",
                                                cursor: "pointer",
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                            }}
                                            title="Delete Record"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </td>
                                    {columns.map((col) => (
                                        <td
                                            key={col}
                                            style={{
                                                padding: "12px 15px",
                                                color: "#e2e8f0",
                                                verticalAlign: "top",
                                            }}
                                        >
                                            {formatCellValue(col, row[col])}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};
