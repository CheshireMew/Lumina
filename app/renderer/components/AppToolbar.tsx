import React, { useEffect, useRef, useState } from "react";
import {
    Activity,
    BookOpen,
    Brain,
    Ellipsis,
    Settings as SettingsIcon,
} from "lucide-react";

interface AppToolbarProps {
    onOpenSettings: () => void;
    onOpenMotionTester: () => void;
    onOpenLLMSettings: () => void;
    onOpenMemoryInspector: () => void;
}

export const AppToolbar: React.FC<AppToolbarProps> = ({
    onOpenSettings,
    onOpenMotionTester,
    onOpenLLMSettings,
    onOpenMemoryInspector,
}) => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const menuRootRef = useRef<HTMLDivElement>(null);
    const menuButtonRef = useRef<HTMLButtonElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);
    const showDeveloperTools = import.meta.env.VITE_SHOW_DEVELOPER_TOOLS === "true";

    useEffect(() => {
        if (!isMenuOpen) return;

        window.requestAnimationFrame(() => {
            menuRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
        });

        const closeOnOutsideClick = (event: MouseEvent) => {
            if (!menuRootRef.current?.contains(event.target as Node)) {
                setIsMenuOpen(false);
            }
        };
        const closeOnEscape = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                setIsMenuOpen(false);
                menuButtonRef.current?.focus();
            }
        };

        document.addEventListener("mousedown", closeOnOutsideClick);
        document.addEventListener("keydown", closeOnEscape);
        return () => {
            document.removeEventListener("mousedown", closeOnOutsideClick);
            document.removeEventListener("keydown", closeOnEscape);
        };
    }, [isMenuOpen]);

    const runAndClose = (action: () => void) => {
        setIsMenuOpen(false);
        action();
    };

    return (
        <div
            ref={menuRootRef}
            className="app-toolbar"
            style={{
                position: "absolute",
                top: 30,
                right: 30,
                display: "flex",
                gap: 10,
                zIndex: 100,
            }}
        >
            <ToolbarButton
                onClick={onOpenSettings}
                icon={<SettingsIcon size={21} />}
                label="设置"
            />
            <ToolbarButton
                onClick={() => setIsMenuOpen((open) => !open)}
                icon={<Ellipsis size={22} />}
                label="更多"
                ariaExpanded={isMenuOpen}
                buttonRef={menuButtonRef}
            />

            {isMenuOpen && (
                <div
                    ref={menuRef}
                    id="lumina-toolbar-menu"
                    role="menu"
                    aria-label="更多功能"
                    onKeyDown={(event) => {
                        const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitem"]'));
                        const current = items.indexOf(document.activeElement as HTMLButtonElement);
                        let next = current;
                        if (event.key === "ArrowDown") next = (current + 1) % items.length;
                        else if (event.key === "ArrowUp") next = (current - 1 + items.length) % items.length;
                        else if (event.key === "Home") next = 0;
                        else if (event.key === "End") next = items.length - 1;
                        else return;
                        event.preventDefault();
                        items[next]?.focus();
                    }}
                    style={{
                        position: "absolute",
                        top: 54,
                        right: 0,
                        width: 210,
                        padding: 8,
                        borderRadius: 16,
                        background: "rgba(255, 255, 255, 0.92)",
                        border: "1px solid rgba(255,255,255,0.75)",
                        boxShadow: "0 16px 40px rgba(15,23,42,0.18)",
                        backdropFilter: "blur(18px)",
                        color: "#334155",
                    }}
                >
                    <MenuButton
                        icon={<Brain size={18} />}
                        label="模型设置"
                        onClick={() => runAndClose(onOpenLLMSettings)}
                    />
                    {showDeveloperTools && <div
                        style={{
                            margin: "8px 10px 5px",
                            paddingTop: 8,
                            borderTop: "1px solid rgba(15,23,42,0.08)",
                            color: "#94a3b8",
                            fontSize: 11,
                            fontWeight: 700,
                            letterSpacing: "0.08em",
                        }}
                    >
                        开发工具
                    </div>}
                    {showDeveloperTools && <MenuButton
                        icon={<BookOpen size={18} />}
                        label="记忆数据"
                        onClick={() => runAndClose(onOpenMemoryInspector)}
                    />}
                    {showDeveloperTools && <MenuButton
                        icon={<Activity size={18} />}
                        label="动作测试"
                        onClick={() => runAndClose(onOpenMotionTester)}
                    />}
                </div>
            )}
        </div>
    );
};

const ToolbarButton: React.FC<{
    onClick: () => void;
    icon: React.ReactNode;
    label: string;
    ariaExpanded?: boolean;
    buttonRef?: React.Ref<HTMLButtonElement>;
}> = ({ onClick, icon, label, ariaExpanded, buttonRef }) => (
    <button
        type="button"
        ref={buttonRef}
        onClick={onClick}
        title={label}
        aria-label={label}
        aria-expanded={ariaExpanded}
        aria-controls={ariaExpanded === undefined ? undefined : "lumina-toolbar-menu"}
        style={{
            width: 44,
            height: 44,
            borderRadius: 14,
            backgroundColor: "rgba(255,255,255,0.72)",
            color: "#475569",
            border: "1px solid rgba(255,255,255,0.72)",
            backdropFilter: "blur(12px)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            cursor: "pointer",
            boxShadow: "0 8px 24px rgba(15,23,42,0.12)",
        }}
    >
        {icon}
    </button>
);

const MenuButton: React.FC<{
    onClick: () => void;
    icon: React.ReactNode;
    label: string;
}> = ({ onClick, icon, label }) => (
    <button
        type="button"
        role="menuitem"
        onClick={onClick}
        style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 12px",
            border: 0,
            borderRadius: 10,
            background: "transparent",
            color: "#475569",
            cursor: "pointer",
            fontSize: 14,
            textAlign: "left",
        }}
    >
        {icon}
        <span>{label}</span>
    </button>
);
