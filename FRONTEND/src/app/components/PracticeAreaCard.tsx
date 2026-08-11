import React from 'react';
import { LucideIcon, ArrowRight } from 'lucide-react';

interface PracticeAreaCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function PracticeAreaCard({ icon: Icon, title, description }: PracticeAreaCardProps) {
  return (
    <div className="bg-white p-7 rounded-3xl border border-slate-200/90 shadow-xs hover:shadow-xl hover:border-amber-500/40 hover:-translate-y-1 transition-all duration-300 cursor-pointer group flex flex-col justify-between h-full">
      <div className="flex flex-col gap-5">
        <div className="w-14 h-14 bg-slate-900 rounded-2xl flex items-center justify-center border border-slate-800 shadow-md group-hover:scale-105 transition-transform duration-300">
          <Icon className="w-7 h-7 text-amber-400 group-hover:rotate-6 transition-transform duration-300" />
        </div>
        
        <div>
          <h3 className="text-slate-900 font-serif font-bold text-xl mb-2 group-hover:text-amber-600 transition-colors leading-snug">
            {title}
          </h3>
          <p className="text-slate-600 text-xs sm:text-sm leading-relaxed">
            {description}
          </p>
        </div>
      </div>

      <div className="pt-6 mt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-slate-900 group-hover:text-amber-600 transition-colors">
        <span>Detaylı Kapsamı İncele</span>
        <ArrowRight className="w-4 h-4 text-amber-500 group-hover:translate-x-1 transition-transform" />
      </div>
    </div>
  );
}