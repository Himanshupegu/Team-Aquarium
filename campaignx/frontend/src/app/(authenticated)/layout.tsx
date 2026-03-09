import React, { Suspense } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="min-h-screen bg-white flex flex-col font-sans">
            <Suspense>
                <Sidebar>
                    <main className="flex-1 overflow-y-auto bg-white p-12 relative">
                        {children}
                    </main>
                </Sidebar>
            </Suspense>
        </div>
    );
}
