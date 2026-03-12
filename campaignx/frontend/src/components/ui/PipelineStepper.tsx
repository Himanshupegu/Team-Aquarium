import React from 'react';
import {
    CheckIcon, FileTextIcon, UsersIcon, SparklesIcon,
    ShieldCheckIcon, PlayIcon, BarChart3Icon, ZapIcon
} from 'lucide-react';

interface PipelineStepperProps {
    stages?: string[];
    currentStageIndex: number;
    completedStages: number[];
}

const stageIcons = [
    FileTextIcon,      // Parsing
    UsersIcon,         // Profiling
    SparklesIcon,      // Generating
    ShieldCheckIcon,   // Approval
    PlayIcon,          // Executing
    BarChart3Icon,     // Analyzing
    ZapIcon,           // Optimizing
];

export function PipelineStepper({
    stages = ['Parsing', 'Profiling', 'Generating', 'Approval', 'Executing', 'Analyzing', 'Optimizing'],
    currentStageIndex,
    completedStages,
}: PipelineStepperProps) {
    return (
        <div className="w-full py-4">
            <div className="flex items-center justify-between relative">
                {stages.map((stage, index) => {
                    const isCompleted = completedStages.includes(index);
                    const isActive = index === currentStageIndex;
                    const isPending = !isCompleted && !isActive;
                    const IconComponent = stageIcons[index] || ZapIcon;

                    return (
                        <React.Fragment key={stage}>
                            {/* Connecting line segment BEFORE this step (except the first) */}
                            {index > 0 && (
                                <div className="flex-1 h-0.5 mx-1 relative bg-gray-200 rounded-full overflow-hidden">
                                    {(isCompleted || isActive) && (
                                        <div
                                            className={`absolute inset-y-0 left-0 bg-blue-500 rounded-full ${isActive ? 'pipeline-line-fill' : 'w-full'
                                                }`}
                                            style={isActive ? undefined : { width: '100%' }}
                                        />
                                    )}
                                </div>
                            )}

                            {/* Step circle + label */}
                            <div className="relative z-10 flex flex-col items-center" style={{ minWidth: 72 }}>
                                <div className="relative flex items-center justify-center mb-2">
                                    {/* Active glow ring */}
                                    {isActive && (
                                        <span className="absolute inset-[-4px] rounded-full stage-icon-active border-2 border-blue-400/50" />
                                    )}

                                    <div
                                        className={`
                                            flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300
                                            ${isCompleted ? 'bg-blue-500 text-white shadow-md shadow-blue-200' : ''}
                                            ${isActive ? 'bg-white border-2 border-blue-500 text-blue-600 shadow-lg shadow-blue-100' : ''}
                                            ${isPending ? 'bg-gray-100 border-2 border-gray-200 text-gray-400' : ''}
                                        `}
                                    >
                                        {isCompleted ? (
                                            <CheckIcon className="w-5 h-5" strokeWidth={3} />
                                        ) : (
                                            <IconComponent className="w-5 h-5" />
                                        )}
                                    </div>
                                </div>

                                <span
                                    className={`
                                        text-[11px] font-semibold uppercase tracking-wide text-center leading-tight
                                        ${isActive ? 'text-blue-600 font-bold' : ''}
                                        ${isCompleted ? 'text-gray-700' : ''}
                                        ${isPending ? 'text-gray-400' : ''}
                                    `}
                                >
                                    {stage}
                                </span>
                            </div>
                        </React.Fragment>
                    );
                })}
            </div>
        </div>
    );
}
