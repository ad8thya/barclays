"use client";

import { useEffect, useState } from "react";
import { useAnalysisContext } from "@/context/AnalysisContext";
import FraudGraph from "@/components/graph/FraudGraph";
import CampaignSummary from "@/components/graph/CampaignSummary";
import { getGraph } from "@/lib/api";

export default function GraphPage() {
  const { graphData, setGraphData, scoreResult } = useAnalysisContext();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchGraph() {
      setLoading(true);
      setError(null);
      try {
        const res = await getGraph();
        if (res.success && res.data) {
          setGraphData(res.data);
        } else {
          setError("Graph endpoint returned no data");
        }
      } catch {
        setError("Could not reach backend — is it running on port 8000?");
      } finally {
        setLoading(false);
      }
    }
    fetchGraph();
  }, []);

  return (
    <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-lg font-medium tracking-tight text-slate-100">
          Graph Intelligence
        </h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Campaign correlation across incidents — shared infrastructure and signals
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="glass-card p-5 mb-5 flex items-center gap-3 animate-fade-in">
          <span className="w-3 h-3 rounded-full bg-accent animate-pulse" />
          <span className="text-sm text-slate-400">Fetching graph from backend...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card p-4 mb-5 border border-red-500/30 animate-fade-in">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Two-panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5" style={{ minHeight: 480 }}>
        <FraudGraph graphData={graphData} />
        <CampaignSummary graphData={graphData} scoreResult={scoreResult} />
      </div>
    </div>
  );
}
