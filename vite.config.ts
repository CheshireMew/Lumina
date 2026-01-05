import { defineConfig } from 'vite'
import path from 'node:path'
import electron from 'vite-plugin-electron/simple'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        nodePolyfills(),
        react(),
        electron({
            main: {
                // Shortcut of `build.lib.entry`.
                entry: 'app/main/main.ts',
                vite: {
                    build: {
                        // Use esbuild instead of rollup for MUCH faster builds (10-100x speedup)
                        minify: false, // Disable minification in dev
                        sourcemap: false, // Disable sourcemaps in dev for speed
                        rollupOptions: {
                            // Strategy: Externalize EVERYTHING except packages that MUST be bundled
                            // This gives us the fastest possible builds
                            external: Object.keys(require('./package.json').dependencies).filter(dep => {
                                // ONLY bundle these packages (ESM-only or have special requirements)
                                const mustBundle = [
                                    'electron-store',        // ESM-only
                                ];
                                // Externalize everything else (including LangChain, axios, etc.)
                                return !mustBundle.includes(dep);
                            }), 
                        },
                    },
                },
            },
            preload: {
                // Shortcut of `build.rollupOptions.input`.
                // Preload scripts may be needed later for IPC
                input: 'app/main/preload.ts',
            },
            // Ployfill the Electron and Node.js built-in modules for Renderer process.
            // See 👉 https://github.com/electron-vite/vite-plugin-electron-renderer
            renderer: {},
        }),
    ],
    optimizeDeps: {
        entries: ['index.html', 'app/**/*.{ts,tsx}'],
        // Explicitly include heavy packages that should be pre-bundled
        include: [
            'react',
            'react-dom',
            '@langchain/core',
            '@langchain/openai',
            'axios',
        ],
        // Exclude packages that don't work well with pre-bundling
        exclude: [
            'electron',
        ],
    },
    resolve: {
        alias: {
            '@core': path.resolve(__dirname, 'core'),
            '@app': path.resolve(__dirname, 'app'),
            '@assets': path.resolve(__dirname, 'assets'),
            // Map web requests for ONNX Runtime .mjs files to node_modules
            '/ort-wasm-simd-threaded.mjs': path.resolve(__dirname, 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.mjs'),
            '/ort-wasm-simd.mjs': path.resolve(__dirname, 'node_modules/onnxruntime-web/dist/ort-wasm-simd.mjs'),
            '/ort-wasm.mjs': path.resolve(__dirname, 'node_modules/onnxruntime-web/dist/ort-wasm.mjs'),
            '/ort-wasm-threaded.mjs': path.resolve(__dirname, 'node_modules/onnxruntime-web/dist/ort-wasm-threaded.mjs'),
        },
    },
})


