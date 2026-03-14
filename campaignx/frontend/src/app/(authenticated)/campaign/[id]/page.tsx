'use client';
import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { StatusBadge, CampaignStatus } from '@/components/ui/StatusBadge';
import { PipelineStepper } from '@/components/ui/PipelineStepper';
import { AgentLogRow } from '@/components/ui/AgentLogRow';
import { SegmentChip } from '@/components/ui/SegmentChip';
import { Card, CardContent } from '@/components/ui/Card';
import {
    ArrowLeftIcon, Loader2Icon, AlertTriangleIcon, CheckCircle2Icon,
    ChevronDownIcon, ChevronRightIcon, ActivityIcon, SettingsIcon
} from 'lucide-react';
import { formatIST } from '@/lib/dateUtils';

interface SegmentData {
    label: string;
    description: string;
    size: number;
    priority: number;
    is_catch_all: boolean;
    recommended_tone: string;
    recommended_send_hour: number;
    key_usp: string;
    persona_hint: string;
}

interface AgentLog {
    timestamp: string;
    agent_name: string;
    action: string;
    level: string;
    color: string;
    data?: any;
}

interface PendingVariant {
    variant_id: string;
    segment_label: string;
}

interface CampaignData {
    campaign_brief: string;
    parsed_brief: any;
    max_iterations: number;
    status: CampaignStatus | 'error';
    error?: string;
    iteration: number;
    all_segments: Record<string, SegmentData>;
    pending_variants: PendingVariant[];
    all_results: any[];
    agent_logs: AgentLog[];
    final_summary: any;
    start_date?: string;
}

const PipelineBreakdown = ({ campaign }: { campaign: CampaignData | null }) => {
    const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({
        profiling: false,
        generating: false,
        executing: false,
        optimizing: false,
    });
    const [expandedSegments, setExpandedSegments] = useState<Record<string, boolean>>({});
    const [expandedBodies, setExpandedBodies] = useState<Record<string, boolean>>({});
    const [expandedOptimizations, setExpandedOptimizations] = useState<Record<string, boolean>>({});

    if (!campaign) return null;

    const toggleCard = (id: string) => {
        setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }));
    };

    // --- Data Extraction ---

    // 1. Profiling
    // We explicitly look for a log that has 'strategy' to avoid accidentally grabbing a warning log.
    const profilerLog = campaign.agent_logs?.find(l => l.agent_name === 'profiler' && l.data?.strategy);
    const profilerData = profilerLog?.data;
    const isProfilingDone = !!profilerData;
    const isProfilingInProgress = campaign.status === 'profiling';

    // 2. Content Generation
    const contentGenLogs = campaign.agent_logs?.filter(l => l.agent_name === 'content_gen' && l.data?.iteration) || [];
    const isGeneratingDone = contentGenLogs.length > 0 && campaign.status !== 'generating' && campaign.status !== 'profiling';
    const isGeneratingInProgress = campaign.status === 'generating';

    // Group variants by segment
    const variantsBySegment: Record<string, any[]> = {};
    contentGenLogs.forEach(l => {
        const seg = l.data.segment;
        if (!variantsBySegment[seg]) variantsBySegment[seg] = [];
        variantsBySegment[seg].push(l.data);
    });

    // 3. Execution
    const executorLogs = campaign.agent_logs?.filter(l => l.agent_name === 'executor') || [];
    const allResults = campaign.all_results || [];
    const isExecutingDone = executorLogs.length > 0 && campaign.status !== 'executing' && campaign.status !== 'sending';
    const isExecutingInProgress = campaign.status === 'executing' || campaign.status === 'sending';

    // 4. Optimization (Optimizer + Analyst)
    const analystLogs = campaign.agent_logs?.filter(l => l.agent_name === 'analyst') || [];
    const optimizerLogs = campaign.agent_logs?.filter(l => l.agent_name === 'optimizer') || [];
    const isOptimizingDone = optimizerLogs.length > 0 || campaign.status === 'done';
    const isOptimizingInProgress = campaign.status === 'optimizing' || campaign.status === 'analyzing';

    const getIcon = (isDone: boolean, isInProgress: boolean) => {
        if (isDone) return <CheckCircle2Icon className="w-5 h-5 text-green-500" />;
        if (isInProgress) return <Loader2Icon className="w-5 h-5 text-blue-500 animate-spin" />;
        return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />;
    };

    const CardHeader = ({ id, title, isDone, isInProgress }: any) => (
        <button
            onClick={() => toggleCard(id)}
            className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
            disabled={!isDone && !isInProgress}
        >
            <div className={`flex items-center gap-3 ${!isDone && !isInProgress ? 'opacity-50' : ''}`}>
                {getIcon(isDone, isInProgress)}
                <h3 className="font-bold text-gray-900 text-base">{title}</h3>
            </div>
            {(isDone || isInProgress) && (
                expandedCards[id] ? <ChevronDownIcon className="w-5 h-5 text-gray-500" /> : <ChevronRightIcon className="w-5 h-5 text-gray-500" />
            )}
        </button>
    );

    return (
        <div className="mb-12 w-full">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Breakdown</h2>
            <div className="flex flex-col gap-4">

                {/* 1. Profiling Stage */}
                <div className={`border border-gray-200 rounded-lg bg-white overflow-hidden ${!isProfilingDone && !isProfilingInProgress ? 'opacity-60 grayscale-[0.5]' : ''}`}>
                    <CardHeader id="profiling" title="Profiling Stage" isDone={isProfilingDone} isInProgress={isProfilingInProgress} />
                    {expandedCards['profiling'] && (isProfilingDone || isProfilingInProgress) && (
                        <div className="p-6 border-t border-gray-200 space-y-6">
                            {profilerData ? (
                                <>
                                    <div>
                                        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">Fields Analyzed</h4>
                                        <div className="flex flex-wrap gap-2">
                                            {profilerData.schema_fields?.map((field: string, i: number) => (
                                                <span key={i} className="bg-blue-50 text-blue-700 border border-blue-100 px-2 py-1 rounded text-xs">
                                                    {field}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">Identified Segments</h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {profilerData.strategy?.map((seg: any, i: number) => (
                                                <div key={i} className="border border-gray-200 rounded-lg p-4 shadow-sm bg-gray-50">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <span className="font-bold text-gray-900 break-words">{seg.label}</span>
                                                        <span className="bg-gray-200 text-gray-800 text-xs font-bold px-2 py-1 rounded-full whitespace-nowrap">
                                                            {profilerData.segment_sizes?.[seg.label]?.size || 0} customers
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-gray-600 mb-3 italic">&quot;{seg.persona_hint}&quot;</p>

                                                    <div className="text-xs text-gray-500 bg-white border border-gray-200 p-2 rounded">
                                                        <span className="font-semibold block mb-1 uppercase tracking-wider text-[10px]">Rules</span>
                                                        {seg.criteria && seg.criteria.length > 0 ? (
                                                            <ul className="list-disc pl-4 space-y-1">
                                                                {seg.criteria.map((c: any, j: number) => (
                                                                    <li key={j}>{c.field} {c.op} {c.value}</li>
                                                                ))}
                                                            </ul>
                                                        ) : (
                                                            <span>Catch-all (No specific rules)</span>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </>
                            ) : <div className="text-sm text-gray-500 py-2">Profiling in progress...</div>}
                        </div>
                    )}
                </div>

                {/* 2. Content Generation Stage */}
                <div className={`border border-gray-200 rounded-lg bg-white overflow-hidden ${!isGeneratingDone && !isGeneratingInProgress ? 'opacity-60 grayscale-[0.5]' : ''}`}>
                    <CardHeader id="generating" title="Content Generation Stage" isDone={isGeneratingDone} isInProgress={isGeneratingInProgress} />
                    {expandedCards['generating'] && (isGeneratingDone || isGeneratingInProgress) && (
                        <div className="p-6 border-t border-gray-200">
                            {Object.keys(variantsBySegment).length > 0 ? (
                                <div className="space-y-3">
                                    {Object.entries(variantsBySegment).map(([segment, variants]) => {
                                        const segKey = `seg_${segment}`;
                                        const isSegExpanded = expandedSegments[segKey] ?? false;
                                        return (
                                            <div key={segment} className="border border-gray-200 rounded-lg overflow-hidden">
                                                <button
                                                    onClick={() => setExpandedSegments(prev => ({ ...prev, [segKey]: !prev[segKey] }))}
                                                    className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-bold text-gray-800">{segment}</span>
                                                        <span className="text-xs bg-blue-50 text-blue-600 border border-blue-100 px-2 py-0.5 rounded-full">{variants.length} variant{variants.length > 1 ? 's' : ''}</span>
                                                    </div>
                                                    {isSegExpanded ? <ChevronDownIcon className="w-4 h-4 text-gray-500" /> : <ChevronRightIcon className="w-4 h-4 text-gray-500" />}
                                                </button>
                                                {isSegExpanded && (
                                                    <div className="p-4 space-y-4 border-t border-gray-200">
                                                        {variants.map((v, idx) => {
                                                            const bodyKey = `body_${segment}_${v.variant}_${v.iteration}`;
                                                            const isBodyExpanded = expandedBodies[bodyKey] ?? false;
                                                            return (
                                                                <div key={idx} className="bg-white border border-gray-100 rounded-lg shadow-sm p-4 text-sm">
                                                                    <div className="flex justify-between items-center mb-2">
                                                                        <span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded text-xs">Variant {v.variant} (Iter {v.iteration})</span>
                                                                    </div>
                                                                    <div className="mb-3">
                                                                        <span className="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-0.5">Subject Line</span>
                                                                        <h5 className="font-bold text-gray-900 text-base">{v.subject}</h5>
                                                                    </div>
                                                                    <div>
                                                                        <button
                                                                            onClick={() => setExpandedBodies(prev => ({ ...prev, [bodyKey]: !prev[bodyKey] }))}
                                                                            className="flex items-center gap-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1 hover:text-gray-600 transition-colors"
                                                                        >
                                                                            {isBodyExpanded ? <ChevronDownIcon className="w-3 h-3" /> : <ChevronRightIcon className="w-3 h-3" />}
                                                                            Email Body
                                                                        </button>
                                                                        {isBodyExpanded && (
                                                                            <div
                                                                                className="text-gray-700 leading-relaxed bg-gray-50 p-3 rounded text-sm italic border border-gray-100"
                                                                                dangerouslySetInnerHTML={{ __html: (v.body || v.body_preview || '').replace(/\\n/g, '<br>').replace(/\n/g, '<br>') }}
                                                                            />
                                                                        )}
                                                                    </div>
                                                                    {v.strategy_notes && (
                                                                        <div className="mt-3 text-xs text-gray-500 border-t border-gray-100 pt-2">
                                                                            <span className="font-semibold text-gray-700">Strategy / Personalization:</span> {v.strategy_notes}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : <div className="text-sm text-gray-500 py-2">Generating in progress...</div>}
                        </div>
                    )}
                </div>

                {/* 3. Execution Stage */}
                <div className={`border border-gray-200 rounded-lg bg-white overflow-hidden ${!isExecutingDone && !isExecutingInProgress ? 'opacity-60 grayscale-[0.5]' : ''}`}>
                    <CardHeader id="executing" title="Execution Stage" isDone={isExecutingDone} isInProgress={isExecutingInProgress} />
                    {expandedCards['executing'] && (isExecutingDone || isExecutingInProgress) && (
                        <div className="p-6 border-t border-gray-200">
                            {executorLogs.length > 0 ? (
                                <div className="relative border-l-2 border-gray-200 ml-3 space-y-8">
                                    {executorLogs.map((log, idx) => {
                                        const iter = log.data?.iteration || idx + 1;

                                        // Derive targeted segments from content_gen logs for this iteration
                                        const segsForIter = contentGenLogs
                                            .filter(l => l.data?.iteration === iter)
                                            .map(l => l.data.segment);
                                        const uniqueSegs = Array.from(new Set(segsForIter));

                                        // Calculate customer count from profiler segment_sizes
                                        const customerCount = uniqueSegs.reduce((sum, segLabel) => {
                                            const segSize = profilerData?.segment_sizes?.[segLabel]?.size || 0;
                                            return sum + segSize;
                                        }, 0);
                                        const expectedTotal = profilerData?.total_customers || 1000;

                                        // Format the coverage display
                                        let coverageLabel: string;
                                        let coverageText: string;
                                        if (iter === 1) {
                                            coverageLabel = "Customers Reached";
                                            coverageText = `${customerCount} / ${expectedTotal} (Full Cohort)`;
                                        } else {
                                            coverageLabel = "Re-targeting";
                                            coverageText = `${customerCount} customers from ${uniqueSegs.length} segment${uniqueSegs.length !== 1 ? 's' : ''}`;
                                        }

                                        return (
                                            <div key={idx} className="relative pl-6">
                                                <div className="absolute w-3 h-3 bg-blue-500 rounded-full -left-[7px] top-1.5 ring-4 ring-white" />
                                                <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
                                                    <div className="flex justify-between items-start mb-4">
                                                        <h4 className="font-bold text-lg text-gray-900 border-b-2 border-blue-200 pb-1">Iteration {iter}</h4>
                                                        <span className="text-xs font-semibold bg-gray-200 text-gray-700 px-2 py-1 rounded">
                                                            {log.timestamp}
                                                        </span>
                                                    </div>

                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                                                        <div>
                                                            <span className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Targeted Segments</span>
                                                            <div className="flex flex-wrap gap-1">
                                                                {uniqueSegs.length > 0 ? uniqueSegs.map((s, i) => (
                                                                    <span key={i} className="bg-white border border-gray-200 px-2 py-1 rounded text-xs text-gray-700">{s}</span>
                                                                )) : <span className="text-gray-400 italic">Unknown</span>}
                                                            </div>
                                                        </div>
                                                        <div className="space-y-3">
                                                            <div className="flex justify-between border-b border-gray-100 pb-1">
                                                                <span className="text-gray-500">API Calls</span>
                                                                <span className="font-medium text-gray-900">
                                                                    <span className="text-green-600 font-bold">{log.data?.sent_count || 0} Sent</span>, <span className="text-red-500">{log.data?.failed_count || 0} Failed</span>
                                                                </span>
                                                            </div>
                                                            <div className="flex justify-between">
                                                                <span className="text-gray-500">{coverageLabel}</span>
                                                                <span className="font-medium text-gray-900">{coverageText}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : <div className="text-sm text-gray-500 py-2">Execution in progress...</div>}
                        </div>
                    )}
                </div>

                {/* 4. Optimization Stage */}
                <div className={`border border-gray-200 rounded-lg bg-white overflow-hidden ${!isOptimizingDone && !isOptimizingInProgress ? 'opacity-60 grayscale-[0.5]' : ''}`}>
                    <CardHeader id="optimizing" title="Optimization Stage" isDone={isOptimizingDone} isInProgress={isOptimizingInProgress} />
                    {expandedCards['optimizing'] && (isOptimizingDone || isOptimizingInProgress) && (
                        <div className="p-6 border-t border-gray-200">
                            {analystLogs.length > 0 ? (
                                <div className="space-y-8">
                                    {analystLogs.map((aLog, idx) => {
                                        const iter = aLog.data?.iteration || idx + 1;
                                        const optLog = optimizerLogs.find(o => o.data?.iteration === iter);
                                        const resultsForIter = allResults.filter(r => r.iteration === iter);

                                        const optKey = `opt_${iter}`;
                                        const isOptExpanded = expandedOptimizations[optKey] ?? false;

                                        return (
                                            <div key={idx} className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
                                                <button
                                                    onClick={() => setExpandedOptimizations(prev => ({ ...prev, [optKey]: !prev[optKey] }))}
                                                    className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left border-b border-gray-200"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-bold text-gray-800">Iteration {iter} Analysis</span>
                                                        <span className="text-xs bg-purple-100 text-purple-700 font-semibold px-2 py-1 rounded border border-purple-200">
                                                            Best: Var {aLog.data?.best_variant || '?'}
                                                        </span>
                                                    </div>
                                                    {isOptExpanded ? <ChevronDownIcon className="w-4 h-4 text-gray-500" /> : <ChevronRightIcon className="w-4 h-4 text-gray-500" />}
                                                </button>

                                                {isOptExpanded && (
                                                    <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                        <div>
                                                            <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Segment Performance Scores</h5>
                                                            <div className="space-y-2">
                                                                {resultsForIter.sort((a, b) => b.composite_score - a.composite_score).slice(0, 12).map((r, i) => (
                                                                    <div key={i} className="flex justify-between items-center text-sm border border-gray-100 p-2 rounded bg-gray-50">
                                                                        <span className="truncate max-w-[150px] font-medium" title={r.segment_label}>{r.segment_label}</span>
                                                                        <div className="flex gap-3 text-xs text-right">
                                                                            <span>Open: {(r.open_rate * 100).toFixed(1)}%</span>
                                                                            <span>Click: {(r.click_rate * 100).toFixed(1)}%</span>
                                                                            <span className="font-bold text-blue-700">Score: {r.composite_score.toFixed(2)}</span>
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>

                                                        <div className="space-y-4">
                                                            <div>
                                                                <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Analyst Summary</h5>
                                                                <p className="text-sm text-gray-700 leading-relaxed bg-blue-50/50 p-3 rounded border border-blue-100">
                                                                    {aLog.data?.analyst_summary || aLog.action}
                                                                </p>
                                                            </div>
                                                            {optLog && (
                                                                <div>
                                                                    <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Optimizer Decisions</h5>
                                                                    <div className="text-sm text-gray-700 leading-relaxed bg-orange-50/50 p-3 rounded border border-orange-100">
                                                                        <div className="font-semibold mb-1 text-orange-900">
                                                                            Decision: {optLog.data?.stop_reason ? `Stopped (${optLog.data.stop_reason})` : 'Continued'}
                                                                        </div>
                                                                        {optLog.data?.next_segments && optLog.data.next_segments.length > 0 && (
                                                                            <div className="mb-2">
                                                                                <span className="font-medium">Re-targeted:</span> {optLog.data.next_segments.join(', ')}
                                                                            </div>
                                                                        )}
                                                                        <div className="italic text-gray-600 text-xs">
                                                                            {optLog.data?.optimization_notes || optLog.action}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : <div className="text-sm text-gray-500 py-2">Optimizing in progress...</div>}
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
};




/* ── Circular Progress Ring (SVG) ── */
const CircularProgressRing = ({ percentage }: { percentage: number }) => {
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;

    return (
        <div className="relative w-32 h-32 progress-ring-animated">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                {/* Background ring */}
                <circle cx="60" cy="60" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="8" />
                {/* Progress ring */}
                <circle
                    cx="60" cy="60" r={radius} fill="none"
                    stroke="#3b82f6" strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-gray-900">{percentage}%</span>
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Target</span>
            </div>
        </div>
    );
};

/* ── Processing Status Panel ── */
const ProcessingStatusPanel = ({
    campaign, segments, currentStageIndex, totalStages, id, router
}: {
    campaign: CampaignData | null; segments: any[]; currentStageIndex: number; totalStages: number; id: string; router: ReturnType<typeof useRouter>;
}) => {
    const isRunning = ['starting', 'parsing', 'profiling', 'analyzing', 'generating', 'sending', 'executing', 'optimizing'].includes(campaign?.status || '');
    const percentage = Math.max(0, Math.min(Math.round((currentStageIndex / totalStages) * 100), 100));
    const customerCount = campaign?.final_summary?.total_customers_reached || Object.values(campaign?.all_segments || {}).reduce((sum: number, s: any) => sum + (s.size || 0), 0) || 0;

    const getStatusLabel = (status?: string) => {
        switch (status) {
            case 'starting': return 'starting pipeline for';
            case 'parsing': return 'parsing brief for';
            case 'profiling': return 'profiling';
            case 'analyzing': return 'analyzing';
            case 'generating': return 'generating content for';
            case 'sending': return 'sending emails to';
            case 'executing': return 'executing campaign for';
            case 'optimizing': return 'optimizing campaign for';
            default: return 'processing';
        }
    };

    return (
        <div className="space-y-4">
            {/* Processing Status Card – shown when running */}
            {isRunning && (
                <Card variant="outlined" className="shadow-sm">
                    <CardContent className="p-6">
                        <div className="flex items-center gap-2 mb-6">
                            <SettingsIcon className="w-5 h-5 text-gray-500 animate-spin" style={{ animationDuration: '3s' }} />
                            <h3 className="text-base font-bold text-gray-900">Processing Status</h3>
                        </div>

                        <div className="flex flex-col items-center mb-6">
                            <CircularProgressRing percentage={percentage} />
                        </div>

                        <div className="text-center space-y-1 mb-6">
                            <div className="flex items-center justify-center gap-2 text-sm text-gray-700">
                                <Loader2Icon className="w-4 h-4 text-blue-500 animate-spin" />
                                <span>AI is {getStatusLabel(campaign?.status)} {customerCount.toLocaleString()} customers.</span>
                            </div>
                            <p className="text-xs text-gray-400">Estimated completion in ~{Math.max(2, 15 - currentStageIndex * 2)} mins</p>
                        </div>

                        {/* Shimmer skeleton bars */}
                        <div className="space-y-2">
                            <div className="shimmer-bar h-3 w-full" />
                            <div className="shimmer-bar h-3 w-4/5" />
                            <div className="shimmer-bar h-3 w-3/5" />
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Error state */}
            {campaign?.status === 'error' && (
                <Card variant="outlined" className="border-red-200 bg-red-50/50 shadow-sm">
                    <CardContent className="p-6 flex flex-col items-center text-center">
                        <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center text-red-600 mb-4">
                            <AlertTriangleIcon className="w-6 h-6" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Pipeline Failed</h3>
                        <p className="text-gray-600 mb-6">{campaign.error || 'An unknown error occurred during execution.'}</p>
                    </CardContent>
                </Card>
            )}

            {/* Awaiting Approval */}
            {campaign?.status === 'awaiting_approval' && (
                <Card variant="outlined" className="border-yellow-200 bg-yellow-50/50 shadow-sm">
                    <CardContent className="p-6 flex flex-col items-center text-center">
                        <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center text-yellow-600 mb-4">
                            <AlertTriangleIcon className="w-6 h-6" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Review Required</h3>
                        <p className="text-gray-600 mb-6">AI has generated <strong>{campaign?.pending_variants?.length || 0} variants</strong> across <strong>{segments.length} segments</strong>. Please review and approve the content before sending.</p>
                        <Button variant="primary" className="w-full" onClick={() => router.push(`/campaign/${id}/approve`)}>
                            Review and Approve
                        </Button>
                    </CardContent>
                </Card>
            )}

            {/* Campaign Complete */}
            {campaign?.status === 'done' && (
                <Card variant="outlined" className="border-green-200 bg-green-50/30 shadow-sm">
                    <CardContent className="p-6">
                        <div className="flex items-center gap-3 mb-6">
                            <CheckCircle2Icon className="w-6 h-6 text-green-500" />
                            <h3 className="text-lg font-bold text-gray-900">Campaign Complete</h3>
                        </div>

                        <div className="flex flex-col items-center mb-6">
                            <CircularProgressRing percentage={100} />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between border-b border-gray-100 pb-2">
                                <span className="text-gray-500 text-sm">Emails Sent</span>
                                <span className="font-semibold text-gray-900">
                                    {campaign?.all_results?.reduce((sum: number, r: any) => sum + r.total_sent, 0) || 0}
                                </span>
                            </div>
                            <div className="flex justify-between border-b border-gray-100 pb-2">
                                <span className="text-gray-500 text-sm">Customers Reached</span>
                                <span className="font-semibold text-gray-900">{campaign?.final_summary?.total_customers_reached || 0}</span>
                            </div>
                            <div className="flex justify-between border-b border-gray-100 pb-2">
                                <span className="text-gray-500 text-sm">Best Variant</span>
                                <span className="font-semibold text-gray-900 truncate max-w-[120px]" title={campaign?.final_summary?.best_overall?.segment_label}>
                                    {(() => {
                                        const best = campaign?.final_summary?.best_overall;
                                        if (!best) return '-';
                                        return `Var ${best.variant_label} (${best.segment_label})`;
                                    })()}
                                </span>
                            </div>
                            <div className="flex justify-between border-b border-gray-100 pb-2">
                                <span className="text-gray-500 text-sm">Open Rate</span>
                                <span className="font-semibold text-green-600">{((campaign?.final_summary?.overall_open_rate || 0) * 100).toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500 text-sm">Click Rate</span>
                                <span className="font-semibold text-green-600">{((campaign?.final_summary?.overall_click_rate || 0) * 100).toFixed(1)}%</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
};

export default function CampaignDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();

    const [campaign, setCampaign] = useState<CampaignData | null>(null);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [expandedIterations, setExpandedIterations] = useState<Record<number, boolean>>({});

    // Grouping helper for the execution summary
    const groupedResultsByIteration = React.useMemo(() => {
        if (!campaign?.all_results) return [];
        const groups: Record<number, any[]> = {};
        campaign.all_results.forEach(result => {
            const iter = result.iteration || 1;
            if (!groups[iter]) groups[iter] = [];
            groups[iter].push(result);
        });

        return Object.entries(groups)
            .map(([iteration, results]) => ({
                iteration: parseInt(iteration),
                results
            }))
            .sort((a, b) => a.iteration - b.iteration);
    }, [campaign?.all_results]);

    React.useEffect(() => {
        if (!id) return;

        let isPolling = true;

        const fetchStatus = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/campaign/${id}/status`, { cache: 'no-store' });

                if (!res.ok) {
                    if (res.status === 404) {
                        setFetchError('Campaign not found.');
                        isPolling = false;
                        return;
                    }
                    throw new Error('Failed to fetch campaign status');
                }

                const data = await res.json();
                setCampaign(data);

                if (data.status === 'done' || data.status === 'error' || data.status === 'awaiting_approval') {
                    // We can keep polling awaiting_approval to see if it changes from another tab, but normally we'd stop.
                    if (data.status === 'done' || data.status === 'error') {
                        isPolling = false;
                    }
                }
            } catch (err) {
                console.error(err);
                setFetchError('Failed to connect to backend.');
                isPolling = false;
            }
        };

        fetchStatus();
        const intervalId = setInterval(() => {
            if (isPolling) {
                fetchStatus();
            } else {
                clearInterval(intervalId);
            }
        }, 3000);

        return () => clearInterval(intervalId);
    }, [id]);

    const getStepperData = (status?: string) => {
        const stages = ['starting', 'parsing', 'profiling', 'analyzing', 'generating', 'awaiting_approval', 'sending', 'executing', 'optimizing', 'done'];
        const currentIndex = status ? stages.indexOf(status) : 0;

        let activeIndex = Math.max(0, currentIndex);
        let completed = Array.from({ length: Math.max(0, currentIndex) }, (_, i) => i);

        if (status === 'done') {
            activeIndex = stages.length;
            completed = Array.from({ length: stages.length }, (_, i) => i);
        }

        if (status === 'error') {
            // Freeze stepper on error
            activeIndex = Math.max(0, currentIndex - 1);
        }

        return { currentStageIndex: activeIndex, completedStages: completed };
    };

    if (fetchError) {
        return (
            <div className="max-w-7xl mx-auto py-12 text-center">
                <AlertTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Campaign</h2>
                <p className="text-gray-500 mb-6">{fetchError}</p>
                <Button variant="secondary" onClick={() => router.push('/dashboard')}>Back to Dashboard</Button>
            </div>
        );
    }

    if (!campaign && !fetchError) {
        return (
            <div className="max-w-7xl mx-auto py-24 flex flex-col items-center justify-center">
                <Loader2Icon className="w-8 h-8 text-blue-500 animate-spin mb-4" />
                <div className="text-gray-500 font-medium">Loading campaign details...</div>
            </div>
        );
    }

    const { currentStageIndex, completedStages } = getStepperData(campaign?.status);
    const segments = Object.values(campaign?.all_segments || {});

    return (
        <div className="max-w-7xl mx-auto">
            <Link href="/campaigns" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 mb-6 transition-colors">
                <ArrowLeftIcon className="w-4 h-4 mr-1" />
                Back to Campaigns
            </Link>

            {/* ── Campaign Header ── */}
            <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6 shadow-sm">
                <div className="flex items-start justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <span className="inline-flex items-center px-3 py-1 rounded-md bg-blue-600 text-white text-sm font-bold font-mono tracking-wider">
                                #{(id || 'cmp_a1b2c3d4').toUpperCase().slice(0, 13)}
                            </span>
                            <StatusBadge status={(campaign?.status === 'error' ? 'starting' : campaign?.status) as CampaignStatus} />
                        </div>
                        <h1 className="text-xl font-bold text-gray-900 mb-1">
                            {campaign?.parsed_brief?.campaign_name || campaign?.campaign_brief?.slice(0, 60) || 'Campaign'}
                        </h1>
                        <p className="text-sm text-gray-500 max-w-2xl leading-relaxed">
                            {campaign?.campaign_brief}
                        </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {campaign?.start_date && (
                            <span className="text-xs font-medium text-gray-400 bg-gray-100 px-3 py-1.5 rounded-lg">
                                {formatIST(campaign.start_date)}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* ── Pipeline Stepper ── */}
            <div className="mb-8 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <PipelineStepper currentStageIndex={currentStageIndex} completedStages={completedStages} />
            </div>

            <div className="flex flex-col lg:flex-row gap-6 mb-8">
                {/* Left: Agent Logs */}
                <div className="flex-1 lg:w-[65%]">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Agent Activity</h2>
                    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden flex flex-col h-[400px]">
                        <div className="bg-gray-50 border-b border-gray-200 px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider flex">
                            <div className="w-24">Timestamp</div>
                            <div className="w-28">Agent</div>
                            <div className="flex-1">Action</div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-1 font-sans">
                            {campaign?.agent_logs?.map((log, i) => {
                                let color = 'gray';
                                if (log.action.includes('error') || log.level === 'ERROR') color = 'red';
                                else if (log.agent_name === 'parser') color = 'purple';
                                else if (log.agent_name === 'profiler') color = 'blue';
                                else if (log.agent_name === 'content_gen') color = 'green';
                                else if (log.agent_name === 'analyzer') color = 'teal';
                                else if (log.agent_name === 'optimizer') color = 'orange';

                                return <AgentLogRow key={i} timestamp={log.timestamp || new Date().toLocaleTimeString()} agent={log.agent_name} message={log.action} agentColor={color} />
                            })}

                            {campaign?.status !== 'done' && campaign?.status !== 'error' && (
                                <div className="flex items-center py-2 px-2">
                                    <div className="w-2 h-4 bg-blue-500 animate-pulse" />
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: Processing Status Panel */}
                <div className="lg:w-[35%]">
                    <ProcessingStatusPanel campaign={campaign} segments={segments} currentStageIndex={currentStageIndex} totalStages={10} id={id} router={router} />
                </div>
            </div>

            <PipelineBreakdown campaign={campaign} />

            {groupedResultsByIteration.length > 0 && (
                <div className="mb-12 w-full">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Execution Summary</h2>
                    <div className="flex flex-col gap-3 w-full">
                        {groupedResultsByIteration.map((group) => {
                            const totalSent = group.results.reduce((sum, r) => sum + r.total_sent, 0);
                            const totalOpens = group.results.reduce((sum, r) => sum + r.opens, 0);
                            const totalClicks = group.results.reduce((sum, r) => sum + r.clicks, 0);
                            const openRate = totalSent > 0 ? totalOpens / totalSent : 0;
                            const clickRate = totalSent > 0 ? totalClicks / totalSent : 0;

                            let bestVariant = group.results[0];
                            group.results.forEach(r => {
                                if ((r.composite_score || 0) > (bestVariant?.composite_score || 0)) {
                                    bestVariant = r;
                                }
                            });

                            const isExpanded = expandedIterations[group.iteration] !== false; // default true

                            const toggleExpand = () => {
                                setExpandedIterations(prev => ({
                                    ...prev,
                                    [group.iteration]: !isExpanded
                                }));
                            };

                            return (
                                <div key={group.iteration} className="border border-gray-200 rounded-lg bg-white overflow-hidden w-full">
                                    <button
                                        onClick={toggleExpand}
                                        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                                    >
                                        <div className="flex items-center gap-3">
                                            {isExpanded ? <ChevronDownIcon className="w-5 h-5 text-gray-500" /> : <ChevronRightIcon className="w-5 h-5 text-gray-500" />}
                                            <h3 className="font-bold text-gray-900 text-base">Iteration {group.iteration}</h3>
                                        </div>
                                        <span className="text-sm font-semibold px-3 py-1 bg-blue-100 text-blue-700 rounded-full">
                                            {totalSent} Sent
                                        </span>
                                    </button>

                                    {isExpanded && (
                                        <div className="p-6 border-t border-gray-200 grid grid-cols-1 lg:grid-cols-3 gap-8">
                                            <div className="lg:col-span-2">
                                                <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">Targeted Segments</h4>
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                    {group.results.map((r, i) => (
                                                        <div key={i} className="text-sm bg-white border border-gray-200 px-3 py-2 rounded-lg text-gray-700 flex items-start justify-between w-full shadow-sm">
                                                            <span className="break-words mr-3 font-medium">{r.segment_label}</span>
                                                            <span className="font-bold text-gray-900 whitespace-nowrap pt-0.5">{r.total_sent}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="space-y-6">
                                                <div>
                                                    <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">Performance</h4>
                                                    <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                                                        <div>
                                                            <div className="text-xs text-gray-500 mb-1">Open Rate</div>
                                                            <div className="font-bold text-green-600 text-lg">{(openRate * 100).toFixed(1)}%</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-xs text-gray-500 mb-1">Click Rate</div>
                                                            <div className="font-bold text-green-600 text-lg">{(clickRate * 100).toFixed(1)}%</div>
                                                        </div>
                                                    </div>
                                                </div>

                                                {bestVariant && bestVariant.total_sent > 0 && bestVariant.variant_label !== 'all' && (
                                                    <div>
                                                        <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">Best Variant</h4>
                                                        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                                                            <p className="text-base font-bold text-blue-900 break-words">
                                                                Var {bestVariant.variant_label}
                                                            </p>
                                                            <p className="text-sm text-blue-700 mt-1 break-words">
                                                                {bestVariant.segment_label}
                                                            </p>
                                                            <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-blue-200">
                                                                <div>
                                                                    <div className="text-[10px] text-blue-500 uppercase tracking-wider font-medium">Open</div>
                                                                    <div className="font-bold text-blue-900 text-sm">{((bestVariant.open_rate || 0) * 100).toFixed(1)}%</div>
                                                                </div>
                                                                <div>
                                                                    <div className="text-[10px] text-blue-500 uppercase tracking-wider font-medium">Click</div>
                                                                    <div className="font-bold text-blue-900 text-sm">{((bestVariant.click_rate || 0) * 100).toFixed(1)}%</div>
                                                                </div>
                                                                <div>
                                                                    <div className="text-[10px] text-blue-500 uppercase tracking-wider font-medium">Score</div>
                                                                    <div className="font-bold text-blue-900 text-sm">{(bestVariant.composite_score || 0).toFixed(2)}</div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

        </div>
    );
}
