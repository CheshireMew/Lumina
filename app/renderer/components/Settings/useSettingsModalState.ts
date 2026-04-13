import React, { useEffect, useRef, useState } from "react";

import { GeneralSettingsInput } from "../../hooks/useSettings";
import { uploadBackground } from "../../platform/electron";

interface UseSettingsModalStateOptions {
    isOpen: boolean;
    currentSettings: GeneralSettingsInput;
    onSave: (settings: GeneralSettingsInput) => Promise<void>;
    onClose: () => void;
}

export const useSettingsModalState = ({
    isOpen,
    currentSettings,
    onSave,
    onClose,
}: UseSettingsModalStateOptions) => {
    const [userName, setUserName] = useState("Master");
    const [highDpiEnabled, setHighDpiEnabled] = useState(false);
    const [backgroundImage, setBackgroundImage] = useState("");
    const [isSaving, setIsSaving] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        setUserName(currentSettings.userName);
        setHighDpiEnabled(currentSettings.live2dHighDpi);
        setBackgroundImage(currentSettings.backgroundImage);
    }, [currentSettings.backgroundImage, currentSettings.live2dHighDpi, currentSettings.userName, isOpen]);

    const handleBackgroundFileSelect = async (
        event: React.ChangeEvent<HTMLInputElement>,
    ) => {
        const file = event.target.files?.[0];
        if (!file || !(file as any).path) {
            return;
        }

        try {
            const safeUrl = await uploadBackground((file as any).path);
            setBackgroundImage(safeUrl);
        } catch (error) {
            console.error("Upload failed", error);
            alert("Failed to save background image.");
        } finally {
            event.target.value = "";
        }
    };

    const handleSave = async () => {
        setIsSaving(true);

        try {
            await onSave({
                userName,
                live2dHighDpi: highDpiEnabled,
                backgroundImage,
            });
            onClose();
        } finally {
            setIsSaving(false);
        }
    };

    return {
        userName,
        setUserName,
        highDpiEnabled,
        setHighDpiEnabled,
        backgroundImage,
        setBackgroundImage,
        isSaving,
        fileInputRef,
        handleBackgroundFileSelect,
        handleSave,
    };
};
