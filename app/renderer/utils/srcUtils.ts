/**
 * transformImageSrc
 *
 * Transforms a local file path or file:// URL into a safe protocol URL for Electron.
 * Required because Electron Sandbox blocks direct file:// access.
 *
 * @param src The source URL or path
 * @returns The transformed URL safe for img src or background-image
 */
export const transformImageSrc = (src: string): string => {
    if (!src) return "";

    // Check if it's already a web URL
    if (
        src.startsWith("http://") ||
        src.startsWith("https://") ||
        src.startsWith("data:") ||
        src.startsWith("blob:")
    ) {
        return src;
    }

    // Check if it's a file protocol or Windows path
    let cleanPath = src;

    // Strip file:/// prefix if present
    if (cleanPath.startsWith("file:///")) {
        cleanPath = cleanPath.replace("file:///", "");
    } else if (cleanPath.startsWith("file://")) {
        cleanPath = cleanPath.replace("file://", "");
    }

    // If it looks like a Windows drive path (e.g. E:/...) or unix path
    // We assume it's local and needs the custom protocol
    // Note: We registered 'lumina-local://' in main.ts

    // Ensure we don't double-prefix if already transformed
    if (cleanPath.startsWith("lumina-local://")) {
        return cleanPath;
    }

    // Windows paths might have backslashes, normalize to forward slashes for URL
    // Windows paths might have backslashes, normalize to forward slashes for URL
    cleanPath = cleanPath.replace(/\\/g, "/");

    // [Fix] Encode the path to ensure spaces and special chars are safe for URL
    // We use encodeURI to preserve slashes but encode spaces/etc.
    const encodedPath = encodeURI(cleanPath);

    // [Environment Check]
    // If running in Browser (no window.electron), 'lumina-local://' won't work.
    // In strict browser Dev mode, we can't easily load local files due to security.
    // But for now, we return the protocol URL so Electron works.
    // If the user is in Browser, they likely need to use a simpler path or drag-drop blob.
    // However, to avoid "broken image icon", we can check slightly:

    // Note: We don't have a reliable "isElectron" check here without importing IPC.
    // Assuming context is mainly Electron app.

    return `lumina-local://${encodedPath}`;
};
