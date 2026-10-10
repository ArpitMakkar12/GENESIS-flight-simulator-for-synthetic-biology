/*
 * Key numbers pulled out of a run's flux solution, plus a short plain-language
 * reading of what the cell is doing. Used by the Markdown reports and the
 * Compare page so they all describe a run the same way.
 *
 * Fluxes are in mmol per gram of dry cell weight per hour (mmol/gDW/h).
 * Reaction IDs are iML1515 (BiGG) names, the same ones the flux map uses.
 */

import { percentOfReference, formatGrowth } from "@/lib/sim-format";

export const FLUX_UNIT = "mmol/gDW/h";

/** Exchange reaction for each carbon source (same as the backend and flux map). */
export const CARBON_EXCHANGE: Record<string, string> = {
  glucose: "EX_glc__D_e",
  fructose: "EX_fru_e",
  galactose: "EX_gal_e",
  lactose: "EX_lcts_e",
  glycerol: "EX_glyc_e",
  xylose: "EX_xyl__D_e",
  arabinose: "EX_arab__L_e",
  acetate: "EX_ac_e",
  succinate: "EX_succ_e",
};

/** Products E. coli can release, with the exchange reaction for each. */
const PRODUCTS: [string, string][] = [
  ["Acetate", "EX_ac_e"],
  ["Formate", "EX_for_e"],
  ["Ethanol", "EX_etoh_e"],
  ["Lactate", "EX_lac__D_e"],
  ["Succinate", "EX_succ_e"],
];

export interface KeyFluxes {
  carbonUptake: number;      // nutrient taken up
  oxygenUptake: number;
  co2Release: number;
  glycolysis: number;        // GAPD; negative = running backwards (gluconeogenesis)
  pppOxidative: number;      // G6PDH2r, start of the pentose phosphate pathway
  pdh: number;               // pyruvate -> acetyl-CoA with oxygen
  pfl: number;               // pyruvate -> acetyl-CoA + formate without oxygen
  tcaEntry: number;          // citrate synthase
  glyoxylateShunt: number;   // isocitrate lyase (used on acetate)
  products: { name: string; value: number }[]; // secreted, biggest first, only > 0
  productTotal: number;
}

const pos = (v: number) => Math.max(0, v);

export function keyFluxes(flux: Record<string, number> | null | undefined, carbonSource: string): KeyFluxes {
  const f = (id: string) => flux?.[id] ?? 0;
  const exchange = CARBON_EXCHANGE[carbonSource.toLowerCase()];
  const products = PRODUCTS
    // the carbon source itself is taken up, not secreted (acetate/succinate runs)
    .filter(([, id]) => id !== exchange)
    .map(([name, id]) => ({ name, value: pos(f(id)) }))
    .filter((p) => p.value > 0.01)
    .sort((a, b) => b.value - a.value);
  return {
    carbonUptake: exchange ? pos(-f(exchange)) : 0,
    oxygenUptake: pos(-f("EX_o2_e")),
    co2Release: pos(f("EX_co2_e")),
    glycolysis: f("GAPD"),
    pppOxidative: pos(f("G6PDH2r")),
    pdh: pos(f("PDH")),
    pfl: pos(f("PFL")),
    tcaEntry: pos(f("CS")),
    glyoxylateShunt: pos(f("ICL")),
    products,
    productTotal: products.reduce((sum, p) => sum + p.value, 0),
  };
}

export const hasFluxData = (flux: Record<string, number> | null | undefined) =>
  !!flux && Object.keys(flux).length > 0;

/** "17.8", or "← 1.9" when a step runs backwards. */
export function fmtFlux(v: number): string {
  if (Math.abs(v) < 0.05) return "0.0";
  return v < 0 ? `← ${Math.abs(v).toFixed(1)}` : v.toFixed(1);
}

/** Short label for how the cell makes its energy. */
export function energyMode(k: KeyFluxes): string {
  if (k.oxygenUptake < 0.1) return "fermentation";
  if (k.productTotal > 0.5 * k.carbonUptake && k.productTotal > 1) return "respiration + overflow";
  return "respiration";
}

export interface ReadableSim {
  carbon_source: string;
  oxygen_level: string;
  temperature: number;
  growth_rate: number | null;
  doubling_time: number | null;
  viability_score: number | null;
  infeasibility_reason?: string | null;
  flux_distribution?: Record<string, number> | null;
  tf_state_changes?: Record<string, string> | null;
}

/**
 * A few plain sentences describing the run, written from the numbers.
 * Every claim comes straight from a value in the solution.
 */
export function interpretRun(sim: ReadableSim): string[] {
  const out: string[] = [];
  const g = sim.growth_rate ?? 0;

  if (g < 0.01) {
    out.push(`No growth is possible under these conditions${sim.infeasibility_reason ? ` (${sim.infeasibility_reason})` : ""}.`);
    return out;
  }
  const pct = percentOfReference(g);
  out.push(
    `The cell grows at ${formatGrowth(g)}${sim.doubling_time != null ? `, doubling every ${sim.doubling_time.toFixed(2)} h` : ""}` +
      `${pct != null ? ` (${pct}% of the reference rate)` : ""}.`,
  );

  if (!hasFluxData(sim.flux_distribution)) return out;
  const k = keyFluxes(sim.flux_distribution, sim.carbon_source);
  const productList = k.products.slice(0, 3).map((p) => `${p.name.toLowerCase()} ${p.value.toFixed(1)}`).join(", ");

  // How carbon gets in
  const c = sim.carbon_source.toLowerCase();
  if (c === "xylose" || c === "arabinose") {
    out.push(`${sim.carbon_source} (${k.carbonUptake.toFixed(1)} ${FLUX_UNIT}) enters through the pentose phosphate pathway, not upper glycolysis.`);
  } else if (c === "acetate") {
    out.push(
      `Acetate (${k.carbonUptake.toFixed(1)} ${FLUX_UNIT}) enters at acetyl-CoA; the glyoxylate shunt carries ${k.glyoxylateShunt.toFixed(1)}` +
        `${k.glycolysis < 0 ? " and glycolysis runs in reverse (gluconeogenesis) to build sugars" : ""}.`,
    );
  } else if (c === "succinate") {
    out.push(`Succinate (${k.carbonUptake.toFixed(1)} ${FLUX_UNIT}) enters directly into the TCA cycle${k.glycolysis < 0 ? "; glycolysis runs in reverse to build sugars" : ""}.`);
  } else if (k.carbonUptake > 0) {
    out.push(`${sim.carbon_source[0].toUpperCase() + sim.carbon_source.slice(1)} is taken up at ${k.carbonUptake.toFixed(1)} ${FLUX_UNIT} and broken down through glycolysis (${fmtFlux(k.glycolysis)}).`);
  }

  // How energy is made
  const mode = energyMode(k);
  if (mode === "fermentation") {
    out.push(
      `With no oxygen used, energy comes from fermentation: pyruvate formate-lyase carries ${k.pfl.toFixed(1)}` +
        `${productList ? ` and the cell releases ${productList}` : ""}.`,
    );
  } else if (mode === "respiration + overflow") {
    out.push(`It respires (oxygen uptake ${k.oxygenUptake.toFixed(1)}) but also overflows carbon into ${productList}.`);
  } else {
    out.push(`It respires fully: oxygen uptake ${k.oxygenUptake.toFixed(1)}, citrate synthase (TCA entry) ${k.tcaEntry.toFixed(1)}${k.productTotal > 0.5 ? `, with minor byproducts (${productList})` : ", no significant byproducts"}.`);
  }

  // Stress
  if (sim.viability_score != null && sim.viability_score < 0.99) {
    out.push(`Viability falls to ${(sim.viability_score * 100).toFixed(0)}% at ${sim.temperature} °C.`);
  }

  // Regulators
  const changes = Object.entries(sim.tf_state_changes ?? {});
  if (changes.length > 0) {
    out.push(`Regulators switched versus the reference: ${changes.map(([tf, s]) => `${tf} ${s}`).join(", ")}.`);
  }
  return out;
}