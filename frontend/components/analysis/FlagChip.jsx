"use client";

export default function FlagChip({ flag }) {
  let color = "bg-accent/10 text-accent border-accent/20";
  let label = flag;

  if (flag.startsWith("credential_")) {
    color = "bg-red-500/10 text-red-400 border-red-500/20";
    label = flag.replace("credential_", "").replace(/_/g, " ");
  } else if (flag.startsWith("suspicious_urls:")) {
    color = "bg-amber-500/10 text-amber-400 border-amber-500/20";
    const count = flag.split(":")[1];
    label = `${count} suspicious URL${count !== "1" ? "s" : ""}`;
  } else if (flag.startsWith("keyword:")) {
    color = "bg-slate-500/10 text-slate-400 border-slate-500/20";
    label = flag.replace("keyword:", "").replace(/_/g, " ");
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded border text-[11px] max-h-6 font-mono ${color}`}
    >
      {label}
    </span>
  );
}
