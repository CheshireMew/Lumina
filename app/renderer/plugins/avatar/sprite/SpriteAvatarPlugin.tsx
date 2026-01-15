import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { IAvatarRenderer } from '../../../core/avatar/types';

interface SpriteAvatarPluginProps {
    /** Base path to sprites folder, e.g. "/sprites/xiaoyue" */
    spritesPath: string;
    /** Default emotion to show on load */
    defaultEmotion?: string;
}

/**
 * Galgame-Style Static Avatar Renderer.
 * 
 * Ultra Lightweight: Just an <img> tag that switches based on emotion.
 * Perfect for MVP and resource-constrained environments.
 * 
 * Expected sprite folder structure:
 *   /sprites/{character}/
 *     neutral.png
 *     joy.png
 *     sad.png
 *     angry.png
 *     surprised.png
 */
const SpriteAvatarPlugin = forwardRef<IAvatarRenderer, SpriteAvatarPluginProps>(
    ({ spritesPath, defaultEmotion = 'neutral' }, ref) => {
    
    const [currentEmotion, setCurrentEmotion] = useState<string>(defaultEmotion);
    const [isTransitioning, setIsTransitioning] = useState<boolean>(false);

    // Implement Standard Interface
    useImperativeHandle(ref, () => ({
        setEmotion: (emotionId: string) => {
            const normalized = emotionId.toLowerCase();
            if (normalized !== currentEmotion) {
                // Trigger fade transition
                setIsTransitioning(true);
                setTimeout(() => {
                    setCurrentEmotion(normalized);
                    setIsTransitioning(false);
                }, 150); // Quick fade
            }
        },
        motion: (group, index) => {
            // Sprites don't have motions, but we can map some to emotions
            console.log('[SpriteAvatar] Motion triggered (mapped to emotion):', group);
            if (group.toLowerCase().includes('tap')) {
                // Could trigger a "surprised" or "happy" on tap
            }
        },
        stopExpression: () => {
            setCurrentEmotion(defaultEmotion);
        },
        speak: async (audioUrl) => {
            // Could add a simple "talking" animation frame later
            // For now, no-op
        },
        lookAt: (x, y) => {
            // Sprites are 2D static, lookAt not applicable
        },
        getCanvas: () => {
            return null; // Uses <img> tag
        },
        setBlendShapes: (data) => {
            // Sprites don't support facial capture blendshapes
        }
    }));

    // Listen for emotion:changed events from WebSocket
    useEffect(() => {
        const handleEmotionEvent = (event: CustomEvent) => {
            const emotion = event.detail?.emotion;
            if (emotion) {
                setCurrentEmotion(emotion.toLowerCase());
            }
        };
        
        // Listen on window for events forwarded from WebSocket handler
        window.addEventListener('lumina:emotion', handleEmotionEvent as EventListener);
        
        return () => {
            window.removeEventListener('lumina:emotion', handleEmotionEvent as EventListener);
        };
    }, []);

    // Build image src
    const imageSrc = `${spritesPath}/${currentEmotion}.png`;
    const fallbackSrc = `${spritesPath}/${defaultEmotion}.png`;

    return (
        <div style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-end',
            overflow: 'hidden',
            position: 'relative'
        }}>
            <img
                src={imageSrc}
                alt={`Avatar - ${currentEmotion}`}
                onError={(e) => {
                    // Fallback to default if emotion sprite not found
                    (e.target as HTMLImageElement).src = fallbackSrc;
                }}
                style={{
                    maxHeight: '90%',
                    maxWidth: '100%',
                    objectFit: 'contain',
                    transition: 'opacity 0.15s ease-in-out',
                    opacity: isTransitioning ? 0.5 : 1,
                    // Center bottom alignment (Galgame style)
                    marginBottom: '5%'
                }}
            />
        </div>
    );
});

export default SpriteAvatarPlugin;
