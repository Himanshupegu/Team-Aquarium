'use client';
import React from 'react';
import { LoadingSpinner } from './LoadingSpinner';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'tertiary' | 'destructive';
    size?: 'small' | 'medium' | 'large';
    loading?: boolean;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
    iconOnly?: React.ReactNode;
    children?: React.ReactNode;
}

export const Button = ({
    variant = 'primary',
    size = 'medium',
    loading = false,
    leftIcon,
    rightIcon,
    iconOnly,
    children,
    disabled,
    className = '',
    ...props
}: ButtonProps) => {
    const baseStyles =
        'inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed';
    const variants = {
        primary:
            'bg-blue-600 text-white shadow-sm hover:bg-blue-700 hover:shadow active:scale-[0.98] disabled:bg-gray-300 disabled:shadow-none focus:ring-blue-500',
        secondary:
            'bg-white border border-gray-200 text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-300 hover:text-gray-900 active:scale-[0.98] disabled:border-gray-200 disabled:text-gray-400 disabled:shadow-none focus:ring-gray-200',
        tertiary:
            'bg-transparent text-gray-600 hover:bg-gray-100 hover:text-gray-900 active:bg-gray-200 disabled:text-gray-400 focus:ring-gray-200',
        destructive:
            'bg-white border border-red-200 text-red-600 shadow-sm hover:bg-red-50 border-red-300 hover:text-red-700 active:scale-[0.98] disabled:bg-gray-50 disabled:border-gray-200 disabled:text-gray-400 focus:ring-red-500',
    };
    const sizes = {
        small: 'text-sm px-3 py-1.5 gap-1.5 rounded-lg',
        medium: 'text-base px-4 py-2 gap-2 rounded-xl',
        large: 'text-lg px-6 py-3 gap-2.5 rounded-xl',
    };
    const iconSizes = {
        small: 'p-1.5',
        medium: 'p-2',
        large: 'p-3',
    };
    return (
        <button
            className={`
        ${baseStyles}
        ${variants[variant]}
        ${iconOnly ? iconSizes[size] : sizes[size]}
        ${className}
      `}
            disabled={disabled || loading}
            {...props}>
            {loading ? (
                <LoadingSpinner className="mr-2" />
            ) : (
                <>
                    {leftIcon}
                    {iconOnly ? iconOnly : children}
                    {rightIcon}
                </>
            )}
        </button>
    );
};
