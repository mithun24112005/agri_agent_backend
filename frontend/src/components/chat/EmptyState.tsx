import { Wheat, Microscope, ShieldCheck, MessageSquare } from "lucide-react";
import { ThreadPrimitive } from "@assistant-ui/react";

const suggestions = [
  {
    icon: Wheat,
    text: "Calculate crop suitability",
    prompt: "My soil has N=90, P=42, K=43, pH=6.5, temperature=25°C, humidity=80%, rainfall=200mm. Which crop is suitable?",
  },
  {
    icon: Microscope,
    text: "Leaf health & disease advisory",
    prompt: "What are the common symptoms and management practices for Early Blight in tomato?",
  },
  {
    icon: ShieldCheck,
    text: "Fertilizer & nutrient management",
    prompt: "What fertilizer schedule should I follow for wheat, and how should phosphorus be applied?",
  },
  {
    icon: MessageSquare,
    text: "Seasonal package of practices",
    prompt: "Explain the sowing window, seed rate, and soil requirements for mustard cultivation.",
  },
];

export function EmptyState() {
  return (
    <div className="empty-state">
      <p className="eyebrow">Field AI Consultation</p>
      <h1>How can I assist your field operations?</h1>
      <p className="empty-description">
        Ask about crop recommendations, plant disease identification, fertilizer schedules, or ICAR-grounded package of practices.
      </p>
      <div className="suggestion-grid">
        {suggestions.map(({ icon: Icon, text, prompt }) => (
          <ThreadPrimitive.Suggestion key={text} prompt={prompt} send className="suggestion-card">
            <Icon size={16} />
            <span>{text}</span>
          </ThreadPrimitive.Suggestion>
        ))}
      </div>
    </div>
  );
}
