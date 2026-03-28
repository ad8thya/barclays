export function formatScore(value) {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatFlag(str) {
  if (!str) return "";
  return str
    .replace(/^(keyword:|credential_|suspicious_urls:)/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatIncidentId(str) {
  if (!str) return "—";
  return str.toUpperCase();
}
