import React, { useState, useEffect } from "react";
import Link from "next/link";

/* ─── Spinner ─────────────────────────────────────────────── */

export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const s = size === "sm" ? "h-5 w-5" : size === "lg" ? "h-10 w-10" : "h-7 w-7";
  return (
    <div className="flex items-center justify-center">
      <div className={`${s} relative`}>
        <div className="absolute inset-0 rounded-full border-2 border-[#3ef2ff]/30" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-[#3ef2ff] animate-spin" />
      </div>
    </div>
  );
}

/* ─── Launch Sequence Loader ──────────────────────────────── */

const LAUNCH_STEPS = [
  "Loading iML1515 \u00b7 2,712 reactions \u00b7 1,877 metabolites",
  "Applying regulation \u00b7 {conditions}",
  "Setting uptake bounds \u00b7 {carbon}, {nitrogen}",
  "Solving for maximum biomass",
  "Solution found",
];

export function LaunchSequence({
  conditions,
  onComplete,
}: {
  conditions?: { temperature: number; oxygen: string; carbon: string; nitrogen: string };
  onComplete?: () => void;
}) {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    if (visibleLines < LAUNCH_STEPS.length) {
      const timer = setTimeout(() => setVisibleLines((v) => v + 1), 430);
      return () => clearTimeout(timer);
    } else if (onComplete) {
      const timer = setTimeout(onComplete, 200);
      return () => clearTimeout(timer);
    }
  }, [visibleLines, onComplete]);

  const formatLine = (line: string) => {
    if (!conditions) return line;
    return line
      .replace("{conditions}", `${conditions.temperature} \u00b0C \u00b7 ${conditions.oxygen}`)
      .replace("{carbon}", conditions.carbon)
      .replace("{nitrogen}", conditions.nitrogen);
  };

  return (
    <div className="rounded-xl bg-[#01070c]/80 border border-white/[0.08] p-5 font-mono-readout text-sm leading-[1.75] text-[#8cc3d4]">
      {LAUNCH_STEPS.slice(0, visibleLines).map((line, i) => (
        <div key={i} className="launch-line" style={{ animationDelay: `${i * 0.05}s` }}>
          <span className="text-[#3ef2ff]">✓</span> {formatLine(line)}
        </div>
      ))}
      {visibleLines < LAUNCH_STEPS.length && (
        <div className="mt-2 flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-[#3ef2ff] pulse-glow" />
          <span className="text-xs text-[#5c8494]">Processing...</span>
        </div>
      )}
    </div>
  );
}

/* ─── Legacy SimulationLoader (uses LaunchSequence) ───────── */

export function SimulationLoader() {
  return <LaunchSequence />;
}

/* ─── Skeleton Row ────────────────────────────────────────── */

export function SkeletonRow() {
  return (
    <div className="flex gap-4 p-4 animate-pulse">
      <div className="h-4 w-24 bg-white/[0.06] rounded" />
      <div className="h-4 w-32 bg-white/[0.06] rounded" />
      <div className="h-4 w-16 bg-white/[0.06] rounded" />
    </div>
  );
}

/* ─── Empty State ─────────────────────────────────────────── */

export function EmptyState({
  icon = "\ud83e\uddea",
  title,
  description,
  actionLabel,
  actionHref,
}: {
  icon?: string;
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
}) {
  return (
    <div className="text-center py-12 px-6">
      <div className="text-4xl mb-3 opacity-60 drop-shadow-[0_0_14px_rgba(62,242,255,0.3)]">{icon}</div>
      <h3 className="text-lg font-semibold text-[#d9f7ff] mb-2">{title}</h3>
      {description && <p className="text-sm text-[#8cc3d4] max-w-sm mx-auto mb-4">{description}</p>}
      {actionLabel && actionHref && (
        <Link
          href={actionHref}
          className="inline-flex px-5 py-2 rounded-full bg-[#3ef2ff]/15 text-[#7dffef] border border-[#3ef2ff]/40 text-sm font-medium hover:bg-[#3ef2ff]/25 transition-all shadow-[0_0_16px_-4px_rgba(62,242,255,0.4)]"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}

/* ─── Error Banner ────────────────────────────────────────── */

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-[#ff5a36]/30 bg-[#ff5a36]/[0.06] backdrop-blur-sm p-4 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[#ff5a36]">\u26a0</span>
          <span className="text-sm text-[#ff8b6e]">{message}</span>
        </div>
        {onRetry && (
          <button onClick={onRetry} className="text-xs text-[#8cc3d4] hover:text-[#3ef2ff] transition-colors px-3 py-1 rounded-full border border-white/10 hover:border-[#3ef2ff]/30">
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
