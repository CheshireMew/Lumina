
import React, { useEffect, useState } from 'react';

/**
 * Widget Definition from Backend Protocol
 */
interface WidgetDef {
    id: string;         // Unique instance ID (e.g. "stock_ticker")
    plugin_id: string;  // Owner plugin (e.g. "system.stocks")
    src: string;        // Asset URL (e.g. "/api/plugins/system.stocks/assets/index.html")
    location: string;   // "sidebar_right", "dashboard", etc.
    height?: string;    // CSS height
    title?: string;
}

interface WidgetContainerProps {
    location: string; // Filter widgets by location
    className?: string;
}

export const WidgetContainer: React.FC<WidgetContainerProps> = ({ location, className }) => {
    const [widgets, setWidgets] = useState<WidgetDef[]>([]);

    useEffect(() => {
        // Handler for "ui:register_widget"
        const handleRegister = (e: Event) => {
            const customEvent = e as CustomEvent;
            const payload = customEvent.detail;
            console.log("🧩 Widget Registration Received:", payload);
            
            // Validate Location
            if (payload.location !== location) return;

            // Add or Update
            setWidgets(prev => {
                // Remove existing if duplicate ID
                const filtered = prev.filter(w => w.id !== payload.id);
                return [...filtered, payload];
            });
        };

        // Handler for "ui:remove_widget"
        const handleRemove = (e: Event) => {
             const customEvent = e as CustomEvent;
             const payload = customEvent.detail;
             if (payload.location !== location) return;
             setWidgets(prev => prev.filter(w => w.id !== payload.id));
        };

        window.addEventListener("ui:register_widget", handleRegister);
        window.addEventListener("ui:remove_widget", handleRemove);

        return () => {
            window.removeEventListener("ui:register_widget", handleRegister);
            window.removeEventListener("ui:remove_widget", handleRemove);
        };
    }, [location]);

    if (widgets.length === 0) return null;

    return (
        <div className={`flex flex-col gap-4 ${className} pointer-events-auto`}>
            {widgets.map(widget => (
                <div key={widget.id} className="bg-white/5 border border-white/10 rounded-lg overflow-hidden backdrop-blur-sm shadow-lg">
                    {widget.title && (
                        <div className="px-3 py-1 bg-white/5 text-xs font-bold text-white/60 uppercase tracking-wider">
                            {widget.title}
                        </div>
                    )}
                    <iframe 
                        src={`http://localhost:8000${widget.src}`} 
                        className="w-full border-0"
                        style={{ height: widget.height || '200px' }}
                        sandbox="allow-scripts allow-forms allow-same-origin" // Security Sandbox
                        title={widget.id}
                    />
                </div>
            ))}
        </div>
    );
};
