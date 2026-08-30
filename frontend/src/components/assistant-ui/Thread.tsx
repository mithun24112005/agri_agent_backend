import { useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ActionBarPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAui,
  type ImageMessagePartProps,
  type TextMessagePartProps,
  type CompleteAttachment,
} from "@assistant-ui/react";
import { ArrowUp, Copy, LoaderCircle, Paperclip, RotateCcw, Square, X } from "lucide-react";
import { EmptyState } from "@/components/chat/EmptyState";

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
  return <MessagePrimitive.Root className="message-row user-row"><div className="message-bubble user-bubble"><MessagePrimitive.Attachments>{({ attachment }) => <MessageAttachment attachment={attachment} />}</MessagePrimitive.Attachments><MessagePrimitive.Content components={{ Text: MarkdownText, Image: ImagePart }} /></div><ActionBarPrimitive.Root className="message-actions"><ActionBarPrimitive.Copy aria-label="Copy message"><Copy size={13} /></ActionBarPrimitive.Copy></ActionBarPrimitive.Root></MessagePrimitive.Root>;
}

function AssistantMessage() {
  return <MessagePrimitive.Root className="message-row assistant-row"><div className="assistant-avatar">✦</div><div className="assistant-message-body"><MessagePrimitive.Content components={{ Text: MarkdownText, Image: ImagePart }} /><ActionBarPrimitive.Root className="message-actions assistant-actions"><ActionBarPrimitive.Copy aria-label="Copy message"><Copy size={13} /></ActionBarPrimitive.Copy><ActionBarPrimitive.Reload aria-label="Regenerate response"><RotateCcw size={13} /></ActionBarPrimitive.Reload></ActionBarPrimitive.Root></div></MessagePrimitive.Root>;
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
  return <div className="composer-attachment"><div className="attachment-thumb">{preview ? <img src={preview} alt="" /> : <Paperclip size={15} />}</div><span>{attachment.name}</span><button type="button" onClick={onRemove} aria-label={`Remove ${attachment.name}`}><X size={14} /></button></div>;
}

function Composer() {
  return <div className="composer-wrap"><ComposerPrimitive.Root className="composer"><ComposerAttachment /><ComposerPrimitive.Input aria-label="Ask AgriMind" placeholder="Ask about crops, soil, plant health…" submitMode="enter" /><div className="composer-toolbar"><ComposerPrimitive.AddAttachment multiple={false} aria-label="Attach an image"><Paperclip size={17} /></ComposerPrimitive.AddAttachment><span className="composer-hint">Images up to 5 MB</span><ComposerPrimitive.Cancel className="icon-button stop-button" aria-label="Stop response"><Square size={13} fill="currentColor" /></ComposerPrimitive.Cancel><ComposerPrimitive.Send className="send-button" aria-label="Send message"><ArrowUp size={17} /></ComposerPrimitive.Send></div></ComposerPrimitive.Root><p className="composer-disclaimer">AgriMind can make mistakes. Verify important decisions with local agronomic expertise.</p></div>;
}

export function AgriThread() {
  return <ThreadPrimitive.Root className="thread-root"><ThreadPrimitive.Viewport className="thread-viewport" turnAnchor="top"><ThreadPrimitive.Empty><EmptyState /></ThreadPrimitive.Empty><div className="message-list"><ThreadPrimitive.Messages components={{ UserMessage, AssistantMessage }} /></div><ThreadPrimitive.ScrollToBottom className="scroll-button"><ArrowUp size={14} /></ThreadPrimitive.ScrollToBottom></ThreadPrimitive.Viewport><Composer /></ThreadPrimitive.Root>;
}
