import { useCallback, useState } from "react";

import { API_CONFIG } from "../../config";

export type PluginUploadStatus = "idle" | "uploading" | "success" | "error";

type UploadRefresh = () => void | Promise<void>;

const parseResponseText = async (response: Response): Promise<any> => {
    const text = await response.text();
    try {
        return JSON.parse(text);
    } catch {
        return { detail: text || response.statusText };
    }
};

export const usePluginUpload = (refreshPlugins?: UploadRefresh) => {
    const [uploadStatus, setUploadStatus] = useState<PluginUploadStatus>("idle");

    const uploadPlugin = useCallback(
        async (file: File) => {
            if (!file.name.endsWith(".zip")) {
                alert("Only .zip files are supported!");
                return false;
            }

            setUploadStatus("uploading");

            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await fetch(
                    `${API_CONFIG.BASE_URL}/plugins/upload`,
                    {
                        method: "POST",
                        body: formData,
                    },
                );

                const data = await parseResponseText(response);

                if (response.ok) {
                    setUploadStatus("success");
                    alert(
                        `Plugin installed: ${data.id || "Unknown"}\nPlease restart backend to load.`,
                    );
                    return true;
                }

                setUploadStatus("error");
                alert(
                    `Upload failed: ${data.detail || String(data).slice(0, 100)}`,
                );
                return false;
            } catch (error: any) {
                console.error(error);
                setUploadStatus("error");
                alert(`Upload error: ${error?.message || String(error)}`);
                return false;
            } finally {
                setUploadStatus("idle");
                if (refreshPlugins) {
                    await refreshPlugins();
                }
            }
        },
        [refreshPlugins],
    );

    return {
        uploadStatus,
        uploadPlugin,
    };
};

