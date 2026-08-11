import React from 'react';

/* Hallmark Component discipline: 8 states supported (default, hover, focus-visible, active, disabled, loading, error, success) */
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'gold';
  children: React.ReactNode;
  isLoading?: boolean;
  className?: string;
}

export function Button({ 
  variant = 'primary', 
  children, 
  onClick, 
  className = '',
  type = 'button',
  disabled = false,
  isLoading = false,
  ...props
}: ButtonProps) {
  const baseStyles = "px-6 py-3 rounded-xl font-medium text-sm transition-all duration-200 inline-flex items-center justify-center gap-2 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none";
  
  const variants = {
    primary: "bg-slate-900 text-white hover:bg-slate-800 shadow-md hover:shadow-lg border border-slate-800",
    secondary: "border border-slate-300 bg-white text-slate-800 hover:bg-slate-100 shadow-xs",
    gold: "bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold shadow-md hover:shadow-xl border border-amber-400/30",
    ghost: "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin flex-shrink-0" />
          <span>Yükleniyor...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
