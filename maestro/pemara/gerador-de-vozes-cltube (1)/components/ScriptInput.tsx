import React, { useState, useEffect } from 'react';
import Spinner from './Spinner';

interface ScriptInputProps {
  script: string;
  onScriptChange: (value: string) => void;
  onSplit: () => void;
  onDistribute: () => void;
  chunksCount: number;
  splitMessage: string;
  isSplitting: boolean;
  splitCharLimit: number;
  onSplitCharLimitChange: (value: number) => void;
}

const ScriptInput: React.FC<ScriptInputProps> = ({
  script,
  onScriptChange,
  onSplit,
  onDistribute,
  chunksCount,
  splitMessage,
  isSplitting,
  splitCharLimit,
  onSplitCharLimitChange,
}) => {
  const [localLimit, setLocalLimit] = useState(String(splitCharLimit));

  useEffect(() => {
    // Sync if parent's prop changes for some reason
    setLocalLimit(String(splitCharLimit));
  }, [splitCharLimit]);
  
  const handleLimitChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value === '') {
        setLocalLimit('');
        return;
    }
    const numValue = parseInt(value, 10);
    if (!isNaN(numValue)) {
        if (numValue > 5000) {
            setLocalLimit('5000');
        } else {
            // Allow typing, but remove leading zeros and non-integer parts.
            setLocalLimit(String(numValue));
        }
    }
  };

  const handleBlur = () => {
    let value = parseInt(localLimit, 10);
    if (isNaN(value) || value < 10) {
      value = 10;
    }
    if (value > 5000) {
      value = 5000;
    }
    setLocalLimit(String(value));
    onSplitCharLimitChange(value);
  };


  return (
    <div className="w-full space-y-4 bg-zinc-700/50 p-4 rounded-lg border border-zinc-600">
        <h2 className="text-lg font-semibold text-gray-200">1. Insira seu roteiro completo</h2>
        <textarea
            value={script}
            onChange={(e) => onScriptChange(e.target.value)}
            placeholder="Cole todo o seu roteiro aqui..."
            className="w-full h-48 p-4 bg-zinc-900 border border-zinc-700 rounded-md focus:ring-2 focus:ring-red-500 focus:outline-none transition-shadow duration-200 text-gray-300 resize-y"
        />

        <div>
            <label htmlFor="char-limit-input" className="block text-sm font-medium text-gray-300 mb-2">
                Limite de caracteres por bloco (10-5000)
            </label>
            <input
                id="char-limit-input"
                type="number"
                min="10"
                max="5000"
                value={localLimit}
                onChange={handleLimitChange}
                onBlur={handleBlur}
                className="w-full sm:w-48 p-2 bg-zinc-900 border border-zinc-600 text-white rounded-md focus:ring-2 focus:ring-red-500 focus:outline-none"
                aria-label="Limite de caracteres por bloco"
            />
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
            <button
                onClick={onSplit}
                disabled={!script || isSplitting}
                className="flex-1 flex items-center justify-center px-6 py-3 bg-red-600 text-white font-bold rounded-md hover:bg-red-700 disabled:bg-zinc-600 disabled:cursor-not-allowed transition-all duration-200"
            >
                {isSplitting ? (
                    <>
                        <Spinner />
                        <span className="ml-2">Separando...</span>
                    </>
                ) : 'Separar Roteiro em Blocos'}
            </button>
            {chunksCount > 0 && (
                 <button
                    onClick={onDistribute}
                    className="flex-1 flex items-center justify-center px-6 py-3 bg-red-800 text-white font-bold rounded-md hover:bg-red-700 transition-all duration-200"
                >
                    Distribuir para as Caixas
                </button>
            )}
        </div>
         {splitMessage && (
            <div className={`p-3 rounded-md text-sm text-center ${splitMessage.includes('Atenção') ? 'bg-yellow-900/50 border border-yellow-700 text-yellow-300' : 'bg-green-900/50 border border-green-700 text-green-300'}`}>
              {splitMessage}
            </div>
          )}
    </div>
  );
};

export default ScriptInput;