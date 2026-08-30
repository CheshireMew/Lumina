import { Settings as SettingsIcon, Sparkles, X } from "lucide-react";
import type { FC, ReactNode } from "react";
import { useDialogAccessibility } from "../../hooks/useDialogAccessibility";
import { modalCss, modalStyles, primaryColor } from "./styles";

interface ModalFrameProps {
    children: ReactNode;
    onClose: () => void;
    onSave: () => void | Promise<void>;
    isSaving?: boolean;
    saveError?: string;
    saveDisabled?: boolean;
}

const ModalFrame: FC<ModalFrameProps> = ({ children, onClose, onSave, isSaving = false, saveError = "", saveDisabled = false }) => {
    const dialogRef = useDialogAccessibility<HTMLDivElement>(true, onClose);

    return (
    <div style={modalStyles.overlay} role="presentation">
        <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="llm-config-title"
            tabIndex={-1}
            style={modalStyles.container}
        >
            <div style={modalStyles.header}>
                <div style={modalStyles.headerTitleWrap}>
                    <div style={modalStyles.headerIcon}>
                        <Sparkles size={20} color={primaryColor} />
                    </div>
                    <div>
                        <h2 id="llm-config-title" style={modalStyles.title}>模型设置</h2>
                        <p style={modalStyles.subtitle}>
                            选择模型服务并调整对话参数
                        </p>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    aria-label="关闭模型设置"
                    className="hover-btn"
                    style={modalStyles.closeButton}
                >
                    <X size={20} />
                </button>
            </div>

            <div style={modalStyles.content} className="custom-scrollbar">
                {children}
            </div>

            <div style={modalStyles.footer}>
                {saveError && <div role="alert" style={{ flex: 1, color: "#b91c1c", fontSize: 12 }}>{saveError}</div>}
                <button onClick={onClose} style={modalStyles.cancelButton}>
                    取消
                </button>
                <button
                    onClick={() => {
                        void onSave();
                    }}
                    disabled={isSaving || saveDisabled}
                    style={{
                        ...modalStyles.saveButton,
                        opacity: isSaving || saveDisabled ? 0.6 : 1,
                        cursor: isSaving ? "wait" : saveDisabled ? "not-allowed" : "pointer",
                    }}
                >
                    <SettingsIcon size={16} /> {isSaving ? "正在保存…" : "保存设置"}
                </button>
            </div>
        </div>

        <style>{modalCss}</style>
    </div>
    );
};

export default ModalFrame;
