"use client";

import { cn } from "@/lib/cn";

export function BentoGrid({ children, className }) {
  return (
    <div
      className={cn(
        "grid w-full auto-rows-[18rem] grid-cols-3 gap-4",
        className
      )}
    >
      {children}
    </div>
  );
}

export function BentoCard({
  name,
  className,
  Icon,
  description,
  tags,
  colSpan,
}) {
  return (
    <div
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-xl",
        "border border-white/[0.06]",
        "bg-[rgba(13,20,36,0.7)] backdrop-blur-[12px]",
        "shadow-[0_0_0_1px_rgba(255,255,255,0.04),0_8px_32px_rgba(0,0,0,0.4)]",
        "transition-all duration-300 hover:border-white/[0.1]",
        colSpan === 2 ? "col-span-2" : "col-span-1",
        className
      )}
    >
      {/* Hover glow */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/[0.04] to-transparent" />
      </div>

      <div className="relative z-10 p-6 flex flex-col h-full">
        {/* Icon */}
        <div className="mb-4 flex items-center justify-between">
          <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            {Icon && <Icon size={20} className="text-accent" strokeWidth={1.5} />}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1">
          <h3 className="text-[15px] font-medium text-slate-100 mb-2 tracking-tight">
            {name}
          </h3>
          <p className="text-[12px] text-slate-400 leading-relaxed line-clamp-3">
            {description}
          </p>
        </div>

        {/* Tags */}
        {tags && tags.length > 0 && (
          <div className="mt-4 pt-3 border-t border-white/[0.04] flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-[10px] px-2 py-0.5 rounded bg-white/[0.04] text-slate-500 uppercase tracking-wider"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
