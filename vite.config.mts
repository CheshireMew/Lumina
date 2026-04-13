import { defineConfig } from "vite";
import path from "node:path";
import electron from "vite-plugin-electron/simple";
import react from "@vitejs/plugin-react";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const dependencies = Object.keys(require("./package.json").dependencies);
const electronNodeTarget = "node18";
const deferredStartupChunkMarkers = [
    "vrm-vendor",
    "mediapipe-vendor",
    "VRMPlugin-",
    "SpriteAvatarPlugin-",
    "FaceTracker-",
];

function rendererManualChunks(id: string) {
    const normalizedId = id.replace(/\\/g, "/");

    if (!normalizedId.includes("node_modules")) {
        return;
    }

    if (
        normalizedId.includes("@pixiv/three-vrm") ||
        normalizedId.includes("@react-three/") ||
        normalizedId.includes("/three/")
    ) {
        return "vrm-vendor";
    }

    if (normalizedId.includes("/eventemitter3/")) {
        return "eventemitter-vendor";
    }

    if (normalizedId.includes("pixi-live2d-display")) {
        return "live2d-vendor";
    }

    if (normalizedId.includes("/pixi.js/")) {
        return "pixi-vendor";
    }

    if (
        normalizedId.includes("/react/") ||
        normalizedId.includes("/react-dom/") ||
        normalizedId.includes("/scheduler/")
    ) {
        return "react-vendor";
    }

    if (normalizedId.includes("/lucide-react/")) {
        return "ui-vendor";
    }

    if (normalizedId.includes("@mediapipe/")) {
        return "mediapipe-vendor";
    }
}

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        // nodePolyfills(), // Removed: Renderer should be pure web now
        react(),
        electron({
            main: {
                // Shortcut of `build.lib.entry`.
                entry: "app/main/main.ts",
                vite: {
                    build: {
                        target: electronNodeTarget,
                        minify: false,
                        sourcemap: false,
                        reportCompressedSize: false,
                        emptyOutDir: false,
                        rollupOptions: {
                            treeshake: false,
                            external: (id) => {
                                const mustBundle: string[] = [
                                    // 'electron-store',
                                ];

                                // 1. Always bundle local imports
                                if (
                                    id.startsWith(".") ||
                                    id.startsWith("/") ||
                                    path.isAbsolute(id)
                                ) {
                                    return false;
                                }

                                // 2. Bundle specific whitelisted packages
                                if (mustBundle.includes(id)) {
                                    return false;
                                }

                                // 3. Externalize known dependencies
                                return dependencies.some(
                                    (dep) =>
                                        id === dep || id.startsWith(`${dep}/`),
                                );
                            },
                        },
                    },
                },
            },
            preload: {
                // Shortcut of `build.rollupOptions.input`.
                input: "app/main/preload.ts",
                vite: {
                    build: {
                        target: electronNodeTarget,
                        minify: false,
                        sourcemap: false,
                        reportCompressedSize: false,
                        emptyOutDir: false,
                        rollupOptions: {
                            treeshake: false,
                        },
                    },
                },
            },
            // Ployfill the Electron and Node.js built-in modules for Renderer process.
            // renderer: {}, // Disabled: We use contextBridge, so we don't need node polyfills in renderer
        }),
    ],
    optimizeDeps: {
        // 只预构建渲染进程依赖，避免把 Electron 主进程入口拖进冷启动扫描
        entries: [
            "index.html",
            "app/renderer/main.tsx",
        ],
        // Explicitly include heavy packages that should be pre-bundled
        include: [
            "react",
            "react-dom",
            // LangChain removed
            "axios",
            "eventemitter3",
            "lucide-react",
        ],
        // Exclude packages that don't work well with pre-bundling
        exclude: ["electron"],
    },
    build: {
        chunkSizeWarningLimit: 1200,
        modulePreload: {
            resolveDependencies: (
                _url: string,
                deps: string[],
                context: { hostType: "html" | "js" },
            ) => {
                if (context.hostType !== "html") {
                    return deps;
                }

                return deps.filter(
                    (dep: string) =>
                        !deferredStartupChunkMarkers.some((marker) =>
                            dep.includes(marker),
                        ),
                );
            },
        },
        rollupOptions: {
            output: {
                manualChunks: rendererManualChunks,
            },
        },
    },
    resolve: {
        alias: {
            "@core": path.resolve(__dirname, "core"),
            "@app": path.resolve(__dirname, "app"),
            "@assets": path.resolve(__dirname, "assets"),
        },
    },
    server: {
        // 加快 dev 启动与热更：忽略大体积/生成目录的文件监听
        watch: {
            ignored: [
                "**/dist/**",
                "**/dist-electron/**",
                "**/dist_backend/**",
                "**/release/**",
                "**/logs/**",
                "**/memory_backups/**",
                "**/GPT-SoVITS/**",
                "**/models/**",
                "**/voiceprint_profiles/**",
                "**/lumina_surreal.db*",
            ],
        },
    },
    test: {
        globals: true,
        environment: "jsdom",
        include: ["app/renderer/**/*.test.{ts,tsx}"],
        setupFiles: ["./app/renderer/tests/setup.ts"],
    },
} as any);
