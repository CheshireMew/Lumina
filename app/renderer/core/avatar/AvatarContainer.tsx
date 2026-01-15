import React, { Suspense, forwardRef } from 'react';
import { AvatarRendererRef } from './types';

// 1. Lazy Import Plugins
// The bundle is split here. Heavy engines are only loaded if needed.
const Live2DPlugin = React.lazy(() => import('../../plugins/avatar/live2d/Live2DPlugin'));
const VRMPlugin = React.lazy(() => import('../../plugins/avatar/vrm/VRMPlugin'));
const SpriteAvatarPlugin = React.lazy(() => import('../../plugins/avatar/sprite/SpriteAvatarPlugin'));

interface AvatarContainerProps {
    type?: 'live2d' | 'vrm' | 'sprite' | 'auto'; // 'auto' = detect from extension
    modelPath: string;   // For live2d/vrm: model file. For sprite: sprites folder path
    highDpi?: boolean;
}

/**
 * The "Switchboard" that decides which renderer to load.
 * Priority:
 *   1. Explicit type override
 *   2. Auto-detect from modelPath extension
 *      - .vrm -> VRM
 *      - .model3.json -> Live2D
 *      - folder path (no extension) -> Sprite
 */
const AvatarContainer = forwardRef<AvatarRendererRef, AvatarContainerProps>(({ type = 'auto', modelPath, highDpi }, ref) => {
    
    // Auto-detect type from file extension if 'auto'
    let finalType: 'live2d' | 'vrm' | 'sprite' = 'live2d';
    if (type !== 'auto') {
        finalType = type;
    } else if (modelPath.endsWith('.vrm')) {
        finalType = 'vrm';
    } else if (modelPath.endsWith('.model3.json') || modelPath.endsWith('.moc3')) {
        finalType = 'live2d';
    } else {
        // Assume sprite folder if no recognized extension
        finalType = 'sprite';
    }

    // Fallback UI while loading the engine
    const LoadingFallback = (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#888' }}>
            {finalType === 'sprite' ? 'Loading Avatar...' : `Initializing ${finalType === 'vrm' ? '3D' : 'Live2D'} Engine...`}
        </div>
    );

    return (
        <Suspense fallback={LoadingFallback}>
            {finalType === 'live2d' && (
                <Live2DPlugin 
                    ref={ref} 
                    modelPath={modelPath} 
                    highDpi={highDpi} 
                />
            )}
             
            {finalType === 'vrm' && (
                <VRMPlugin 
                    ref={ref} 
                    modelPath={modelPath} 
                />
            )}

            {finalType === 'sprite' && (
                <SpriteAvatarPlugin
                    ref={ref}
                    spritesPath={modelPath}
                    defaultEmotion="neutral"
                />
            )}
        </Suspense>
    );
});

export default AvatarContainer;

