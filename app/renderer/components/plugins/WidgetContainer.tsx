
import React from 'react';
import { PluginSlot } from '../PluginSlot';

interface WidgetContainerProps {
    location: string;
    className?: string;
}

/**
 * WidgetContainer (Legacy Name, New Implementation)
 * Wrapper around PluginSlot to maintain generic "Widget" naming in App.tsx
 */
export const WidgetContainer: React.FC<WidgetContainerProps> = ({ location, className }) => {
    return (
        <PluginSlot 
            name={location} 
            className={`flex flex-col gap-4 ${className} pointer-events-auto`}
            style={{ width: '100%' }}
        />
    );
};
