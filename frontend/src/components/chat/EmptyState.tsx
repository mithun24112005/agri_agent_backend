import { Sprout, ScanLine, Droplets, Wheat } from "lucide-react";
import { ThreadPrimitive } from "@assistant-ui/react";

const suggestions = [
  { icon: Sprout, text: "Which crop fits these soil conditions?", prompt: "Which crop is best for my soil if N=90, P=42, K=43, temperature 25°C, humidity 80%, pH 6.5 and rainfall 200 mm?" },
  { icon: ScanLine, text: "Can you diagnose this leaf?", prompt: "Can you diagnose this leaf and tell me what I should do next?" },
  { icon: Droplets, text: "How do I control powdery mildew?", prompt: "How can I control powdery mildew using practical farm-safe steps?" },
  { icon: Wheat, text: "What should I consider before planting rice?", prompt: "What should I consider before planting rice this season?" },
];

export function EmptyState() {
  return <div className="empty-state"><p className="eyebrow">CropSage assistant</p><h1>How can I help you today?</h1><p className="empty-description">Ask about crop selection, plant health, soil conditions, or practical agricultural questions.</p><div className="suggestion-grid">{suggestions.map(({ icon: Icon, text, prompt }) => <ThreadPrimitive.Suggestion key={text} prompt={prompt} send className="suggestion-card"><Icon size={16} /><span>{text}</span></ThreadPrimitive.Suggestion>)}</div></div>;
}
