/*
 * One place for how a simulation is named and how its numbers and dates look.
 * Every page imports from here, so the Results list, the detail page, the
 * home page, compare and the Markdown export all show the same thing.
 */

export interface SimIdentity {
  run_number?: number | null;
  name?: string | null;
  temperature: number;
  ph: number;
  oxygen_level: string;
  carbon_source: string;
}

/** Unit for growth rate, used everywhere (was a mix of "h⁻¹" and "hr⁻¹"). */
export const GROWTH_UNIT = "h⁻¹";

const capitalize = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

/** "#12" (empty for very old rows that somehow have no number). */
export function runLabel(sim: { run_number?: number | null }): string {
  return sim.run_number != null ? `#${sim.run_number}` : "";
}

/** Title built from the conditions: "Glucose · microaerobic · 37 °C · pH 7". */
export function autoTitle(sim: SimIdentity): string {
  return `${capitalize(sim.carbon_source)} · ${sim.oxygen_level} · ${sim.temperature} °C · pH ${sim.ph}`;
}

/** The name the user gave it, or the auto title when there is none. */
export function simTitle(sim: SimIdentity): string {
  return sim.name?.trim() || autoTitle(sim);
}

/** "#12 · Heat shock test" — for places with room for only one line. */
export function fullTitle(sim: SimIdentity): string {
  const run = runLabel(sim);
  return run ? `${run} · ${simTitle(sim)}` : simTitle(sim);
}

/** Short condition line for under a custom name: "37 °C · pH 7 · microaerobic · glucose". */
export function conditionLine(sim: SimIdentity): string {
  return `${sim.temperature} °C · pH ${sim.ph} · ${sim.oxygen_level} · ${sim.carbon_source}`;
}

/** "Oct 6, 2026, 4:08 AM" — same format on every page. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** "0.228 h⁻¹" — always 3 decimals so columns line up. */
export function formatGrowth(value: number | null | undefined, withUnit = true): string {
  if (value == null) return "—";
  return withUnit ? `${value.toFixed(3)} ${GROWTH_UNIT}` : value.toFixed(3);
}