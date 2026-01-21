import './polyfills';
import './index.css';
import './App.css'; // Global Styles
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

import { updateApiConfig } from './config';

const isDev = import.meta.env.DEV

const initApp = async () => {
    try {
        // [Dynamic Port Discovery]
        // Fetch actual bound ports from Main Process before React mounts
        const appApi = (window as any).app;
        if (appApi && appApi.getPorts) {
            const ports = await appApi.getPorts();
            console.log("🔌 [Init] Received Dynamic Ports:", ports);
            updateApiConfig(ports);
        } else {
            console.warn("⚠️ [Init] window.app.getPorts not available. Using default ports.");
        }
    } catch (e) {
        console.error("❌ [Init] Failed to sync ports:", e);
    }

    const root = ReactDOM.createRoot(document.getElementById('root')!)
    
    root.render(
        isDev ? (
            <App />
        ) : (
            <React.StrictMode>
                <App />
            </React.StrictMode>
        ),
    )
};

initApp();
