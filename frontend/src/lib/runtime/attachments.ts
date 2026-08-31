import { useSyncExternalStore } from "react";
import type { AttachmentAdapter, CompleteAttachment, PendingAttachment } from "@assistant-ui/react";

export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp,image/gif";

const SUPPORTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
let attachmentError = "";
const attachmentErrorListeners = new Set<() => void>();

function setAttachmentError(message: string) {
  attachmentError = message;
  attachmentErrorListeners.forEach((listener) => listener());
}

export function useAttachmentError() {
  return useSyncExternalStore(
    (listener) => {
      attachmentErrorListeners.add(listener);
      return () => attachmentErrorListeners.delete(listener);
    },
    () => attachmentError,
    () => attachmentError,
  );
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the image."));
    reader.readAsDataURL(file);
  });
}

export const gatewayAttachmentAdapter: AttachmentAdapter = {
  accept: IMAGE_ACCEPT,
  async add({ file }): Promise<PendingAttachment> {
    if (!SUPPORTED_IMAGE_TYPES.has(file.type.toLowerCase())) {
      const message = "Please choose a JPEG, PNG, WebP, or GIF image.";
      setAttachmentError(message);
      throw new Error(message);
    }
    if (file.size > MAX_IMAGE_BYTES) {
      const message = "That image is too large. The maximum size is 5 MB.";
      setAttachmentError(message);
      throw new Error(message);
    }
    setAttachmentError("");
    return {
      id: crypto.randomUUID(),
      type: "image",
      name: file.name,
      contentType: file.type,
      file,
      status: { type: "requires-action", reason: "composer-send" },
    };
  },
  async send(attachment): Promise<CompleteAttachment> {
    return {
      id: attachment.id,
      type: "image",
      name: attachment.name,
      contentType: attachment.contentType,
      file: attachment.file,
      content: [{ type: "image", image: await fileToDataUrl(attachment.file), filename: attachment.name }],
      status: { type: "complete" },
    };
  },
  async remove() {
    // Composer previews own their object URLs. Sent-message images are data URLs,
    // so removing a pending attachment never invalidates a rendered message.
  },
};
