"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAnalysis } from "@/context/AnalysisContext";
import {
  analyzeWebsite,
  analyzeAttachment,
  analyzeScore,
  analyzeExplain,
  getGraph,
} from "@/lib/api";

export default function InputPage() {
  const router = useRouter();
  const ctx = useAnalysis();

  const [url, setUrl] = useState("");
  const [attachmentFile, setAttachmentFile] = useState(null);
  const [fileDragOver, setFileDragOver] = useState(false);

  const [layerProgress, setLayerProgress] = useState({
    website: "idle", attachment: "idle", score: "idle", graph: "idle",
  });

  function updateProgress(layer, status) {
    setLayerProgress((prev) => ({ ...prev, [layer]: status }));
  }

  async function handleAnalyze() {
    ctx.setAnalyzing(true);
    setLayerProgress({
      website:    url ? "running" : "skipped",
      attachment: attachmentFile ? "running" : "skipped",
      score:      "waiting",
      graph:      "waiting",
    });

    const id = ctx.incidentId;

    const results = await Promise.allSettled([
      url
        ? analyzeWebsite(id, url)
            .then((r) => { updateProgress("website", "done"); return r; })
            .catch(() => { updateProgress("website", "done"); return null; })
        : Promise.resolve(null),

      attachmentFile
        ? analyzeAttachment(id, attachmentFile)
            .then((r) => { updateProgress("attachment", "done"); return r; })
            .catch(() => { updateProgress("attachment", "done"); return null; })
        : Promise.resolve(null),
    ]);

    const webRes    = results[0].status === "fulfilled" ? results[0].value : null;
    const attachRes = results[1].status === "fulfilled" ? results[1].value : null;

    // attachment doc risk score
    const attachScore = attachRes?.success ? (attachRes.data?.risk_score ?? 0) : 0;

    // email risk extracted from attachment document
    const emailScoreFromAttachment = attachRes?.data?.email_risk_score ?? 0;

    // website score
    let webScore = 0;
    if (webRes?.success && webRes.data) {
      const d = webRes.data;
      if (d.final_score != null)     webScore = d.final_score / 100;
      else if (d.risk_score != null) webScore = d.risk_score;
    }

    const websiteSuspicious =
      webRes?.data?.typosquatting?.is_suspicious === true ||
      (webRes?.data?.final_risk === "HIGH" && webRes?.data?.score > 60);

    const extractedDomains = [];
    if (websiteSuspicious) {
      const d = webRes?.data?.domain;
      if (d) extractedDomains.push(d);
    }

    // store results in context
    ctx.setWebsiteResult(webRes?.data || null);
    ctx.setAttachmentResult(attachRes?.data || null);
    ctx.setAudioResult(null);

    // set email result from attachment extraction so analysis page can show it
    ctx.setEmailResult(
      attachRes?.data?.email_risk_score != null ? {
        risk_score:      attachRes.data.email_risk_score,
        label:           attachRes.data.email_label,
        signals:         attachRes.data.email_signals   || {},
        flagged_phrases: attachRes.data.email_flagged   || [],
        source:          "extracted_from_attachment",
      } : null
    );

    // score fusion
    updateProgress("score", "running");
    try {
      const scoreRes = await analyzeScore({
        incident_id:      id,
        account_id:       ctx.accountId,
        email_score:      emailScoreFromAttachment,
        website_score:    webScore,
        attachment_score: attachScore,
        audio_score:      0,
        domains:          extractedDomains,
        ips:              [],
      });
      updateProgress("score", "done");

      if (scoreRes?.success && scoreRes.data) {
        ctx.setScoreResult(scoreRes.data);
        if (scoreRes.data.oob_triggered) ctx.setOobTriggered(true);

        analyzeExplain(id, scoreRes.data)
          .then((r) => {
            if (r?.success && r.data?.explanation) ctx.setExplanation(r.data.explanation);
          })
          .catch(() => {});
      }
    } catch (e) {
      console.error("Score failed:", e);
      updateProgress("score", "done");
    }

    // graph
    updateProgress("graph", "running");
    try {
      const graphRes = await getGraph();
      if (graphRes?.success && graphRes.data) ctx.setGraphData(graphRes.data);
    } catch (e) {
      console.warn("Graph fetch failed:", e);
    }
    updateProgress("graph", "done");

    ctx.setAnalyzing(false);
    router.push("/analysis");
  }

  const isRunning   = ctx.analyzing;
  const anyProgress = Object.values(layerProgress).some((s) => s !== "idle");

  return (
    <>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1.5 h-5 rounded-full bg-accent" />
          <h2 className="text-xl font-semibold tracking-tight">Attack Ingestion</h2>
        </div>
        <p className="text-sm text-slate-500 ml-5">
          Submit suspicious signals for unified campaign analysis
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        <div className="glass-card p-5">
          <SectionHeader icon="🌐" label="Website Analysis" />
          <Field
            label="Suspicious URL"
            value={url}
            onChange={setUrl}
            placeholder="https://suspicious-domain.com/login"
          />
        </div>

        <div className="glass-card p-5">
          <SectionHeader icon="📎" label="Attachment Analysis" />
          <p className="text-[11px] text-slate-600 mb-3">
            Upload email screenshot, PDF, or document — email content will be extracted automatically
          </p>
          <DropZone
            accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
            types="PDF, PNG, JPG, DOC"
            file={attachmentFile}
            setFile={setAttachmentFile}
            dragOver={fileDragOver}
            setDragOver={setFileDragOver}
            icon={
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="12" y1="18" x2="12" y2="12"/>
                <line x1="9"  y1="15" x2="12" y2="12"/>
                <line x1="15" y1="15" x2="12" y2="12"/>
              </svg>
            }
          />
        </div>
      </div>

      {anyProgress && (
        <div className="glass-card p-4 mb-5 animate-fade-in">
          <div className="flex items-center gap-4 flex-wrap">
            {["website", "attachment", "score", "graph"].map((layer) => {
              const st = layerProgress[layer];
              return (
                <div key={layer} className="flex items-center gap-2 text-[11px]">
                  {st === "running" && <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />}
                  {st === "done"    && <span className="w-2 h-2 rounded-full bg-emerald-500" />}
                  {st === "waiting" && <span className="w-2 h-2 rounded-full bg-slate-700" />}
                  {st === "skipped" && <span className="w-2 h-2 rounded-full bg-slate-800" />}
                  {st === "idle"    && <span className="w-2 h-2 rounded-full bg-slate-800" />}
                  <span className={`uppercase tracking-wide font-medium ${
                    st === "done" ? "text-emerald-500" : st === "running" ? "text-accent" : "text-slate-600"
                  }`}>
                    {layer}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex items-end gap-4 pt-5 border-t border-white/[0.04]">
        <div>
          <label className="block text-[10px] font-medium text-slate-600 uppercase tracking-widest mb-1">
            Account ID
          </label>
          <input
            type="text"
            value={ctx.accountId}
            onChange={(e) => ctx.setAccountId(e.target.value)}
            className="bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 w-48 focus:outline-none focus:border-accent/40 font-mono transition-colors"
          />
        </div>
        <div className="mr-auto">
          <label className="block text-[10px] font-medium text-slate-600 uppercase tracking-widest mb-1">
            Incident ID
          </label>
          <input
            type="text"
            value={ctx.incidentId}
            onChange={(e) => ctx.setIncidentId(e.target.value)}
            className="bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 w-48 focus:outline-none focus:border-accent/40 font-mono transition-colors"
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={isRunning}
          className={`ml-auto bg-accent hover:bg-accent-light text-white px-10 py-3.5 rounded-xl text-sm font-semibold transition-all disabled:cursor-not-allowed ${
            isRunning ? "btn-analyzing opacity-90" : "hover:shadow-lg hover:shadow-accent/20"
          }`}
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Analyzing...
            </span>
          ) : (
            "Run Analysis"
          )}
        </button>
      </div>
    </>
  );
}

function SectionHeader({ icon, label }) {
  return (
    <div className="flex items-center gap-2.5 mb-4">
      <span className="text-base">{icon}</span>
      <h3 className="text-[13px] font-semibold text-slate-300">{label}</h3>
    </div>
  );
}

function Field({ label, value, onChange, placeholder }) {
  return (
    <div className="mt-2 first:mt-0">
      <label className="block text-[10px] font-medium text-slate-600 uppercase tracking-widest mb-1">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-700 focus:outline-none focus:border-accent/40 transition-colors"
      />
    </div>
  );
}

function DropZone({ accept, types, file, setFile, dragOver, setDragOver, icon }) {
  const inputRef = useRef(null);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) setFile(f);
  }

  return (
    <div
      className={`drop-zone rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer min-h-[140px] transition-all ${dragOver ? "drag-over" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={(e) => setFile(e.target.files[0] || null)}
        className="hidden"
      />
      {file ? (
        <div className="animate-fade-in">
          <div className="w-10 h-10 mx-auto mb-2 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <p className="text-sm text-slate-300 font-medium">{file.name}</p>
          <p className="text-[10px] text-slate-600 mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
          <button
            onClick={(e) => { e.stopPropagation(); setFile(null); }}
            className="text-[10px] text-red-400/70 hover:text-red-400 mt-2 transition-colors"
          >
            Remove
          </button>
        </div>
      ) : (
        <>
          <div className="mb-3 opacity-40">{icon}</div>
          <p className="text-sm text-slate-500 mb-1">
            Drag & drop or <span className="text-accent font-medium">browse</span>
          </p>
          <p className="text-[10px] text-slate-700">Accepted: {types}</p>
        </>
      )}
    </div>
  );
}