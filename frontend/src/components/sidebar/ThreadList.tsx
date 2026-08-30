import { useMemo, useState } from "react";
import {
  ThreadListItemPrimitive,
  ThreadListPrimitive,
  useAui,
  useAuiState,
} from "@assistant-ui/react";
import { Check, MoreHorizontal, Pencil, Plus, Search, Trash2, X } from "lucide-react";

function SessionItem() {
  const aui = useAui();
  const isActive = useAuiState((state) => state.threads.mainThreadId === state.threadListItem.id);
  const title = useAuiState((state) => state.threadListItem.title);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title ?? "New conversation");

  const save = async () => {
    await aui.threadListItem.rename(draft.trim() || "New conversation");
    setEditing(false);
  };

  return <ThreadListItemPrimitive.Root className={`thread-list-item ${isActive ? "active" : ""}`}><div className="thread-item-main">{editing ? <input autoFocus value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void save(); if (event.key === "Escape") setEditing(false); }} aria-label="Rename conversation" /> : <ThreadListItemPrimitive.Trigger><ThreadListItemPrimitive.Title fallback="New conversation" /></ThreadListItemPrimitive.Trigger>}</div>{editing ? <div className="thread-item-actions"><button type="button" onClick={() => void save()} aria-label="Save conversation name"><Check size={14} /></button><button type="button" onClick={() => setEditing(false)} aria-label="Cancel rename"><X size={14} /></button></div> : <details className="thread-more"><summary aria-label="Conversation actions"><MoreHorizontal size={15} /></summary><div className="thread-menu"><button type="button" onClick={() => { setDraft(title ?? "New conversation"); setEditing(true); }}><Pencil size={13} /> Rename</button><button type="button" className="danger" onClick={() => { if (window.confirm("Delete this conversation?")) void aui.threadListItem.delete(); }}><Trash2 size={13} /> Delete</button></div></details>}</ThreadListItemPrimitive.Root>;
}

export function ThreadList() {
  const [query, setQuery] = useState("");
  const queryKey = useMemo(() => query.trim().toLowerCase(), [query]);
  return <div className="sidebar-thread-list"><div className="sidebar-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search conversations" aria-label="Search conversations" /></div><ThreadListPrimitive.Root><div className="thread-list-heading"><span>Conversations</span><span className="thread-list-count">{queryKey ? "filtered" : "recent"}</span></div><ThreadListPrimitive.Items>{({ threadListItem }) => { const title = (threadListItem.title ?? "New conversation").toLowerCase(); return queryKey && !title.includes(queryKey) ? null : <SessionItem />; }}</ThreadListPrimitive.Items></ThreadListPrimitive.Root></div>;
}

export function NewChatButton() {
  return <ThreadListPrimitive.New className="new-chat-button"><Plus size={17} /><span>New conversation</span><kbd>⌘ K</kbd></ThreadListPrimitive.New>;
}
