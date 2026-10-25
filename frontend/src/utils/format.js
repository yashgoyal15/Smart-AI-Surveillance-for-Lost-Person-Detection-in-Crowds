// small helpers for showing data nicely

// the backend sends times in UTC (ISO format), the browser turns them into local time
export function formatTime(isoString) {
  if (!isoString) return "";
  return new Date(isoString).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatPercent(score) {
  return Math.round(score * 100) + "%";
}
