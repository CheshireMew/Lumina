import React from "react";
import { CheckCircle, Clock } from "lucide-react";

export interface TableViewMeta {
    title: string;
    sidebarLabel: string;
    sidebarHint: string;
    singular: string;
    subtitle: string;
    countLabel: string;
    technicalName: string;
}

const fallbackTableMeta: TableViewMeta = {
    title: "数据记录",
    sidebarLabel: "数据记录",
    sidebarHint: "已保存的数据行",
    singular: "记录",
    subtitle: "可检查的本地数据记录。",
    countLabel: "条",
    technicalName: "table",
};

export const tableViewMeta: Record<string, TableViewMeta> = {
    conversation_turns: {
        title: "对话历史",
        sidebarLabel: "对话历史",
        sidebarHint: "原始对话内容",
        singular: "对话轮次",
        subtitle: "提炼为长期记忆前保存的完整对话。",
        countLabel: "轮",
        technicalName: "conversation_turns",
    },
    memory_items: {
        title: "长期记忆",
        sidebarLabel: "长期记忆",
        sidebarHint: "对话时可回忆的内容",
        singular: "记忆项",
        subtitle: "对话时可供角色回忆的事实与偏好。",
        countLabel: "条",
        technicalName: "memory_items",
    },
    memory_consolidation_jobs: {
        title: "记忆整理队列",
        sidebarLabel: "记忆整理",
        sidebarHint: "从历史提炼记忆",
        singular: "整理任务",
        subtitle: "把对话历史提炼为长期记忆的后台任务。",
        countLabel: "项",
        technicalName: "memory_consolidation_jobs",
    },
};

const tableColumnOrder: Record<string, string[]> = {
    conversation_turns: [
        "narrative",
        "user_message",
        "assistant_message",
        "processed_at",
        "created_at",
        "session_id",
        "user_id",
        "character_id",
    ],
    memory_items: [
        "content",
        "summary",
        "memory_type",
        "scope",
        "status",
        "importance",
        "confidence",
        "source_turn_ids",
        "created_at",
        "updated_at",
        "last_used_at",
        "user_id",
        "character_id",
    ],
    memory_consolidation_jobs: [
        "status",
        "turn_ids",
        "error",
        "created_at",
        "updated_at",
        "user_id",
        "character_id",
    ],
};

const columnLabels: Record<string, string> = {
    id: "ID",
    narrative: "对话",
    user_message: "用户内容",
    assistant_message: "角色回复",
    processed_at: "记忆状态",
    created_at: "创建时间",
    updated_at: "更新时间",
    last_used_at: "最后使用",
    session_id: "会话",
    user_id: "用户",
    character_id: "角色",
    content: "记忆内容",
    summary: "摘要",
    memory_type: "类型",
    scope: "范围",
    status: "状态",
    importance: "重要程度",
    confidence: "可信度",
    source_turn_ids: "来源对话",
    turn_ids: "对话轮次",
    error: "错误",
    name: "名称",
    type: "类型",
};

const hiddenColumns = new Set(["id", "embedding", "vector", "metadata"]);

const statusColors: Record<string, { color: string; background: string; border: string }> = {
    active: {
        color: "#a7f3d0",
        background: "rgba(5, 150, 105, 0.18)",
        border: "rgba(5, 150, 105, 0.35)",
    },
    pending: {
        color: "#fde68a",
        background: "rgba(180, 83, 9, 0.18)",
        border: "rgba(180, 83, 9, 0.35)",
    },
    completed: {
        color: "#a7f3d0",
        background: "rgba(5, 150, 105, 0.18)",
        border: "rgba(5, 150, 105, 0.35)",
    },
    failed: {
        color: "#fecaca",
        background: "rgba(220, 38, 38, 0.18)",
        border: "rgba(220, 38, 38, 0.35)",
    },
};

export const getTableViewMeta = (tableName: string | null | undefined): TableViewMeta => {
    if (!tableName) {
        return fallbackTableMeta;
    }

    return tableViewMeta[tableName] || {
        ...fallbackTableMeta,
        title: tableName,
        sidebarLabel: tableName,
        technicalName: tableName,
    };
};

export const getColumnLabel = (key: string) => {
    return columnLabels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const renderStatusPill = (label: string, palette = statusColors.pending) => (
    <span
        style={{
            color: palette.color,
            background: palette.background,
            padding: "2px 7px",
            borderRadius: "12px",
            fontSize: "11px",
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            width: "fit-content",
            border: `1px solid ${palette.border}`,
            whiteSpace: "nowrap",
        }}
    >
        {label}
    </span>
);

export const formatCellValue = (key: string, value: any) => {
    if (key === "processed_at") {
        return value ?
            <span style={{color:"#a7f3d0", background:"rgba(5, 150, 105, 0.2)", padding:"2px 6px", borderRadius:"12px", fontSize:"11px", display:"flex", alignItems:"center", gap:"4px", width:"fit-content", border:"1px solid rgba(5, 150, 105, 0.4)", whiteSpace: "nowrap"}}>
                <CheckCircle size={10} /> 已提炼
            </span> :
            <span style={{color:"#fde68a", background:"rgba(180, 83, 9, 0.2)", padding:"2px 6px", borderRadius:"12px", fontSize:"11px", display:"flex", alignItems:"center", gap:"4px", width:"fit-content", border:"1px solid rgba(180, 83, 9, 0.4)", whiteSpace: "nowrap"}}>
                <Clock size={10} /> 未提炼
            </span>;
    }

    if (value === null || value === undefined || value === "") return <span style={{color:"rgba(255,255,255,0.3)"}}>-</span>;

    const isLikelyDate = key === "created_at" || key === "updated_at" || key === "timestamp" || key === "date" || key.endsWith("_at");
    if (isLikelyDate) {
        try {
            return <span style={{fontSize:"12px", color:"#9ca3af", whiteSpace: "nowrap"}}>{new Date(value).toLocaleString()}</span>;
        } catch (e) { return value; }
    }

    if (key === "status" && typeof value === "string") {
        const normalized = value.toLowerCase();
        return renderStatusPill(value, statusColors[normalized] || statusColors.pending);
    }

    if ((key === "importance" || key === "confidence" || key === "weight") && typeof value === "number") {
        return <span style={{ color: "#e9d5ff", fontVariantNumeric: "tabular-nums" }}>{value.toFixed(2)}</span>;
    }

    if (Array.isArray(value)) {
        return (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px", minWidth: "140px" }}>
                {value.length === 0 ? (
                    <span style={{color:"rgba(255,255,255,0.3)"}}>-</span>
                ) : value.map((item, index) => (
                    <span
                        key={`${String(item)}-${index}`}
                        title={String(item)}
                        style={{
                            border: "1px solid rgba(165, 180, 252, 0.22)",
                            color: "#c7d2fe",
                            background: "rgba(99, 102, 241, 0.12)",
                            borderRadius: "10px",
                            padding: "2px 6px",
                            fontSize: "11px",
                            maxWidth: "120px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                        }}
                    >
                        {String(item)}
                    </span>
                ))}
            </div>
        );
    }

    if (key === "id" && typeof value === "string") {
        return value.includes(":") ? <span title={value} style={{fontFamily:"monospace", color:"#f472b6"}}>{value.split(":")[1]}</span> : value;
    }

    if (typeof value === "object") {
        return (
            <div style={{maxHeight:"72px", overflowY:"auto", fontSize:"11px", fontFamily:"monospace", whiteSpace:"pre-wrap", color:"rgba(255,255,255,0.7)", minWidth: "180px"}}>
                {JSON.stringify(value, null, 2)}
            </div>
        );
    }

    if (typeof value === "string" && value.length > 50) {
        return <div style={{ minWidth: "240px", maxWidth: "420px", whiteSpace: "pre-wrap", color:"#fff", lineHeight: 1.55 }}>{value}</div>;
    }

    return String(value);
};

export const getOrderedColumns = (data: any[], tableName?: string | null) => {
    if (!data || data.length === 0) return [];

    const keySet = new Set<string>();
    data.forEach(row => {
        if (row && typeof row === "object") {
            Object.keys(row).forEach(k => keySet.add(k));
        }
    });
    const allKeys = Array.from(keySet);
    const priority = tableName ? tableColumnOrder[tableName] || [] : [];
    
    const ordered: string[] = [];
    priority.forEach(key => {
        if (allKeys.includes(key)) {
            ordered.push(key);
        }
    });

    allKeys.forEach(key => {
        if (!ordered.includes(key) && !hiddenColumns.has(key)) {
            ordered.push(key);
        }
    });

    return ordered.filter(col => !hiddenColumns.has(col));
};
