import { Brain, MessageSquare, Sparkles, Zap } from "lucide-react";
import type { FC } from "react";
import {
    contextStyles,
    parameterStyles,
    primaryColor,
    secondaryColor,
    sectionTitleStyle,
} from "./styles";
import { FREE_LLM_PROVIDER_ID, LlmProviderId, OverflowStrategy } from "./types";

interface ContextPolicySectionProps {
    providerId: LlmProviderId;
    historyLimit: number;
    overflowStrategy: OverflowStrategy;
    onHistoryLimitChange: (historyLimit: number) => void;
    onOverflowStrategyChange: (overflowStrategy: OverflowStrategy) => void;
    onResetContext: () => void;
}

const ContextPolicySection: FC<ContextPolicySectionProps> = ({
    providerId,
    historyLimit,
    overflowStrategy,
    onHistoryLimitChange,
    onOverflowStrategyChange,
    onResetContext,
}) => {
    const slideActive = overflowStrategy === "slide";
    const resetActive = overflowStrategy === "reset";
    const maxHistory = providerId === FREE_LLM_PROVIDER_ID ? 5 : 50;

    return (
        <>
            <div style={sectionTitleStyle}>
                <MessageSquare size={14} /> 上下文管理
            </div>

            <div style={contextStyles.card}>
                <div style={contextStyles.limitWrap}>
                    <div style={parameterStyles.row}>
                        <span style={parameterStyles.mainLabel}>
                            上下文长度
                        </span>
                        <span style={parameterStyles.secondaryValue}>
                            {historyLimit} 轮
                        </span>
                    </div>
                    <input
                        type="range"
                        min="5"
                        max={maxHistory}
                        step="1"
                        value={historyLimit}
                        onChange={(event) =>
                            onHistoryLimitChange(parseInt(event.target.value))
                        }
                        className="gal-range violet"
                    />
                    {providerId === FREE_LLM_PROVIDER_ID && (
                        <div style={contextStyles.warning}>
                            Pollinations 模式固定最多保留 5 轮上下文。
                        </div>
                    )}
                </div>

                <div style={contextStyles.overflowWrap}>
                    <label style={contextStyles.overflowLabel}>
                        超出长度时
                    </label>
                    <div style={contextStyles.overflowGrid}>
                        <button
                            type="button"
                            onClick={() => onOverflowStrategyChange("slide")}
                            style={contextStyles.overflowButton(
                                slideActive,
                                primaryColor,
                            )}
                        >
                            <div style={contextStyles.overflowTitle(slideActive)}>
                                滑动保留
                            </div>
                            <div
                                style={contextStyles.overflowDescription(
                                    slideActive,
                                )}
                            >
                                淘汰最早内容
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
                            type="button"
                            onClick={() => onOverflowStrategyChange("reset")}
                            style={contextStyles.overflowButton(
                                resetActive,
                                secondaryColor,
                            )}
                        >
                            <div style={contextStyles.overflowTitle(resetActive)}>
                                重新开始
                            </div>
                            <div
                                style={contextStyles.overflowDescription(
                                    resetActive,
                                )}
                            >
                                清空短期上下文
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
                            ? "达到上限后，只移除最早的对话内容。"
                            : "达到上限后，清空本次会话的短期上下文。"}
                    </div>
                </div>

                <button type="button" onClick={onResetContext} style={contextStyles.resetButton}>
                    <Brain size={16} /> 立即清除本次上下文
                </button>
            </div>
        </>
    );
};

export default ContextPolicySection;
