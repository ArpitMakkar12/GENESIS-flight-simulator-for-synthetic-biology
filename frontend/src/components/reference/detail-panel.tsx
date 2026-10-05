/**
 * Shared Reference Detail Panel for the Reference Library.
 * Used by Parts, Genes, TFs, and Pathways.
 *
 * Field states:
 *   "populated"  → shows the real value
 *   "na"         → italic muted: "Not applicable — {reason}"
 *   "pending"    → small "pending" tag
 */

import React from "react";
import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { X } from "lucide-react";

/* ─── Field state types ─────────────────────────────────── */

export type FieldState = "populated" | "na" | "pending";

export interface DetailField {
  label: string;
  value: React.ReactNode;
  state: FieldState;
  /** Reason shown for "na" state, e.g. "Not applicable to CDS parts" */
  naReason?: string;
}

/* ─── Field renderers ───────────────────────────────────── */

function FieldValue({ field }: { field: DetailField }) {
  switch (field.state) {
    case "populated":
      return <span className="text-[#eaffff]">{field.value}</span>;
    case "na":
      return (
        <span className="text-[#5c8494] text-xs italic">
          {field.naReason || "Not applicable"}
        </span>
      );
    case "pending":
      return (
        <span className="inline-flex px-2 py-0.5 text-[10px] rounded-full bg-white/[0.05] text-[#5c8494] border border-white/10">
          Not yet catalogued
        </span>
      );
    default:
      return null;
  }
}

/* ─── Detail Panel ──────────────────────────────────────── */

export interface ReferenceDetailPanelProps {
  /** Title (e.g. part name, gene name) */
  title: string;
  /** Optional subtitle (e.g. type badge) */
  subtitle?: React.ReactNode;
  /** Field rows */
  fields: DetailField[];
  /** Optional bottom section (e.g. sequence block, reaction list) */
  children?: React.ReactNode;
  /** Close handler */
  onClose: () => void;
}

export function ReferenceDetailPanel({
  title,
  subtitle,
  fields,
  children,
  onClose,
}: ReferenceDetailPanelProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-[#3ef2ff]">{title}</h3>
          {subtitle && <div className="mt-0.5">{subtitle}</div>}
        </div>
        <button
          onClick={onClose}
          aria-label="Close detail panel"
          className="text-[#5c8494] hover:text-white transition-colors text-lg leading-none ml-3"
        >
          <X className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
        </button>
      </div>

      <div className="space-y-0">
        {fields.map((field) => (
          <div
            key={field.label}
            className="flex justify-between items-baseline py-1.5 border-b border-white/[0.06] last:border-0"
          >
            <span className="text-[#8cc3d4] text-sm">{field.label}</span>
            <div className="text-sm text-right">
              <FieldValue field={field} />
            </div>
          </div>
        ))}
      </div>

      {children}
    </Card>
  );
}

/* ─── Empty State ───────────────────────────────────────── */

export function DetailEmptyState({
  icon: Icon,
  text,
}: {
  icon: LucideIcon;
  text: string;
}) {
  return (
    <Card className="p-8 text-center border-dashed">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[#3ef2ff]/[0.06] ring-1 ring-[#3ef2ff]/15">
        <Icon className="h-6 w-6 text-[#7dffef]/70" strokeWidth={1.5} aria-hidden="true" />
      </div>
      <p className="text-sm text-[#5c8494]">{text}</p>
    </Card>
  );
}

/* ─── Footer Count ──────────────────────────────────────── */

export function ResultCount({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-4 py-2 border-t border-white/[0.06] text-xs text-[#5c8494]">
      {children}
    </div>
  );
}
