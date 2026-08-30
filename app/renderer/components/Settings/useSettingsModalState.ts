import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
    const [draft, setDraft] = useState(currentSettings);
    const [baseline, setBaseline] = useState(currentSettings);
    const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
    const [saveMessage, setSaveMessage] = useState("");
    const [pendingBackgroundPath, setPendingBackgroundPath] = useState("");
    const [pendingBackgroundName, setPendingBackgroundName] = useState("");

    useEffect(() => {
        setDraft(currentSettings);
        setBaseline(currentSettings);
        setPendingBackgroundPath("");
        setPendingBackgroundName("");
    }, [
        currentSettings.backgroundImage,
        currentSettings.isTTSEnabled,
        currentSettings.live2dHighDpi,
        currentSettings.userName,
    ]);

    const isDirty = useMemo(
        () => JSON.stringify(draft) !== JSON.stringify(baseline) || Boolean(pendingBackgroundPath),
        [baseline, draft, pendingBackgroundPath],
    );

    const updateDraft = useCallback((patch: GeneralSettingsPatch) => {
        setDraft((current) => ({ ...current, ...patch }));
        setSaveStatus("idle");
        setSaveMessage("");
    }, []);

    const save = useCallback(async () => {
        const userName = draft.userName.trim();
        if (!userName) {
            setSaveStatus("error");
            setSaveMessage("请填写希望角色使用的称呼。 ");
            return false;
        }
        setSaveStatus("saving");
        setSaveMessage("");
        try {
            const next = { ...draft, userName };
            if (pendingBackgroundPath) {
                next.backgroundImage = await uploadBackground(pendingBackgroundPath);
            }
            await onChange(next);
            setDraft(next);
            setBaseline(next);
            setSaveStatus("saved");
            setSaveMessage("常规设置已保存");
            setPendingBackgroundPath("");
            setPendingBackgroundName("");
            return true;
        } catch (error) {
            console.error("[Settings] Failed to save general settings", error);
            setSaveStatus("error");
            setSaveMessage(error instanceof Error ? error.message : "常规设置保存失败。 ");
            return false;
        }
    }, [draft, onChange, pendingBackgroundPath]);

    const reset = useCallback(() => {
        setDraft(baseline);
        setSaveStatus("idle");
        setSaveMessage("");
        setPendingBackgroundPath("");
        setPendingBackgroundName("");
    }, [baseline]);

    const handleBackgroundFileSelect = async (
        event: React.ChangeEvent<HTMLInputElement>,
    ) => {
        const file = event.target.files?.[0];
        if (!file || !(file as any).path) {
            return;
        }

        try {
            setPendingBackgroundPath((file as any).path);
            setPendingBackgroundName(file.name);
            setSaveStatus("idle");
            setSaveMessage("");
        } catch (error) {
            console.error("Upload failed", error);
            setSaveStatus("error");
            setSaveMessage(error instanceof Error ? error.message : "背景图片读取失败。 ");
        } finally {
            event.target.value = "";
        }
    };

    return {
        userName: draft.userName,
        setUserName: (userName: string) => updateDraft({ userName }),
        highDpiEnabled: draft.live2dHighDpi,
        setHighDpiEnabled: (live2dHighDpi: boolean) => updateDraft({ live2dHighDpi }),
        ttsEnabled: draft.isTTSEnabled,
        setTtsEnabled: (isTTSEnabled: boolean) => updateDraft({ isTTSEnabled }),
        backgroundImage: pendingBackgroundName ? `待保存：${pendingBackgroundName}` : draft.backgroundImage,
        setBackgroundImage: (backgroundImage: string) => {
            setPendingBackgroundPath("");
            setPendingBackgroundName("");
            updateDraft({ backgroundImage });
        },
        fileInputRef,
        handleBackgroundFileSelect,
        isDirty,
        save,
        reset,
        saveStatus,
        saveMessage,
    };
};
