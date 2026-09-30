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

  // Strength — applicable to promoters, RBS, terminators; not CDS
  if (type === "cds") {
    fields.push(notApplicable("Strength", "Not applicable to CDS parts"));
  } else {
    fields.push(
      populated("Strength", part.strength, (v) => (
        <span className="font-mono-readout">{(Number(v) * 100).toFixed(0)}%</span>
      ))
    );
  }

  // Protein / Product — only for CDS
  if (type === "cds") {
    const protein = part.annotations?.protein;
    const func = part.annotations?.function;
    fields.push(populated("Protein", protein));
    fields.push(populated("Function", func));
  } else {
    fields.push(notApplicable("Protein", `Not applicable to ${type} parts`));
  }

  // Inducer / Repressor — only for promoters
  if (type === "promoter") {
    const annoType = part.annotations?.type;
    if (annoType === "constitutive") {
      fields.push(notApplicable("Inducer", "Not applicable — constitutive promoter"));
      fields.push(notApplicable("Repressor", "Not applicable — constitutive promoter"));
    } else if (annoType === "phage") {
      const requires = part.annotations?.requires;
      fields.push(notApplicable("Inducer", `Not applicable — requires ${requires || "phage polymerase"}`));
      fields.push(notApplicable("Repressor", `Not applicable — requires ${requires || "phage polymerase"}`));
    } else {
      fields.push(populated("Inducer", part.annotations?.inducer));
      fields.push(populated("Repressor", part.annotations?.repressor));
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
