/*
 * Pathway differences between 2–4 runs.
 *
 * Uses pathway_fluxes: the total flux through EVERY pathway, which the
 * backend works out when a run is opened. (The older active_pathways list
 * only holds each run's top 15, so a pathway missing from it may still be
 * running — comparing those lists made false "only in A" claims.)
 *
 * Two kinds of difference are reported:
 *   1. Switched on/off: carries flux in some runs and none in others.
 *   2. Biggest changes: runs in all of them, but at very different levels
 *      AFTER allowing for growth. A cell growing 3× faster builds 3× more of
 *      everything, so raw flux ratios would mostly repeat the growth ratio.
 *      Dividing each run's pathway flux by its growth rate removes that, and
 *      what is left is a real shift in how the cell uses its metabolism.
 */

export const MAX_COMPARE = 4;

/** Below this total flux a pathway counts as off (tiny traces are not "on"). */
const ACTIVE_THRESHOLD = 0.05;
/** Growth-adjusted max/min ratio a shared pathway needs to count as a big change. */
const CHANGE_RATIO = 2;
/** The raw totals must also differ by at least this much. */
const MIN_RAW_RATIO = 1.25;

export interface PathwaySource {
  growth_rate?: number | null;
  fba_results?: {
    pathway_fluxes?: Record<string, number> | null;
    active_pathways?: string[] | null;
  } | null;
}

export interface PathwayRow {
  pathway: string;
  values: number[];   // total flux per run (0 = off)
  ratio?: number;     // max ÷ min of flux per unit growth, for big changes
}

export interface PathwayDiff {
  exact: boolean;            // true when every run has full pathway totals
  growthAdjusted: boolean;   // big changes were measured per unit of growth
  shared: string[];          // on in every run
  switched: PathwayRow[];    // on in some, off in others
  bigChanges: PathwayRow[];  // on in all, ≥ CHANGE_RATIO× apart
}

export function pathwayDiff(sims: PathwaySource[], maxRows = 12): PathwayDiff {
  const exact = sims.every((s) => s.fba_results?.pathway_fluxes && Object.keys(s.fba_results.pathway_fluxes).length > 0);

  // Flux per pathway per run. Without full totals, fall back to the top-15
  // lists (1 = listed, 0 = not listed) — the UI says so when this happens.
  const tables: Record<string, number>[] = sims.map((s) => {
    if (exact) return s.fba_results!.pathway_fluxes as Record<string, number>;
    return Object.fromEntries((s.fba_results?.active_pathways ?? []).map((p) => [p, 1]));
  });

  const all = Array.from(new Set(tables.flatMap((t) => Object.keys(t))));
  // Growth-adjusted comparison needs every run to be growing
  const growth = sims.map((s) => s.growth_rate ?? 0);
  const canAdjust = growth.every((g) => g > 0.01);
  const shared: string[] = [];
  const switched: PathwayRow[] = [];
  const bigChanges: PathwayRow[] = [];

  for (const pathway of all) {
    const values = tables.map((t) => t[pathway] ?? 0);
    const on = values.map((v) => v > ACTIVE_THRESHOLD);
    if (on.every(Boolean)) {
      shared.push(pathway);
      const perGrowth = canAdjust ? values.map((v, i) => v / growth[i]) : values;
      const ratio = Math.max(...perGrowth) / Math.min(...perGrowth);
      // A pathway whose raw flux is the same everywhere has not shifted, even if
      // dividing by growth makes it look different (e.g. the fixed maintenance cost)
      const rawRatio = Math.max(...values) / Math.min(...values);
      if (exact && ratio >= CHANGE_RATIO && rawRatio >= MIN_RAW_RATIO) bigChanges.push({ pathway, values, ratio });
    } else if (on.some(Boolean)) {
      switched.push({ pathway, values });
    }
  }

  // Most flux first, so the differences that matter most lead
  switched.sort((a, b) => Math.max(...b.values) - Math.max(...a.values));
  bigChanges.sort((a, b) => (b.ratio ?? 0) - (a.ratio ?? 0));
  shared.sort((a, b) => a.localeCompare(b));

  return { exact, growthAdjusted: canAdjust, shared, switched: switched.slice(0, maxRows), bigChanges: bigChanges.slice(0, maxRows) };
}

/** "both" for 2 runs, "all 3" / "all 4" otherwise. */
export const allOf = (n: number) => (n === 2 ? "both" : `all ${n}`);

/** Table cell text for one pathway value. */
export function fmtPathway(v: number, exact: boolean): string {
  if (!exact) return v > 0 ? "✓" : "—";
  if (v <= ACTIVE_THRESHOLD) return "—";
  return v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2);
}