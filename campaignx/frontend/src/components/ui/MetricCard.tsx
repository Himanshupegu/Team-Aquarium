import React from 'react';
import { Card, CardContent } from './Card';

interface MetricCardProps {
    icon: React.ReactNode;
    value: string | number;
    label: string;
    delta?: string;
}

export function MetricCard({ icon, value, label, delta }: MetricCardProps) {
    return (
        <Card variant="outlined">
            <CardContent className="p-5">
                <div className="flex items-center justify-between mb-4">
                    <div className="text-gray-500">{icon}</div>
                </div>
                <div>
                    <div className="text-3xl font-bold text-gray-900">{value}</div>
                    <div className="flex items-center justify-between mt-1">
                        <div className="text-sm text-gray-500">{label}</div>
                        {delta && (
                            <div className="text-xs font-medium text-green-600">{delta}</div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
