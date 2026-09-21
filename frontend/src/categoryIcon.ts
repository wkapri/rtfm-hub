// Free-text category -> emoji, matched by keyword rather than exact string since
// users type whatever they want ("vacuum", "robot vacuum", "Vacuums"...). Emoji
// over custom SVGs here deliberately: zero asset weight, already full-color, and
// this project has no product-photo storage (a real feature, not a quick add) —
// see the "actual product image" idea in the roadmap if that's wanted later.
const CATEGORY_ICONS: [keywords: string[], emoji: string][] = [
  [["vacuum", "robot vacuum"], "🧹"],
  [["car", "vehicle", "truck", "suv"], "🚗"],
  [["motorcycle", "bike", "bicycle"], "🏍️"],
  [["kitchen", "oven", "stove", "microwave", "fridge", "refrigerator"], "🍳"],
  [["tv", "television"], "📺"],
  [["phone", "mobile"], "📱"],
  [["computer", "laptop", "pc"], "💻"],
  [["camera"], "📷"],
  [["speaker", "audio", "headphone"], "🔊"],
  [["game", "gaming", "console"], "🎮"],
  [["tool", "drill", "saw"], "🔧"],
  [["furniture", "chair", "desk", "table"], "🪑"],
  [["appliance"], "🔌"],
  [["hvac", "thermostat", "heater", "ac", "air condition"], "🌡️"],
  [["light", "lamp"], "💡"],
  [["router", "network", "wifi"], "📶"],
];

export function categoryIcon(category: string | null): string {
  if (!category) return "📦";
  const lower = category.toLowerCase();
  for (const [keywords, emoji] of CATEGORY_ICONS) {
    if (keywords.some((kw) => lower.includes(kw))) return emoji;
  }
  return "📦";
}
