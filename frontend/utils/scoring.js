export function computeFRS(scores) {
  const baseWeights = {
    email: 0.40,
    website: 0.30,
    attachment: 0.20,
    graph: 0.10,
  };
  // Only include layers that are not null/undefined
  const active = Object.entries(baseWeights).filter(
    ([k]) => scores[k] != null
  );
  const weightSum = active.reduce((s, [k]) => s + baseWeights[k], 0);
  if (weightSum === 0) return 0;
  return active.reduce(
    (s, [k]) => s + (baseWeights[k] / weightSum) * scores[k],
    0
  );
}

export function getVerdict(frs) {
  if (frs > 0.60) return "oob_required";
  if (frs > 0.45) return "suspicious";
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
