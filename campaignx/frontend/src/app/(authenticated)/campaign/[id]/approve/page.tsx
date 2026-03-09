'use client';
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { VariantEmailCard } from '@/components/ui/VariantEmailCard';
import { Dialog, DialogContent, DialogHeader, DialogFooter } from '@/components/ui/Dialog';
import { ArrowLeftIcon, Loader2Icon, AlertTriangleIcon } from 'lucide-react';

interface PendingVariant {
    variant_label: 'A' | 'B';
    segment_label: string;
    subject: string;
    body: string;
    customer_ids: string[];
    send_time: string;
    strategy_notes: string;
}

interface SegmentData {
    label: string;
    description: string;
    size: number;
    recommended_tone: string;
}

interface CampaignState {
    status: string;
    iteration: number;
    pending_variants: PendingVariant[];
    all_segments: Record<string, SegmentData>;
}

export default function ApprovalPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();

    const [campaign, setCampaign] = useState<CampaignState | null>(null);
    const [fetchError, setFetchError] = useState<string | null>(null);

    const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
    const [feedback, setFeedback] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (!id) return;

        const fetchStatus = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/campaign/${id}/status`);

                if (!res.ok) {
                    if (res.status === 404) {
                        setFetchError('Campaign not found.');
                        return;
                    }
                    throw new Error('Failed to fetch campaign status');
                }

                const data = await res.json();
                setCampaign(data);

                // If not awaiting approval anymore, bounce back
                if (data.status !== 'awaiting_approval' && data.status !== 'error') {
                    router.push(`/campaign/${id}`);
                }
            } catch (err) {
                console.error(err);
                setFetchError('Failed to connect to backend.');
            }
        };

        fetchStatus();
    }, [id, router]);

    const handleDecision = async (decision: 'approve' | 'reject') => {
        if (!id || isSubmitting) return;
        setIsSubmitting(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiUrl}/api/campaign/${id}/decision`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ decision, feedback }),
            });

            if (!res.ok) throw new Error(`Decision failed: ${res.status}`);

            router.push(`/campaign/${id}`);
        } catch (err) {
            console.error('Failed to submit decision:', err);
            alert('Failed to submit decision. Please try again.');
        } finally {
            setIsSubmitting(false);
            setIsRejectModalOpen(false);
        }
    };

    if (fetchError) {
        return (
            <div className="max-w-7xl mx-auto py-12 text-center">
                <AlertTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Campaign</h2>
                <p className="text-gray-500 mb-6">{fetchError}</p>
                <Button variant="secondary" onClick={() => router.push('/campaigns')}>Back to Campaigns</Button>
            </div>
        );
    }

    if (!campaign && !fetchError) {
        return (
            <div className="max-w-7xl mx-auto py-24 flex flex-col items-center justify-center">
                <Loader2Icon className="w-8 h-8 text-blue-500 animate-spin mb-4" />
                <div className="text-gray-500 font-medium">Loading variants for review...</div>
            </div>
        );
    }

    // Group variants by segment
    const variantsBySegment = (campaign?.pending_variants || []).reduce((acc, variant) => {
        if (!acc[variant.segment_label]) {
            acc[variant.segment_label] = [];
        }
        acc[variant.segment_label].push(variant);
        return acc;
    }, {} as Record<string, PendingVariant[]>);

    const segmentCount = Object.keys(variantsBySegment).length;
    const variantCount = campaign?.pending_variants?.length || 0;

    // Helper to extract a CTA URL if present in body (naive regex extraction)
    const extractUrl = (html: string) => {
        const match = html.match(/href="([^"]+)"/);
        return match ? match[1] : '';
    };

    // Helper to strip HTML for character count
    const stripHtml = (html: string) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        return doc.body.textContent || '';
    };

    return (
        <div className="max-w-7xl mx-auto pb-24">
            <div className="mb-8">
                <Link
                    href={`/campaign/${id}`}
                    className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 mb-4 transition-colors">
                    <ArrowLeftIcon className="w-4 h-4 mr-1" />
                    Back to Campaign
                </Link>
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">Review Campaign Content</h1>
                        <p className="text-gray-500">
                            Iteration {campaign?.iteration} · {segmentCount} segments · {variantCount} variants
                        </p>
                    </div>
                    <StatusBadge status="awaiting_approval" />
                </div>
            </div>

            <div className="space-y-12">
                {Object.entries(variantsBySegment).map(([segmentLabel, variants]) => {
                    const segMeta = campaign?.all_segments?.[segmentLabel];

                    return (
                        <section key={segmentLabel}>
                            <div className="flex items-center gap-4 mb-6 pb-2 border-b border-gray-200">
                                <h2 className="text-xl font-bold text-gray-900 capitalize">
                                    {segmentLabel.replace(/_/g, ' ')}
                                </h2>
                                <span className="text-gray-500 text-sm">{segMeta?.size || 0} customers</span>
                                <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded uppercase tracking-wider ml-auto">
                                    Tone: {segMeta?.recommended_tone || 'Professional'}
                                </span>
                            </div>
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {variants.map((v) => (
                                    <VariantEmailCard
                                        key={v.variant_label}
                                        variant={v.variant_label}
                                        type={v.variant_label === 'A' ? 'rational' : 'emotional'}
                                        subjectLine={v.subject}
                                        bodyHtml={v.body.replace(/\n/g, '<br/>')}
                                        ctaText="Learn More"
                                        ctaUrl={extractUrl(v.body)}
                                        subjectCharCount={v.subject.length}
                                        bodyCharCount={stripHtml(v.body.replace(/<br\/>/g, '\n')).length}
                                        strategyNotes={v.strategy_notes}
                                    />
                                ))}
                            </div>
                        </section>
                    );
                })}

                {variantCount === 0 && (
                    <div className="text-center py-12 bg-gray-50 rounded-xl border border-gray-100">
                        <p className="text-gray-500">No pending variants found for this campaign.</p>
                    </div>
                )}
            </div>

            {/* Sticky Bottom Bar */}
            <div className="fixed bottom-0 left-[240px] right-0 bg-white border-t border-gray-200 px-12 py-4 flex items-center justify-between z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
                <div className="text-sm text-gray-500 font-medium">
                    Iteration {campaign?.iteration} · {variantCount} variants across {segmentCount} segments
                </div>
                <div className="flex gap-3">
                    <Button
                        variant="destructive"
                        className="bg-white text-red-600 border border-red-200 hover:bg-red-50"
                        disabled={isSubmitting || variantCount === 0}
                        onClick={() => setIsRejectModalOpen(true)}>
                        Reject and Regenerate
                    </Button>
                    <Button
                        variant="primary"
                        size="large"
                        disabled={isSubmitting || variantCount === 0}
                        onClick={() => handleDecision('approve')}>
                        {isSubmitting ? 'Approving...' : 'Approve and Send'}
                    </Button>
                </div>
            </div>

            {/* Rejection Modal */}
            <Dialog isOpen={isRejectModalOpen} onClose={() => !isSubmitting && setIsRejectModalOpen(false)} size="md">
                <DialogHeader>Provide Feedback</DialogHeader>
                <DialogContent>
                    <p className="text-sm text-gray-500 mb-4">
                        Be specific about what to improve. The AI will use this feedback to generate Iteration {(campaign?.iteration || 0) + 1}.
                    </p>
                    <textarea
                        className="w-full min-h-[150px] p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-y text-gray-900"
                        placeholder="E.g. Make the subject lines shorter. The emotional variants are a bit too dramatic, tone them down to be more professional."
                        value={feedback}
                        disabled={isSubmitting}
                        onChange={(e) => setFeedback(e.target.value)}
                    />
                    <div className="text-right mt-1 text-xs text-gray-400 font-mono">{feedback.length} chars</div>
                </DialogContent>
                <DialogFooter>
                    <Button variant="tertiary" disabled={isSubmitting} onClick={() => setIsRejectModalOpen(false)}>Cancel</Button>
                    <Button variant="primary" disabled={feedback.length === 0 || isSubmitting} onClick={() => handleDecision('reject')}>
                        {isSubmitting ? 'Regenerating...' : 'Regenerate with Feedback'}
                    </Button>
                </DialogFooter>
            </Dialog>
        </div>
    );
}
