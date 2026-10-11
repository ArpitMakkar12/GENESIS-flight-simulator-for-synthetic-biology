/**
 * Field contract definitions for the Reference Library.
 * Each entity type declares which fields it shows, and the rule
 * for whether each field is Populated, Not-applicable, or Pending.
 */

import { DetailField } from "@/components/reference/detail-panel";

/* ─── Helper: treat "N/A", null, undefined, empty as missing ─── */

function isMissing(v: unknown): boolean {
  if (v === null || v === undefined) return true;
  if (typeof v === "string" && (v === "" || v.toUpperCase() === "N/A")) return true;
  return false;
}

/** Create a populated field, or pending if the value is missing. */
export function populated(label: string, value: unknown, format?: (v: unknown) => React.ReactNode): DetailField {
  if (isMissing(value)) {
    return { label, value: null, state: "pending" };
  }
  return { label, value: format ? format(value) : String(value), state: "populated" };
}

/** Create a not-applicable field. */
export function notApplicable(label: string, reason: string): DetailField {
  return { label, value: null, state: "na", naReason: reason };
}

/** Create an explicitly pending field. */
export function pending(label: string): DetailField {
  return { label, value: null, state: "pending" };
}

import React from "react";

/* ─── Part activity: what the "Strength / role" column should say ───
 *
 * One number can't describe every part, so each type gets the measure that
 * fits it. All the information comes from the part's own data (strength and
 * annotations), so nothing is hard-coded per part:
 *
 *   constitutive promoter → bar, % of BBa_J23100 (the reference promoter)
 *   inducible promoter    → "Inducible · IPTG"  (output depends on the inducer)
 *   phage promoter        → "Needs T7 RNAP"     (silent without its polymerase)
 *   RBS                   → bar, % of BBa_B0034 (the reference RBS)
 *   terminator            → bar, termination efficiency (how much it stops)
 *   CDS                   → what it encodes, e.g. "LacI · repressor"
 *
 * In the data, inducible and phage promoters are stored with strength 0.
 * That 0 means "no fixed value", not "off", so it is never drawn as 0%.
 * The list table and the detail panel both use this one helper.
 */
export type StrengthInfo =
  | { kind: "value"; fraction: number; percent: number; basis: string }  // bar + %
  | { kind: "conditional"; label: string; detail: string }               // inducible promoter
  | { kind: "requires"; label: string; detail: string }                  // e.g. T7 promoter
  | { kind: "encodes"; label: string; detail: string }                   // CDS
  | { kind: "na"; reason: string };                                      // nothing recorded

/** Shorter form for badges: "T7 RNA polymerase" → "T7 RNAP". */
function shortPolymerase(text: string): string {
  return text.replace(/RNA polymerase/i, "RNAP");
}

function str(v: unknown): string {
  return typeof v === "string" ? v.trim() : "";
}

export function partStrength(
  partType: string | null | undefined,
  strength: number | null | undefined,
  annotations?: Record<string, unknown> | null,
): StrengthInfo {
  const type = (partType || "").toLowerCase();
  const anno = annotations || {};
  const hasValue = typeof strength === "number" && strength > 0;

  // CDS: no strength; say what protein it makes and what that protein does
  if (type === "cds") {
    const protein = str(anno.protein);
    const role =
      str(anno.function) ||
      (anno.excitation != null || anno.emission != null ? "fluorescent reporter" : "");
    if (!protein) return { kind: "na", reason: "Protein not recorded" };
    const light =
      anno.excitation != null && anno.emission != null
        ? ` (excitation ${anno.excitation} nm, emission ${anno.emission} nm)`
        : "";
    return {
      kind: "encodes",
      label: role ? `${protein} · ${role}` : protein,
      detail: `Encodes ${protein}${role ? `, a ${role}` : ""}${light}`,
    };
  }

  if (type === "promoter" && !hasValue) {
    // Phage promoters are silent unless their own polymerase is present
    const requires = str(anno.requires);
    if (requires) {
      return {
        kind: "requires",
        label: `Needs ${shortPolymerase(requires)}`,
        detail: `Only active when ${requires} is present in the cell`,
      };
    }
    // Inducible: off (or low) until the inducer is added
    const inducer = str(anno.inducer);
    const repressor = str(anno.repressor);
    return {
      kind: "conditional",
      label: inducer ? `Inducible · ${inducer}` : "Inducible",
      detail:
        (inducer ? `Turned on by ${inducer}` : "Turned on by its inducer") +
        (repressor ? `; held off by ${repressor} until then` : ""),
    };
  }

  if (hasValue) {
    // Terminators: prefer the measured efficiency when the data has it
    if (type === "terminator") {
      const eff = typeof anno.efficiency === "number" ? anno.efficiency : (strength as number);
      return { kind: "value", fraction: eff, percent: Math.round(eff * 100), basis: "termination efficiency" };
    }
    const basis =
      type === "promoter" ? "of BBa_J23100" :
      type === "rbs" ? "of BBa_B0034" :
      "relative strength";
    return { kind: "value", fraction: strength as number, percent: Math.round((strength as number) * 100), basis };
  }

  return { kind: "na", reason: "Not yet characterised" };
}

/* ─── Part field config ───────────────────────────────── */

interface PartData {
  name: string;
  part_type: string;
  sequence_length: number | null;
  source: string | null;
  registry_id: string | null;
  strength: number | null;
  sequence: string | null;
  annotations: Record<string, string | number | boolean> | null;
}

export function getPartFields(part: PartData): DetailField[] {
  const fields: DetailField[] = [];
  const type = part.part_type?.toLowerCase();

  // Type
  fields.push(populated("Type", part.part_type));

  // Part Length (total iGEM Registry part length, includes downstream registry sequence)
  fields.push(
    populated("Part Length", part.sequence_length, (v) => (
      <span className="font-mono-readout">{Number(v).toLocaleString()} bp</span>
    ))
  );

  // Coding Sequence — only for CDS, computed from the actual sequence
  if (type === "cds" && part.sequence && part.sequence.toUpperCase() !== "N/A") {
    const seq = part.sequence.toUpperCase();
    const stops = new Set(["TAA", "TAG", "TGA"]);
    let stopIdx = -1;
    for (let i = 0; i <= seq.length - 3; i += 3) {
      if (stops.has(seq.substring(i, i + 3))) { stopIdx = i; break; }
    }
    if (stopIdx > 0) {
      const orfBp = stopIdx;
      const orfAa = orfBp / 3;
      fields.push(populated("Coding Sequence", orfBp, () => (
        <span className="font-mono-readout">{orfBp.toLocaleString()} bp ({orfAa} aa)</span>
      )));
    }
  }

  // Source / Registry ID
  fields.push(populated("Source", part.source));
  if (part.registry_id) {
    fields.push(populated("Registry ID", part.registry_id, (v) => (
      <span className="text-[#3ef2ff] font-mono-readout">{String(v)}</span>
    )));
  }

  // Strength / efficiency — one rule, shared with the list table
  const strength = partStrength(part.part_type, part.strength, part.annotations);
  if (strength.kind === "value") {
    const label = type === "terminator" ? "Efficiency" : "Strength";
    fields.push(populated(label, strength.fraction, () => (
      <span>
        <span className="font-mono-readout">{strength.percent}%</span>
        <span className="ml-1.5 text-xs text-[#5c8494]">{strength.basis}</span>
      </span>
    )));
  } else if (strength.kind === "conditional" || strength.kind === "requires") {
    // e.g. "Inducible · IPTG" with the explanation underneath
    fields.push(populated("Strength", strength.label, () => (
      <span className="text-right">
        <span className="block">{strength.label}</span>
        <span className="block text-xs text-[#8cc3d4]">{strength.detail}</span>
      </span>
    )));
  } else if (strength.kind === "encodes") {
    fields.push(notApplicable("Strength", "Not applicable — a CDS makes a protein; its output is set by the promoter and RBS in front of it"));
  } else {
    fields.push(notApplicable("Strength", strength.reason));
  }

  // Protein / Product — only for CDS
  if (type === "cds") {
    const protein = part.annotations?.protein;
    fields.push(populated("Protein", protein));
    // Function: from the data, or "fluorescent reporter" for GFP / mRFP1 etc.
    const fluor = part.annotations?.excitation != null && part.annotations?.emission != null;
    const func = part.annotations?.function ?? (fluor ? "fluorescent reporter" : null);
    fields.push(populated("Function", func));
    if (fluor) {
      fields.push(populated("Light", part.annotations?.excitation, () => (
        <span className="font-mono-readout">ex {String(part.annotations?.excitation)} / em {String(part.annotations?.emission)} nm</span>
      )));
    }
  } else {
    fields.push(notApplicable("Protein", `Not applicable to ${type} parts`));
  }

  // Inducer / Repressor — only for promoters. A promoter with a fixed
  // strength is constitutive (no inducer); otherwise it is signal-driven.
  if (type === "promoter") {
    if (strength.kind === "value") {
      fields.push(notApplicable("Inducer", "Not applicable — constitutive promoter"));
      fields.push(notApplicable("Repressor", "Not applicable — constitutive promoter"));
    } else {
      const requires = part.annotations?.requires;
      if (requires) {
        // phage promoters (e.g. T7) need their own polymerase, not an inducer
        fields.push(notApplicable("Inducer", `Not applicable — requires ${requires}`));
        fields.push(notApplicable("Repressor", `Not applicable — requires ${requires}`));
      } else {
        fields.push(populated("Inducer", part.annotations?.inducer));
        fields.push(populated("Repressor", part.annotations?.repressor));
      }
    }
  }

  return fields;
}

/* ─── Gene field config ───────────────────────────────── */

interface GeneData {
  locus_tag: string;
  name: string | null;
  product: string | null;
  start_pos: number;
  end_pos: number;
  strand: string;
  gc_content: number | null;
  length_bp: number | null;
}

export function getGeneFields(gene: GeneData): DetailField[] {
  return [
    populated("Locus Tag", gene.locus_tag, (v) => (
      <span className="font-mono-readout">{String(v)}</span>
    )),
    populated("Gene Name", gene.name),
    populated("Product", gene.product),
    populated("Position", `${gene.start_pos}–${gene.end_pos}`, () => (
      <span className="font-mono-readout">{gene.start_pos.toLocaleString()} – {gene.end_pos.toLocaleString()}</span>
    )),
    populated("Strand", gene.strand, () => gene.strand === "+" ? "Forward (+)" : "Reverse (−)"),
    populated("Length", gene.length_bp, (v) => (
      <span className="font-mono-readout">{Number(v).toLocaleString()} bp</span>
    )),
    populated("GC Content", gene.gc_content, (v) => (
      <span className="font-mono-readout">{(Number(v) * 100).toFixed(1)}%</span>
    )),
  ];
}

/* ─── TF field config ─────────────────────────────────── */

interface TFData {
  name: string;
  tf_family: string | null;
  sensing_signal: string | null;
  active_form: string | null;
  regulated_gene_count: number;
}

export function getTFFields(tf: TFData): DetailField[] {
  return [
    populated("Name", tf.name),
    populated("Regulated Genes", tf.regulated_gene_count, (v) => (
      <span className="font-mono-readout">{Number(v).toLocaleString()}</span>
    )),
    // These exist in the schema but are not populated yet
    tf.tf_family ? populated("Family", tf.tf_family) : pending("Family"),
    tf.sensing_signal ? populated("Sensing Signal", tf.sensing_signal) : pending("Sensing Signal"),
    tf.active_form ? populated("Active Form", tf.active_form) : pending("Active Form"),
  ];
}

/* ─── Pathway field config ────────────────────────────── */

interface PathwayData {
  subsystem: string;
  reaction_count: number;
}

export function getPathwayFields(pw: PathwayData): DetailField[] {
  return [
    populated("Subsystem", pw.subsystem),
    populated("Reactions", pw.reaction_count, (v) => (
      <span className="font-mono-readout">{Number(v).toLocaleString()}</span>
    )),
  ];
}