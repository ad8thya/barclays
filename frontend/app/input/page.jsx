"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalysisContext } from "@/context/AnalysisContext";
import { useAnalysis } from "@/hooks/useAnalysis";
import EmailInput from "@/components/input/EmailInput";
import UrlInput from "@/components/input/UrlInput";
import FileDropzone from "@/components/input/FileDropzone";
import AudioDropzone from "@/components/input/AudioDropzone";
import StatusPill from "@/components/shared/StatusPill";
import { LiquidButton } from "@/components/ui/liquid-glass-button";

export default function InputPage() {
  const router = useRouter();
  const ctx = useAnalysisContext();
  const { runAnalysis, isLoading } = useAnalysis();

  const [sender, setSender] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [url, setUrl] = useState("");
  const [attachmentFile, setAttachmentFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);

  async function handleRun() {
    await runAnalysis({
      emailText: body,
      emailSubject: subject,
      emailSender: sender,
      url,
      file: attachmentFile,
      audio: audioFile,
    });
    router.push("/analysis");
  }

  const layers = [
    { name: "Email", status: ctx.layerResults?.email?.status || "pending" },
    { name: "Website", status: ctx.layerResults?.website?.status || "pending" },
    { name: "Attachment", status: ctx.layerResults?.attachment?.status || "pending" },
    { name: "Audio", status: ctx.layerResults?.audio?.status || "pending" },
  ];

  return (
    <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-1.5 h-5 rounded-full bg-accent" />
          <h2 className="text-xl font-medium tracking-tight text-slate-100">
            Attack Ingestion
          </h2>
        </div>
        <p className="text-sm text-slate-500 ml-5">
          Submit suspicious signals for unified campaign analysis
        </p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        {/* Left column */}
        <div className="space-y-5">
          <EmailInput
            subject={subject} setSubject={setSubject}
            body={body} setBody={setBody}
            sender={sender} setSender={setSender}
          />
          <UrlInput url={url} setUrl={setUrl} />
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <FileDropzone file={attachmentFile} setFile={setAttachmentFile} />
          <AudioDropzone file={audioFile} setFile={setAudioFile} />
        </div>
      </div>

      {/* Layer progress */}
      {ctx.analysisStatus === "running" && (
        <div className="glass-card p-4 mb-5 animate-fade-in">
          <div className="space-y-3">
            {layers.map(({ name, status }) => (
              <div key={name} className="flex items-center gap-4">
                <span className="text-[11px] uppercase tracking-[0.08em] text-slate-500 w-20 font-medium">
                  {name}
                </span>
                <div className="flex-1 h-1 rounded-full bg-white/[0.04] overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      status === "complete" ? "w-full bg-emerald-500" :
                      status === "analysing" ? "w-3/4 bg-accent animate-pulse" :
                      status === "error" ? "w-full bg-red-500" :
                      "w-0"
                    }`}
                  />
                </div>
                <StatusPill status={status} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-end gap-4 pt-5 border-t border-white/[0.04]">
        <div>
          <label className="block text-[11px] font-medium text-slate-600 uppercase tracking-[0.08em] mb-1">
            Incident ID
          </label>
          <input
            type="text"
            value={ctx.incidentId}
            onChange={(e) => ctx.setIncidentId(e.target.value)}
            className="bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 w-40 focus:outline-none focus:border-accent/40 font-mono transition-colors"
          />
        </div>
        <div>
          <label className="block text-[11px] font-medium text-slate-600 uppercase tracking-[0.08em] mb-1">
            Account ID
          </label>
          <input
            type="text"
            value={ctx.accountId}
            onChange={(e) => ctx.setAccountId(e.target.value)}
            className="bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 w-40 focus:outline-none focus:border-accent/40 font-mono transition-colors"
          />
        </div>
        <div className="ml-auto">
          <LiquidButton
            onClick={handleRun}
            disabled={isLoading}
            className={isLoading ? "btn-analyzing" : ""}
            size="lg"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing...
              </span>
            ) : (
              "Run Analysis"
            )}
          </LiquidButton>
        </div>
      </div>
    </div>
  );
}
