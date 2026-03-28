"use client";

import { useState } from "react";

export default function UrlInput({ url, setUrl }) {
  const [error, setError] = useState(false);

  function validate() {
    if (!url) { setError(false); return; }
    try {
      new URL(url);
      setError(false);
    } catch {
      setError(true);
    }
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
        </div>
        <h3 className="text-[13px] font-medium text-slate-300 uppercase tracking-[0.06em]">
          Website Analysis
        </h3>
      </div>

      <label className="block text-[11px] font-medium text-slate-600 uppercase tracking-[0.08em] mb-1.5">
        Suspicious URL
      </label>
      <input
        type="text"
        value={url}
        onChange={(e) => { setUrl(e.target.value); setError(false); }}
        onBlur={validate}
        placeholder="https://suspicious-domain.com/login"
        className={`w-full bg-white/[0.02] border rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-700 focus:outline-none transition-colors ${
          error ? "border-red-500/60 focus:border-red-500/80" : "border-white/[0.06] focus:border-accent/40"
        }`}
      />
      {error && (
        <p className="text-[11px] text-red-400 mt-1.5">Please enter a valid URL</p>
      )}
    </div>
  );
}
