import React, { Component, Suspense, forwardRef } from 'react';
import { AvatarRendererRef } from './types';
import type { Live2DBehavior } from '@core/llm/types';

const Live2DRenderer = React.lazy(() => import('./live2d/Live2DRenderer'));

interface AvatarContainerProps {
    modelPath: string;
    highDpi?: boolean;
    cubismCoreSrc: string;
    rendererRuntimeSrc: string;
    behavior: Live2DBehavior;
}

class AvatarErrorBoundary extends Component<
    { children: React.ReactNode; resetKey: string },
    { error: Error | null }
> {
    state: { error: Error | null } = { error: null };

    static getDerivedStateFromError(error: Error) {
        return { error };
    }

    componentDidCatch(error: Error) {
        console.error('[AvatarContainer] Avatar renderer crashed:', error);
    }

    componentDidUpdate(prevProps: { resetKey: string }) {
        if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
            this.setState({ error: null });
        }
    }

    render() {
        if (this.state.error) {
            return (
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    color: '#64748b',
                    textAlign: 'center',
                    maxWidth: 'min(720px, 80vw)',
                    pointerEvents: 'none',
                }}>
                    <div>Avatar failed to load</div>
                    <div style={{ marginTop: 8, fontSize: 13, color: '#94a3b8', wordBreak: 'break-word' }}>
                        {this.state.error.message}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

const AvatarContainer = forwardRef<AvatarRendererRef, AvatarContainerProps>(({ modelPath, highDpi, cubismCoreSrc, rendererRuntimeSrc, behavior }, ref) => {
    const resetKey = `${modelPath}|${cubismCoreSrc || ''}|${rendererRuntimeSrc || ''}|${highDpi ? 'hdpi' : 'sdpi'}|${JSON.stringify(behavior)}`;
    const LoadingFallback = (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#888' }}>
            Initializing Live2D Engine...
        </div>
    );

    return (
        <AvatarErrorBoundary resetKey={resetKey}>
            <Suspense fallback={LoadingFallback}>
                <Live2DRenderer
                    ref={ref}
                    modelPath={modelPath}
                    highDpi={highDpi}
                    cubismCoreSrc={cubismCoreSrc}
                    rendererRuntimeSrc={rendererRuntimeSrc}
                    behavior={behavior}
                />
            </Suspense>
        </AvatarErrorBoundary>
    );
});

export default AvatarContainer;

