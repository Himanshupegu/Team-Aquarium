'use client';
import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ZapIcon, SparklesIcon, ArrowRightIcon, MailIcon, FileTextIcon } from 'lucide-react';

export default function LandingPage() {
    const router = useRouter();
    const [brief, setBrief] = React.useState('');

    const handleQuickStart = (text: string) => {
        router.push(`/campaign/new?brief=${encodeURIComponent(text)}`);
    };

    const handleStartCampaign = () => {
        if (brief.trim()) {
            router.push(`/campaign/new?brief=${encodeURIComponent(brief)}`);
        } else {
            router.push('/campaign/new');
        }
    };

    return (
        <div className="min-h-screen bg-white flex flex-col font-sans">
            {/* Standalone Top Nav */}
            <header className="h-16 flex items-center justify-between px-6 shrink-0">
                <img src="/assets/logo.webp" alt="CampaignX" className="h-14 w-auto mt-3" />
                <Link href="/dashboard">
                    <Button variant="secondary" size="small">
                        Dashboard
                    </Button>
                </Link>
            </header>

            {/* Hero Section */}
            <main className="flex-1 flex flex-col items-center justify-center px-4 py-20">
                <div className="max-w-3xl w-full text-center flex flex-col items-center">
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-gray-50 text-xs font-medium text-gray-600 mb-8">
                        <ZapIcon className="w-3.5 h-3.5 text-yellow-500" />
                        Powered by Multi-Agent AI
                    </div>

                    <h1 className="text-5xl md:text-6xl text-gray-900 tracking-tight mb-6 leading-tight">
                        <span className="font-light block">Your marketing,</span>
                        <span className="font-bold block">powered by AI</span>
                    </h1>

                    <p className="text-lg text-gray-500 mb-12 max-w-xl mx-auto">
                        Write a brief. AI segments, generates, sends, and optimizes your campaigns automatically.
                    </p>

                    {/* Search-style Input */}
                    <div className="w-full max-w-2xl relative group mb-8">
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                            <SparklesIcon className="h-5 w-5 text-blue-500" />
                        </div>
                        <input
                            type="text"
                            value={brief}
                            onChange={(e) => setBrief(e.target.value)}
                            className="block w-full pl-12 pr-32 py-4 text-lg border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm transition-shadow"
                            placeholder="What do you want to create today?"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleStartCampaign();
                            }}
                        />
                        <div className="absolute inset-y-0 right-2 flex items-center gap-3">
                            <button className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
                                Options
                            </button>
                            <button
                                onClick={handleStartCampaign}
                                className="p-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors">
                                <ArrowRightIcon className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Quick Start Pills */}
                    <div className="flex flex-wrap justify-center gap-3">
                        <button
                            onClick={() => handleQuickStart('Draft a welcome series for new signups')}
                            className="inline-flex items-center px-4 py-2 rounded-full border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all">
                            ✨ Draft a welcome series
                        </button>
                        <button
                            onClick={() => handleQuickStart('Launch our new Q4 product update')}
                            className="inline-flex items-center px-4 py-2 rounded-full border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all">
                            🚀 Launch product update
                        </button>
                        <button
                            onClick={() =>
                                handleQuickStart("Re-engage users who haven't logged in for 30 days")
                            }
                            className="inline-flex items-center px-4 py-2 rounded-full border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all">
                            📈 Re-engage inactive users
                        </button>
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="w-full max-w-3xl mt-24">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500">
                            Recent Activity
                        </h2>
                        <Link href="/dashboard" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                            View All
                        </Link>
                    </div>

                    <div className="space-y-3">
                        <div
                            className="flex items-center justify-between p-4 rounded-xl border border-gray-100 bg-white hover:border-gray-200 transition-colors cursor-pointer"
                            onClick={() => router.push('/campaign/cmp_1')}>
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 shrink-0">
                                    <MailIcon className="w-5 h-5" />
                                </div>
                                <div>
                                    <div className="font-medium text-gray-900">Q3 Newsletter</div>
                                    <div className="text-sm text-gray-500">Sent to 12.4k subscribers · 2 hours ago</div>
                                </div>
                            </div>
                            <StatusBadge status="sending" />
                        </div>

                        <div
                            className="flex items-center justify-between p-4 rounded-xl border border-gray-100 bg-white hover:border-gray-200 transition-colors cursor-pointer"
                            onClick={() => router.push('/campaign/cmp_2')}>
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-lg bg-yellow-50 flex items-center justify-center text-yellow-600 shrink-0">
                                    <ZapIcon className="w-5 h-5" />
                                </div>
                                <div>
                                    <div className="font-medium text-gray-900">Product Update Launch</div>
                                    <div className="text-sm text-gray-500">Targeting 8.2k users · 5 hours ago</div>
                                </div>
                            </div>
                            <StatusBadge status="awaiting_approval" />
                        </div>

                        <div
                            className="flex items-center justify-between p-4 rounded-xl border border-gray-100 bg-white hover:border-gray-200 transition-colors cursor-pointer"
                            onClick={() => router.push('/campaign/cmp_3')}>
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-gray-600 shrink-0">
                                    <FileTextIcon className="w-5 h-5" />
                                </div>
                                <div>
                                    <div className="font-medium text-gray-900">Welcome Series Draft</div>
                                    <div className="text-sm text-gray-500">Automated workflow · 1 day ago</div>
                                </div>
                            </div>
                            <StatusBadge status="drafting" />
                        </div>
                    </div>
                </div>
            </main>

            <footer className="py-6 text-center text-sm text-gray-400">
                © 2026 CampaignX · Team Aquarium
            </footer>
        </div>
    );
}
