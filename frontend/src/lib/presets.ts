/**
 * Shared preset definitions for GENESIS.
 * Single source of truth — imported by both /simulate and / (home).
 */

export interface EnvParams {
  temperature: number;
  ph: number;
  oxygen: string;
  carbon: string;
  nitrogen: string;
}

export const DEFAULT_PARAMS: EnvParams = {
  temperature: 37,
  ph: 7,
  oxygen: "aerobic",
  carbon: "glucose",
  nitrogen: "ammonium",
};

export const PRESETS: Record<string, { label: string; params: EnvParams }> = {
  reference: {
    label: "Reference",
    params: { temperature: 37, ph: 7, oxygen: "aerobic", carbon: "glucose", nitrogen: "ammonium" },
  },
  anaerobic: {
    label: "Anaerobic",
    params: { temperature: 37, ph: 7, oxygen: "anaerobic", carbon: "glucose", nitrogen: "ammonium" },
  },
  heatShock: {
    label: "Heat Shock",
    params: { temperature: 42, ph: 7, oxygen: "aerobic", carbon: "glucose", nitrogen: "ammonium" },
  },
  acidStress: {
    label: "Acid Stress",
    params: { temperature: 37, ph: 5.5, oxygen: "aerobic", carbon: "glycerol", nitrogen: "ammonium" },
  },
  glycerolFeed: {
    label: "Glycerol Feed",
    params: { temperature: 37, ph: 7, oxygen: "aerobic", carbon: "glycerol", nitrogen: "ammonium" },
  },
};

/** Shallow-compare two EnvParams objects. */
export function shallowEqual(a: EnvParams, b: EnvParams): boolean {
  return (
    a.temperature === b.temperature &&
    a.ph === b.ph &&
    a.oxygen === b.oxygen &&
    a.carbon === b.carbon &&
    a.nitrogen === b.nitrogen
  );
}

/** Build a URL search string for a preset (used by Home "Try It Now" cards). */
export function presetToSearchParams(id: string): string {
  const p = PRESETS[id].params;
  return `temperature=${p.temperature}&ph=${p.ph}&oxygen_level=${p.oxygen}&carbon_source=${p.carbon}&nitrogen_source=${p.nitrogen}`;
}

/** Stat constants used by the hero and the "By the Numbers" section. */
export const GENESIS_STATS = {
  genes: { value: "4,651", label: "Genes", source: "E. coli K-12 MG1655" },
  reactions: { value: "2,712", label: "Reactions", source: "iML1515 FBA model" },
  tfs: { value: "371", label: "Transcription Factors", source: "PRECISE-1K network" },
  parts: { value: "23", label: "Parts", source: "iGEM Registry" },
} as const;
