import React from 'react';
import { cn } from '../utils';

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
    title?: string;
    subtitle?: string;
}

export const CardHeader = ({
    className,
    title,
    subtitle,
    children,
    ...props
}: CardHeaderProps) => {
    return (
        <div className={cn('space-y-1.5 pb-4', className)} {...props}>
            {children || (
                <>
                    {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
                    {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
                </>
            )}
        </div>
    );
};
