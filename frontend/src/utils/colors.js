// the 12 colour names the AI service can recognise on clothes
export const COLOR_NAMES = ["black", "white", "grey", "red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "beige"];

// the real colour shown in the small round chip
const HEX = {
  black: "#111827", white: "#f9fafb", grey: "#9ca3af", red: "#ef4444", orange: "#f97316", yellow: "#facc15",
  green: "#22c55e", blue: "#3b82f6", purple: "#a855f7", pink: "#f9a8d4", brown: "#92400e", beige: "#d6c3a1",
};

export function colorHex(name) {
  return HEX[name] || "#475569";
}
