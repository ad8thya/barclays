"use client";

import { useAnalysis } from "@/context/AnalysisContext";
import LayerCard from "@/components/LayerCard";
import SignalTag from "@/components/SignalTag";

const LAYERS = [
  { key: "email", icon: "✉", title: "Email", weight: 35 },
  { key: "website", icon: "🌐", title: "Website", weight: 25 },
  { key: "attachment", icon: "📎", title: "Attachment", weight: 15 },
  { key: "audio", icon: "🎙", title: "Audio", weight: 15 },
];

export default function AnalysisPage() {
  const { emailResult, websiteResult, attachmentResult, audioResult, analyzing } = useAnalysis();

  const resultMap = {
    email: emailResult,
    website: websiteResult,
    attachment: attachmentResult,
    audio: audioResult,
  };

  return (
    <>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1.5 h-5 rounded-full bg-accent" />
          <h2 className="text-xl font-semibold tracking-tight">Layer-by-Layer Analysis</h2>
        </div>
        <p className="text-sm text-slate-500 ml-5">
          Individual module results — raw signals before fusion
        </p>
      </div>

      {/* 2×2 grid with staggered entrance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {LAYERS.map((layer, idx) => {
          const data = resultMap[layer.key];
          return (
            <div key={layer.key} style={{ animationDelay: `${idx * 150}ms` }} className="animate-slide-up">
              <LayerCard
                icon={layer.icon}
                title={layer.title}
                weight={layer.weight}
                status={analyzing ? "running" : data ? "complete" : "pending"}
                score={data?.risk_score}
              >
                <SignalList data={data} />

                {/* Email flagged phrases */}
                {layer.key === "email" && data?.flagged_phrases?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/[0.04]">
                    <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-2 font-medium">
                      Flagged Phrases
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {data.flagged_phrases.map((p, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 border border-red-500/20 font-mono">
                          &ldquo;{p}&rdquo;
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Website reasons */}
                {layer.key === "website" && data?.reasons?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/[0.04]">
                    <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-2 font-medium">
                      Detections
                    </p>
                    <ul className="space-y-1">
                      {data.reasons.map((r, i) => (
                        <li key={i} className="text-[11px] text-slate-400 flex items-start gap-2">
                          <span className="text-red-400 mt-0.5">›</span> {r}
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
    </>
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
