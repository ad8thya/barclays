"use client";

import { useState } from "react";
import * as SwitchPrimitive from "@radix-ui/react-switch";

/*
  SignalTag — two modes:

  1. Static (default): just a badge, no toggle. Used for read-only signal lists.
     <SignalTag label="spoofed sender" danger />

  2. Toggleable: analyst can acknowledge/suppress a signal.
     <SignalTag label="urgency language" danger toggleable onToggle={fn} />
*/

export default function SignalTag({
  label,
  danger   = false,
  info     = false,
  toggleable = false,
  defaultActive = true,
  onToggle,
}) {
  const [active, setActive] = useState(defaultActive);

  const handleToggle = (next) => {
    setActive(next);
    onToggle?.(next);
  };

  /* ── color tokens ── */
  const colors = danger
    ? {
        border:     active ? "#451a1a" : "#1e2530",
        bg:         active ? "#110a0a" : "#0f1117",
        dot:        "#ef4444",
        text:       active ? "#f87171" : "#334155",
        switchOn:   "#ef4444",
      }
    : info
    ? {
        border:     active ? "#1e3a5f" : "#1e2530",
        bg:         active ? "#0a1120" : "#0f1117",
        dot:        "#3b82f6",
        text:       active ? "#60a5fa" : "#334155",
        switchOn:   "#3b82f6",
      }
    : {
        border:     active ? "#1e3a5f" : "#1e2530",
        bg:         active ? "#0a1120" : "#0f1117",
        dot:        "#3b82f6",
        text:       active ? "#60a5fa" : "#334155",
        switchOn:   "#3b82f6",
      };

  if (!toggleable) {
    /* ── Static badge ── */
    return (
      <span style={{
        display:        "inline-flex",
        alignItems:     "center",
        gap:            5,
        padding:        "2px 7px",
        border:         `1px solid ${colors.border}`,
        borderRadius:   3,
        background:     colors.bg,
        fontFamily:     "monospace",
        fontSize:       10,
        fontWeight:     500,
        color:          colors.text,
        textTransform:  "uppercase",
        letterSpacing:  "0.06em",
        whiteSpace:     "nowrap",
        marginRight:    4,
        marginBottom:   4,
      }}>
        {(danger || info) && (
          <span style={{
            width: 5, height: 5,
            borderRadius: "50%",
            background: colors.dot,
            flexShrink: 0,
          }} />
        )}
        {label}
      </span>
    );
  }

  /* ── Toggleable tag ── */
  return (
    <span style={{
      display:      "inline-flex",
      alignItems:   "center",
      gap:          7,
      padding:      "3px 8px 3px 7px",
      border:       `1px solid ${colors.border}`,
      borderRadius: 3,
      background:   colors.bg,
      fontFamily:   "monospace",
      fontSize:     10,
      color:        colors.text,
      textTransform:"uppercase",
      letterSpacing:"0.06em",
      whiteSpace:   "nowrap",
      marginRight:  4,
      marginBottom: 4,
      transition:   "background 150ms ease, border-color 150ms ease",
      opacity:      active ? 1 : 0.45,
    }}>
      {/* dot */}
      <span style={{
        width: 5, height: 5,
        borderRadius: "50%",
        background: active ? colors.dot : "#334155",
        flexShrink: 0,
        transition: "background 150ms ease",
      }} />

      {/* label */}
      <span style={{ transition: "color 150ms ease" }}>{label}</span>

      {/* Radix switch — restyled to fit */}
      <SwitchPrimitive.Root
        checked={active}
        onCheckedChange={handleToggle}
        style={{
          display:        "inline-flex",
          alignItems:     "center",
          width:          24,
          height:         13,
          borderRadius:   7,
          border:         `1px solid ${active ? colors.switchOn : "#1e2530"}`,
          background:     active ? colors.switchOn : "#1e2530",
          cursor:         "pointer",
          flexShrink:     0,
          outline:        "none",
          transition:     "background 150ms ease, border-color 150ms ease",
          padding:        0,
          position:       "relative",
        }}
        aria-label={`Toggle signal: ${label}`}
      >
        <SwitchPrimitive.Thumb style={{
          display:      "block",
          width:        9,
          height:       9,
          borderRadius: "50%",
          background:   "#e2e8f0",
          transform:    active ? "translateX(12px)" : "translateX(2px)",
          transition:   "transform 150ms ease",
          flexShrink:   0,
        }} />
      </SwitchPrimitive.Root>
    </span>
  );
}