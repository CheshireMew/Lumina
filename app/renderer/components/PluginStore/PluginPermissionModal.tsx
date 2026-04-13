import React from "react";

import type { PluginStatus } from "../../hooks/usePluginManager";

interface PluginPermissionModalProps {
    plugin: PluginStatus;
    onCancel: () => void;
    onConfirm: () => void;
}

const PluginPermissionModal: React.FC<PluginPermissionModalProps> = ({
    plugin,
    onCancel,
    onConfirm,
}) => {
    return (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
            <div
                className="modal-content glass-panel"
                style={{ maxWidth: "400px" }}
            >
                <h3>🛡️ Permission Request</h3>
                <p>
                    <strong>{plugin.name}</strong> requires the following permissions:
                </p>
                <ul
                    className="perm-list"
                    style={{
                        textAlign: "left",
                        background: "rgba(0,0,0,0.2)",
                        padding: "10px",
                        borderRadius: "8px",
                        margin: "10px 0",
                    }}
                >
                    {plugin.permissions?.map((permission) => (
                        <li
                            key={permission}
                            style={{
                                color: "#ff6b6b",
                                listStyle: "none",
                                paddingLeft: "20px",
                                position: "relative",
                            }}
                        >
                            <span style={{ position: "absolute", left: 0 }}>⚠️</span>
                            {permission}
                        </li>
                    ))}
                </ul>
                <p style={{ fontSize: "0.9em", color: "#ccc" }}>
                    Do you want to trust this plugin?
                </p>
                <div className="modal-actions">
                    <button onClick={onCancel} className="cancel-btn">
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className="save-btn"
                        style={{ background: "#ff4757" }}
                    >
                        Allow & Enable
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PluginPermissionModal;

