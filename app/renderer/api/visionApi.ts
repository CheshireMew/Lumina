import { requestJson } from "./client";

export const analyzeImage = async (
    visionBaseUrl: string,
    file: File,
    prompt = "Describe this image in detail.",
) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("prompt", prompt);

    return requestJson<{ description: string }>(
        `${visionBaseUrl}/analyze`,
        { method: "POST", body: formData },
    );
};
