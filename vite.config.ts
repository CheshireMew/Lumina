import { defineConfig } from 'vite'
import path from 'node:path'
import electron from 'vite-plugin-electron/simple'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        nodePolyfills(),
        react(),
        electron({
            main: {
                // Shortcut of `build.lib.entry`.
                entry: 'app/main/main.ts',
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


