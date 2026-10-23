/**
 * Share cards and photo files, drawn and saved on this PC. In Electron, saving, copying and
 * opening X go through the validated IPC channels (image:save, clipboard:write and the
 * share:open allowlist); in browser dev mode they fall back to a download, the browser
 * clipboard and a new tab. Nothing is uploaded by the app.
 */
import type { ShareCardText } from "@ascend/shared";

export const CARD_SIZE = 1080;

/** Draw the card on a canvas; returns a PNG data URL, or null where canvas is unavailable. */
export function drawCard(card: ShareCardText, trainerName: string, canvas: HTMLCanvasElement = document.createElement("canvas")): string | null {
  canvas.width = CARD_SIZE;
  canvas.height = CARD_SIZE;
  let ctx: CanvasRenderingContext2D | null;
  try {
    ctx = canvas.getContext("2d");
  } catch {
    return null;
  }
  if (!ctx) return null;
  const g = ctx.createLinearGradient(0, 0, CARD_SIZE, CARD_SIZE);
  g.addColorStop(0, "#0A0E15");
  g.addColorStop(1, "#13233a");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, CARD_SIZE, CARD_SIZE);
  ctx.strokeStyle = "#3ee0ff";
  ctx.lineWidth = 6;
  ctx.strokeRect(48, 48, CARD_SIZE - 96, CARD_SIZE - 96);
  ctx.fillStyle = "#3ee0ff";
  ctx.font = "700 44px Rajdhani, sans-serif";
  ctx.fillText(card.title.toUpperCase(), 110, 210);
  ctx.fillStyle = "#ffffff";
  ctx.font = "700 96px Rajdhani, sans-serif";
  wrap(ctx, card.headline, 110, 380, CARD_SIZE - 220, 104);
  ctx.fillStyle = "#b8c4d6";
  ctx.font = "500 44px Inter, sans-serif";
  wrap(ctx, card.detail, 110, 660, CARD_SIZE - 220, 56);
  ctx.fillStyle = "#3ee0ff";
  ctx.font = "700 52px Rajdhani, sans-serif";
  ctx.fillText("ASCEND", 110, CARD_SIZE - 120);
  ctx.fillStyle = "#8494ab";
  ctx.font = "400 30px Inter, sans-serif";
  ctx.fillText(`with ${trainerName}`, 330, CARD_SIZE - 124);
  try {
    return canvas.toDataURL("image/png");
  } catch {
    return null;
  }
}

function wrap(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, width: number, lh: number) {
  let line = "";
  let yy = y;
  for (const word of text.split(" ")) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > width && line) {
      ctx.fillText(line, x, yy);
      line = word;
      yy += lh;
    } else {
      line = test;
    }
  }
  if (line) ctx.fillText(line, x, yy);
}

export async function saveImage(defaultName: string, dataUrl: string): Promise<boolean> {
  if (window.ascend) return (await window.ascend.saveImage({ defaultName, dataUrl })).saved;
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = defaultName;
  a.click();
  return true;
}

export async function copyToClipboard(text?: string, imageDataUrl?: string): Promise<boolean> {
  if (window.ascend) return window.ascend.copyToClipboard({ text, imageDataUrl });
  if (text && navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  return false;
}

export async function openShareLink(url: string): Promise<boolean> {
  if (window.ascend) return window.ascend.openShareLink(url);
  window.open(url, "_blank", "noopener");
  return true;
}

/**
 * Re-encode a photo through a canvas: the browser applies the camera's rotation, and the
 * canvas writes a JPEG with no EXIF (no GPS, no camera serial). Longest side 1600 px.
 */
export async function reencodePhoto(file: File, maxSide = 1600): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error("That file is not a photo this app can read."));
      i.src = url;
    });
    const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Can't process photos here.");
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.88);
  } finally {
    URL.revokeObjectURL(url);
  }
}
