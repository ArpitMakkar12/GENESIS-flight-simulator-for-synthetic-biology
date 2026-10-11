"use client";

import { Search, X, LoaderCircle } from "lucide-react";

/**
 * The one search box used by every Library tab, so Parts, Genes,
 * Transcription Factors and Pathways all behave the same way:
 * results update as you type, no separate Search button to press.
 *
 * The magnifier sits inside the box on the left, a clear (×) button
 * appears on the right once there is text, and a small spinner replaces
 * the magnifier while a server search is in flight.
 */
export function LibrarySearch({
  value,
  onChange,
  placeholder,
  busy = false,
  label,
  className = "",
}: {
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
  /** true while waiting for the server, so the icon becomes a spinner */
  busy?: boolean;
  /** accessible name, e.g. "Search genes" */
  label: string;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      {busy ? (
        <LoaderCircle
          className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-[#7dffef]"
          aria-hidden="true"
        />
      ) : (
        <Search
          className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#5c8494]"
          aria-hidden="true"
        />
      )}

      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Escape") onChange(""); }}
        placeholder={placeholder}
        aria-label={label}
        className="w-full rounded-xl border border-white/10 bg-[#01070c]/60 py-2.5 pl-10 pr-10 text-sm text-[#eaffff] placeholder-[#5c8494] transition-colors focus:border-[#3ef2ff]/60 focus:outline-none"
      />

      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-[#5c8494] transition-colors hover:text-[#eaffff]"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export default LibrarySearch;