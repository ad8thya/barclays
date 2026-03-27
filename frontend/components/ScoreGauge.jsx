"use client";

import { useEffect, useState } from "react";

const TICKS = [0, 25, 50, 70, 80, 100];
const CX = 150, CY = 140, R = 110;
const START_DEG = 240; // 240° arc span
const START_ANGLE = (180 + (360 - START_DEG) / 2); // degrees from 3 o'clock

function degToRad(d) { return (d * Math.PI) / 180; }

function polarToCart(cx, cy, r, deg) {
  const rad = degToRad(deg);
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx, cy, r, startDeg, endDeg) {
  const s = polarToCart(cx, cy, r, startDeg);
  const e = polarToCart(cx, cy, r, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

function valToDeg(val) {
  return START_ANGLE + (val / 100) * START_DEG;
}

export default function ScoreGauge({ score = 0 }) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const target = Math.max(0, Math.min(1, score)) * 100;
    let current = 0;
    const step = target / 40;
    const interval = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(interval);
      }
      setAnimatedScore(current);
    }, 20);
    return () => clearInterval(interval);
  }, [score]);

  const scoreDeg = valToDeg(animatedScore);
  const endDeg = START_ANGLE + START_DEG;
  const needlePoint = polarToCart(CX, CY, R - 20, scoreDeg);

  const color = animatedScore >= 80 ? "#ef4444" : animatedScore >= 70 ? "#f59e0b" : "#10b981";
  const verdict = score > 0.8 ? "OOB TRIGGERED" : score > 0.7 ? "SUSPICIOUS" : "CLEAR";
  const verdictColor = score > 0.8 ? "text-red-400" : score > 0.7 ? "text-amber-400" : "text-emerald-400";
  const glowColor = score > 0.8 ? "rgba(239,68,68,0.3)" : score > 0.7 ? "rgba(245,158,11,0.2)" : "rgba(16,185,129,0.2)";

  return (
    <div className="glass-card p-8 flex flex-col items-center">
      <svg viewBox="0 0 300 200" className="w-full max-w-[280px]">
        {/* Background arc */}
        <path d={describeArc(CX, CY, R, START_ANGLE, endDeg)} fill="none" stroke="#1e293b" strokeWidth="14" strokeLinecap="round" />

        {/* Color zones: green 0-70, amber 70-80, red 80-100 */}
        <path d={describeArc(CX, CY, R, START_ANGLE, valToDeg(70))} fill="none" stroke="#10b981" strokeWidth="14" strokeLinecap="round" opacity="0.15" />
        <path d={describeArc(CX, CY, R, valToDeg(70), valToDeg(80))} fill="none" stroke="#f59e0b" strokeWidth="14" opacity="0.15" />
        <path d={describeArc(CX, CY, R, valToDeg(80), endDeg)} fill="none" stroke="#ef4444" strokeWidth="14" strokeLinecap="round" opacity="0.15" />

        {/* Active score arc */}
        {animatedScore > 0 && (
          <path
            d={describeArc(CX, CY, R, START_ANGLE, scoreDeg)}
            fill="none"
            stroke={color}
            strokeWidth="14"
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 8px ${glowColor})` }}
          />
        )}

        {/* Tick marks + labels */}
        {TICKS.map((val) => {
          const deg = valToDeg(val);
          const outer = polarToCart(CX, CY, R + 8, deg);
          const inner = polarToCart(CX, CY, R - 20, deg);
          const labelPt = polarToCart(CX, CY, R + 22, deg);
          return (
            <g key={val}>
              <line x1={outer.x} y1={outer.y} x2={inner.x} y2={inner.y} stroke="#334155" strokeWidth="1.5" />
              <text x={labelPt.x} y={labelPt.y} textAnchor="middle" dominantBaseline="middle" fill="#475569" fontSize="9" fontFamily="monospace" fontWeight="500">
                {val}
              </text>
            </g>
          );
        })}

        {/* Needle */}
        <line x1={CX} y1={CY} x2={needlePoint.x} y2={needlePoint.y} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={CX} cy={CY} r="5" fill={color} opacity="0.8" />
        <circle cx={CX} cy={CY} r="2.5" fill="#0a0f1e" />
      </svg>

      {/* Score value */}
      <div className="mt-2 text-center">
        <div className="text-4xl font-bold tabular-nums tracking-tight" style={{ color }}>
          {(score * 100).toFixed(0)}
          <span className="text-lg text-slate-600 font-medium ml-1">%</span>
        </div>
        <div className={`text-xs font-bold uppercase tracking-[0.2em] mt-1 ${verdictColor}`}
          style={score > 0.8 ? { textShadow: `0 0 20px ${glowColor}` } : {}}>
          {verdict}
        </div>
      </div>
    </div>
  );
}
