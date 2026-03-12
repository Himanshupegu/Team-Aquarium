import React from 'react';
import { Card, CardContent } from './Card';

export type MetricAccentColor = 'blue' | 'green' | 'purple' | 'orange' | 'teal' | 'red' | 'gray';

interface MetricCardProps {
    icon: React.ReactNode;
    value: string | number;
    label: string;
    delta?: string;
    accentColor?: MetricAccentColor;
}

export function MetricCard({ icon, value, label, delta, accentColor = 'gray' }: MetricCardProps) {
    const getColorClasses = (color: MetricAccentColor) => {
        switch (color) {
            case 'blue': return 'bg-blue-50 text-blue-600 border-blue-100';
            case 'green': return 'bg-emerald-50 text-emerald-600 border-emerald-100';
            case 'purple': return 'bg-purple-50 text-purple-600 border-purple-100';
            case 'orange': return 'bg-orange-50 text-orange-600 border-orange-100';
            case 'teal': return 'bg-teal-50 text-teal-600 border-teal-100';
            case 'red': return 'bg-red-50 text-red-600 border-red-100';
            default: return 'bg-gray-50 text-gray-500 border-gray-100';
        }
    };

    const colorClasses = getColorClasses(accentColor);

    return (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden relative">
            <div className="p-5 flex items-start gap-4">
                {/* Icon Container */}
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 border ${colorClasses}`}>
                    {icon}
                </div>

                {/* Content */}
                <div className="flex-1">
                    <div className="text-3xl font-bold text-gray-900 tracking-tight">{value}</div>
                    <div className="text-sm font-medium text-gray-500 mt-1">{label}</div>

                    {delta && (
                        <div className="mt-2 inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-100">
                            {delta}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
