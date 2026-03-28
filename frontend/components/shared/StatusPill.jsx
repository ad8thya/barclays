"use client";

export default function StatusPill({ status }) {
  const config = {
    pending: { bg: "bg-slate-800/60", text: "text-slate-500", label: "PENDING", dot: null },
    analysing: { bg: "bg-accent/10", text: "text-accent", label: "ANALYSING", dot: "bg-accent" },
    complete: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "COMPLETE", dot: null },
    error: { bg: "bg-red-500/10", text: "text-red-400", label: "ERROR", dot: null },
  };

  const c = config[status] || config.pending;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${c.bg} ${c.text} text-[10px] font-medium uppercase tracking-[0.08em]`}
    >
      {c.dot && (
        <span className={`w-1.5 h-1.5 rounded-full ${c.dot} animate-spin`}>
          <span className="block w-full h-full rounded-full border border-current border-t-transparent animate-spin" />
        </span>
      )}
      {status === "analysing" && (
        <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
      )}
      {c.label}
    </span>
  );
}
