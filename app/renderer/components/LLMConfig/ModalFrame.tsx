import { Settings as SettingsIcon, Sparkles, X } from "lucide-react";
import type { FC, ReactNode } from "react";
import { modalCss, modalStyles, primaryColor } from "./styles";

interface ModalFrameProps {
    children: ReactNode;
    onClose: () => void;
    onSave: () => void | Promise<void>;
    isSaving?: boolean;
}

const ModalFrame: FC<ModalFrameProps> = ({ children, onClose, onSave, isSaving = false }) => (
    <div style={modalStyles.overlay}>
        <div style={modalStyles.container}>
            <div style={modalStyles.header}>
                <div style={modalStyles.headerTitleWrap}>
                    <div style={modalStyles.headerIcon}>
                        <Sparkles size={20} color={primaryColor} />
                    </div>
                    <div>
                        <h2 style={modalStyles.title}>Neural Link</h2>
                        <p style={modalStyles.subtitle}>
                            Configure Agent Intelligence
                        </p>
                    </div>
                </div>
                <button
                    onClick={onClose}
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
                <button onClick={onClose} style={modalStyles.cancelButton}>
                    Cancel
                </button>
                <button
                    onClick={() => {
                        void onSave();
                    }}
                    disabled={isSaving}
                    style={{
                        ...modalStyles.saveButton,
                        opacity: isSaving ? 0.72 : 1,
                        cursor: isSaving ? "wait" : "pointer",
                    }}
                >
                    <SettingsIcon size={16} /> {isSaving ? "Saving..." : "Save System"}
                </button>
            </div>
        </div>

        <style>{modalCss}</style>
    </div>
);

export default ModalFrame;
