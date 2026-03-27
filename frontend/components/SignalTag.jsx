"use client";

export default function SignalTag({ label, danger = false }) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-md mr-1.5 mb-1.5 tracking-wide ${
        danger
          ? "bg-red-500/8 text-red-400 border border-red-500/10"
          : "bg-accent/8 text-accent-light border border-accent/10"
      }`}
    >
      {danger && (
        <span className="w-1 h-1 rounded-full bg-red-400 flex-shrink-0" />
      )}
      {label}
    </span>
  );
}
