import React from 'react';

interface InputProps {
  type?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  label?: string;
  required?: boolean;
}

export function Input({ 
  type = 'text', 
  placeholder, 
  value, 
  onChange, 
  error,
  label,
  required = false
}: InputProps) {
  return (
    <div className="flex flex-col gap-2 w-full">
      {label && (
        <label className="text-[var(--color-text-primary)]">
          {label} {required && <span className="text-[var(--color-error)]">*</span>}
        </label>
      )}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className={`px-4 py-3 border rounded-lg transition-all duration-200 ${
          error 
            ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:ring-2 focus:ring-[var(--color-error)] focus:ring-opacity-20' 
            : 'border-[var(--color-border)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-opacity-20'
        } outline-none`}
      />
      {error && (
        <span className="caption text-[var(--color-error)]">{error}</span>
      )}
    </div>
  );
}

interface TextareaProps {
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  error?: string;
  label?: string;
  required?: boolean;
  rows?: number;
}

export function Textarea({ 
  placeholder, 
  value, 
  onChange, 
  error,
  label,
  required = false,
  rows = 5
}: TextareaProps) {
  return (
    <div className="flex flex-col gap-2 w-full">
      {label && (
        <label className="text-[var(--color-text-primary)]">
          {label} {required && <span className="text-[var(--color-error)]">*</span>}
        </label>
      )}
      <textarea
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        rows={rows}
        className={`px-4 py-3 border rounded-lg transition-all duration-200 resize-vertical ${
          error 
            ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:ring-2 focus:ring-[var(--color-error)] focus:ring-opacity-20' 
            : 'border-[var(--color-border)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-opacity-20'
        } outline-none`}
      />
      {error && (
        <span className="caption text-[var(--color-error)]">{error}</span>
      )}
    </div>
  );
}
