import './polyfills';
import './index.css';
import './App.css'; // Global Styles
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

const isDev = import.meta.env.DEV
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
