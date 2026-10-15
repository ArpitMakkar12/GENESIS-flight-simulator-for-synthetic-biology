/*
 * Gene knockouts: shared types and wording.
 *
 * A knockout deletes genes from the metabolic model (iML1515). Each gene
 * may carry a record from the essential-gene check (backend/validation):
 * what the lab found, and whether GENESIS agreed. Both were measured in
 * RICH broth (LB), so every label says so — a gene can be harmless to lose
 * in broth but lethal on a minimal medium.
 */

export const MAX_KNOCKOUTS = 10;

export interface EssentialityRecord {
  lab_essential: boolean;    // lab: the cell cannot live without this gene (in LB)
  model_essential: boolean;  // GENESIS screen: knockout growth < 1% of wild type (in LB)
  outcome: "TP" | "TN" | "FP" | "FN";
  agrees: boolean;           // GENESIS made the same call as the lab
}

export interface KnockoutGene {
  locus_tag: string;          // e.g. "b0903"
  name: string | null;        // e.g. "pflB"
  product?: string | null;
  record?: EssentialityRecord | null;
}

export interface KnockoutBlock {
  genes: KnockoutGene[];
  wild_type: {
    growth_rate: number;
    doubling_time: number | null;
    growth_state: string;
    solver_status: string;
    pathway_fluxes?: Record<string, number>;
  };
}

/** "pflB" or the locus tag when the gene has no name. */
export const geneLabel = (g: { name?: string | null; locus_tag: string }) => g.name || g.locus_tag;

/** "Essential in LB" / "Not essential in LB" / null when never screened. */
export function labLabel(record?: EssentialityRecord | null): string | null {
  if (!record) return null;
  return record.lab_essential ? "Essential in LB" : "Not essential in LB";
}

/** One sentence on how GENESIS did on this gene in the screen. */
export function trackRecord(record?: EssentialityRecord | null): string {
  if (!record) return "Not in the lab data, so there is no track record for this gene.";
  const lab = record.lab_essential ? "essential" : "not essential";
  return record.agrees
    ? `The lab found it ${lab} in LB broth, and the GENESIS screen agreed.`
    : `The lab found it ${lab} in LB broth; the GENESIS screen called it ${record.model_essential ? "essential" : "not essential"}.`;
}

/** Signed percent change, e.g. "−19%" (true minus sign), "+0%" when unchanged. */
export function percentChange(from: number, to: number): string {
  if (from <= 0) return "—";
  const pct = Math.round(((to - from) / from) * 100);
  return pct < 0 ? `−${Math.abs(pct)}%` : `+${pct}%`;
}