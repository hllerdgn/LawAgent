import React from 'react';
import { LucideIcon, ArrowRight } from 'lucide-react';

interface PracticeAreaCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function PracticeAreaCard({ icon: Icon, title, description }: PracticeAreaCardProps) {
  return (
    <div className="bg-white p-6 rounded-xl border border-[var(--color-border)] hover:border-[var(--color-accent)] hover:shadow-xl hover:scale-105 transition-all duration-300 cursor-pointer group">
      <div className="flex flex-col gap-4">
        <div className="w-14 h-14 bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-dark)] rounded-xl flex items-center justify-center group-hover:from-[var(--color-accent)] group-hover:to-[var(--color-accent-dark)] transition-all duration-300 shadow-md group-hover:shadow-lg">
          <Icon className="w-7 h-7 text-[var(--color-accent)] group-hover:text-white transition-colors group-hover:scale-110" />
        </div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-[var(--color-primary)] group-hover:text-[var(--color-accent)] transition-colors flex-1">
            {title}
          </h3>
          <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-[var(--color-accent)] group-hover:translate-x-1 transition-all opacity-0 group-hover:opacity-100" />
        </div>
        <p className="text-[var(--color-text-secondary)] leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
}