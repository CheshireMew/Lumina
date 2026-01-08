import React, { useState, useEffect } from 'react';
import { Heart, Zap, Smile, X, User, Activity, Brain } from 'lucide-react';


interface SoulProfile {
    identity: {
        name: string;
    };
    personality: {
        pad_model: {
            pleasure: number;
            arousal: number;
            dominance: number;
        };
        big_five: {
            openness: number;
            conscientiousness: number;
            extraversion: number;
            agreeableness: number;
            neuroticism: number;
        };
    };
    state: {
        energy_level: number;
        last_interaction: string;
        current_mood?: string;
    };
    relationship: {
        user_name: string;
        level: number;
        progress: number;
        target_stage?: string;
        current_stage_label?: string;
    };
}

const LEVEL_COLORS: {[key: number]: string[]} = {
    [-1]: ['#434343', '#000000'], // Hostile: Black/Dark Grey
    0: ['#bdc3c7', '#7f8c8d'],     // Stranger: Gray
    1: ['#89f7fe', '#66a6ff'],     // Acquaintance: Blue
    2: ['#00b09b', '#96c93d'],     // Friend: Green
    3: ['#f6d365', '#fda085'],     // Close Friend: Orange
    4: ['#a18cd1', '#fbc2eb'],     // Ambiguous: Purple
    5: ['#ff9a9e', '#ff69b4'],     // Lover: Pink
};



interface GalGameHudProps {
    activeCharacterId: string;
    onOpenSurrealViewer?: () => void;
}

const GalGameHud: React.FC<GalGameHudProps> = ({ activeCharacterId, onOpenSurrealViewer }) => {
    const [isVisible, setIsVisible] = useState(false);
    const [profile, setProfile] = useState<SoulProfile | null>(null);

    // Poll Backend for Soul State (使用新的多角色 API)
    useEffect(() => {
        if (!isVisible || !activeCharacterId) return;

        const fetchSoul = async () => {
            try {
                // ⚡ 分别获取 soul 和 state 数据
                const soulRes = await fetch(`http://localhost:8001/soul/${activeCharacterId}`);
                const stateRes = await fetch(`http://localhost:8001/galgame/${activeCharacterId}/state`);
                
                if (soulRes.ok && stateRes.ok) {
                    const soulData = await soulRes.json();
                    const stateData = await stateRes.json();
                    
                    // 合并为 SoulProfile 格式
                    setProfile({
                        identity: { name: activeCharacterId },
                        personality: soulData.personality,
                        state: {
                            current_mood: soulData.state?.current_mood || 'neutral',
                            energy_level: stateData.energy_level || 100,
                            last_interaction: stateData.last_interaction || new Date().toISOString()
                        },
                        relationship: stateData.relationship || {
                            user_name: 'Master',
                            level: 0,
                            progress: 0,
                           current_stage_label: '陌生人'
                        }
                    });
                }
            } catch (err) {
                console.error("Failed to fetch soul:", err);
            }
        };

        fetchSoul();
        const interval = setInterval(fetchSoul, 3000); // Poll every 3s
        return () => clearInterval(interval);
    }, [isVisible, activeCharacterId]); // ⚡ 依赖 activeCharacterId

    // Mood Icon Logic using Lucide SVGs
    const getMoodIcon = (mood: string) => {
        const size = 32;
        switch (mood?.toLowerCase()) {
            case 'happy':
            case 'excited':
            case 'joyful':
                return <Smile size={size} color="#FFD700" fill="rgba(255, 215, 0, 0.2)" />;
            case 'sad':
            case 'depressed':
                return <Smile size={size} color="#4facfe" style={{ transform: 'rotate(180deg)' }} />; // Inverted smile for sad
            case 'angry':
            case 'anxious':
                return <Activity size={size} color="#ff6b6b" />;
            case 'content':
            case 'relaxed':
                return <Smile size={size} color="#96c93d" />;
            case 'neutral':
            case 'calm':
            default:
                return <Smile size={size} color="#bdc3c7" />;
        }
    };
    
    // Tiny SVG Radar Chart Component
    const PersonalityRadar = ({ traits }: { traits: SoulProfile['personality']['big_five'] }) => {
        if (!traits) return null;
        const size = 100;
        const center = size / 2;
        const radius = 40;
        const keys = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism'];
        
        // Calculate points
        const points = keys.map((key, i) => {
            const value = (traits as any)[key] || 0.5;
            const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
            const x = center + radius * value * Math.cos(angle);
            const y = center + radius * value * Math.sin(angle);
            return `${x},${y}`;
        }).join(' ');

        // Background web
        const webPoints = [0.2, 0.4, 0.6, 0.8, 1.0].map(scale => {
             return keys.map((_, i) => {
                const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
                const x = center + radius * scale * Math.cos(angle);
                const y = center + radius * scale * Math.sin(angle);
                return `${x},${y}`;
            }).join(' ');
        });

        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <svg width={size} height={size} style={{ overflow: 'visible' }}>
                    {/* Web */}
                    {webPoints.map((pts, i) => (
                        <polygon key={i} points={pts} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                    ))}
                    {/* Axis Lines */}
                    {keys.map((_, i) => {
                         const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
                         const x = center + radius * Math.cos(angle);
                         const y = center + radius * Math.sin(angle);
                         return <line key={`line-${i}`} x1={center} y1={center} x2={x} y2={y} stroke="rgba(255,255,255,0.1)" />;
                    })}
                    {/* Data Polygon */}
                    <polygon points={points} fill="rgba(255, 105, 180, 0.3)" stroke="#ff69b4" strokeWidth="2" />
                    {/* Labels (simplified) */}
                    {keys.map((k, i) => {
                        // Just first letter for compactness
                        const label = k[0].toUpperCase(); 
                        const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
                        const x = center + (radius + 10) * Math.cos(angle);
                        const y = center + (radius + 10) * Math.sin(angle);
                        return <text key={`label-${i}`} x={x} y={y} fill="#aaa" fontSize="8" textAnchor="middle" dominantBaseline="middle">{label}</text>
                    })}
                </svg>
                <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>O-C-E-A-N</div>
            </div>
        );
    };
    
    // Helper to get gradient
    const getLevelGradient = (level: number = 0) => {
        const colors = LEVEL_COLORS[level] || LEVEL_COLORS[0];
        return `linear-gradient(90deg, ${colors[0]} 0%, ${colors[1]} 100%)`;
    };

    return (
        <>
            {/* Sidebar Actions */}
            <div style={{
                position: 'absolute',
                top: 20,
                left: 20,
                display: 'flex',
                flexDirection: 'column',
                gap: '15px',
                zIndex: 1000
            }}>
                {/* Heart / Status Toggle */}
                <button
                    onClick={() => {
                        setIsVisible(!isVisible);
                    }}
                    style={{
                        background: isVisible ? 'rgba(255, 105, 180, 0.8)' : 'rgba(255, 105, 180, 0.2)',
                        backdropFilter: 'blur(8px)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        borderRadius: '50%',
                        width: '48px',
                        height: '48px',
                        cursor: 'pointer',
                        boxShadow: '0 4px 15px rgba(255, 105, 180, 0.3)',
                        color: isVisible ? '#fff' : '#ff69b4',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.3s ease'
                    }}
                    title="Toggle Status"
                >
                    <Heart size={24} fill={isVisible ? "currentColor" : "none"} />
                </button>

                {/* Brain / Memory Inspector */}
                <button
                    onClick={() => {
                        setIsVisible(false); 
                        onOpenSurrealViewer?.();
                    }}
                    style={{
                        background: 'rgba(0, 255, 157, 0.2)',
                        backdropFilter: 'blur(8px)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        borderRadius: '50%',
                        width: '48px',
                        height: '48px',
                        cursor: 'pointer',
                        boxShadow: '0 4px 15px rgba(0, 255, 157, 0.3)',
                        color: '#00ff9d',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.3s ease'
                    }}
                    title="Open Neural Interface"
                >
                    <Brain size={24} />
                </button>
            </div>

            {/* Status Panel */}
            {isVisible && (
                <div style={{
                    position: 'absolute',
                    top: 20,
                    left: 80, // Offset to right of sidebar
                    width: '280px',
                    background: 'rgba(20, 20, 30, 0.7)', // Dark Glass
                    backdropFilter: 'blur(10px)',
                    borderRadius: '16px',
                    padding: '16px',
                    color: 'white',
                    border: '1px solid rgba(255,255,255,0.1)',
                    zIndex: 1000,
                    fontFamily: "'Segoe UI', Roboto, sans-serif",
                    boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Activity size={18} color="#ff69b4" />
                            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Lumina State</h3>
                        </div>
                        <button 
                            onClick={() => setIsVisible(false)} 
                            style={{ background: 'transparent', border: 'none', color: '#aaa', cursor: 'pointer', display: 'flex' }}
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {profile ? (
                        <>
                            {/* Character Name */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', marginBottom: '16px', color: '#ddd' }}>
                                <User size={16} />
                                <span>Agent: <span style={{ color: '#fff', fontWeight: 'bold' }}>{profile.identity?.name}</span></span>
                            </div>

                            {/* Intimacy Bar (Level System) */}
                            <div style={{ marginBottom: '14px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                        <Heart size={14} color="#ff69b4" fill="#ff69b4" />
                                        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.7)', background: 'rgba(255, 255, 255, 0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                                            Lv.{profile.relationship?.level ?? 0} {profile.relationship?.current_stage_label}
                                        </span>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <span style={{ color: '#ff69b4', fontWeight: 'bold', fontSize: '14px' }}>
                                            {Math.floor(profile.relationship?.progress ?? 0)}
                                        </span>
                                    </div>
                                </div>
                                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                                    <div style={{
                                        width: `${Math.min(100, profile.relationship?.progress || 0)}%`,
                                        height: '100%',
                                        background: getLevelGradient(profile.relationship?.level),
                                        transition: 'width 0.5s ease',
                                        boxShadow: '0 0 8px rgba(0,0,0,0.3)'
                                    }} />
                                </div>
                            </div>

                            {/* Energy Bar */}
                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                                        <Zap size={14} color="#4facfe" fill="#4facfe" />
                                        <span>Energy</span>
                                    </div>
                                    <span style={{ color: '#4facfe', fontWeight: 'bold' }}>{Math.round(profile.state?.energy_level || 0)}</span>
                                </div>
                                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                                    <div style={{
                                        width: `${profile.state?.energy_level || 0}%`,
                                        height: '100%',
                                        background: 'linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)',
                                        transition: 'width 0.5s ease'
                                    }} />
                                </div>
                            </div>

                            {/* Mood & Personality Grid */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                {/* Left: Mood */}
                                <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '10px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                                    <div style={{ marginBottom: '8px' }}>
                                        {getMoodIcon(profile.state?.current_mood || 'neutral')}
                                    </div>
                                    <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '4px' }}>
                                        {profile.state?.current_mood || 'Neutral'}
                                    </div>
                                    <div style={{ fontSize: '10px', fontFamily: 'monospace', color: '#eee', textAlign: 'center' }}>
                                        <div>P: {(profile.personality.pad_model.pleasure).toFixed(2)}</div>
                                        <div>A: {(profile.personality.pad_model.arousal).toFixed(2)}</div>
                                        <div>D: {(profile.personality.pad_model.dominance).toFixed(2)}</div>
                                    </div>
                                </div>
                                
                                {/* Right: Big Five Radar */}
                                <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '10px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                    <PersonalityRadar traits={profile.personality.big_five} />
                                </div>
                            </div>
                        </>
                    ) : (
                        <div style={{ padding: '20px', textAlign: 'center', color: '#666', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                            <Activity className="spin" size={24} />
                            <span>Syncing Soul...</span>
                        </div>
                    )}
                    
                    <style>{`
                        .spin { animation: spin 2s linear infinite; }
                        @keyframes spin { 100% { transform: rotate(360deg); } }
                    `}</style>
                </div>
            )}
            

        </>
    );
};

export default GalGameHud;
