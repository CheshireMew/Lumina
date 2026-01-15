import React from 'react';
import './GalgameToggle.css';

interface GalgameToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  labelOn?: string;
  labelOff?: string;
}

const GalgameToggle: React.FC<GalgameToggleProps> = ({ 
  checked, 
  onChange, 
  disabled = false,
  labelOn = 'ON',
  labelOff = 'OFF'
}) => {
  return (
    <div 
      className={`galgame-toggle-wrapper ${checked ? 'is-checked' : ''} ${disabled ? 'is-disabled' : ''}`}
      onClick={() => !disabled && onChange(!checked)}
    >
      <div className="galgame-toggle-track">
        <div className="galgame-toggle-thumb">
           <div className="thumb-glow"></div>
        </div>
        <div className="toggle-labels">
            <span className={`label-text off ${!checked ? 'active' : ''}`}>{labelOff}</span>
            <span className={`label-text on ${checked ? 'active' : ''}`}>{labelOn}</span>
        </div>
      </div>
    </div>
  );
};

export default GalgameToggle;
