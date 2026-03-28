"use client";

export default function SignalTag({ label }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded bg-white/[0.04] text-[11px] text-slate-400 border border-white/[0.06] max-h-6 font-mono">
      {label}
    </span>
  );
}
