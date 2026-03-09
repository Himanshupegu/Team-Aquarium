'use client';
import React from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ClipboardIcon } from 'lucide-react';

export default function SettingsPage() {
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
                            <div className="px-6 py-4 flex items-center justify-between border-l-4 border-blue-500 bg-blue-50/10">
                                <div className="flex items-center gap-4">
                                    <div className="w-2 h-2 rounded-full bg-green-500" />
                                    <div>
                                        <div className="font-medium text-gray-900">Gemini{' '}<span className="text-xs font-mono text-gray-500 ml-2">gemini-1.5-flash</span></div>
                                        <div className="text-sm text-gray-500">Primary provider for fast generation</div>
                                    </div>
                                </div>
                                <span className="px-2.5 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">Active</span>
                            </div>
                            <div className="px-6 py-4 flex items-center justify-between border-l-4 border-transparent">
                                <div className="flex items-center gap-4">
                                    <div className="w-2 h-2 rounded-full bg-yellow-500" />
                                    <div>
                                        <div className="font-medium text-gray-900">Groq{' '}<span className="text-xs font-mono text-gray-500 ml-2">llama-3.1-70b</span></div>
                                        <div className="text-sm text-gray-500">Fallback provider</div>
                                    </div>
                                </div>
                                <span className="px-2.5 py-1 rounded-full bg-yellow-100 text-yellow-700 text-xs font-medium">Quota Exceeded</span>
                            </div>
                            <div className="px-6 py-4 flex items-center justify-between border-l-4 border-transparent">
                                <div className="flex items-center gap-4">
                                    <div className="w-2 h-2 rounded-full bg-gray-300" />
                                    <div>
                                        <div className="font-medium text-gray-900">Mistral{' '}<span className="text-xs font-mono text-gray-500 ml-2">mistral-large-latest</span></div>
                                        <div className="text-sm text-gray-500">Secondary fallback</div>
                                    </div>
                                </div>
                                <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-medium">Standby</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* API Config */}
                <Card variant="outlined">
                    <CardContent className="p-0">
                        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">API Configuration</h2>
                        </div>
                        <div className="p-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Backend URL</label>
                            <div className="flex gap-2">
                                <input
                                    type="text" readOnly value="https://campaignx-api.example.com/v1"
                                    className="flex-1 p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-gray-600 font-mono text-sm outline-none"
                                />
                                <Button variant="secondary" iconOnly={<ClipboardIcon className="w-4 h-4" />} aria-label="Copy URL" />
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
                                <div className="text-3xl font-bold text-gray-900">67{' '}<span className="text-lg text-gray-400 font-normal">/ 100</span></div>
                                <div className="text-sm font-medium text-blue-600">33 remaining</div>
                            </div>
                            <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: '67%' }} />
                            </div>
                            <p className="text-sm text-gray-500">Resets daily at midnight UTC.</p>
                        </div>
                    </CardContent>
                </Card>

                {/* Preferences */}
                <Card variant="outlined">
                    <CardContent className="p-0">
                        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">Preferences</h2>
                        </div>
                        <div className="p-6 space-y-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="font-medium text-gray-900">Show agent logs in campaign view</div>
                                    <div className="text-sm text-gray-500">Display the real-time reasoning feed from the AI agents.</div>
                                </div>
                                <div className="w-11 h-6 bg-blue-600 rounded-full relative cursor-pointer shrink-0">
                                    <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full" />
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="font-medium text-gray-900">Auto-approve campaigns (demo mode)</div>
                                    <div className="text-sm text-gray-500">Skip the human-in-the-loop approval step.</div>
                                </div>
                                <div className="w-11 h-6 bg-gray-200 rounded-full relative cursor-pointer shrink-0">
                                    <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm" />
                                </div>
                            </div>
                            <div>
                                <label className="block font-medium text-gray-900 mb-1">Default max iterations</label>
                                <div className="text-sm text-gray-500 mb-3">How many times the AI should attempt to optimize before presenting variants.</div>
                                <select className="w-48 p-2 border border-gray-300 rounded-lg bg-white text-gray-900 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option>1 (Fastest)</option>
                                    <option>2 (Balanced)</option>
                                    <option>3 (Best Quality)</option>
                                </select>
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
