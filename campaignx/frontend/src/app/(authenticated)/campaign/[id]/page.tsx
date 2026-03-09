'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { StatusBadge, CampaignStatus } from '@/components/ui/StatusBadge';
import { PipelineStepper } from '@/components/ui/PipelineStepper';
import { AgentLogRow } from '@/components/ui/AgentLogRow';
import { SegmentChip } from '@/components/ui/SegmentChip';
import { Card, CardContent } from '@/components/ui/Card';
import { ArrowLeftIcon, Loader2Icon, AlertTriangleIcon, CheckCircle2Icon } from 'lucide-react';
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
    agent_logs: AgentLog[];
    final_summary: any;
    start_date?: string;
}

export default function CampaignDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();

    const [campaign, setCampaign] = useState<CampaignData | null>(null);
    const [fetchError, setFetchError] = useState<string | null>(null);

    React.useEffect(() => {
        if (!id) return;

        let isPolling = true;

        const fetchStatus = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/campaign/${id}/status`);

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
        const stages = ['starting', 'analyzing', 'generating', 'awaiting_approval', 'sending', 'optimizing', 'done'];
        const currentIndex = status ? stages.indexOf(status) : 0;

        let activeIndex = currentIndex;
        let completed = Array.from({ length: currentIndex }, (_, i) => i);

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

            <div className="flex items-start justify-between mb-8">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <h1 className="text-2xl font-bold font-mono text-gray-900">{id || 'cmp_a1b2c3d4'}</h1>
                        {campaign?.start_date && (
                            <span className="text-sm font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                                Created: {formatIST(campaign.start_date)}
                            </span>
                        )}
                    </div>
                    <p className="text-gray-500 max-w-2xl">
                        &quot;{campaign?.campaign_brief}&quot;
                    </p>
                </div>
                <StatusBadge status={(campaign?.status === 'error' ? 'starting' : campaign?.status) as CampaignStatus} />
            </div>

            <div className="mb-12 bg-gray-50/50 p-6 rounded-xl border border-gray-100">
                <PipelineStepper currentStageIndex={currentStageIndex} completedStages={completedStages} />
            </div>

            <div className="flex flex-col lg:flex-row gap-8 mb-8">
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
                                // Add logic to resolve color from level/agent_name string
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

                {/* Right: Status Panel */}
                <div className="lg:w-[35%]">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Status</h2>

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

                    {['starting', 'analyzing', 'generating', 'sending', 'optimizing'].includes(campaign?.status || '') && (
                        <Card variant="outlined">
                            <CardContent className="p-8 flex flex-col items-center text-center">
                                <Loader2Icon className="w-8 h-8 text-blue-500 animate-spin mb-4" />
                                <h3 className="text-lg font-semibold text-gray-900 mb-2 text-capitalize">
                                    {campaign?.status?.charAt(0).toUpperCase() + (campaign?.status || '').slice(1)}...
                                </h3>
                                <p className="text-gray-500">The AI agents are hard at work processing your campaign.</p>
                            </CardContent>
                        </Card>
                    )}

                    {campaign?.status === 'done' && (
                        <Card variant="outlined" className="border-green-200 bg-green-50/30">
                            <CardContent className="p-6">
                                <div className="flex items-center gap-3 mb-6">
                                    <CheckCircle2Icon className="w-6 h-6 text-green-500" />
                                    <h3 className="text-lg font-bold text-gray-900">Campaign Complete</h3>
                                </div>
                                <div className="space-y-4">
                                    <div className="flex justify-between border-b border-gray-100 pb-2"><span className="text-gray-500">Emails Sent</span><span className="font-semibold text-gray-900">{campaign?.final_summary?.total_campaigns_sent || 0}</span></div>
                                    <div className="flex justify-between border-b border-gray-100 pb-2"><span className="text-gray-500">Customers Reached</span><span className="font-semibold text-gray-900">{campaign?.final_summary?.total_customers_reached || 0}</span></div>
                                    <div className="flex justify-between border-b border-gray-100 pb-2">
                                        <span className="text-gray-500">Best Variant</span>
                                        <span className="font-semibold text-gray-900 truncate max-w-[120px]" title={campaign?.final_summary?.best_overall?.segment_label}>
                                            {campaign?.final_summary?.best_overall ? `Var ${campaign.final_summary.best_overall.variant_label} (${campaign.final_summary.best_overall.segment_label})` : '-'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between border-b border-gray-100 pb-2"><span className="text-gray-500">Open Rate</span><span className="font-semibold text-green-600">{((campaign?.final_summary?.overall_open_rate || 0) * 100).toFixed(1)}%</span></div>
                                    <div className="flex justify-between"><span className="text-gray-500">Click Rate</span><span className="font-semibold text-green-600">{((campaign?.final_summary?.overall_click_rate || 0) * 100).toFixed(1)}%</span></div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>

            <div>
                <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">Identified Segments</h2>
                <div className="flex flex-wrap gap-3">
                    {segments.length === 0 ? (
                        <div className="text-sm text-gray-500 italic">No segments identified yet.</div>
                    ) : (
                        segments.map(seg => (
                            <SegmentChip key={seg.label} label={seg.label} count={seg.size} isCatchAll={seg.is_catch_all} />
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
