import React, { Fragment, useMemo, useState } from "react";

interface RichTextProps {
    content: string;
}

const INLINE_PATTERN = /(\[[^\]]+\]\(https?:\/\/[^)\s]+\)|`[^`]+`|\*\*[^*]+\*\*)/g;

function InlineText({ text }: { text: string }) {
    const parts = text.split(INLINE_PATTERN).filter(Boolean);
    return (
        <>
            {parts.map((part, index) => {
                const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
                if (link) {
                    return (
                        <a
                            key={index}
                            href={link[2]}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(event) => {
                                event.preventDefault();
                                void window.app.openExternal(link[2]);
                            }}
                            style={{ color: "#4f46e5", textDecoration: "underline" }}
                        >
                            {link[1]}
                        </a>
                    );
                }
                if (part.startsWith("`") && part.endsWith("`")) {
                    return (
                        <code key={index} style={{ padding: "1px 5px", borderRadius: 5, background: "rgba(15,23,42,.08)", fontSize: ".92em" }}>
                            {part.slice(1, -1)}
                        </code>
                    );
                }
                if (part.startsWith("**") && part.endsWith("**")) {
                    return <strong key={index}>{part.slice(2, -2)}</strong>;
                }
                return <Fragment key={index}>{part}</Fragment>;
            })}
        </>
    );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
    const [copied, setCopied] = useState(false);
    const copy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
    };
    return (
        <div style={{ margin: "8px 0", borderRadius: 10, overflow: "hidden", background: "#0f172a", color: "#e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", background: "#1e293b", fontSize: 11, color: "#94a3b8" }}>
                <span>{language || "代码"}</span>
                <button type="button" onClick={copy} style={{ border: 0, background: "transparent", color: "#cbd5e1", cursor: "pointer", fontSize: 11 }}>
                    {copied ? "已复制" : "复制代码"}
                </button>
            </div>
            <pre style={{ margin: 0, padding: 12, overflowX: "auto", whiteSpace: "pre", fontSize: 12, lineHeight: 1.55 }}>
                <code>{code}</code>
            </pre>
        </div>
    );
}

function TextBlock({ content }: { content: string }) {
    const lines = content.split("\n");
    const nodes: React.ReactNode[] = [];
    let list: string[] = [];
    const flushList = () => {
        if (!list.length) return;
        nodes.push(
            <ul key={`list-${nodes.length}`} style={{ margin: "6px 0", paddingLeft: 22 }}>
                {list.map((item, index) => <li key={index}><InlineText text={item} /></li>)}
            </ul>,
        );
        list = [];
    };

    lines.forEach((line, index) => {
        const item = line.match(/^\s*[-*]\s+(.+)$/);
        if (item) {
            list.push(item[1]);
            return;
        }
        flushList();
        const heading = line.match(/^(#{1,3})\s+(.+)$/);
        if (heading) {
            nodes.push(
                <div key={index} style={{ margin: "8px 0 4px", fontSize: heading[1].length === 1 ? 18 : 15, fontWeight: 700 }}>
                    <InlineText text={heading[2]} />
                </div>,
            );
        } else if (line.trim()) {
            nodes.push(<div key={index}><InlineText text={line} /></div>);
        } else {
            nodes.push(<div key={index} style={{ height: 8 }} />);
        }
    });
    flushList();
    return <>{nodes}</>;
}

export function RichText({ content }: RichTextProps) {
    const blocks = useMemo(() => {
        const parsed: Array<{ type: "text" | "code"; content: string; language?: string }> = [];
        const pattern = /```([^\n`]*)\n?([\s\S]*?)```/g;
        let cursor = 0;
        let match: RegExpExecArray | null;
        while ((match = pattern.exec(content)) !== null) {
            if (match.index > cursor) parsed.push({ type: "text", content: content.slice(cursor, match.index) });
            parsed.push({ type: "code", language: match[1].trim(), content: match[2].replace(/\n$/, "") });
            cursor = pattern.lastIndex;
        }
        if (cursor < content.length) parsed.push({ type: "text", content: content.slice(cursor) });
        return parsed;
    }, [content]);

    return (
        <div style={{ overflowWrap: "anywhere" }}>
            {blocks.map((block, index) => block.type === "code"
                ? <CodeBlock key={index} language={block.language || ""} code={block.content} />
                : <TextBlock key={index} content={block.content} />)}
        </div>
    );
}
