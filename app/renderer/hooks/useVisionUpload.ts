import { useCallback, useState } from "react";

import { analyzeImage } from "../api/visionApi";

export const useVisionUpload = (
    visionBaseUrl: string,
    visionCapabilityState: string,
) => {
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const analyze = useCallback(async (file: File) => {
        if (visionCapabilityState !== "ready") {
            throw new Error("视觉能力未安装");
        }

        setIsAnalyzing(true);
        try {
            const data = await analyzeImage(visionBaseUrl, file);
            if (typeof data.description !== "string" || !data.description.trim()) {
                throw new Error("Vision response did not include a description");
            }
            return data.description;
        } finally {
            setIsAnalyzing(false);
        }
    }, [visionBaseUrl, visionCapabilityState]);

    return { isAnalyzing, analyze };
};
