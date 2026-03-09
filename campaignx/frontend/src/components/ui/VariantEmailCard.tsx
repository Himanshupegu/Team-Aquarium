'use client';
import React, { useState } from 'react';
import { Card, CardContent } from './Card';
import { ChevronDownIcon, ChevronUpIcon } from 'lucide-react';

interface VariantEmailCardProps {
    variant: 'A' | 'B';
    type: 'rational' | 'emotional';
    subjectLine: string;
    bodyHtml: string;
    ctaText: string;
    ctaUrl: string;
    subjectCharCount: number;
    bodyCharCount: number;
    strategyNotes: string;
}

export function VariantEmailCard({
    variant,
    type,
    subjectLine,
    bodyHtml,
    ctaText,
    ctaUrl,
    subjectCharCount,
    bodyCharCount,
    strategyNotes,
}: VariantEmailCardProps) {
    const [notesExpanded, setNotesExpanded] = useState(false);
    return (
        <Card variant="outlined" className="h-full flex flex-col bg-white">
            <CardContent className="p-0 flex flex-col h-full">
                {/* Header */}
                <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                    <span className="font-semibold text-gray-900">Variant {variant}</span>
                    <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${type === 'rational'
                                ? 'bg-blue-50 text-blue-700 border border-blue-100'
                                : 'bg-pink-50 text-pink-700 border border-pink-100'
                            }`}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                    </span>
                </div>

                {/* Subject */}
                <div className="px-5 py-4 border-b border-gray-100">
                    <div className="text-xs text-gray-500 mb-1 uppercase tracking-wider font-semibold">Subject</div>
                    <div className="text-lg font-semibold text-gray-900">{subjectLine}</div>
                </div>

                {/* Body Preview */}
                <div className="px-5 py-4 flex-1 overflow-y-auto max-h-64 bg-white">
                    <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider font-semibold">
                        Body Preview
                    </div>
                    <div
                        className="text-sm text-gray-700 space-y-3 prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ __html: bodyHtml }}
                    />
                    <div className="mt-6">
                        <div className="inline-block px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-md text-center cursor-default">
                            {ctaText}
                        </div>
                        <div className="mt-2 text-xs text-gray-400 font-mono truncate">{ctaUrl}</div>
                    </div>
                </div>

                {/* Footer Stats */}
                <div className="px-5 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
                    <span>Subject: {subjectCharCount} chars</span>
                    <span>Body: {bodyCharCount} chars</span>
                </div>

                {/* Strategy Notes */}
                <div className="border-t border-gray-100">
                    <button
                        onClick={() => setNotesExpanded(!notesExpanded)}
                        className="w-full px-5 py-3 flex items-center justify-between text-sm text-gray-600 hover:bg-gray-50 transition-colors">
                        <span className="font-medium">Strategy Notes</span>
                        {notesExpanded ? (
                            <ChevronUpIcon className="w-4 h-4" />
                        ) : (
                            <ChevronDownIcon className="w-4 h-4" />
                        )}
                    </button>
                    {notesExpanded && (
                        <div className="px-5 pb-4 pt-1 text-sm text-gray-600 italic bg-gray-50/50 border-t border-gray-50">
                            {strategyNotes}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
