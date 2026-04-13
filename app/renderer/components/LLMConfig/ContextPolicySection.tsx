import { Brain, MessageSquare, Sparkles, Zap } from "lucide-react";
import type { FC } from "react";
import {
    contextStyles,
    parameterStyles,
    primaryColor,
    secondaryColor,
    sectionTitleStyle,
} from "./styles";
import { OverflowStrategy, ProviderType } from "./types";

interface ContextPolicySectionProps {
    providerType: ProviderType;
    historyLimit: number;
    overflowStrategy: OverflowStrategy;
    onHistoryLimitChange: (historyLimit: number) => void;
    onOverflowStrategyChange: (overflowStrategy: OverflowStrategy) => void;
    onResetContext: () => void;
}

const ContextPolicySection: FC<ContextPolicySectionProps> = ({
    providerType,
    historyLimit,
    overflowStrategy,
    onHistoryLimitChange,
    onOverflowStrategyChange,
    onResetContext,
}) => {
    const slideActive = overflowStrategy === "slide";
    const resetActive = overflowStrategy === "reset";

    return (
        <>
            <div style={sectionTitleStyle}>
                <MessageSquare size={14} /> Memory Management
            </div>

            <div style={contextStyles.card}>
                <div style={contextStyles.limitWrap}>
                    <div style={parameterStyles.row}>
                        <span style={parameterStyles.mainLabel}>
                            Context Window
                        </span>
                        <span style={parameterStyles.secondaryValue}>
                            {historyLimit} turns
                        </span>
                    </div>
                    <input
                        type="range"
                        min="5"
                        max="50"
                        step="1"
                        value={historyLimit}
                        onChange={(event) =>
                            onHistoryLimitChange(parseInt(event.target.value))
                        }
                        className="gal-range violet"
                    />
                    {providerType === "free" && historyLimit > 5 && (
                        <div style={contextStyles.warning}>
                            ⚠️ Free Tier auto-caps at 5 turns.
                        </div>
                    )}
                </div>

                <div style={contextStyles.overflowWrap}>
                    <label style={contextStyles.overflowLabel}>
                        Overflow Strategy
                    </label>
                    <div style={contextStyles.overflowGrid}>
                        <button
                            onClick={() => onOverflowStrategyChange("slide")}
                            style={contextStyles.overflowButton(
                                slideActive,
                                primaryColor,
                            )}
                        >
                            <div style={contextStyles.overflowTitle(slideActive)}>
                                Slide
                            </div>
                            <div
                                style={contextStyles.overflowDescription(
                                    slideActive,
                                )}
                            >
                                Rolling Window
                            </div>
                            {slideActive && (
                                <Sparkles
                                    size={60}
                                    color="white"
                                    style={contextStyles.overflowIcon}
                                />
                            )}
                        </button>

                        <button
                            onClick={() => onOverflowStrategyChange("reset")}
                            style={contextStyles.overflowButton(
                                resetActive,
                                secondaryColor,
                            )}
                        >
                            <div style={contextStyles.overflowTitle(resetActive)}>
                                Reset
                            </div>
                            <div
                                style={contextStyles.overflowDescription(
                                    resetActive,
                                )}
                            >
                                Clear & Cache+
                            </div>
                            {resetActive && (
                                <Zap
                                    size={60}
                                    color="white"
                                    style={contextStyles.overflowIcon}
                                />
                            )}
                        </button>
                    </div>
                    <div style={contextStyles.overflowInfo}>
                        {overflowStrategy === "slide"
                            ? "ℹ️ Seamless conversation. Oldest context slides out."
                            : "ℹ️ Optimized for speed & cost. Clears memory when full."}
                    </div>
                </div>

                <button onClick={onResetContext} style={contextStyles.resetButton}>
                    <Brain size={16} /> Reset Session Context
                </button>
            </div>
        </>
    );
};

export default ContextPolicySection;
