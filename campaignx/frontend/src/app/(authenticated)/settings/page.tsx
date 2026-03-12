'use client';
import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ClipboardIcon, CheckCircle, XCircle } from 'lucide-react';

export default function SettingsPage() {
    const [budget, setBudget] = useState<{ used: number; remaining: number } | null>(null);
    const [connectionStatus, setConnectionStatus] = useState<'connected' | 'unreachable' | null>(null);
    const [mockApi, setMockApi] = useState<boolean | null>(null);
    const [maxIterations, setMaxIterations] = useState<number>(3);
    const [isTesting, setIsTesting] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    // Fetch budget periodically
    useEffect(() => {
        const fetchBudget = async () => {
            try {
                const res = await fetch(`${apiUrl}/api/budget`);
                if (res.ok) {
                    const data = await res.json();
                    setBudget({
                        used: data.used || 0,
                        remaining: data.remaining || 0
                    });
                }
            } catch (err) {
                console.error("Failed to fetch budget", err);
            }
        };
        fetchBudget();
        const interval = setInterval(fetchBudget, 30000);
        return () => clearInterval(interval);
    }, [apiUrl]);

    // Fetch config on mount
    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const res = await fetch(`${apiUrl}/api/config`);
                if (res.ok) {
                    const data = await res.json();
                    setMockApi(data.mock_api);
                }
            } catch (err) {
                console.error("Failed to fetch config", err);
            }
        };
        fetchConfig();
    }, [apiUrl]);

    const testConnection = async () => {
        setIsTesting(true);
        setConnectionStatus(null);
        try {
            const res = await fetch(`${apiUrl}/api/health`);
            if (res.ok) {
                setConnectionStatus('connected');
            } else {
                setConnectionStatus('unreachable');
            }
        } catch (err) {
            setConnectionStatus('unreachable');
        } finally {
            setIsTesting(false);
        }
    };

    const handleCopyUrl = () => {
        navigator.clipboard.writeText(apiUrl);
    };

    const budgetTotal = budget ? budget.used + budget.remaining : 100;
    const budgetPercent = budgetTotal > 0 && budget ? (budget.used / budgetTotal) * 100 : 0;

    return (
        <div className="max-w-3xl mx-auto pb-12">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-gray-900 mb-1">Settings</h1>
                <p className="text-gray-500">Manage your CampaignX configuration and preferences.</p>
            </div>

            <div className="space-y-6">
                {/* LLM Provider Status */}
                <Card variant="outlined">
                    <CardContent className="p-0">
                        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">LLM Provider Status</h2>
                        </div>
                        <div className="divide-y divide-gray-100">
                            <div className="px-6 py-4 flex items-center justify-between border-l-4 border-yellow-500 bg-yellow-50/10">
                                <div className="flex items-center gap-4">
                                    <div className="w-2 h-2 rounded-full bg-yellow-500" />
                                    <div>
                                        <div className="font-medium text-gray-900">Gemini{' '}<span className="text-xs font-mono text-gray-500 ml-2">gemini-2.0-flash-lite</span></div>
                                        <div className="text-sm text-gray-500">Primary provider for fast generation</div>
                                    </div>
                                </div>
                                <span className="px-2.5 py-1 rounded-full bg-yellow-100 text-yellow-700 text-xs font-medium">Quota Limited (Primary)</span>
                            </div>
                            <div className="px-6 py-4 flex items-center justify-between border-l-4 border-green-500 bg-green-50/10">
                                <div className="flex items-center gap-4">
                                    <div className="w-2 h-2 rounded-full bg-green-500" />
                                    <div>
                                        <div className="font-medium text-gray-900">Groq{' '}<span className="text-xs font-mono text-gray-500 ml-2">llama-3.3-70b-versatile</span></div>
                                        <div className="text-sm text-gray-500">Fallback provider</div>
                                    </div>
                                </div>
                                <span className="px-2.5 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">Active (Current)</span>
                            </div>
                            <div className="px-6 py-4 flex items-center justify-between border-l-4 border-transparent">
                                <div className="flex items-center gap-4">
                                    <div className="w-2 h-2 rounded-full bg-gray-300" />
                                    <div>
                                        <div className="font-medium text-gray-900">Mistral{' '}<span className="text-xs font-mono text-gray-500 ml-2">mistral-small</span></div>
                                        <div className="text-sm text-gray-500">Secondary fallback</div>
                                    </div>
                                </div>
                                <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">Standby (Fallback)</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* API Config */}
                <Card variant="outlined">
                    <CardContent className="p-0">
                        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
                            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">API Configuration</h2>
                            {mockApi !== null && (
                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${mockApi ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                                    {mockApi ? 'Mock Mode' : 'Live Mode'}
                                </span>
                            )}
                        </div>
                        <div className="p-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Backend URL</label>
                            <div className="flex gap-2 mb-4">
                                <input
                                    type="text" readOnly value={apiUrl}
                                    className="flex-1 p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-gray-600 font-mono text-sm outline-none"
                                />
                                <Button variant="secondary" iconOnly={<ClipboardIcon className="w-4 h-4" />} aria-label="Copy URL" onClick={handleCopyUrl} />
                            </div>
                            <div className="flex items-center gap-4">
                                <Button onClick={testConnection} disabled={isTesting}>
                                    {isTesting ? 'Testing...' : 'Test Connection'}
                                </Button>
                                {connectionStatus === 'connected' && (
                                    <span className="flex items-center gap-1.5 text-sm font-medium text-green-600">
                                        <CheckCircle className="w-4 h-4" /> Connected
                                    </span>
                                )}
                                {connectionStatus === 'unreachable' && (
                                    <span className="flex items-center gap-1.5 text-sm font-medium text-red-600">
                                        <XCircle className="w-4 h-4" /> Unreachable
                                    </span>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* API Budget */}
                <Card variant="outlined">
                    <CardContent className="p-0">
                        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">API Budget &amp; Usage</h2>
                        </div>
                        <div className="p-6">
                            <div className="flex justify-between items-end mb-2">
                                <div className="text-3xl font-bold text-gray-900">
                                    {budget !== null ? budget.used : '--'}{' '}
                                    <span className="text-lg text-gray-400 font-normal">/ {budget !== null ? budgetTotal : '--'}</span>
                                </div>
                                <div className="text-sm font-medium text-blue-600">
                                    {budget !== null ? `${budget.remaining} remaining` : 'Loading...'}
                                </div>
                            </div>
                            <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
                                <div className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-in-out" style={{ width: `${budgetPercent}%` }} />
                            </div>
                            <p className="text-sm text-gray-500">Resets daily at midnight UTC.</p>
                        </div>
                    </CardContent>
                </Card>

                {/* Campaign Defaults */}
                <Card variant="outlined">
                    <CardContent className="p-0">
                        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Campaign Defaults</h2>
                        </div>
                        <div className="p-6 space-y-6">
                            <div>
                                <label className="block font-medium text-gray-900 mb-1">Default max iterations</label>
                                <div className="text-sm text-gray-500 mb-3">How many times the AI should attempt to optimize before presenting variants.</div>
                                <input
                                    type="number"
                                    value={maxIterations}
                                    onChange={(e) => setMaxIterations(Number(e.target.value))}
                                    min={1}
                                    max={10}
                                    className="w-48 p-2 border border-gray-300 rounded-lg bg-white text-gray-900 outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="flex justify-end pt-4">
                    <Button variant="primary">Save Preferences</Button>
                </div>
            </div>
        </div>
    );
}
