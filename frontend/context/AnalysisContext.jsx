"use client";

import { createContext, useContext, useState } from "react";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  // Input state
  const [incidentId, setIncidentId] = useState("INC-2042");
  const [accountId, setAccountId] = useState("acct_4821");

  // Layer results — each is the raw API response .data
  const [emailResult, setEmailResult] = useState(null);
  const [websiteResult, setWebsiteResult] = useState(null);
  const [attachmentResult, setAttachmentResult] = useState(null);
  const [audioResult, setAudioResult] = useState(null);

  // Score result — the full /analyze/score .data
  const [scoreResult, setScoreResult] = useState(null);

  // Graph data — the full /graph/all .data
  const [graphData, setGraphData] = useState(null);

  // Explanation text
  const [explanation, setExplanation] = useState("");

  // OOB
  const [oobTriggered, setOobTriggered] = useState(false);

  // Loading
  const [analyzing, setAnalyzing] = useState(false);

  return (
    <AnalysisContext.Provider
      value={{
        incidentId, setIncidentId,
        accountId, setAccountId,
        emailResult, setEmailResult,
        websiteResult, setWebsiteResult,
        attachmentResult, setAttachmentResult,
        audioResult, setAudioResult,
        scoreResult, setScoreResult,
        graphData, setGraphData,
        explanation, setExplanation,
        oobTriggered, setOobTriggered,
        analyzing, setAnalyzing,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
}
