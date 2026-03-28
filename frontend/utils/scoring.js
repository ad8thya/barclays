export function computeFRS(scores) {
  const { email = 0, website = 0, attachment = 0, graph = 0 } = scores;
  return 0.40 * email + 0.30 * website + 0.20 * attachment + 0.10 * graph;
}

export function getVerdict(frs) {
  if (frs >= 0.80) return "oob_required";
  if (frs >= 0.70) return "suspicious";
  return "clear";
}

export function getVerdictColor(verdict) {
  switch (verdict) {
    case "oob_required":
      return "#ef4444";
    case "suspicious":
      return "#f59e0b";
    case "clear":
    default:
      return "#10b981";
  }
}
