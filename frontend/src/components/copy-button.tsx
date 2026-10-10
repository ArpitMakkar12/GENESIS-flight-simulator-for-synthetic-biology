"use client";

import { useEffect, useRef, useState } from "react";

type State = "idle" | "copied" | "failed";

/**
 * Icon-only copy button with a small animation:
 *   1. the front sheet slides onto the back sheet (the "copy"),
 *   2. both fade out while a tick draws itself in,
 *   3. a "Copied" label slides in beside the button,
 *   4. after a moment it all returns to the copy icon.
 * If the browser blocks the clipboard, it shows a cross and "Copy failed".
 * Everything is plain CSS transitions, so no extra library or global CSS.
 */
export function CopyButton({
  getText,
  label = "Copy",
  className = "",
}: {
  /** Called on click, so large text (like the raw JSON) is only built when needed */
  getText: () => string;
  /** Accessible name, e.g. "Copy raw JSON" */
  label?: string;
  className?: string;
}) {
  const [state, setState] = useState<State>("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const copy = async () => {
    if (timer.current) clearTimeout(timer.current);
    try {
      await navigator.clipboard.writeText(getText());
      setState("copied");
    } catch {
      setState("failed");
    }
    timer.current = setTimeout(() => setState("idle"), 1800);
  };

  const copied = state === "copied";
  const failed = state === "failed";
  const busy = state !== "idle";
  // shared transition settings; switched off for people who prefer less motion
  const t = "transition-all duration-300 ease-out motion-reduce:transition-none";

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {/* Status text: slides in from the right, read out by screen readers */}
      <span
        aria-live="polite"
        className={`${t} text-xs font-medium whitespace-nowrap ${
          busy ? "opacity-100 translate-x-0" : "opacity-0 translate-x-2 pointer-events-none"
        } ${failed ? "text-[#ff8b6e]" : "text-[#7dffef]"}`}
      >
        {copied ? "Copied" : failed ? "Copy failed" : ""}
      </span>

      <button
        type="button"
        onClick={copy}
        aria-label={label}
        title={label}
        className={`${t} relative grid place-items-center h-8 w-8 rounded-lg border backdrop-blur-sm active:scale-90 ${
          copied
            ? "border-[#3ef2ff]/60 bg-[#3ef2ff]/15 shadow-[0_0_14px_rgba(62,242,255,0.35)]"
            : failed
              ? "border-[#ff8b6e]/50 bg-[#ff8b6e]/10"
              : "border-white/10 bg-[#031722]/80 hover:bg-white/[0.08] hover:border-white/20"
        }`}
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 overflow-visible" fill="none" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          {/* back sheet */}
          <path
            d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"
            stroke="#8cc3d4"
            className={t}
            style={{ opacity: busy ? 0 : 1, transitionDelay: busy ? "120ms" : "0ms" }}
          />
          {/* front sheet: slides up-left onto the back sheet, then fades */}
          <rect
            x="8" y="8" width="14" height="14" rx="2"
            stroke="#eaffff"
            className={t}
            style={{
              transform: busy ? "translate(-6px, -6px) scale(0.9)" : "none",
              transformOrigin: "15px 15px",
              opacity: busy ? 0 : 1,
            }}
          />
          {/* tick: draws itself in after the sheets merge */}
          <path
            d="M5 12.5l4.5 4.5L19 7.5"
            stroke="#3ef2ff"
            strokeWidth={2.4}
            className={t}
            style={{
              strokeDasharray: 24,
              strokeDashoffset: copied ? 0 : 24,
              transitionDuration: copied ? "380ms" : "150ms",
              transitionDelay: copied ? "180ms" : "0ms",
            }}
          />
          {/* cross: shown only if copying failed */}
          <path
            d="M7 7l10 10M17 7L7 17"
            stroke="#ff8b6e"
            strokeWidth={2.2}
            className={t}
            style={{ opacity: failed ? 1 : 0, transitionDelay: failed ? "150ms" : "0ms" }}
          />
        </svg>
      </button>
    </span>
  );
}

export default CopyButton;