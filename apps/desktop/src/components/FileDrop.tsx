import { useId, useState, type DragEvent } from "react";

import { IconUpload } from "./Icons";

/**
 * Drop a file or pick one. The whole box is a real <label> for a visually hidden
 * file input, so Enter/Space and screen readers work without extra handlers.
 */
export function FileDrop({
  accept = ".csv,text/csv",
  label,
  hint,
  fileName,
  disabled = false,
  onFile,
}: {
  accept?: string;
  label: string;
  hint?: string;
  fileName?: string | null;
  disabled?: boolean;
  onFile: (file: File) => void;
}) {
  const id = useId();
  const [over, setOver] = useState(false);

  function drop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  }

  return (
    <label
      htmlFor={id}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
      data-over={over || undefined}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/30 ${
        over ? "border-accent bg-accent/5" : "border-line-2 hover:border-accent/60"
      } ${disabled ? "pointer-events-none opacity-50" : ""}`}
    >
      <IconUpload width={26} height={26} className="text-accent" aria-hidden />
      <span className="text-sm font-medium text-ink">{fileName ?? label}</span>
      {hint && <span className="text-xs text-muted">{hint}</span>}
      <input
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          // Allow picking the same file again after fixing it.
          e.target.value = "";
        }}
      />
    </label>
  );
}
