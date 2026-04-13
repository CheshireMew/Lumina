import type { CSSProperties } from "react";

export const primaryColor = "#ec4899";
export const secondaryColor = "#8b5cf6";

export const glassStyle: CSSProperties = {
    background: "rgba(255, 255, 255, 0.85)",
    backdropFilter: "blur(12px)",
    border: "1px solid rgba(255, 255, 255, 0.5)",
    boxShadow: "0 8px 32px 0 rgba(31, 38, 135, 0.15)",
};

export const inputStyle: CSSProperties = {
    width: "100%",
    padding: "10px 14px",
    borderRadius: "12px",
    border: "1px solid rgba(236, 72, 153, 0.2)",
    fontSize: "14px",
    marginTop: "6px",
    boxSizing: "border-box",
    outline: "none",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
    background: "rgba(255, 255, 255, 0.6)",
    color: "#4b5563",
};

export const labelStyle: CSSProperties = {
    display: "block",
    fontSize: "13px",
    fontWeight: 600,
    color: "#6b7280",
    marginTop: "16px",
    letterSpacing: "0.02em",
};

export const sectionTitleStyle: CSSProperties = {
    fontSize: "12px",
    fontWeight: 700,
    color: primaryColor,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: "8px",
    display: "flex",
    alignItems: "center",
    gap: "6px",
};

export const modalStyles = {
    overlay: {
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.4)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 20000,
        padding: "20px",
    } satisfies CSSProperties,
    container: {
        width: "520px",
        maxHeight: "85vh",
        display: "flex",
        flexDirection: "column",
        ...glassStyle,
        borderRadius: "28px",
        animation: "slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
        overflow: "hidden",
    } satisfies CSSProperties,
    header: {
        padding: "20px 24px",
        background: `linear-gradient(135deg, ${primaryColor}15 0%, ${secondaryColor}15 100%)`,
        borderBottom: "1px solid rgba(255,255,255,0.5)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexShrink: 0,
    } satisfies CSSProperties,
    headerTitleWrap: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
    } satisfies CSSProperties,
    headerIcon: {
        background: "white",
        padding: "8px",
        borderRadius: "14px",
        boxShadow: "0 4px 12px rgba(236, 72, 153, 0.15)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
    } satisfies CSSProperties,
    title: {
        margin: 0,
        fontSize: "18px",
        fontWeight: 800,
        color: "#1f2937",
        letterSpacing: "-0.02em",
    } satisfies CSSProperties,
    subtitle: {
        margin: "2px 0 0 0",
        fontSize: "12px",
        color: "#6b7280",
        fontWeight: 500,
    } satisfies CSSProperties,
    closeButton: {
        background: "white",
        border: "none",
        color: "#9ca3af",
        cursor: "pointer",
        padding: "8px",
        borderRadius: "12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "all 0.2s",
    } satisfies CSSProperties,
    content: {
        padding: "24px",
        overflowY: "auto",
        flex: 1,
    } satisfies CSSProperties,
    formBody: {
        animation: "fadeIn 0.3s ease",
    } satisfies CSSProperties,
    footer: {
        padding: "20px 24px",
        background: "rgba(255,255,255,0.8)",
        borderTop: "1px solid rgba(0,0,0,0.05)",
        display: "flex",
        justifyContent: "flex-end",
        gap: "12px",
        backdropFilter: "blur(10px)",
        flexShrink: 0,
    } satisfies CSSProperties,
    cancelButton: {
        padding: "10px 20px",
        borderRadius: "12px",
        border: "none",
        background: "transparent",
        color: "#6b7280",
        fontWeight: 600,
        cursor: "pointer",
        fontSize: "14px",
    } satisfies CSSProperties,
    saveButton: {
        padding: "10px 24px",
        borderRadius: "12px",
        border: "none",
        background: `linear-gradient(135deg, ${primaryColor} 0%, ${secondaryColor} 100%)`,
        color: "white",
        fontWeight: 700,
        cursor: "pointer",
        boxShadow: "0 4px 12px rgba(236, 72, 153, 0.3)",
        fontSize: "14px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
    } satisfies CSSProperties,
};

export const providerToggleStyles = {
    container: {
        display: "flex",
        background: "rgba(255,255,255,0.5)",
        padding: "5px",
        borderRadius: "16px",
        marginBottom: "24px",
        border: "1px solid rgba(255,255,255,0.6)",
    } satisfies CSSProperties,
    button: (active: boolean) =>
        ({
            flex: 1,
            padding: "10px",
            borderRadius: "12px",
            background: active ? "white" : "transparent",
            boxShadow: active ? "0 4px 12px rgba(0,0,0,0.05)" : "none",
            border: "none",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: "13px",
            color: active ? primaryColor : "#9ca3af",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
        }) satisfies CSSProperties,
};

export const providerSectionStyles = {
    freeCard: {
        background: `linear-gradient(180deg, ${primaryColor}08 0%, ${secondaryColor}08 100%)`,
        padding: "20px",
        borderRadius: "20px",
        border: `1px solid ${primaryColor}20`,
    } satisfies CSSProperties,
    freeTitle: {
        fontSize: "14px",
        fontWeight: 700,
        color: primaryColor,
        marginBottom: "8px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
    } satisfies CSSProperties,
    freeDescription: {
        fontSize: "13px",
        color: "#4b5563",
        lineHeight: 1.6,
        marginBottom: "16px",
    } satisfies CSSProperties,
    selectWrapper: {
        position: "relative",
    } satisfies CSSProperties,
    selectIcon: {
        position: "absolute",
        right: "14px",
        top: "50%",
        transform: "translateY(-50%)",
        pointerEvents: "none",
        color: primaryColor,
    } satisfies CSSProperties,
    customEndpoint: {
        animation: "slideDown 0.2s",
    } satisfies CSSProperties,
    deepSeekCard: {
        marginTop: "20px",
        padding: "16px",
        background: "#f8fafc",
        borderRadius: "16px",
        border: "1px solid #e2e8f0",
    } satisfies CSSProperties,
    deepSeekRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    } satisfies CSSProperties,
    deepSeekTitle: {
        fontSize: "14px",
        fontWeight: 700,
        color: "#334155",
    } satisfies CSSProperties,
    deepSeekHint: {
        fontSize: "12px",
        color: "#64748b",
        marginTop: "4px",
    } satisfies CSSProperties,
};

export const parameterStyles = {
    section: {
        marginTop: "32px",
    } satisfies CSSProperties,
    card: {
        background: "rgba(255,255,255,0.5)",
        padding: "16px",
        borderRadius: "16px",
        marginBottom: "16px",
    } satisfies CSSProperties,
    row: {
        display: "flex",
        justifyContent: "space-between",
        marginBottom: "8px",
    } satisfies CSSProperties,
    mainLabel: {
        fontSize: "13px",
        fontWeight: 600,
        color: "#4b5563",
    } satisfies CSSProperties,
    primaryValue: {
        fontSize: "13px",
        fontWeight: 700,
        color: primaryColor,
    } satisfies CSSProperties,
    advancedGrid: {
        marginTop: "20px",
        paddingTop: "16px",
        borderTop: "1px dashed #e5e7eb",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "20px",
    } satisfies CSSProperties,
    smallLabel: {
        fontSize: "12px",
        fontWeight: 600,
        color: "#6b7280",
    } satisfies CSSProperties,
    secondaryValue: {
        fontSize: "12px",
        color: secondaryColor,
        fontWeight: 700,
    } satisfies CSSProperties,
    fullWidth: {
        gridColumn: "span 2",
    } satisfies CSSProperties,
};

export const contextStyles = {
    card: {
        background: "white",
        padding: "20px",
        borderRadius: "20px",
        border: "1px solid rgba(0,0,0,0.05)",
        boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
    } satisfies CSSProperties,
    limitWrap: {
        marginBottom: "20px",
    } satisfies CSSProperties,
    warning: {
        fontSize: "11px",
        color: "#f59e0b",
        marginTop: "6px",
        fontWeight: 500,
    } satisfies CSSProperties,
    overflowWrap: {
        borderTop: "1px dashed #e5e7eb",
        paddingTop: "16px",
    } satisfies CSSProperties,
    overflowLabel: {
        fontSize: "13px",
        fontWeight: 600,
        color: "#4b5563",
        display: "block",
        marginBottom: "12px",
    } satisfies CSSProperties,
    overflowGrid: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "12px",
    } satisfies CSSProperties,
    overflowButton: (active: boolean, color: string) =>
        ({
            padding: "12px",
            borderRadius: "12px",
            background: active ? color : "#f9fafb",
            border: active ? `2px solid ${color}` : "2px solid transparent",
            cursor: "pointer",
            textAlign: "left",
            transition: "all 0.2s",
            position: "relative",
            overflow: "hidden",
        }) satisfies CSSProperties,
    overflowTitle: (active: boolean) =>
        ({
            fontSize: "13px",
            fontWeight: 700,
            color: active ? "white" : "#6b7280",
        }) satisfies CSSProperties,
    overflowDescription: (active: boolean) =>
        ({
            fontSize: "10px",
            color: active ? "rgba(255,255,255,0.9)" : "#9ca3af",
            marginTop: "2px",
        }) satisfies CSSProperties,
    overflowIcon: {
        position: "absolute",
        right: -20,
        bottom: -20,
        opacity: 0.2,
    } satisfies CSSProperties,
    overflowInfo: {
        fontSize: "12px",
        color: "#6b7280",
        marginTop: "12px",
        background: "#f3f4f6",
        padding: "8px 12px",
        borderRadius: "8px",
    } satisfies CSSProperties,
    resetButton: {
        marginTop: "16px",
        padding: "10px",
        borderRadius: "12px",
        background: "#fef2f2",
        border: "1px solid #fecaca",
        color: "#dc2626",
        fontWeight: 600,
        cursor: "pointer",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "8px",
        width: "100%",
    } satisfies CSSProperties,
};

export const modalCss = `
    @keyframes slideIn {
        from { transform: scale(0.95) translateY(20px); opacity: 0; }
        to { transform: scale(1) translateY(0); opacity: 1; }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideDown {
        from { transform: translateY(-4px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    .hover-btn:hover { background: #f3f4f6 !important; }

    .gal-range {
        -webkit-appearance: none; width: 100%; height: 6px; background: #e5e7eb; border-radius: 4px; outline: none;
    }
    .gal-range::-webkit-slider-thumb {
        -webkit-appearance: none; appearance: none;
        width: 20px; height: 20px; border-radius: 50%;
        background: ${primaryColor};
        cursor: pointer; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        transition: transform 0.1s;
    }
    .gal-range::-webkit-slider-thumb:hover { transform: scale(1.1); }
    .gal-range.violet::-webkit-slider-thumb { background: ${secondaryColor}; }

    .switch { position: relative; display: inline-block; width: 48px; height: 26px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #e5e7eb; transition: .4s; border-radius: 24px; }
    .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    input:checked + .slider { background-color: ${primaryColor}; }
    input:checked + .slider:before { transform: translateX(22px); }

    .custom-scrollbar::-webkit-scrollbar { width: 6px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 3px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.2); }
`;
