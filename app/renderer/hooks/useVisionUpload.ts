import { useCallback, useState } from "react";

import { analyzeImage } from "../api/visionApi";

export const useVisionUpload = (
    visionBaseUrl: string,
    visionCapabilityState: string,
    visionCapabilityError?: string | null,
) => {
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const analyze = useCallback(async (file: File) => {
        if (visionCapabilityState !== "ready") {
            throw new Error(visionCapabilityError || "视觉能力尚未就绪");
        }

        setIsAnalyzing(true);
        try {
            const data = await analyzeImage(visionBaseUrl, file);
            if (typeof data.description !== "string" || !data.description.trim()) {
                throw new Error("视觉服务没有返回图片描述");
            }
            return data.description;
        } finally {
            setIsAnalyzing(false);
        }
    }, [visionBaseUrl, visionCapabilityError, visionCapabilityState]);

    return { isAnalyzing, analyze };
};
