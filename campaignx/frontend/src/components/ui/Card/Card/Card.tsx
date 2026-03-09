import React, { forwardRef } from 'react';
import { cn } from '../utils';

type CardVariant = 'elevated' | 'outlined' | 'filled';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: CardVariant;
    isClickable?: boolean;
    padding?: 'none' | 'small' | 'medium' | 'large';
    rounded?: 'none' | 'small' | 'medium' | 'large';
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
    (
        {
            children,
            className,
            variant = 'outlined',
            isClickable = false,
            padding = 'medium',
            rounded = 'medium',
            ...props
        },
        ref
    ) => {
        const baseStyles = 'w-full transition-all duration-200';
        const variantStyles = {
            elevated: 'bg-white border border-gray-200 shadow-md hover:shadow-lg',
            outlined: 'border border-gray-300 hover:border-gray-400',
            filled: 'bg-gray-100 hover:bg-gray-200',
        };
        const paddingStyles = {
            none: 'p-0',
            small: 'p-2',
            medium: 'p-4',
            large: 'p-6',
        };
        const roundedStyles = {
            none: 'rounded-none',
            small: 'rounded',
            medium: 'rounded-lg',
            large: 'rounded-xl',
        };
        const clickableStyles = isClickable
            ? 'cursor-pointer focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2'
            : '';
        return (
            <div
                ref={ref}
                className={cn(
                    baseStyles,
                    variantStyles[variant],
                    paddingStyles[padding],
                    roundedStyles[rounded],
                    clickableStyles,
                    className
                )}
                {...props}>
                {children}
            </div>
        );
    }
);
Card.displayName = 'Card';
