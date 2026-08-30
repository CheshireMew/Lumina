import { Brain } from "lucide-react";
import type { FC } from "react";
import {
    parameterStyles,
    sectionTitleStyle,
} from "./styles";

interface GenerationParamsSectionProps {
    temperature: number;
    topP: number;
    presencePenalty: number;
    frequencyPenalty: number;
    onTemperatureChange: (temperature: number) => void;
    onTopPChange: (topP: number) => void;
    onPresencePenaltyChange: (presencePenalty: number) => void;
    onFrequencyPenaltyChange: (frequencyPenalty: number) => void;
}

const GenerationParamsSection: FC<GenerationParamsSectionProps> = ({
    temperature,
    topP,
    presencePenalty,
    frequencyPenalty,
    onTemperatureChange,
    onTopPChange,
    onPresencePenaltyChange,
    onFrequencyPenaltyChange,
}) => (
    <div>
        <div style={sectionTitleStyle}>
            <Brain size={14} /> 生成参数
        </div>

        <div style={parameterStyles.card}>
            <div style={parameterStyles.row}>
                <span style={parameterStyles.mainLabel}>
                    随机性（Temperature）
                </span>
                <span style={parameterStyles.primaryValue}>{temperature}</span>
            </div>
            <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(event) =>
                    onTemperatureChange(parseFloat(event.target.value))
                }
                className="gal-range"
            />

            <div style={parameterStyles.advancedGrid}>
                <div>
                    <div style={parameterStyles.row}>
                        <span style={parameterStyles.smallLabel}>Top P</span>
                        <span style={parameterStyles.secondaryValue}>{topP}</span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={topP}
                        onChange={(event) =>
                            onTopPChange(parseFloat(event.target.value))
                        }
                        className="gal-range violet"
                    />
                </div>
                <div>
                    <div style={parameterStyles.row}>
                        <span style={parameterStyles.smallLabel}>
                            重复惩罚
                        </span>
                        <span style={parameterStyles.secondaryValue}>
                            {frequencyPenalty}
                        </span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={frequencyPenalty}
                        onChange={(event) =>
                            onFrequencyPenaltyChange(
                                parseFloat(event.target.value),
                            )
                        }
                        className="gal-range violet"
                    />
                </div>
                <div style={parameterStyles.fullWidth}>
                    <div style={parameterStyles.row}>
                        <span style={parameterStyles.smallLabel}>
                            话题新鲜度
                        </span>
                        <span style={parameterStyles.secondaryValue}>
                            {presencePenalty}
                        </span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={presencePenalty}
                        onChange={(event) =>
                            onPresencePenaltyChange(
                                parseFloat(event.target.value),
                            )
                        }
                        className="gal-range violet"
                    />
                </div>
            </div>
        </div>
    </div>
);

export default GenerationParamsSection;
