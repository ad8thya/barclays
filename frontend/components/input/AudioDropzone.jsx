"use client";

import { useRef, useState } from "react";
import { Mic } from "lucide-react";

export default function AudioDropzone({ file, setFile }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) setFile(f);
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
          <Mic size={16} className="text-accent" strokeWidth={1.5} />
        </div>
        <h3 className="text-[13px] font-medium text-slate-300 uppercase tracking-[0.06em]">
          Audio / Deepfake Detection
        </h3>
      </div>

      <div
        className={`drop-zone rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer min-h-[140px] transition-all ${
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
          accept=".wav,.mp3,.m4a"
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="hidden"
        />

        {file ? (
          <div className="animate-fade-in">
            <div className="w-10 h-10 mx-auto mb-2 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
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
            <Mic size={28} className="mb-3 text-slate-700" strokeWidth={1.2} />
            <p className="text-sm text-slate-500 mb-1">
              Drag & drop or <span className="text-accent font-medium">browse</span>
            </p>
            <p className="text-[10px] text-slate-700">Accepted: WAV, MP3, M4A</p>
          </>
        )}
      </div>
    </div>
  );
}
