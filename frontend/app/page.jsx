"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAnalysis } from "@/context/AnalysisContext";
import {
  analyzeEmail,
  analyzeWebsite,
  analyzeAttachment,
  analyzeAudio,
  analyzeScore,
  analyzeExplain,
  getGraph,
} from "@/lib/api";

export default function InputPage() {
  const router = useRouter();
  const ctx = useAnalysis();

  const [sender, setSender] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [url, setUrl] = useState("");
  const [attachmentFile, setAttachmentFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);

  // Drag state
  const [fileDragOver, setFileDragOver] = useState(false);
  const [audioDragOver, setAudioDragOver] = useState(false);

  // Progress per layer
  const [layerProgress, setLayerProgress] = useState({
    email: "idle", website: "idle", attachment: "idle", audio: "idle",
    score: "idle", graph: "idle",
  });

  function updateProgress(layer, status) {
    setLayerProgress((prev) => ({ ...prev, [layer]: status }));
  }

  async function handleAnalyze() {
    ctx.setAnalyzing(true);
    setLayerProgress({
      email: "running", website: "running",
      attachment: attachmentFile ? "running" : "skipped",
      audio: audioFile ? "running" : "skipped",
      score: "waiting", graph: "waiting",
    });

    const id = ctx.incidentId;

    // Run all 4 layers in parallel
    const results = await Promise.allSettled([
      analyzeEmail(id, subject, body, sender).then((r) => { updateProgress("email", "done"); return r; }),
      analyzeWebsite(id, url).then((r) => { updateProgress("website", "done"); return r; }),
      attachmentFile
        ? analyzeAttachment(id, attachmentFile).then((r) => { updateProgress("attachment", "done"); return r; })
        : Promise.resolve(null),
      audioFile
        ? analyzeAudio(id, audioFile).then((r) => { updateProgress("audio", "done"); return r; })
        : Promise.resolve(null),
    ]);

    const emailRes = results[0].status === "fulfilled" ? results[0].value : null;
    const webRes = results[1].status === "fulfilled" ? results[1].value : null;
    const attachRes = results[2].status === "fulfilled" ? results[2].value : null;
    const audioRes = results[3].status === "fulfilled" ? results[3].value : null;

    const emailScore = emailRes?.success ? (emailRes.data?.risk_score || 0) : 0;


    let webScore = 0;
  if (webRes?.success && webRes.data) {
    const wd = webRes.data;
    webScore = wd.final_score != null
      ? wd.final_score / 100
      : (wd.risk_score || 0);
  }
    const attachScore = attachRes?.success ? (attachRes.data?.risk_score || 0) : 0;
    const audioScore = audioRes?.success ? (audioRes.data?.risk_score || 0) : 0;

    ctx.setEmailResult(emailRes?.data || null);
    ctx.setWebsiteResult(webRes?.data || webRes || null);
    ctx.setAttachmentResult(attachRes?.data || null);
    ctx.setAudioResult(audioRes?.data || null);

    // Score fusion
    updateProgress("score", "running");
    try {
      const scoreRes = await analyzeScore({
        incident_id: id,
        account_id: ctx.accountId,
        email_score: emailScore,
        website_score: webScore,
        attachment_score: attachScore,
        audio_score: audioScore,
        domains: ["barcl4ys-secure.com"],
        ips: ["185.220.101.45"],
      });
      updateProgress("score", "done");

      if (scoreRes.success && scoreRes.data) {
        ctx.setScoreResult(scoreRes.data);
        if (scoreRes.data.oob_triggered) {
          ctx.setOobTriggered(true);
        }
        try {
          const explainRes = await analyzeExplain(id, scoreRes.data);
          if (explainRes?.success && explainRes.data) {
            ctx.setExplanation(explainRes.data.explanation || "");
          }
        } catch (e) { console.warn("Explain failed:", e); }
      }
    } catch (e) { console.error("Score failed:", e); }

    // Graph
    updateProgress("graph", "running");
    try {
      const graphRes = await getGraph();
      if (graphRes.success && graphRes.data) {
        ctx.setGraphData(graphRes.data);
      }
    } catch (e) { console.warn("Graph fetch failed:", e); }
    updateProgress("graph", "done");

    ctx.setAnalyzing(false);
    router.push("/analysis");
  }

  const isRunning = ctx.analyzing;
  const anyProgress = Object.values(layerProgress).some((s) => s !== "idle");

  return (
    <>
      {/* Page header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1.5 h-5 rounded-full bg-accent" />
          <h2 className="text-xl font-semibold tracking-tight">Attack Ingestion</h2>
        </div>
        <p className="text-sm text-slate-500 ml-5">
          Submit suspicious signals for unified campaign analysis
        </p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        {/* LEFT — Email & URL */}
        <div className="space-y-5">
          {/* Email body */}
          <div className="glass-card p-5">
            <SectionHeader icon="✉" label="Email Analysis" />
            <div className="grid grid-cols-2 gap-3 mb-3">
              <Field label="Incident ID" value={ctx.incidentId} onChange={ctx.setIncidentId} />
              <Field label="Sender" value={sender} onChange={setSender} placeholder="sender@domain.com" />
            </div>
            <Field label="Subject" value={subject} onChange={setSubject} placeholder="Email subject line" />
            <div className="mt-3">
              <div className="flex justify-between items-center mb-1">
                <label className="text-[10px] font-medium text-slate-600 uppercase tracking-widest">Body</label>
                <span className="text-[10px] tabular-nums text-slate-700">{body.length} chars</span>
              </div>
              <textarea
                rows={6}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Paste the full email body here..."
                className="w-full bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-3 text-sm text-slate-200 placeholder:text-slate-700 focus:outline-none focus:border-accent/40 resize-none transition-colors font-mono text-[13px] leading-relaxed"
              />
            </div>
          </div>

          {/* URL */}
          <div className="glass-card p-5">
            <SectionHeader icon="🌐" label="Website Analysis" />
            <Field label="Suspicious URL" value={url} onChange={setUrl} placeholder="https://suspicious-domain.com/login" />
          </div>
        </div>

        {/* RIGHT — File uploads */}
        <div className="space-y-5">
          {/* Attachment drop zone */}
          <div className="glass-card p-5">
            <SectionHeader icon="📎" label="Attachment Analysis" />
            <DropZone
              accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
              types="PDF, PNG, JPG, DOC"
              file={attachmentFile}
              setFile={setAttachmentFile}
              dragOver={fileDragOver}
              setDragOver={setFileDragOver}
              icon={
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="12" y2="12"/><line x1="15" y1="15" x2="12" y2="12"/>
                </svg>
              }
            />
          </div>

          {/* Audio drop zone */}
          <div className="glass-card p-5">
            <SectionHeader icon="🎙" label="Audio / Deepfake Detection" />
            <DropZone
              accept=".wav,.mp3,.ogg,.m4a"
              types="WAV, MP3, OGG, M4A"
              file={audioFile}
              setFile={setAudioFile}
              dragOver={audioDragOver}
              setDragOver={setAudioDragOver}
              icon={
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="1.5">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
              }
            />
          </div>
        </div>
      </div>

      {/* Progress indicators */}
      {anyProgress && (
        <div className="glass-card p-4 mb-5 animate-fade-in">
          <div className="flex items-center gap-4 flex-wrap">
            {["email", "website", "attachment", "audio", "score", "graph"].map((layer) => {
              const st = layerProgress[layer];
              return (
                <div key={layer} className="flex items-center gap-2 text-[11px]">
                  {st === "running" && <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />}
                  {st === "done" && <span className="w-2 h-2 rounded-full bg-emerald-500" />}
                  {st === "waiting" && <span className="w-2 h-2 rounded-full bg-slate-700" />}
                  {st === "skipped" && <span className="w-2 h-2 rounded-full bg-slate-800" />}
                  {st === "idle" && <span className="w-2 h-2 rounded-full bg-slate-800" />}
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

      {/* Action bar */}
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

/* ── Helpers ── */

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
      className={`drop-zone rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer min-h-[140px] transition-all ${
        dragOver ? "drag-over" : ""
      }`}
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
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
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
