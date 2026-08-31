import { useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ActionBarPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAui,
  useAuiState,
  type ImageMessagePartProps,
  type TextMessagePartProps,
  type CompleteAttachment,
} from "@assistant-ui/react";
import { ArrowDown, ArrowUp, Copy, LoaderCircle, Paperclip, Square, X } from "lucide-react";
import { EmptyState } from "@/components/chat/EmptyState";
import { AgentActivity } from "@/components/chat/AgentActivity";
import { useAttachmentError } from "@/lib/runtime/attachments";

function MarkdownText({ text }: TextMessagePartProps) {
  return text ? <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown></div> : <span className="message-thinking"><LoaderCircle className="spin" size={15} />Thinking through the field notes…</span>;
}

function ImagePart({ image, filename }: ImageMessagePartProps) {
  return <img className="message-image" src={image} alt={filename ?? "Attached plant image"} />;
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
  return <MessagePrimitive.Root className="message-row assistant-row"><div className="assistant-avatar">✦</div><div className="assistant-message-body"><MessagePrimitive.Content components={{ Text: MarkdownText, Image: ImagePart }} /><ActionBarPrimitive.Root className="message-actions assistant-actions"><ActionBarPrimitive.Copy aria-label="Copy response"><Copy size={13} /></ActionBarPrimitive.Copy></ActionBarPrimitive.Root></div></MessagePrimitive.Root>;
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
  return <div className="composer-wrap"><ComposerAttachmentError /><ComposerPrimitive.Root className="composer"><ComposerAttachment /><ComposerPrimitive.Input aria-label="Ask AgriMind" placeholder="Ask about crops, soil, plant health…" submitMode="enter" /><div className="composer-toolbar"><ComposerPrimitive.AddAttachment multiple={false} aria-label="Attach an image"><Paperclip size={17} /></ComposerPrimitive.AddAttachment><span className="composer-hint">{isRunning ? "Working…" : "Images up to 5 MB"}</span><ComposerSubmitControl /></div></ComposerPrimitive.Root><p className="composer-disclaimer">AgriMind can make mistakes. Verify important decisions with local agronomic expertise.</p></div>;
}

export function AgriThread() {
  return <ThreadPrimitive.Root className="thread-root"><ThreadPrimitive.Viewport className="thread-viewport" turnAnchor="top"><ThreadPrimitive.Empty><EmptyState /></ThreadPrimitive.Empty><div className="message-list"><ThreadPrimitive.Messages components={{ UserMessage, AssistantMessage }} /></div><AgentActivity /><ThreadPrimitive.ScrollToBottom className="scroll-button" aria-label="Scroll to latest message"><ArrowDown size={14} /></ThreadPrimitive.ScrollToBottom></ThreadPrimitive.Viewport><Composer /></ThreadPrimitive.Root>;
}
