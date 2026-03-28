/*
 * API service — all backend calls in one place.
 * Edit BASE_URL and endpoint paths here when swapping environments.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ENDPOINTS = {
  email: "/analyze/email",
  website: "/analyze/website",
  attachment: "/analyze/attachment",
  audio: "/analyze/audio",
  score: "/analyze/score",
  explain: "/analyze/explain",
  graphAll: "/graph/all",
};

function url(key) {
  return BASE_URL + ENDPOINTS[key];
}

// ---- Email ----
export async function analyzeEmail(incidentId, subject, body, sender) {
  const res = await fetch(url("email"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ incident_id: incidentId, subject, body, sender }),
  });
  return res.json();
}

// ---- Website ----
export async function analyzeWebsite(incidentId, targetUrl) {
  const res = await fetch(url("website"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ incident_id: incidentId, url: targetUrl }),
  });
  return res.json();
}

// ---- Attachment (file upload) ----
export async function analyzeAttachment(incidentId, file) {
  const form = new FormData();
  form.append("incident_id", incidentId);
  form.append("file", file);
  const res = await fetch(url("attachment"), { method: "POST", body: form });
  return res.json();
}

// ---- Audio (file upload) ----
export async function analyzeAudio(incidentId, file) {
  const form = new FormData();
  form.append("incident_id", incidentId);
  form.append("file", file);
  const res = await fetch(url("audio"), { method: "POST", body: form });
  return res.json();
}

// ---- Score (fused FRS) ----
export async function analyzeScore(payload) {
  const res = await fetch(url("score"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

// ---- Explain ----
export async function analyzeExplain(incidentId, scoreData) {
  const res = await fetch(url("explain"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ incident_id: incidentId, ...scoreData }),
  });
  return res.json();
}

// ---- Graph (all nodes + edges) ----
export async function getGraph() {
  const res = await fetch(url("graphAll"));
  return res.json();
}
