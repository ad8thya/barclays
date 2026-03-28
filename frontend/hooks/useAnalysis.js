"use client";

import { useState, useCallback } from "react";
import { useAnalysisContext } from "@/context/AnalysisContext";
import {
  analyzeEmail,
  analyzeWebsite,
  analyzeAttachment,
  analyzeAudio,
  analyzeScore,
  analyzeExplain,
  getGraph,
} from "@/lib/api";

export function useAnalysis() {
  const ctx = useAnalysisContext();
  const [isLoading, setIsLoading] = useState(false);

  const runAnalysis = useCallback(
    async ({ emailText, emailSubject, emailSender, url, file, audio }) => {
      setIsLoading(true);
      ctx.setAnalysisStatus("running");
      ctx.setLayerResults({});

      const id = ctx.incidentId;

      // Mark all layers as analysing
      const layerStatus = { email: "analysing", website: "analysing", attachment: file ? "analysing" : "pending", audio: audio ? "analysing" : "pending" };
      ctx.setLayerResults(
        Object.fromEntries(
          Object.entries(layerStatus).map(([k, v]) => [k, { status: v }])
        )
      );

      // Fire all layers in parallel
      const results = await Promise.allSettled([
        analyzeEmail(id, emailSubject || "", emailText || "", emailSender || ""),
        analyzeWebsite(id, url || ""),
        file ? analyzeAttachment(id, file) : Promise.resolve(null),
        audio ? analyzeAudio(id, audio) : Promise.resolve(null),
      ]);

      const emailRes = results[0].status === "fulfilled" ? results[0].value : null;
      const webRes = results[1].status === "fulfilled" ? results[1].value : null;
      const attachRes = results[2].status === "fulfilled" ? results[2].value : null;
      const audioRes = results[3].status === "fulfilled" ? results[3].value : null;

      // Update layer results
      ctx.updateLayerResult("email", {
        status: emailRes?.success ? "complete" : emailRes ? "error" : "complete",
        data: emailRes?.data || null,
        error: emailRes?.error || null,
      });
      ctx.updateLayerResult("website", {
        status: webRes?.success ? "complete" : webRes ? "error" : "complete",
        data: webRes?.data || null,
        error: webRes?.error || null,
      });
      ctx.updateLayerResult("attachment", {
        status: attachRes?.success ? "complete" : !file ? "pending" : attachRes ? "error" : "complete",
        data: attachRes?.data || null,
        error: attachRes?.error || null,
      });
      ctx.updateLayerResult("audio", {
        status: audioRes?.success ? "complete" : !audio ? "pending" : audioRes ? "error" : "complete",
        data: audioRes?.data || null,
        error: audioRes?.error || null,
      });

      // Extract scores
      const emailScore = emailRes?.success ? (emailRes.data?.risk_score || 0) : 0;
      let webScore = 0;
      if (webRes?.success && webRes.data) {
        const d = webRes.data;
        if (d.final_score != null) webScore = d.final_score / 100;
        else if (d.risk_score != null) webScore = d.risk_score;
      } else if (webRes?.final_score != null) {
        webScore = webRes.final_score / 100;
      }
      const attachScore = attachRes?.success ? (attachRes.data?.risk_score || 0) : 0;
      const audioScore = audioRes?.success ? (audioRes.data?.risk_score || 0) : 0;

      // Extract domains
      const domains = [];
      const domainFromWeb = webRes?.data?.domain || webRes?.domain;
      if (domainFromWeb) domains.push(domainFromWeb);

      // Score fusion
      try {
        const scoreRes = await analyzeScore({
          incident_id: id,
          account_id: ctx.accountId,
          email_score: emailScore,
          website_score: webScore,
          attachment_score: attachScore,
          audio_score: audioScore,
          domains: domains,
          ips: [],
        });

        if (scoreRes?.success && scoreRes.data) {
          ctx.setScoreResult(scoreRes.data);
          ctx.setFrs(scoreRes.data.final_risk_score || 0);
          ctx.setVerdict(scoreRes.data.verdict || "CLEAR");
          if (scoreRes.data.oob_triggered) {
            ctx.setOobTriggered(true);
          }

          // Get explanation (fire and forget, will update context when ready)
          analyzeExplain(id, scoreRes.data)
            .then((r) => {
              if (r?.success && r.data?.explanation) {
                ctx.setExplanation(r.data.explanation);
              }
            })
            .catch(() => {});
        }
      } catch (e) {
        console.error("Score fusion failed:", e);
      }

      // Fetch graph
      try {
        const graphRes = await getGraph();
        if (graphRes?.success && graphRes.data) {
          ctx.setGraphData(graphRes.data);
        }
      } catch (e) {
        console.warn("Graph fetch failed:", e);
      }

      ctx.setAnalysisStatus("complete");
      setIsLoading(false);
    },
    [ctx]
  );

  return { runAnalysis, isLoading };
}
