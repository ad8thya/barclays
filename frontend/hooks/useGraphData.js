"use client";

import { useMemo } from "react";
import { useAnalysisContext } from "@/context/AnalysisContext";

export function useGraphData() {
  const { graphData } = useAnalysisContext();

  return useMemo(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
      return { nodes: [], edges: [], isEmpty: true };
    }

    const nodes = graphData.nodes.map((n) => ({
      id: n.id,
      type: n.type || "incident",
      label: n.label || n.id,
      risk_score: n.risk_score || 0,
      campaign_id: n.campaign_id || null,
      timestamp: n.timestamp || null,
    }));

    const edges = (graphData.edges || []).map((e) => ({
      source: e.source,
      target: e.target,
      relation: e.relation || "shared_signal",
      shared: e.shared || [],
    }));

    return { nodes, edges, isEmpty: false };
  }, [graphData]);
}
