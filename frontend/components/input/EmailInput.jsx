"use client";

import { useState } from "react";

export default function EmailInput({ subject, setSubject, body, setBody, sender, setSender }) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.5">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <polyline points="22,4 12,13 2,4" />
          </svg>
        </div>
        <h3 className="text-[13px] font-medium text-slate-300 uppercase tracking-[0.06em]">
          Email Analysis
        </h3>
      </div>

      {/* Subject */}
      <div className="mb-3">
        <label className="block text-[11px] font-medium text-slate-600 uppercase tracking-[0.08em] mb-1.5">
          Subject
        </label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Email subject line"
          className="w-full bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-700 focus:outline-none focus:border-accent/40 transition-colors"
        />
      </div>

      {/* Sender */}
      <div className="mb-3">
        <label className="block text-[11px] font-medium text-slate-600 uppercase tracking-[0.08em] mb-1.5">
          Sender
        </label>
        <input
          type="text"
          value={sender}
          onChange={(e) => setSender(e.target.value)}
          placeholder="sender@domain.com"
          className="w-full bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-700 focus:outline-none focus:border-accent/40 transition-colors"
        />
      </div>

      {/* Body */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <label className="text-[11px] font-medium text-slate-600 uppercase tracking-[0.08em]">
            Body
          </label>
          <span className="text-[10px] tabular-nums text-slate-700">{body.length} chars</span>
        </div>
        <textarea
          rows={8}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Paste the full email body here..."
          className="w-full bg-white/[0.02] border border-white/[0.06] rounded-lg px-3.5 py-3 text-sm text-slate-200 placeholder:text-slate-700 focus:outline-none focus:border-accent/40 resize-none transition-colors font-mono text-[13px] leading-relaxed"
        />
      </div>
    </div>
  );
}
