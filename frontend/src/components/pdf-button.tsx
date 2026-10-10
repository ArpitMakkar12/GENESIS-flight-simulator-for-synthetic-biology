"use client";

import { useState } from "react";
import { FileDown, LoaderCircle } from "lucide-react";

/**
 * "Export .pdf" button. Making a PDF takes a second or two on the backend,
 * so the button shows a spinner meanwhile, blocks double-clicks, and shows
 * the error message underneath if something goes wrong.
 */
export function PdfButton({ onExport, className = "" }: { onExport: () => Promise<void>; className?: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      await onExport();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="relative inline-flex flex-col items-end">
      <button onClick={run} disabled={busy} className={`inline-flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-wait ${className}`}>
        {busy ? (
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <FileDown className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
        )}
        {busy ? "Preparing PDF…" : "Export .pdf"}
      </button>
      {error && (
        <span role="alert" className="absolute top-full right-0 mt-1 w-64 text-right text-xs text-[#ff8b6e]">
          {error}
        </span>
      )}
    </span>
  );
}