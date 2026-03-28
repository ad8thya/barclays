"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import LayerCard from "@/components/LayerCard";
import SignalTag from "@/components/SignalTag";

const LAYERS = [
  { key: "email",      icon: "✉",  title: "Email",      weight: 35 },
  { key: "website",    icon: "🌐", title: "Website",    weight: 25 },
  { key: "attachment", icon: "📎", title: "Attachment", weight: 15 },
  { key: "audio",      icon: "🎙", title: "Audio",      weight: 15 },
];

export default function AnalysisPage() {
  const { emailResult, websiteResult, attachmentResult, audioResult, analyzing } = useAnalysis();

  const resultMap = {
    email:      emailResult,
    website:    websiteResult,
    attachment: attachmentResult,
    audio:      audioResult,
  };

  return (
    <>
      <div className="mb-8">
        <h2 className="text-lg font-semibold tracking-tight text-slate-100">Module Breakdown</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Raw output per analyzer — before score fusion
        </p>
      </div>

      {/* 2×2 grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {LAYERS.map((layer, idx) => {
          const data = resultMap[layer.key];

          // derive score — website uses final_score/100, others use risk_score
          let score = data?.risk_score ?? null;
          if (layer.key === "website" && data?.final_score != null) {
            score = data.final_score / 100;
          }

          return (
            <div
              key={layer.key}
              style={{
                opacity: 0,
                animation: `fadeSlideIn 0.3s ease forwards`,
                animationDelay: `${idx * 120}ms`,
              }}
            >
              <LayerCard
                icon={layer.icon}
                title={layer.title}
                weight={layer.weight}
                status={analyzing ? "running" : data ? "complete" : "pending"}
                score={score}
              >
                <SignalList data={data} />

                {/* Email flagged phrases */}
                {layer.key === "email" && data?.flagged_phrases?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/[0.05]">
                    <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-2">
                      Flagged phrases
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {data.flagged_phrases.map((p, i) => (
                        <span
                          key={i}
                          className="text-[11px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-mono"
                        >
                          &ldquo;{p}&rdquo;
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Website detections */}
                {layer.key === "website" && data?.reasons?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/[0.05]">
                    <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-2">
                      Detections
                    </p>
                    <ul className="space-y-1">
                      {data.reasons.map((r, i) => (
                        <li key={i} className="text-[11px] text-slate-400 flex items-start gap-2">
                          <span className="text-red-500 mt-0.5 select-none">–</span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </LayerCard>
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  );
}

/* ── Helpers ── */

function RiskBadge({ label, level }) {
  const cls =
    level === "HIGH" || level === "OOB"
      ? "bg-red-500/10 text-red-400 border-red-500/20"
      : level === "MEDIUM"
      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold border ${cls}`}>
      {label}
    </span>
  );
}

function SignalList({ data }) {
  if (!data?.signals) return null;
  const entries = Object.entries(data.signals).filter(
    ([, val]) => val === true || typeof val === "number" || (typeof val === "string" && val)
  );
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {entries.map(([key, val]) => {
        if (val === true) return <SignalTag key={key} label={formatKey(key)} danger />;
        return <SignalTag key={key} label={`${formatKey(key)}: ${val}`} />;
      })}
    </div>
  );
}

function formatKey(k) {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}