import React, { useCallback, useRef } from "react";

import { GeneralSettingsInput, GeneralSettingsPatch } from "../../hooks/useSettings";
import { uploadBackground } from "../../platform/electron";

interface UseSettingsModalStateOptions {
    currentSettings: GeneralSettingsInput;
    onChange: (settings: GeneralSettingsPatch) => Promise<void>;
}

export const useSettingsModalState = ({
    currentSettings,
    onChange,
}: UseSettingsModalStateOptions) => {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const applySettings = useCallback(
        async (patch: GeneralSettingsPatch) => {
            try {
                await onChange(patch);
            } catch (error) {
                console.error("[Settings] Failed to save general setting", error);
                alert("Failed to save setting.");
            }
        },
        [onChange],
    );

    const handleBackgroundFileSelect = async (
        event: React.ChangeEvent<HTMLInputElement>,
    ) => {
        const file = event.target.files?.[0];
        if (!file || !(file as any).path) {
            return;
        }

        try {
            const safeUrl = await uploadBackground((file as any).path);
            await applySettings({ backgroundImage: safeUrl });
        } catch (error) {
            console.error("Upload failed", error);
            alert("Failed to save background image.");
        } finally {
            event.target.value = "";
        }
    };

    return {
        userName: currentSettings.userName,
        setUserName: (userName: string) => {
            void applySettings({ userName });
        },
        highDpiEnabled: currentSettings.live2dHighDpi,
        setHighDpiEnabled: (live2dHighDpi: boolean) => {
            void applySettings({ live2dHighDpi });
        },
        backgroundImage: currentSettings.backgroundImage,
        setBackgroundImage: (backgroundImage: string) => {
            void applySettings({ backgroundImage });
        },
        fileInputRef,
        handleBackgroundFileSelect,
    };
};
