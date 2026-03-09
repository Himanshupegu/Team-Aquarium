import React from 'react';

export type CampaignStatus =
    | 'idle'
    | 'starting'
    | 'parsing'
    | 'profiling'
    | 'generating'
    | 'processing'
    | 'awaiting_approval'
    | 'executing'
    | 'analyzing'
    | 'optimizing'
    | 'done'
    | 'error'
    | 'sending'
    | 'drafting';

interface StatusBadgeProps {
    status: CampaignStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    const getStatusConfig = (s: CampaignStatus) => {
        switch (s) {
            case 'idle':
            case 'drafting':
                return { bg: 'bg-gray-100', text: 'text-gray-700', dot: 'bg-gray-500', pulse: false };
            case 'starting':
            case 'parsing':
            case 'profiling':
            case 'generating':
            case 'processing':
            case 'executing':
            case 'analyzing':
            case 'optimizing':
            case 'sending':
                return { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500', pulse: true };
            case 'awaiting_approval':
                return { bg: 'bg-yellow-50', text: 'text-yellow-700', dot: 'bg-yellow-500', pulse: false };
            case 'done':
                return { bg: 'bg-green-50', text: 'text-green-700', dot: 'bg-green-500', pulse: false };
            case 'error':
                return { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', pulse: false };
            default:
                return { bg: 'bg-gray-100', text: 'text-gray-700', dot: 'bg-gray-500', pulse: false };
        }
    };
    const config = getStatusConfig(status);
    const label = status
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase());
    return (
        <div
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
            <div className="relative flex h-2 w-2 mr-2">
                {config.pulse && (
                    <span
                        className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.dot}`}
                    />
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${config.dot}`} />
            </div>
            {label}
        </div>
    );
}
