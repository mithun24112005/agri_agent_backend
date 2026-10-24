import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ActionBarPrimitive,
  ChainOfThoughtPrimitive,
  ComposerPrimitive,
  ErrorPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAui,
  useAuiState,
  type ImageMessagePartProps,
  type TextMessagePartProps,
  type CompleteAttachment,
  type ReasoningMessagePartProps,
  type ToolCallMessagePartProps,
} from "@assistant-ui/react";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  CircleCheck,
  Copy,
  LoaderCircle,
  Paperclip,
  Square,
  X,
} from "lucide-react";
import { EmptyState } from "@/components/chat/EmptyState";
import { useAttachmentError } from "@/lib/runtime/attachments";

function MarkdownText({ text }: TextMessagePartProps) {
  return text ? (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  ) : (
    <span className="message-thinking">
      <LoaderCircle className="spin animate-spin" size={15} />
      Thinking through the field notes…
    </span>
  );
}

function ImagePart({ image, filename }: ImageMessagePartProps) {
  return <img className="message-image" src={image} alt={filename ?? "Attached plant image"} />;
}

const agentStepTitles: Record<string, string> = {
  disease_agent: "Diagnosed plant health and disease indicators",
  crop_agent: "Evaluated crop suitability and soil conditions",
  general_agent: "Synthesized agronomic advisory notes",
  routing: "Routing question to specialized field agents",
};

const agentLabels: Record<string, string> = {
  disease_agent: "Disease Diagnosis Agent",
  crop_agent: "Crop Advisory Agent",
  general_agent: "General Agriculture Agent",
  routing: "Field Supervisor",
};

function ActivityReasoning({ text }: ReasoningMessagePartProps) {
  void text;
  return null;
}

function ActivityTool({ toolName, args, result, status }: ToolCallMessagePartProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const running = status.type === "running";
  const title = agentStepTitles[toolName] ?? toolName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const agentLabel = agentLabels[toolName] ?? toolName;

  const queryText = typeof args?.query === "string" ? args.query : "";
  const resultText = typeof result === "string" ? result : result ? JSON.stringify(result, null, 2) : "";

  return (
    <div className="chain-step-item">
      <button
        type="button"
        className="chain-step-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
      >
        <span className="chain-step-icon">
          {running ? (
            <LoaderCircle size={14} className="animate-spin spin" />
          ) : (
            <CircleCheck size={14} />
          )}
        </span>
        <span className="chain-step-title">{title}</span>
        <ChevronDown
          size={13}
          className={`chain-step-chevron ${isExpanded ? "expanded" : ""}`}
        />
      </button>

      {isExpanded && (
        <div className="chain-step-details">
          <div className="chain-step-badge">{agentLabel}</div>
          {queryText && (
            <div className="chain-step-block">
              <span className="chain-step-label">Query</span>
              <p className="chain-step-query">{queryText}</p>
            </div>
          )}
          {resultText && (
            <div className="chain-step-block">
              <span className="chain-step-label">Findings</span>
              <div className="chain-step-output">{resultText}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ChainOfThought() {
  const aui = useAui();
  const collapsed = useAuiState((state) => state.chainOfThought.collapsed);
  const parts = useAuiState((state) => state.chainOfThought.parts);
  const isRunning = parts.some((p) => p.status?.type === "running");
  const toolParts = parts.filter((p) => p.type === "tool-call");
  const stepCount = toolParts.length > 0 ? toolParts.length : parts.length;

  useEffect(() => {
    if (parts.length > 0) aui.chainOfThought.setCollapsed(false);
  }, [aui, parts.length]);

  return (
    <ChainOfThoughtPrimitive.Root className="chain-of-thought">
      <ChainOfThoughtPrimitive.AccordionTrigger className="chain-trigger">
        <span className="chain-trigger-icon">
          {isRunning ? (
            <LoaderCircle size={14} className="spin animate-spin" />
          ) : (
            <CircleCheck size={14} />
          )}
        </span>
        <span className="chain-trigger-text">
          {isRunning
            ? "Researching"
            : `Researched in ${stepCount} step${stepCount === 1 ? "" : "s"}`}
        </span>
        <ChevronDown
          size={13}
          className={`chain-trigger-chevron ${!collapsed ? "expanded" : ""}`}
        />
      </ChainOfThoughtPrimitive.AccordionTrigger>
      <ChainOfThoughtPrimitive.Parts
        components={{
          Reasoning: ActivityReasoning,
          tools: { Fallback: ActivityTool },
          Layout: ({ children }) => <div className="chain-parts">{children}</div>,
        }}
      />
    </ChainOfThoughtPrimitive.Root>
  );
}

function MessageAttachment({ attachment }: { attachment: CompleteAttachment }) {
  const image = attachment.content.find((part) => part.type === "image");
  if (image?.type !== "image") return null;
  return <img className="message-image" src={image.image} alt={image.filename ?? attachment.name} />;
}

function UserMessage() {
  return <MessagePrimitive.Root className="message-row user-row"><div className="message-bubble user-bubble"><MessagePrimitive.Attachments>{({ attachment }) => <MessageAttachment attachment={attachment} />}</MessagePrimitive.Attachments><MessagePrimitive.Content components={{ Text: MarkdownText, Image: ImagePart }} /></div></MessagePrimitive.Root>;
}

function AssistantMessage() {
  return <MessagePrimitive.Root className="message-row assistant-row"><div className="assistant-avatar">✦</div><div className="assistant-message-body"><MessagePrimitive.Content components={{ Text: MarkdownText, Image: ImagePart, ChainOfThought }} /><MessagePrimitive.Error><ErrorPrimitive.Root className="message-error"><ErrorPrimitive.Message /><ActionBarPrimitive.Reload className="message-error-retry">Retry</ActionBarPrimitive.Reload></ErrorPrimitive.Root></MessagePrimitive.Error><ActionBarPrimitive.Root className="message-actions assistant-actions"><ActionBarPrimitive.Copy aria-label="Copy response"><Copy size={13} /></ActionBarPrimitive.Copy><ActionBarPrimitive.Reload aria-label="Retry response"><span className="sr-only">Retry</span></ActionBarPrimitive.Reload></ActionBarPrimitive.Root></div></MessagePrimitive.Root>;
}

function ComposerAttachment() {
  const aui = useAui();
  return <ComposerPrimitive.Attachments>{({ attachment }) => <AttachmentChip attachment={attachment} onRemove={() => void aui.thread.composer().attachment({ id: attachment.id }).remove()} />}</ComposerPrimitive.Attachments>;
}

function AttachmentChip({ attachment, onRemove }: { attachment: { name: string; file?: File }; onRemove: () => void }) {
  const preview = useMemo(() => attachment.file ? URL.createObjectURL(attachment.file) : null, [attachment.file]);
  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [preview]);
  return <div className="composer-attachment"><div className="attachment-thumb">{preview ? <img src={preview} alt="" /> : <Paperclip size={15} />}</div><div className="attachment-details"><strong>{attachment.name}</strong><span>Image{attachment.file ? ` · ${formatBytes(attachment.file.size)}` : ""}</span></div><button type="button" onClick={onRemove} aria-label={`Remove ${attachment.name}`}><X size={14} /></button></div>;
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ComposerAttachmentError() {
  const error = useAttachmentError();
  if (!error) return null;
  return <div className="composer-error" role="alert"><span>{error}</span></div>;
}

function ComposerSubmitControl() {
  const isRunning = useAuiState((state) => state.thread.isRunning);
  return <div className="composer-submit-slot">{isRunning ? <ComposerPrimitive.Cancel className="stop-button" aria-label="Stop response"><Square size={13} fill="currentColor" /></ComposerPrimitive.Cancel> : <ComposerPrimitive.Send className="send-button" aria-label="Send message"><ArrowUp size={17} /></ComposerPrimitive.Send>}</div>;
}

function Composer() {
  const isRunning = useAuiState((state) => state.thread.isRunning);
  return <div className="composer-wrap"><ComposerAttachmentError /><ComposerPrimitive.Root className="composer"><ComposerAttachment /><ComposerPrimitive.Input aria-label="Ask CropSage" placeholder="Ask about crops, soil, plant health…" submitMode="enter" /><div className="composer-toolbar"><ComposerPrimitive.AddAttachment multiple={false} aria-label="Attach an image"><Paperclip size={17} /></ComposerPrimitive.AddAttachment><span className="composer-hint">{isRunning ? "Working…" : "Images up to 5 MB"}</span><ComposerSubmitControl /></div></ComposerPrimitive.Root><p className="composer-disclaimer">CropSage can make mistakes. Verify important decisions with local agronomic expertise.</p></div>;
}

export function AgriThread() {
  return <ThreadPrimitive.Root className="thread-root"><ThreadPrimitive.Viewport className="thread-viewport" turnAnchor="top"><ThreadPrimitive.Empty><EmptyState /></ThreadPrimitive.Empty><div className="message-list"><ThreadPrimitive.Messages components={{ UserMessage, AssistantMessage }} /></div><ThreadPrimitive.ScrollToBottom className="scroll-button" aria-label="Scroll to latest message"><ArrowDown size={14} /></ThreadPrimitive.ScrollToBottom></ThreadPrimitive.Viewport><Composer /></ThreadPrimitive.Root>;
}
