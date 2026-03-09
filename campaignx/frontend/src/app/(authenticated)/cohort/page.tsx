'use client';
import React, { useEffect, useState } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { Button } from '@/components/ui/Button';
import { RefreshCwIcon, Loader2Icon, AlertTriangleIcon } from 'lucide-react';

interface CohortSummaryData {
    total_customers: number;
    total_cities: number;
    average_age: number;
    dominant_income_tier: string;
    gender_split: Record<string, { count: number; percentage: number }>;
    age_distribution: Record<string, number>;
    income_distribution: Record<string, { count: number; percentage: number }>;
    top_cities: { name: string; count: number; percentage: number }[];
    current_segments: { segment_label: string; customer_count: number; percentage: number }[];
}

export default function CohortExplorerPage() {
    const [data, setData] = useState<CohortSummaryData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchCohortData = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiUrl}/api/cohort/summary`);
            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(errData?.detail || `API error (${res.status})`);
            }
            const json = await res.json();

            // If the cache is empty initially, the dict might be empty
            if (Object.keys(json).length === 0) {
                throw new Error("Cohort data is empty. Backend returned {}.");
            }
            setData(json);
        } catch (err: any) {
            console.error("Failed to fetch cohort summary:", err);
            setError(err.message || "Failed to load cohort data");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchCohortData();
    }, []);

    if (isLoading) {
        return (
            <div className="max-w-7xl mx-auto py-24 flex flex-col items-center justify-center">
                <Loader2Icon className="w-8 h-8 text-blue-500 animate-spin mb-4" />
                <div className="text-gray-500 font-medium">Loading cohort metrics...</div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="max-w-7xl mx-auto py-12 text-center">
                <AlertTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Cohort</h2>
                <p className="text-gray-500 mb-6">{error || "Unknown error"}</p>
                <Button variant="secondary" leftIcon={<RefreshCwIcon className="w-4 h-4" />} onClick={fetchCohortData}>
                    Try Again
                </Button>
            </div>
        );
    }

    // Prepare chart rendering data
    const formatNumber = (num: number) => new Intl.NumberFormat().format(num);
    const maxAgeCount = Math.max(...Object.values(data.age_distribution || {}));
    const ageBars = Object.entries(data.age_distribution || {}).map(([label, count]) => {
        const pct = maxAgeCount > 0 ? (count / maxAgeCount) * 100 : 0;
        return { label, count, pct, shade: 'bg-blue-400' };
    });

    const genderEntries = Object.entries(data.gender_split || {}).map(([label, val], i) => {
        const colors = ['bg-blue-500', 'bg-pink-500', 'bg-purple-500'];
        return { label, pct: val.percentage, count: val.count, color: colors[i % colors.length] };
    });

    const segmentColors = ['bg-gray-900', 'bg-gray-700', 'bg-gray-500', 'bg-gray-400', 'bg-gray-300', 'bg-gray-800'];
    const segments = (data.current_segments || []).map((seg, i) => ({
        num: i + 1,
        label: seg.segment_label,
        count: seg.customer_count,
        pct: seg.percentage,
        bg: segmentColors[i % segmentColors.length]
    }));

    return (
        <div className="max-w-7xl mx-auto">
            <div className="flex items-start justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-1">Cohort Explorer</h1>
                    <p className="text-gray-500">{formatNumber(data.total_customers)} customers</p>
                </div>
                <Button variant="secondary" leftIcon={<RefreshCwIcon className="w-4 h-4" />} onClick={fetchCohortData}>Refresh</Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <MetricCard icon={null} value={formatNumber(data.total_customers)} label="Total Customers" />
                <MetricCard icon={null} value={formatNumber(data.total_cities)} label="Number of Cities" />
                <MetricCard icon={null} value={data.average_age.toString()} label="Average Age" />
                <MetricCard icon={null} value={data.dominant_income_tier} label="Dominant Income" />
            </div>

            <div className="flex flex-col lg:flex-row gap-8 mb-8">
                {/* Left: Demographics */}
                <div className="lg:w-[65%] space-y-6">
                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-6">Gender Split</h3>
                        <div className="space-y-4">
                            {genderEntries.map((g) => (
                                <div key={g.label}>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-700">{g.label} ({formatNumber(g.count)})</span>
                                        <span className="font-medium">{g.pct}%</span>
                                    </div>
                                    <div className="w-full h-4 bg-gray-100 rounded-full overflow-hidden">
                                        <div className={`h-full ${g.color}`} style={{ width: `${g.pct}%` }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-6">Age Distribution</h3>
                        <div className="flex h-48 gap-4 items-end">
                            {ageBars.map((bar) => (
                                <div key={bar.label} className="flex-1 flex flex-col items-center h-full">
                                    <div className="w-full flex-1 flex flex-col justify-end">
                                        <div className={`w-full ${bar.shade} rounded-t-md relative group`} style={{ height: `${bar.pct}%` }}>
                                            <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 text-white px-2 py-1 rounded whitespace-nowrap z-10">{formatNumber(bar.count)}</span>
                                        </div>
                                    </div>
                                    <span className="text-xs text-gray-500 mt-2">{bar.label}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right: Segmentation */}
                <div className="lg:w-[35%]">
                    <div className="bg-white border border-gray-200 rounded-xl p-6 h-full">
                        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-6">Current Segmentation</h3>
                        {segments.length === 0 ? (
                            <div className="text-sm text-gray-500 italic text-center py-12">No campaign segments sent yet.</div>
                        ) : (
                            <div className="space-y-6">
                                {segments.map((seg) => {
                                    const isCatchAll = seg.label === 'catch_all' || seg.label.toLowerCase().includes('catch');
                                    return (
                                        <div key={seg.num} className={isCatchAll ? "pt-4 border-t border-gray-100" : ""}>
                                            <div className="flex items-center justify-between mb-2">
                                                {isCatchAll ? (
                                                    <span className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 text-[10px] uppercase tracking-wider font-bold">Catch-all</span>
                                                ) : (
                                                    <div className="flex items-center gap-2">
                                                        <span className={`w-5 h-5 rounded-full ${seg.bg} text-white text-[10px] flex items-center justify-center font-bold`}>{seg.num}</span>
                                                        <span className="font-medium text-gray-900 truncate" title={seg.label}>{seg.label}</span>
                                                    </div>
                                                )}
                                                <span className="text-sm font-medium">{seg.pct}%</span>
                                            </div>
                                            <div className="text-xs text-gray-500 mb-2">{formatNumber(seg.count)} customers</div>
                                            <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                                <div className={`h-full ${isCatchAll ? 'bg-gray-300' : seg.bg}`} style={{ width: `${seg.pct}%` }} />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Top Cities Table */}
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Top Cities</h3>
                </div>
                <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 font-medium">
                        <tr>
                            <th className="px-6 py-3 w-16">Rank</th>
                            <th className="px-6 py-3">City Name</th>
                            <th className="px-6 py-3 text-right">Customer Count</th>
                            <th className="px-6 py-3 text-right">% of Total</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {(data.top_cities || []).map((row, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-6 py-3 text-gray-500">{idx + 1}</td>
                                <td className="px-6 py-3 font-medium text-gray-900">{row.name}</td>
                                <td className="px-6 py-3 text-right text-gray-600">{formatNumber(row.count)}</td>
                                <td className="px-6 py-3 text-right text-gray-500">{row.percentage}%</td>
                            </tr>
                        ))}
                        {data.top_cities?.length === 0 && (
                            <tr>
                                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">No city data available</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

