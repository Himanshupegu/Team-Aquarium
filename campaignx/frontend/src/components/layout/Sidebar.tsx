'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    UserIcon,
    LayoutDashboardIcon,
    MailIcon,
    UsersIcon,
    SettingsIcon,
} from 'lucide-react';

interface SidebarProps {
    children: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
    const pathname = usePathname();
    const [budget, setBudget] = React.useState<{ used: number, limit: number } | null>(null);

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
        const intervalId = setInterval(fetchBudget, 3000);
        return () => clearInterval(intervalId);
    }, []);

    const navLinks = [
        { path: '/dashboard', label: 'Dashboard', icon: <LayoutDashboardIcon className="w-5 h-5" />, matchPrefix: undefined as string | undefined },
        { path: '/campaigns', label: 'Campaigns', icon: <MailIcon className="w-5 h-5" />, matchPrefix: '/campaign' as string | undefined },
        { path: '/cohort', label: 'Cohort', icon: <UsersIcon className="w-5 h-5" />, matchPrefix: undefined as string | undefined },
        { path: '/settings', label: 'Settings', icon: <SettingsIcon className="w-5 h-5" />, matchPrefix: undefined as string | undefined },
    ];

    const isActive = (path: string, matchPrefix?: string) => {
        if (matchPrefix && pathname.startsWith(matchPrefix)) return true;
        return pathname === path;
    };

    return (
        <>
            {/* Top Navigation Bar */}
            <header className="h-16 border-b border-gray-200 flex items-center justify-between px-6 bg-white shrink-0 z-10">
                <Link
                    href="/"
                    className="flex items-center hover:opacity-80 transition-opacity">
                    <img src="/assets/logo.webp" alt="CampaignX" className="h-14 w-auto mt-3" />
                </Link>
                <div className="w-10 h-10 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-500 cursor-pointer hover:bg-gray-200 transition-colors">
                    <UserIcon className="w-5 h-5" />
                </div>
            </header>

            {/* Body: sidebar + page content */}
            <div className="flex flex-1 overflow-hidden">
                <aside className="w-[240px] border-r border-gray-200 bg-gray-50/30 flex flex-col shrink-0">
                    <nav className="flex-1 py-6 px-3 space-y-1">
                        {navLinks.map((link) => {
                            const active = isActive(link.path, link.matchPrefix);
                            return (
                                <Link
                                    key={link.path}
                                    href={link.path}
                                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${active
                                        ? 'bg-blue-50 text-blue-700'
                                        : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                                        }`}>
                                    <span className={active ? 'text-blue-600' : 'text-gray-400'}>{link.icon}</span>
                                    {link.label}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* API Budget */}
                    <div className="p-6 border-t border-gray-200">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">
                            API Budget
                        </div>
                        <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden mb-2">
                            <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${budget ? (budget.used / budget.limit) * 100 : 0}%` }} />
                        </div>
                        <div className="text-xs text-gray-500 font-medium">
                            {budget ? `${budget.used} / ${budget.limit} calls today` : 'Loading budget...'}
                        </div>
                    </div>
                </aside>

                {/* Page content slot */}
                {children}
            </div>
        </>
    );
}
