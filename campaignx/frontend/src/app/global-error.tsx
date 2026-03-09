'use client';
import { useEffect } from 'react';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <html>
            <body>
                <div className="min-h-screen bg-white flex items-center justify-center px-4">
                    <div className="text-center max-w-md">
                        <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
                        <p className="text-gray-500 text-sm mb-6">{error.message}</p>
                        <button
                            onClick={reset}
                            className="px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors">
                            Try again
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
