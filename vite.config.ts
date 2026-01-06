import { defineConfig } from 'vite'
import path from 'node:path'
import electron from 'vite-plugin-electron/simple'
import react from '@vitejs/plugin-react'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        // nodePolyfills(), // Removed: Renderer should be pure web now
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
                            // Strategy: Externalize explicitly listed dependencies.
                            external: (id) => {
                                const dependencies = Object.keys(require('./package.json').dependencies);
                                const mustBundle: string[] = [
                                    // 'electron-store',
                                ];

                                // 1. Always bundle local imports
                                if (id.startsWith('.') || id.startsWith('/') || path.isAbsolute(id)) {
                                    return false;
                                }

                                // 2. Bundle specific whitelisted packages
                                if (mustBundle.includes(id)) {
                                    return false;
                                }

                                // 3. Externalize known dependencies
                                return dependencies.some(dep => id === dep || id.startsWith(`${dep}/`));
                            }, 
                        },
                    },
                },
            },
            preload: {
                // Shortcut of `build.rollupOptions.input`.
                input: 'app/main/preload.ts',
            },
            // Ployfill the Electron and Node.js built-in modules for Renderer process.
            // renderer: {}, // Disabled: We use contextBridge, so we don't need node polyfills in renderer
        }),
    ],
    optimizeDeps: {
        entries: ['index.html', 'app/**/*.{ts,tsx}'],
        // Explicitly include heavy packages that should be pre-bundled
        include: [
            'react',
            'react-dom',
            // LangChain removed
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
        },
    },
})


