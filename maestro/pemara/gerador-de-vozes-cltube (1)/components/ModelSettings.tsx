import React, { useState } from 'react';

interface ModelSettingsProps {
  speed: number;
  onSpeedChange: (value: number) => void;
  temperature: number;
  onTemperatureChange: (value: number) => void;
}

const ChevronDownIcon: React.FC<{ className?: string }> = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
        <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
);


const ModelSettings: React.FC<ModelSettingsProps> = ({ speed, onSpeedChange, temperature, onTemperatureChange }) => {
  const [isOpen, setIsOpen] = useState(true);

  const handleSpeedSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSpeedChange(parseFloat(e.target.value));
  };

  const handleSpeedInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = parseFloat(e.target.value);
    if (isNaN(value)) {
      value = 0.5;
    }
    if (value > 2.0) value = 2.0;
    if (value < 0.5) value = 0.5;
    onSpeedChange(value);
  };

  const handleTemperatureSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onTemperatureChange(parseFloat(e.target.value));
  };

  const handleTemperatureInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = parseFloat(e.target.value);
    if (isNaN(value)) {
      value = 1.0;
    }
    if (value > 2.0) value = 2.0;
    if (value < 0.0) value = 0.0;
    onTemperatureChange(value);
  };

  return (
    <div className="w-full bg-zinc-700/50 p-4 rounded-lg border border-zinc-600">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex justify-between items-center text-lg font-semibold text-gray-200"
        aria-expanded={isOpen}
        aria-controls="model-settings-content"
      >
        <span>3. Configurações do modelo</span>
        <ChevronDownIcon className={`w-6 h-6 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div id="model-settings-content" className="mt-4 space-y-6">
           <div className="space-y-2">
            <label htmlFor="speed-slider" className="block text-sm font-medium text-gray-300">
              Velocidade
            </label>
            <div className="flex items-center gap-4">
              <input
                id="speed-slider"
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={speed}
                onChange={handleSpeedSliderChange}
                className="w-full h-2 bg-zinc-600 rounded-lg appearance-none cursor-pointer accent-red-600"
              />
              <div className="relative">
                <input
                    type="number"
                    min="0.5"
                    max="2.0"
                    step="0.1"
                    value={speed}
                    onChange={handleSpeedInputChange}
                    className="w-24 bg-zinc-900 border border-zinc-600 text-white text-center rounded-md p-1 pl-2 pr-6 focus:ring-2 focus:ring-red-500 focus:outline-none"
                    aria-label="Valor da velocidade"
                />
                 <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">x</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="temperature-slider" className="block text-sm font-medium text-gray-300">
              Temperatura
            </label>
            <div className="flex items-center gap-4">
              <input
                id="temperature-slider"
                type="range"
                min="0.0"
                max="2.0"
                step="0.1"
                value={temperature}
                onChange={handleTemperatureSliderChange}
                className="w-full h-2 bg-zinc-600 rounded-lg appearance-none cursor-pointer accent-red-600"
              />
              <div className="relative">
                <input
                    type="number"
                    min="0.0"
                    max="2.0"
                    step="0.1"
                    value={temperature}
                    onChange={handleTemperatureInputChange}
                    className="w-24 bg-zinc-900 border border-zinc-600 text-white text-center rounded-md p-1 pl-2 pr-4 focus:ring-2 focus:ring-red-500 focus:outline-none"
                    aria-label="Valor da temperatura"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelSettings;