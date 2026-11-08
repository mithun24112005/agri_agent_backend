import { useMemo, useState } from "react";
import {
  ThreadListItemPrimitive,
  ThreadListPrimitive,
  useAui,
  useAuiState,
} from "@assistant-ui/react";
import { Check, MoreHorizontal, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { ConfirmDialog } from "@/components/layout/ConfirmDialog";

interface SessionItemProps {
  onOpenChat?: () => void;
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
}

function SessionItem({ onOpenChat, menuOpen, onMenuOpenChange }: SessionItemProps) {
  const aui = useAui();
  const isActive = useAuiState((state) => state.threads.mainThreadId === state.threadListItem.id);
  const title = useAuiState((state) => state.threadListItem.title);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title ?? "New conversation");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const save = async () => {
    onMenuOpenChange(false);
    await aui.threadListItem.rename(draft.trim() || "New conversation");
    setEditing(false);
  };

  const handleDelete = async () => {
    onMenuOpenChange(false);
    await aui.threadListItem.delete();
    setShowDeleteConfirm(false);
  };

  return (
    <>
      <ThreadListItemPrimitive.Root className={`thread-list-item ${isActive ? "active" : ""}`}>
        <div className="thread-item-main">
          {editing ? (
            <input
              autoFocus
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void save();
                if (event.key === "Escape") setEditing(false);
              }}
              aria-label="Rename conversation"
            />
          ) : (
            <ThreadListItemPrimitive.Trigger
              onClick={() => {
                onMenuOpenChange(false);
                onOpenChat?.();
              }}
            >
              <ThreadListItemPrimitive.Title fallback="New conversation" />
            </ThreadListItemPrimitive.Trigger>
          )}
        </div>

        {editing ? (
          <div className="thread-item-actions">
            <button type="button" onClick={() => void save()} aria-label="Save conversation name">
              <Check size={14} />
            </button>
            <button type="button" onClick={() => setEditing(false)} aria-label="Cancel rename">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="thread-more">
            <button
              type="button"
              className="thread-more-toggle"
              aria-label="Conversation actions"
              aria-expanded={menuOpen}
              onClick={(event) => {
                event.stopPropagation();
                onMenuOpenChange(!menuOpen);
              }}
            >
              <MoreHorizontal size={15} />
            </button>
            {menuOpen && (
              <div className="thread-menu" role="menu" onClick={(event) => event.stopPropagation()}>
              <button
                type="button"
                onClick={() => {
                  setDraft(title ?? "New conversation");
                  setEditing(true);
                  onMenuOpenChange(false);
                }}
              >
                <Pencil size={13} /> Rename
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => {
                  setShowDeleteConfirm(true);
                  onMenuOpenChange(false);
                }}
              >
                <Trash2 size={13} /> Delete
              </button>
              </div>
            )}
          </div>
        )}
      </ThreadListItemPrimitive.Root>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Conversation?"
        message={`Are you sure you want to delete "${title || "New conversation"}"? This action cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        isDestructive={true}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </>
  );
}

export function ThreadList({ onOpenChat }: { onOpenChat?: () => void }) {
  const [query, setQuery] = useState("");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const queryKey = useMemo(() => query.trim().toLowerCase(), [query]);

  return (
    <div
      className="sidebar-thread-list"
      onClick={(event) => {
        if (!(event.target as HTMLElement).closest(".thread-more")) setOpenMenuId(null);
      }}
    >
      <div className="sidebar-search">
        <Search size={15} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search conversations"
          aria-label="Search conversations"
        />
      </div>

      <ThreadListPrimitive.Root>
        <div className="thread-list-heading">
          <span>Conversations</span>
          <span className="thread-list-count">{queryKey ? "filtered" : "recent"}</span>
        </div>
        <ThreadListPrimitive.Items>
          {({ threadListItem }) => {
            const itemTitle = (threadListItem.title ?? "New conversation").toLowerCase();
            return queryKey && !itemTitle.includes(queryKey) ? null : (
              <SessionItem
                key={threadListItem.id}
                onOpenChat={onOpenChat}
                menuOpen={openMenuId === threadListItem.id}
                onMenuOpenChange={(open) => setOpenMenuId(open ? threadListItem.id : null)}
              />
            );
          }}
        </ThreadListPrimitive.Items>
      </ThreadListPrimitive.Root>
    </div>
  );
}

export function NewChatButton({ onOpenChat }: { onOpenChat?: () => void }) {
  return (
    <ThreadListPrimitive.New className="new-chat-button" onClick={onOpenChat}>
      <Plus size={17} />
      <span>New conversation</span>
    </ThreadListPrimitive.New>
  );
}
