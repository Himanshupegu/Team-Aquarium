import Link from 'next/link';

export default function NotFound() {
    return (
        <div className="min-h-screen bg-white flex items-center justify-center px-4">
            <div className="text-center max-w-md">
                <div className="text-6xl font-bold text-gray-200 mb-4">404</div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Page not found</h2>
                <p className="text-gray-500 text-sm mb-6">
                    The page you&apos;re looking for doesn&apos;t exist.
                </p>
                <Link
                    href="/"
                    className="px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors">
                    Back to Home
                </Link>
            </div>
        </div>
    );
}
