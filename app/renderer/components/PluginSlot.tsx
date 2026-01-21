import React, { useMemo } from 'react';
import { usePluginSlots } from '../hooks/usePluginSlots';
import { API_CONFIG } from '../config';

interface PluginSlotProps {
    name: string; // The slot identifier (e.g., "sidebar_bottom")
    className?: string;
    style?: React.CSSProperties;
}

/**
 * PluginSlot
 * 
 * A placeholder container that automatically renders UI widgets injected by Plugins.
 * Uses <iframe> for sandboxing constraint (Backend serves the HTML).
 */
export const PluginSlot: React.FC<PluginSlotProps> = ({ name, className, style }) => {
    const { slots } = usePluginSlots();

    // Filter slots targeting this location
    const activeWidgets = useMemo(() => {
        return slots.filter(s => s.slot === name);
    }, [slots, name]);

    if (activeWidgets.length === 0) return null;

    return (
        <div className={`plugin-slot-container ${className || ''}`} style={style}>
            {activeWidgets.map((widget) => {
                // Determine Source URL
                // If src starts with http, use it.
                // If relative (e.g. 'ui/index.html'), construct local backend static path
                // We need a way to serve plugin assets. 
                // Assumption: Backend creates a static route for active plugins at /plugins/assets/{plugin_id}/...
                
                let widgetUrl = widget.src;
                // [Security] robust absolute URL check (http, https, //, data, blob)
                const isAbsolute = /^(https?:|\/\/|data:|blob:)/i.test(widgetUrl);
                
                if (!isAbsolute) {
                    widgetUrl = `${API_CONFIG.BASE_URL}/plugins/assets/${widget.plugin_id}/${widget.src}`;
                }

                // [Security] Inject Scoped Token if available
                if (widget._token) {
                    const separator = widgetUrl.includes('?') ? '&' : '?';
                    widgetUrl += `${separator}token=${encodeURIComponent(widget._token)}`;
                }

                return (
                    <div key={`${widget.plugin_id}-${name}-${widget.name}`} className="plugin-widget mb-4">
                        <iframe 
                            src={widgetUrl}
                            title={widget.name}
                            style={{
                                width: widget.width ?? '100%',
                                height: widget.height || 200,
                                border: 'none',
                                borderRadius: '8px',
                                background: 'rgba(255,255,255,0.05)',
                            }}
                            // Security: Sandbox the iframe
                            // [Security] Removed allow-same-origin
                            sandbox="allow-scripts allow-forms allow-popups"
                        ></iframe>
                    </div>
                );
            })}
        </div>
    );
};
