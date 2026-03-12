'use client';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ZapIcon, SparklesIcon, ArrowRightIcon, MailIcon, Loader2Icon } from 'lucide-react';
import { formatIST } from '@/lib/dateUtils';

export default function LandingPage() {
    const router = useRouter();
    const [brief, setBrief] = useState('');
    const [recentCampaigns, setRecentCampaigns] = useState<any[]>([]);
    const [isLoadingRecent, setIsLoadingRecent] = useState(true);

    useEffect(() => {
        const fetchRecent = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/campaigns`);
                if (res.ok) {
                    const data = await res.json();
                    const fetched = data.campaigns || [];
                    fetched.sort((a: any, b: any) => {
                        const dateA = new Date(a.created_at || a.start_date || 0).getTime();
                        const dateB = new Date(b.created_at || b.start_date || 0).getTime();
                        return dateB - dateA;
                    });
                    setRecentCampaigns(fetched.slice(0, 3));
                }
            } catch (err) {
                console.error('Failed to fetch recent campaigns', err);
            } finally {
                setIsLoadingRecent(false);
            }
        };
        fetchRecent();
    }, []);

    const handleQuickStart = (text: string) => {
        setBrief(text);
        // Optional: auto-submit after setting the brief (uncomment if desired)
        // router.push(`/campaign/new?brief=${encodeURIComponent(text)}`);
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
            <header className="h-16 flex items-center justify-between px-6 shrink-0 border-b border-gray-100">
                <img src="/assets/logo.webp" alt="CampaignX" className="h-14 w-auto mt-3" />
                <Link href="/dashboard">
                    <Button variant="primary" size="medium">
                        Dashboard
                    </Button>
                </Link>
            </header>

            {/* Hero Section */}
            <main className="flex-1 flex flex-col items-center justify-center px-4 py-20">
                <div className="max-w-3xl w-full text-center flex flex-col items-center">
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-200 bg-blue-50 text-xs font-semibold text-blue-700 mb-8 shadow-sm">
                        <ZapIcon className="w-3.5 h-3.5 fill-blue-500 text-blue-500" />
                        Powered by Multi-Agent AI
                    </div>

                    <h1 className="text-5xl md:text-6xl text-gray-900 tracking-tight mb-6 leading-tight">
                        <span className="font-light block">Your marketing,</span>
                        <span className="font-bold block text-blue-600">powered by AI</span>
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
                            className="block w-full pl-12 pr-32 py-4 text-lg border border-gray-200 rounded-2xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm hover:shadow-md transition-all"
                            placeholder="What do you want to create today?"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleStartCampaign();
                            }}
                        />
                        <div className="absolute inset-y-0 right-2 flex items-center gap-3">
                            <button className="text-sm font-semibold text-gray-500 hover:text-gray-900 transition-colors">
                                Options
                            </button>
                            <button
                                onClick={handleStartCampaign}
                                className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 active:scale-95 transition-all shadow-sm">
                                <ArrowRightIcon className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Quick Start Pills */}
                    <div className="flex flex-wrap justify-center gap-4 mt-6">
                        <button
                            onClick={() => handleQuickStart('Draft a welcome email series for new users who sign up for FinGrow, a personal finance platform that helps users track expenses, set savings goals, and invest in mutual funds. Introduce the platform’s key features across 3 emails: platform overview, key tools, and getting started tips. Encourage users to complete their profile and link their bank account. Optimise for open rate and click rate. Include the call to action: https://fingrow.com/get-started.')}
                            className="inline-flex items-center px-5 py-3 rounded-xl border border-blue-200 bg-blue-50 text-base font-semibold text-blue-700 hover:bg-blue-600 hover:border-blue-600 hover:text-white shadow-sm transition-all active:scale-95">
                            ✨ Draft a welcome series
                        </button>
                        <button
                            onClick={() => handleQuickStart('Launch the new "Smart Budget" product update for FinGrow. Write an email to our active users explaining how the new automatic expense categorization saves them 2 hours a week. Highlight the new AI-driven savings recommendations. Optimise for open rate and click rate. Include the call to action: https://fingrow.com/smart-budget.')}
                            className="inline-flex items-center px-5 py-3 rounded-xl border border-blue-200 bg-blue-50 text-base font-semibold text-blue-700 hover:bg-blue-600 hover:border-blue-600 hover:text-white shadow-sm transition-all active:scale-95">
                            🚀 Launch product update
                        </button>
                        <button
                            onClick={() => handleQuickStart("Re-engage users who haven't logged into FinGrow for 30 days. Write a short, empathetic email reminding them of their financial goals and offering a free 15-minute consultation with a financial advisor to get them back on track. Optimise for open rate and click rate. Include the call to action: https://fingrow.com/book-consult.")}
                            className="inline-flex items-center px-5 py-3 rounded-xl border border-blue-200 bg-blue-50 text-base font-semibold text-blue-700 hover:bg-blue-600 hover:border-blue-600 hover:text-white shadow-sm transition-all active:scale-95">
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
                        <Link href="/dashboard" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
                            View All
                        </Link>
                    </div>

                    <div className="space-y-3">
                        {isLoadingRecent ? (
                            <div className="flex items-center justify-center p-8 border border-gray-100 rounded-2xl bg-gray-50/50">
                                <Loader2Icon className="w-6 h-6 animate-spin text-blue-500" />
                            </div>
                        ) : recentCampaigns.length === 0 ? (
                            <div className="text-center p-8 border border-gray-100 rounded-2xl bg-gray-50 italic text-sm text-gray-500">
                                No recent campaigns found.
                            </div>
                        ) : (
                            recentCampaigns.map((c) => (
                                <div
                                    key={c.campaign_id}
                                    className="flex items-center justify-between p-4 rounded-xl border border-gray-100 bg-white hover:border-gray-300 hover:shadow-sm transition-all cursor-pointer group"
                                    onClick={() => router.push(`/campaign/${c.campaign_id}`)}>
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600 shrink-0 border border-blue-100 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                            <MailIcon className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <div className="font-semibold text-gray-900 truncate max-w-sm">
                                                {c.campaign_brief || `Campaign ${(c.campaign_id || '').split('-')[0]}`}
                                            </div>
                                            <div className="text-sm text-gray-500 flex items-center gap-2 mt-0.5">
                                                {c.status === 'done' ? (
                                                    <span>Sent to {c.customers_sent > 999 ? `${(c.customers_sent / 1000).toFixed(1)}k` : c.customers_sent} users</span>
                                                ) : (
                                                    <span className="capitalize">{c.status}</span>
                                                )}
                                                <span className="text-gray-300">•</span>
                                                <span>{formatIST(c.start_date || c.created_at)}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <StatusBadge status={c.status as any} />
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </main>

            <footer className="py-8 text-center text-sm text-gray-400 border-t border-gray-100 mt-auto">
                © 2026 CampaignX · Team Aquarium
            </footer>
        </div>
    );
}
