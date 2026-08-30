import { Check, CircleDot, LoaderCircle, Network } from "lucide-react";
import { useAgentActivity } from "@/lib/runtime/activity";

const labels: Record<string, string> = { disease_agent: "Disease agent", crop_agent: "Crop agent", general_agent: "General agent" };

export function AgentActivity() {
  const activity = useAgentActivity();
  if (activity.status === "idle") return null;
  const processing = activity.status === "processing";
  return <div className={`agent-activity ${processing ? "processing" : ""}`}><div className="activity-heading"><span className="activity-icon">{processing ? <LoaderCircle className="spin" size={14} /> : activity.status === "complete" ? <Check size={14} /> : <CircleDot size={14} />}</span><span>Agent activity</span><span className="activity-status">{processing ? "working" : activity.status === "complete" ? `${activity.selectedCount} selected` : "unavailable"}</span></div>{processing ? <div className="activity-flow"><Network size={14} /> Supervisor is routing your question…</div> : activity.agents.length > 0 && <div className="activity-agents"><span className="activity-supervisor">Supervisor</span>{activity.agents.map((agent) => <span className="activity-agent" key={agent}><span className="connector" />{labels[agent] ?? agent}</span>)}</div>}</div>;
}
