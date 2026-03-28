"use client";

import { createContext, useContext, useState } from "react";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  const [layerResults, setLayerResults] = useState({});
  const [frs, setFrs] = useState(null);
  const [verdict, setVerdict] = useState(null);
  const [oobTriggered, setOobTriggered] = useState(false);
  const [explanation, setExplanation] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState("idle");
  const [scoreResult, setScoreResult] = useState(null);
  const [incidentId, setIncidentId] = useState("INC-2042");
  const [accountId, setAccountId] = useState("acct_4821");

  function updateLayerResult(layer, data) {
    setLayerResults((prev) => ({ ...prev, [layer]: data }));
  }

  function resetAnalysis() {
    setLayerResults({});
    setFrs(null);
    setVerdict(null);
    setOobTriggered(false);
    setExplanation(null);
    setGraphData(null);
    setAnalysisStatus("idle");
    setScoreResult(null);
  }

  return (
    <AnalysisContext.Provider
      value={{
        layerResults, setLayerResults, updateLayerResult,
        frs, setFrs,
        verdict, setVerdict,
        oobTriggered, setOobTriggered,
        explanation, setExplanation,
        graphData, setGraphData,
        analysisStatus, setAnalysisStatus,
        scoreResult, setScoreResult,
        incidentId, setIncidentId,
        accountId, setAccountId,
        resetAnalysis,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysisContext() {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysisContext must be used within AnalysisProvider");
  return ctx;
}
