import React, {
    forwardRef,
    useImperativeHandle,
    useRef,
    useState,
    useEffect,
    Suspense
} from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import * as THREE from 'three';
import { IAvatarRenderer, FaceTrackingData } from '../../../core/avatar/types';

// Extend Three.js loader with VRM plugin
// Note: We need to register the plugin in the loader
function VRMModel({ url, onVRMLoaded }: { url: string; onVRMLoaded: (vrm: any) => void }) {
    const gltf = useGLTF(url, (loader) => {
        loader.register((parser) => {
            return new VRMLoaderPlugin(parser);
        });
    });

    useEffect(() => {
        if (gltf.userData.vrm) {
            VRMUtils.removeUnnecessaryVertices(gltf.scene);
            VRMUtils.combineSkeletons(gltf.scene);
            onVRMLoaded(gltf.userData.vrm);
        }
    }, [gltf, onVRMLoaded]);

    return <primitive object={gltf.scene} position={[0, -1.5, 0]} />; // Adjust position as needed
}

interface VRMPluginProps {
    modelPath: string;
}

const VRMPlugin = forwardRef<IAvatarRenderer, VRMPluginProps>(({ modelPath }, ref) => {
    const vrmRef = useRef<any>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [sceneReady, setSceneReady] = useState(false);

    // Internal state for smooth transitions
    const currentEmotion = useRef<string>('neutral');
    const blendShapeTarget = useRef<Map<string, number>>(new Map());

    useImperativeHandle(ref, () => ({
        initialize: async (container) => {
            console.log('[VRM] Initialized');
            setSceneReady(true);
        },
        destroy: () => {
            console.log('[VRM] Destroy');
            setSceneReady(false);
            if (vrmRef.current) {
                VRMUtils.deepDispose(vrmRef.current.scene);
            }
        },
        speak: async (audioUrl, visemes) => {
            if (!vrmRef.current) return;
            // Simple lip sync simulation if visemes provided
            // In a real app, we would play audio and analyze FFT or use visemes array
            // detailed lip sync logic would go here
            console.log('[VRM] Speak:', audioUrl);
        },
        setExpression: (emotion, intensity = 1.0) => {
            if (!vrmRef.current) return;
            // Map standard emotions to VRM presets or custom blendshapes
            // VRM 0.0 uses presets like LOOKUP, DOWN, LEFT, RIGHT, BLINK, etc.
            // VRM 1.0 uses ExpressionManager
            
            const expressionManager = vrmRef.current.expressionManager;
            if (expressionManager) {
                // Reset typical emotions
               expressionManager.setValue('happy', 0);
               expressionManager.setValue('angry', 0);
               expressionManager.setValue('sad', 0);
               expressionManager.setValue('relaxed', 0);
               
               // Set new emotion
               const vrmEmotion = mapEmotionToVRM(emotion);
               if (vrmEmotion) {
                   expressionManager.setValue(vrmEmotion, intensity);
               }
            }
        },
        lookAt: (x: number, y: number) => {
             if (!vrmRef.current || !vrmRef.current.lookAt) return;
             // VRM LookAt usually takes a target Vector3
             // We can use a helper or directly set the target
             // Here we just store it, and useFrame update will apply it relative to head
             const lookAt = vrmRef.current.lookAt;
             if(lookAt.target) {
                 // Map 0..1 screen coord to 3D world coord roughly
                 // This is a simplification. For accurate lookAt, we need raycasting or projection.
                 lookAt.target.position.set((x - 0.5) * 10, (0.5 - y) * 10, 20); 
             }
        },
        getCanvas: () => {
            return canvasRef.current;
        },
        setBlendShapes: (data: FaceTrackingData) => {
            if (!vrmRef.current || !vrmRef.current.expressionManager) return;
            const em = vrmRef.current.expressionManager;
            
            // Map MediaPipeBlendShapes to VRM Expression Presets
            // This is a critical part of Phase 29/31 integration
            
            // Blinking
            em.setValue('blinkLeft', data.eyeBlinkLeft || 0);
            em.setValue('blinkRight', data.eyeBlinkRight || 0);
            
            // Mouth
            em.setValue('aa', data.jawOpen || 0); // Simple mapping
            
            // Head Rotation (handled by humanoid bone rotation usually, or FaceTracker passes raw rotation)
            // If FaceTracker passes standard facial blendshapes, we map them here.
            // Complex mappings (brows, smile) would be added here.
        }
    }));

    // Animation Loop
    // functionality handled inside Canvas children usually

    const onVRMLoaded = (vrm: any) => {
        vrmRef.current = vrm;
        console.log('[VRM] Model Loaded', vrm);
        // Initial setup
        vrm.scene.rotation.y = Math.PI; // Face forward
    };
    
    // Updater component to hook into R3F loop
    const VRMUpdater = () => {
        useFrame((state, delta) => {
            if (vrmRef.current) {
                vrmRef.current.update(delta);
            }
        });
        return null;
    }

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <Canvas 
                ref={canvasRef}
                camera={{ fov: 30, position: [0, 0.0, 2.0] }}
            >
                <ambientLight intensity={0.8} />
                <directionalLight position={[1, 1, 1]} intensity={1} />
                
                <Suspense fallback={null}>
                    {modelPath && (
                        <VRMModel url={modelPath} onVRMLoaded={onVRMLoaded} />
                    )}
                </Suspense>
                
                <VRMUpdater />
                <OrbitControls target={[0, -0.8, 0]} /> 
            </Canvas>
        </div>
    );
});

// Helper to map generic emotions to VRM 1.0 / 0.0 presets
function mapEmotionToVRM(emotion: string): string | null {
    const map: Record<string, string> = {
        'happy': 'happy',
        'joy': 'happy',
        'angry': 'angry',
        'sad': 'sad',
        'sorrow': 'sad',
        'fun': 'relaxed',
        'surprised': 'surprised',
        'neutral': 'neutral'
    };
    return map[emotion.toLowerCase()] || null;
}

export default VRMPlugin;
