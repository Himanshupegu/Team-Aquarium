'use client';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { MetricCard } from '@/components/ui/MetricCard';
import { StatusBadge, CampaignStatus } from '@/components/ui/StatusBadge';
import {
    LayersIcon, UsersIcon, MailOpenIcon, TrendingUpIcon,
    SearchIcon, ChevronRightIcon, PlusIcon, Loader2Icon
} from 'lucide-react';
import { formatIST } from '@/lib/dateUtils';

interface CampaignData {
    campaign_id: string;
    campaign_brief: string;
    status: string;
    segments_count: number;
    customers_sent: number;
    total_sent: number;
    open_rate: number;
    click_rate: number;
    start_date: string;
}

export default function DashboardPage() {
    const router = useRouter();
    const [campaigns, setCampaigns] = useState<CampaignData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 10;

    useEffect(() => {
        const fetchCampaigns = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/campaigns`, { cache: 'no-store' });
                if (res.ok) {
                    const data = await res.json();
                    const fetchedCampaigns = data.campaigns || [];
                    fetchedCampaigns.sort((a: any, b: any) => {
                        const dateA = new Date(a.created_at || a.start_date || 0).getTime();
                        const dateB = new Date(b.created_at || b.start_date || 0).getTime();
                        return dateB - dateA;
                    });
                    setCampaigns(fetchedCampaigns);
                }
            } catch (err) {
                console.error("Failed to fetch campaigns", err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchCampaigns();
        const interval = setInterval(fetchCampaigns, 5000);
        return () => clearInterval(interval);
    }, []);

    // Aggregate metrics
    const totalCampaigns = campaigns.length;
    const totalCustomers = campaigns.reduce((acc, c) => acc + (c.customers_sent || 0), 0);

    const avgOpenRate = campaigns.length > 0
        ? campaigns.reduce((acc, c) => acc + (c.open_rate || 0), 0) / campaigns.length
        : 0;
    const avgClickRate = campaigns.length > 0
        ? campaigns.reduce((acc, c) => acc + (c.click_rate || 0), 0) / campaigns.length
        : 0;

    const formatRate = (rate: number) => `${(rate * 100).toFixed(1)}%`;
    const formatNumber = (num: number) => num > 999 ? `${(num / 1000).toFixed(1)}k` : num.toString();

    // Pagination logic
    const totalPages = Math.ceil(campaigns.length / ITEMS_PER_PAGE);
    const paginatedCampaigns = campaigns.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

    return (
        <div className="max-w-7xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                <Link href="/campaign/new">
                    <Button variant="primary" leftIcon={<PlusIcon className="w-4 h-4" />}>
                        New Campaign
                    </Button>
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
                <MetricCard icon={<LayersIcon className="w-5 h-5" />} value={totalCampaigns.toString()} label="Total Campaigns" accentColor="purple" />
                <MetricCard icon={<UsersIcon className="w-5 h-5" />} value={formatNumber(totalCustomers)} label="Customers Reached" accentColor="blue" />
                <MetricCard icon={<MailOpenIcon className="w-5 h-5" />} value={formatRate(avgOpenRate)} label="Avg Open Rate" accentColor="green" />
                <MetricCard icon={<TrendingUpIcon className="w-5 h-5" />} value={formatRate(avgClickRate)} label="Avg Click Rate" accentColor="orange" />
            </div>

            <div className="mb-6 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Campaigns</h2>
                <div className="w-72">
                    <Input placeholder="Search campaigns..." startAdornment={<SearchIcon className="w-4 h-4 text-gray-400" />} size="small" />
                </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 font-medium">
                            <tr>
                                <th className="px-6 py-4">Campaign ID</th>
                                <th className="px-6 py-4">Brief Snippet</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Segments</th>
                                <th className="px-6 py-4">Sent</th>
                                <th className="px-6 py-4">Open Rate</th>
                                <th className="px-6 py-4">Click Rate</th>
                                <th className="px-6 py-4">Started</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {isLoading ? (
                                <tr>
                                    <td colSpan={9} className="px-6 py-12 text-center text-gray-400">
                                        <Loader2Icon className="w-6 h-6 animate-spin mx-auto mb-2" />
                                        Loading campaigns...
                                    </td>
                                </tr>
                            ) : campaigns.length === 0 ? (
                                <tr>
                                    <td colSpan={9} className="px-6 py-12 text-center text-gray-500">
                                        <div className="max-w-sm mx-auto">
                                            <p className="mb-4">No campaigns exist yet. Start your first AI-driven marketing campaign.</p>
                                            <Link href="/campaign/new">
                                                <Button variant="secondary">Create Campaign</Button>
                                            </Link>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                paginatedCampaigns.map((campaign) => {
                                    const open = campaign.open_rate;
                                    const openFormatted = formatRate(open);
                                    const click = campaign.click_rate;
                                    const clickFormatted = formatRate(click);

                                    return (
                                        <tr key={campaign.campaign_id} className="hover:bg-gray-50 cursor-pointer transition-colors" onClick={() => router.push(`/campaign/${campaign.campaign_id}`)}>
                                            <td className="px-6 py-4 font-mono text-xs text-gray-500">{campaign.campaign_id.split('-')[0]}</td>
                                            <td className="px-6 py-4 text-gray-900 truncate max-w-[200px]">{campaign.campaign_brief}</td>
                                            <td className="px-6 py-4"><StatusBadge status={campaign.status as CampaignStatus} /></td>
                                            <td className="px-6 py-4 text-gray-600">{campaign.segments_count}</td>
                                            <td className="px-6 py-4 text-gray-600">{formatNumber(campaign.total_sent)}</td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-gray-900 font-medium">{openFormatted}</span>
                                                    {open !== undefined && (
                                                        <div className="w-16 h-1 bg-gray-100 rounded-full overflow-hidden">
                                                            <div className="h-full bg-blue-500" style={{ width: `${open * 100}%` }} />
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-gray-900 font-medium">{clickFormatted}</span>
                                                    {click !== undefined && (
                                                        <div className="w-16 h-1 bg-gray-100 rounded-full overflow-hidden">
                                                            <div className="h-full bg-blue-400" style={{ width: `${click * 100}%` }} />
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-gray-500">{formatIST(campaign.start_date)}</td>
                                            <td className="px-6 py-4 text-right"><ChevronRightIcon className="w-5 h-5 text-gray-400 inline-block" /></td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {!isLoading && campaigns.length > 0 && (
                    <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-gray-50/50">
                        <span className="text-sm text-gray-500">
                            Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to {Math.min(currentPage * ITEMS_PER_PAGE, campaigns.length)} of {campaigns.length} campaigns
                        </span>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="secondary"
                                size="small"
                                disabled={currentPage === 1}
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                            >
                                Previous
                            </Button>
                            <span className="text-sm text-gray-600 px-2">Page {currentPage} of {totalPages}</span>
                            <Button
                                variant="secondary"
                                size="small"
                                disabled={currentPage === totalPages || totalPages === 0}
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                            >
                                Next
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
