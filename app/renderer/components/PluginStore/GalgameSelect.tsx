import React, { useState, useRef, useEffect } from 'react';
import './GalgameSelect.css';

interface Option {
  value: string;
  label: string;
}

interface GalgameSelectProps {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  placeholder?: string;
}

const GalgameSelect: React.FC<GalgameSelectProps> = ({ value, options, onChange, placeholder = "Select..." }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find(opt => opt.value === value);

  return (
    <div className={`galgame-select-container ${isOpen ? 'is-open' : ''}`} ref={containerRef}>
      <div 
        className="galgame-select-trigger" 
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="selected-text">{selectedOption ? selectedOption.label : placeholder}</span>
        <div className="arrow-icon">▼</div>
      </div>
      
      {isOpen && (
        <div className="galgame-select-dropdown">
          {options.map(option => (
            <div 
              key={option.value} 
              className={`select-option ${option.value === value ? 'selected' : ''}`}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
            >
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GalgameSelect;
