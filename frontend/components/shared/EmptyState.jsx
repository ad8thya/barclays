"use client";

export default function EmptyState({ icon: Icon, title, message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6">
      {Icon && (
        <div className="mb-4">
          <Icon size={32} className="text-accent/40" strokeWidth={1.5} />
        </div>
      )}
      <p className="text-[14px] font-medium text-slate-400 mb-1">{title}</p>
      <p className="text-[12px] text-slate-600 text-center max-w-xs">{message}</p>
    </div>
  );
}
