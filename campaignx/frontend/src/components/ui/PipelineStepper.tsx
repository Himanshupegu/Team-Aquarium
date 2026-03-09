import React from 'react';
import { CheckIcon } from 'lucide-react';

interface PipelineStepperProps {
    stages?: string[];
    currentStageIndex: number;
    completedStages: number[];
}

export function PipelineStepper({
    stages = ['Parsing', 'Profiling', 'Generating', 'Approval', 'Executing', 'Analyzing', 'Optimizing'],
    currentStageIndex,
    completedStages,
}: PipelineStepperProps) {
    return (
        <div className="w-full py-6">
            <div className="flex items-center justify-between relative">
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-gray-200 z-0" />
                {stages.map((stage, index) => {
                    const isCompleted = completedStages.includes(index);
                    const isActive = index === currentStageIndex;
                    const isPending = !isCompleted && !isActive;
                    return (
                        <div key={stage} className="relative z-10 flex flex-col items-center group">
                            {index > 0 && (isCompleted || isActive) && (
                                <div
                                    className="absolute right-1/2 top-4 -translate-y-1/2 h-0.5 bg-blue-500 -z-10"
                                    style={{ width: '100vw', maxWidth: '100%' }}
                                />
                            )}
                            <div className="relative flex items-center justify-center w-8 h-8 mb-2 bg-white">
                                {isActive && (
                                    <span className="absolute inset-0 rounded-full animate-ping bg-blue-400 opacity-20" />
                                )}
                                <div
                                    className={`
                    flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors duration-200
                    ${isCompleted ? 'bg-blue-500 border-blue-500 text-white' : ''}
                    ${isActive ? 'bg-white border-blue-500 text-blue-600' : ''}
                    ${isPending ? 'bg-white border-gray-300 text-gray-400' : ''}
                  `}>
                                    {isCompleted ? (
                                        <CheckIcon className="w-4 h-4" />
                                    ) : (
                                        <span className="text-xs font-semibold">{index + 1}</span>
                                    )}
                                </div>
                            </div>
                            <span
                                className={`text-xs font-medium ${isActive ? 'text-blue-600' : isCompleted ? 'text-gray-900' : 'text-gray-400'
                                    }`}>
                                {stage}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
