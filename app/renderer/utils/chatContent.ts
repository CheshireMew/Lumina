const SYSTEM_TOKEN_PATTERN = /<\|.*?\|>/g;
const EMOTION_TAG_PATTERN =
    /\s*[\[\(](joy|happy|sad|angry|surprised|neutral|thinking|shy|love|sleepy|confused|serious|embarrassed)[\]\)]\s*/gi;

export function stripAssistantProtocolMarkup(content: string): string {
    return content
        .replace(SYSTEM_TOKEN_PATTERN, "")
        .replace(EMOTION_TAG_PATTERN, " ");
}

export function formatAssistantDisplay(content: string): string {
    return stripAssistantProtocolMarkup(content).trimStart();
}

export function finalizeAssistantContent(content: string): string {
    return stripAssistantProtocolMarkup(content).trim();
}
