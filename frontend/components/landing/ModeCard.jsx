"use client";

export default function ModeCard({ icon: Icon, title, description }) {
  return (
    <div className="glass-card p-5 flex items-start gap-4 hover:border-white/[0.1] transition-all">
      <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0">
        {Icon && <Icon size={18} className="text-accent" strokeWidth={1.5} />}
      </div>
      <div>
        <h3 className="text-[13px] font-medium text-slate-200 mb-1">{title}</h3>
        <p className="text-[11px] text-slate-500 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}
