import React from 'react';

interface SegmentChipProps {
    label: string;
    count: number;
    isCatchAll?: boolean;
}

export function SegmentChip({ label, count, isCatchAll }: SegmentChipProps) {
    return (
        <div
            className={`inline-flex items-center px-3 py-1.5 rounded-full border text-sm ${isCatchAll
                    ? 'border-dashed border-gray-300 bg-gray-50 text-gray-600'
                    : 'border-gray-200 bg-white text-gray-800'
                }`}>
            <span className="font-medium">{label}</span>
            <span className="ml-2 text-gray-500">({count.toLocaleString()})</span>
            {isCatchAll && (
                <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider bg-gray-200 text-gray-600 font-semibold">
                    Catch-all
                </span>
            )}
        </div>
    );
}
