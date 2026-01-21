import path from "node:path";

/**
 * [Security Standardization] Safe File System Utilities
 */

/**
 * Checks if a child path is contained within a parent directory.
 * Prevents Path Traversal attacks.
 *
 * @param parent - Trusted Parent Directory (Absolute)
 * @param child - Potentially Untrusted Child Path (Absolute)
 * @returns true if child is strictly inside parent
 */
export function isChildOf(parent: string, child: string): boolean {
    const relative = path.relative(parent, child);
    return (
        !!relative && !relative.startsWith("..") && !path.isAbsolute(relative)
    );
}
