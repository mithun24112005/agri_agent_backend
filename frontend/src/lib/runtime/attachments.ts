import type { Attachment, AttachmentAdapter, CompleteAttachment, PendingAttachment } from "@assistant-ui/react";

export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp,image/gif";

const filesByPreviewUrl = new Map<string, File>();

export const gatewayAttachmentAdapter: AttachmentAdapter = {
  accept: IMAGE_ACCEPT,
  async add({ file }): Promise<PendingAttachment> {
    if (!file.type.startsWith("image/")) throw new Error("Please choose an image file.");
    if (file.size > MAX_IMAGE_BYTES) throw new Error("That image is too large. The maximum size is 5 MB.");
    const previewUrl = URL.createObjectURL(file);
    filesByPreviewUrl.set(previewUrl, file);
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
    const previewUrl = [...filesByPreviewUrl.entries()].find(([, file]) => file === attachment.file)?.[0] ?? URL.createObjectURL(attachment.file);
    filesByPreviewUrl.set(previewUrl, attachment.file);
    return {
      id: attachment.id,
      type: "image",
      name: attachment.name,
      contentType: attachment.contentType,
      file: attachment.file,
      content: [{ type: "image", image: previewUrl, filename: attachment.name }],
      status: { type: "complete" },
    };
  },
  async remove(attachment: Attachment) {
    if (attachment.file) {
      const previewUrl = [...filesByPreviewUrl.entries()].find(([, file]) => file === attachment.file)?.[0];
      if (previewUrl) {
        filesByPreviewUrl.delete(previewUrl);
        URL.revokeObjectURL(previewUrl);
        return;
      }
    }
    const image = attachment.content?.find((part) => part.type === "image");
    if (image?.type === "image") {
      filesByPreviewUrl.delete(image.image);
      URL.revokeObjectURL(image.image);
    }
  },
};

export function getFileForPreviewUrl(url: string) {
  return filesByPreviewUrl.get(url);
}
