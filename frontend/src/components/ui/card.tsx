import React from "react";
import type { LucideIcon } from "lucide-react";
import { growthStateLabel, referenceNote } from "@/lib/sim-format";

/* ─── Glass Card ──────────────────────────────────────────── */

export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-white/[0.12] bg-white/[0.05] backdrop-blur-[18px] ${
        hover ? "glass-hover cursor-pointer" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

/* ─── Metric Card ─────────────────────────────────────────── */

const METRIC_COLORS: Record<string, { text: string; glow: string }> = {
  green: { text: "text-[#7dffef]", glow: "shadow-[0_0_12px_-4px_rgba(62,242,255,0.4)]" },
  cyan: { text: "text-[#3ef2ff]", glow: "shadow-[0_0_12px_-4px_rgba(62,242,255,0.4)]" },
  blue: { text: "text-[#7dccff]", glow: "shadow-[0_0_12px_-4px_rgba(125,204,255,0.3)]" },
  purple: { text: "text-[#d4bcff]", glow: "shadow-[0_0_12px_-4px_rgba(185,139,255,0.3)]" },
  yellow: { text: "text-[#ffcf66]", glow: "shadow-[0_0_12px_-4px_rgba(255,207,102,0.3)]" },
  red: { text: "text-[#ff8b6e]", glow: "shadow-[0_0_12px_-4px_rgba(255,90,54,0.3)]" },
  gray: { text: "text-[#8cc3d4]", glow: "" },
};

export function MetricCard({
  label,
  value,
  color = "cyan",
  icon: Icon,
  subtitle,
}: {
  label: string;
  value: string;
  color?: string;
  icon?: LucideIcon;
  subtitle?: string;
}) {
  const c = METRIC_COLORS[color] || METRIC_COLORS.cyan;
  return (
    <Card className={`p-4 ${c.glow}`}>
      <div className="flex items-start gap-2">
        {Icon && <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${c.text}`} strokeWidth={1.75} aria-hidden="true" />}
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-medium text-[#8cc3d4] uppercase tracking-wider mb-1">{label}</div>
          <div className={`text-xl font-semibold font-mono-readout ${c.text} leading-none`}>{value}</div>
          {subtitle && <div className="text-[10px] text-[#5c8494] mt-1">{subtitle}</div>}
        </div>
      </div>
    </Card>
  );
}

/* ─── Status Badge ────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  optimal: "bg-[#3ef2ff]/10 text-[#7dffef] border-[#3ef2ff]/25",
  slowed: "bg-[#ffcf66]/10 text-[#ffcf66] border-[#ffcf66]/25",
  stressed: "bg-[#ff5a36]/10 text-[#ff8b6e] border-[#ff5a36]/25",
  "not-viable": "bg-[#ff5a36]/20 text-[#ff5a36] border-[#ff5a36]/50",
  stalled: "bg-white/[0.05] text-[#5c8494] border-white/10",
  running: "bg-[#b98bff]/10 text-[#d4bcff] border-[#b98bff]/25",
};

/**
 * Coloured pill for a run's state. Growth states show friendlier words
 * ("stressed" → "much slower", see growthStateLabel); pass growthRate to get
 * a hover note like "28% of reference growth (...)".
 */
export function StatusBadge({ status, growthRate }: { status: string; growthRate?: number | null }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.stalled;
  const note = referenceNote(growthRate);
  return (
    <span
      className={`inline-flex px-2.5 py-0.5 text-[11px] font-medium rounded-full border whitespace-nowrap ${style}`}
      title={note || undefined}
    >
      {growthStateLabel(status)}
    </span>
  );
}

/* ─── Pathway Tag ─────────────────────────────────────────── */

export function PathwayTag({ name }: { name: string }) {
  return (
    <span className="inline-flex px-3 py-1 text-[11px] rounded-full border border-[#3ef2ff]/25 bg-[#3ef2ff]/[0.06] text-[#7dffef] font-medium">
      {name}
    </span>
  );
}

/* ─── Detail Row ──────────────────────────────────────────── */

export function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-white/[0.06] last:border-0">
      <span className="text-[#8cc3d4] text-sm">{label}</span>
      <span className="text-[#eaffff] text-sm font-mono-readout">{value}</span>
    </div>
  );
}