import React, { Component, Suspense, forwardRef } from 'react';
import { AvatarRendererRef } from './types';

const Live2DRenderer = React.lazy(() => import('./live2d/Live2DRenderer'));

interface AvatarContainerProps {
    modelPath: string;
    highDpi?: boolean;
    cubismCoreSrc?: string;
}

class AvatarErrorBoundary extends Component<
    { children: React.ReactNode },
    { error: Error | null }
> {
    state: { error: Error | null } = { error: null };

    static getDerivedStateFromError(error: Error) {
        return { error };
    }

    componentDidCatch(error: Error) {
        console.error('[AvatarContainer] Avatar renderer crashed:', error);
    }

    render() {
        if (this.state.error) {
            return (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#64748b' }}>
                    Avatar failed to load
                </div>
            );
        }

        return this.props.children;
    }
}

const AvatarContainer = forwardRef<AvatarRendererRef, AvatarContainerProps>(({ modelPath, highDpi, cubismCoreSrc }, ref) => {
    const LoadingFallback = (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#888' }}>
            Initializing Live2D Engine...
        </div>
    );

    return (
        <AvatarErrorBoundary>
            <Suspense fallback={LoadingFallback}>
                <Live2DRenderer
                    ref={ref}
                    modelPath={modelPath}
                    highDpi={highDpi}
                    cubismCoreSrc={cubismCoreSrc}
                />
            </Suspense>
        </AvatarErrorBoundary>
    );
});

export default AvatarContainer;

