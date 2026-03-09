import React from 'react';
import { cn } from '../utils';

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
    mediaUrl?: string;
    mediaAspectRatio?: '16:9' | '4:3' | '1:1';
}

export const CardContent = ({
    className,
    children,
    mediaUrl,
    mediaAspectRatio = '16:9',
    ...props
}: CardContentProps) => {
    const aspectRatioClasses = {
        '16:9': 'aspect-video',
        '4:3': 'aspect-[4/3]',
        '1:1': 'aspect-square',
    };
    return (
        <div className={cn('space-y-4', className)} {...props}>
            {mediaUrl && (
                <div className={cn('overflow-hidden', aspectRatioClasses[mediaAspectRatio])}>
                    <img src={mediaUrl} alt="" className="w-full h-full object-cover" />
                </div>
            )}
            {children}
        </div>
    );
};
