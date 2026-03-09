import React from 'react';
import { formatIST } from '@/lib/dateUtils';

interface AgentLogRowProps {
    timestamp: string;
    agent: string;
    message: string;
    agentColor?: string;
}

export function AgentLogRow({ timestamp, agent, message, agentColor }: AgentLogRowProps) {
    const getColorClasses = (color?: string) => {
        switch (color) {
            case 'purple': return 'bg-purple-100 text-purple-700 border-purple-200';
            case 'blue': return 'bg-blue-100 text-blue-700 border-blue-200';
            case 'green': return 'bg-green-100 text-green-700 border-green-200';
            case 'orange': return 'bg-orange-100 text-orange-700 border-orange-200';
            case 'teal': return 'bg-teal-100 text-teal-700 border-teal-200';
            case 'pink': return 'bg-pink-100 text-pink-700 border-pink-200';
            default: return 'bg-gray-100 text-gray-700 border-gray-200';
        }
    };
    return (
        <div className="flex items-start py-2 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors px-2 -mx-2 rounded">
            <div className="w-24 flex-shrink-0 pt-0.5">
                <span className="font-mono text-xs text-gray-400">{formatIST(timestamp)}</span>
            </div>
            <div className="w-28 flex-shrink-0">
                <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium border uppercase tracking-wider ${getColorClasses(agentColor)}`}>
                    {agent}
                </span>
            </div>
            <div className="flex-1 text-sm text-gray-700 pt-0.5">{message}</div>
        </div>
    );
}
