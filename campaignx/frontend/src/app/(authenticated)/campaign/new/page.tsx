'use client';
import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { ArrowLeftIcon } from 'lucide-react';

function NewCampaignForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [brief, setBrief] = useState(searchParams.get('brief') || '');
    const [includeInactive, setIncludeInactive] = useState(false);
    const [maxIterations, setMaxIterations] = useState(3);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [budget, setBudget] = useState<{ used: number, limit: number } | null>(null);

    React.useEffect(() => {
        const fetchBudget = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/budget`);
                if (res.ok) {
                    const data = await res.json();
                    setBudget(data);
                }
            } catch (err) {
                console.error('Failed to fetch budget:', err);
            }
        };
        fetchBudget();
    }, []);

    const handleStart = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const finalBrief = includeInactive
                ? `${brief}\n\nNote: Include inactive customers. Expand audience to users who haven't logged in for 30+ days.`
                : brief;

            const res = await fetch(`${apiUrl}/api/campaign/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    campaign_brief: finalBrief,
                    max_iterations: maxIterations
                }),
            });

            if (!res.ok) {
                throw new Error('Failed to start campaign');
            }

            const data = await res.json();
            router.push(`/campaign/${data.campaign_id}`);
        } catch (err) {
            console.error('Error starting campaign:', err);
            setError('Failed to start campaign. The backend may not be running.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto pb-24">
            <div className="mb-8">
                <Link
                    href="/dashboard"
                    className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 mb-4 transition-colors">
                    <ArrowLeftIcon className="w-4 h-4 mr-1" />
                    Back to Dashboard
                </Link>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Campaign</h1>
                <p className="text-gray-500">Start by describing what you want to achieve in plain English.</p>
            </div>

            <div className="flex flex-col lg:flex-row gap-8">
                {/* Left Column: Brief */}
                <div className="flex-1 lg:w-[60%]">
                    <div className="mb-2 font-medium text-gray-900">Campaign Brief</div>
                    <textarea
                        className="w-full min-h-[300px] p-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-y text-gray-900 placeholder-gray-400 text-lg leading-relaxed shadow-sm"
                        placeholder="E.g. We are launching our new Q4 product update next week. I want to send an email to all active users highlighting the new AI features, and a different email to inactive users offering a 20% discount to come back and try it out. The CTA should link to /features/q4."
                        value={brief}
                        onChange={(e) => setBrief(e.target.value)}
                    />
                    <div className="flex justify-between items-start mt-2">
                        <p className="text-sm text-gray-500 max-w-md">
                            <span className="font-semibold">Tip:</span> Include your product name, target audience, any special offers, and a call-to-action URL.
                        </p>
                        <span className="text-sm text-gray-400 font-mono">{brief.length} chars</span>
                    </div>
                </div>

                {/* Right Column: Config */}
                <div className="lg:w-[40%] space-y-4">
                    <div className="font-medium text-gray-900 mb-2">Configuration</div>

                    <Card variant="outlined">
                        <CardContent className="p-5">
                            <div className="flex items-center justify-between mb-1">
                                <label className="font-medium text-gray-900">Include inactive customers</label>
                                <div
                                    className={`w-11 h-6 rounded-full relative cursor-pointer transition-colors duration-200 ${includeInactive ? 'bg-blue-600' : 'bg-gray-200'}`}
                                    onClick={() => setIncludeInactive(!includeInactive)}
                                >
                                    <div
                                        className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform duration-200 ${includeInactive ? 'right-1 translate-x-0' : 'left-1 translate-x-0'}`}
                                    />
                                </div>
                            </div>
                            <p className="text-sm text-gray-500">Will expand audience to users who haven&apos;t logged in for 30+ days.</p>
                        </CardContent>
                    </Card>

                    <Card variant="outlined">
                        <CardContent className="p-5">
                            <label className="block font-medium text-gray-900 mb-2">Max Iterations</label>
                            <select
                                className="w-full p-2.5 border border-gray-300 rounded-lg bg-white text-gray-900 outline-none focus:ring-2 focus:ring-blue-500"
                                value={maxIterations}
                                onChange={(e) => setMaxIterations(Number(e.target.value))}
                            >
                                <option value={1}>1 (Fastest)</option>
                                <option value={2}>2 (Balanced)</option>
                                <option value={3}>3 (Best Quality)</option>
                            </select>
                        </CardContent>
                    </Card>

                    <Card variant="outlined">
                        <CardContent className="p-5">
                            <label className="block font-medium text-gray-900 mb-2">Optimize For</label>
                            <select className="w-full p-2.5 border border-gray-300 rounded-lg bg-white text-gray-900 outline-none focus:ring-2 focus:ring-blue-500">
                                <option>Open Rate</option>
                                <option>Click Rate</option>
                                <option>Both (Balanced)</option>
                            </select>
                        </CardContent>
                    </Card>

                    <Card variant="filled" className="bg-gray-50 border-none mt-6">
                        <CardContent className="p-5">
                            <div className="flex justify-between text-sm mb-2">
                                <span className="font-medium text-gray-700">API Budget</span>
                                <span className="text-gray-500">
                                    {budget ? `${budget.used}/${budget.limit}` : '...'} calls
                                </span>
                            </div>
                            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
                                <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${budget ? (budget.used / budget.limit) * 100 : 0}%` }} />
                            </div>
                            <p className="text-xs text-gray-500">
                                {budget && budget.used >= budget.limit ? 'Budget exhausted. Cannot start new campaigns.' : 'Sufficient budget for this campaign.'}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Sticky Bottom Bar */}
            <div className="fixed bottom-0 left-[240px] right-0 bg-white border-t border-gray-200 px-12 py-4 flex items-center justify-between z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
                <div className="flex flex-col">
                    <div className="text-sm text-gray-500">
                        {brief.length > 0 ? 'Ready to generate.' : 'Write a brief to continue.'}
                    </div>
                    {error && (
                        <div className="text-sm text-red-500 mt-1 font-medium">
                            {error}
                        </div>
                    )}
                </div>
                <div className="flex gap-3">
                    <Button variant="tertiary" onClick={() => router.push('/dashboard')} disabled={isLoading}>Cancel</Button>
                    <Button variant="primary" onClick={handleStart} disabled={brief.length === 0 || isLoading}>
                        {isLoading ? (
                            <div className="flex items-center gap-2">
                                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                Starting...
                            </div>
                        ) : (
                            'Start Campaign'
                        )}
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default function NewCampaignPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading campaign...</div>}>
            <NewCampaignForm />
        </Suspense>
    );
}
