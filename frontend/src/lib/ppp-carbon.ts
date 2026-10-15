/*
 * Pentose phosphate pathway (PPP) bookkeeping for the flux map, counted in
 * carbon atoms. Kept here, away from the drawing code, so it can be tested.
 *
 * The PPP has several equally good routes back to glycolysis (TKT2, TALA,
 * the PFK_3/FBA3 bypass, or Entner–Doudoroff), and the solver may pick any
 * of them. Counting carbon atoms makes the arrows come out the same
 * whichever route the solver chose.
 */

/** Flux of one reaction in mmol/gDW/h; 0 if the backend did not store it. */
export type Flux = (id: string) => number;

/** Keep the forward part only: negative becomes 0. */
export const pos = (v: number) => Math.max(0, v);

/** Make a Flux reader from the backend's { reaction_id: flux } map. */
export const fluxReader = (fluxes: Partial<Record<string, number>>): Flux => (id) => fluxes[id] ?? 0;

/* Carbon going from glycolysis into PPP (C-mmol/gDW/h):
 *   G6PDH2r brings in glucose-6-P            +6 C
 *   TKT1 sends out glyceraldehyde-3-P        −3 C
 *   TKT2 sends out fructose-6-P + G3P        −9 C
 *   TALA takes in G3P, sends out F6P         −3 C (net)
 *   FBA3 sends out DHAP (bypass)             −3 C
 *   EDA sends out G3P + pyruvate (E–D path)  −6 C
 * Negative = carbon flowing from PPP back into glycolysis (e.g. on xylose).
 */
export const pppCarbonFromGlycolysis = (f: Flux) =>
  6 * f("G6PDH2r") - 3 * f("TKT1") - 9 * f("TKT2") - 3 * f("TALA") - 3 * f("FBA3") - 6 * f("EDA");

/* Carbon left in PPP for building blocks = what came in − what left as CO2.
 * In: from glycolysis (above) + xylose/arabinose entering directly (5 C each).
 * Out as CO2: GND (1 C each). What remains feeds nucleotides & aromatic amino acids.
 */
export const pppCarbonForPrecursors = (f: Flux) =>
  pppCarbonFromGlycolysis(f) + 5 * (pos(f("XYLK")) + pos(f("RBK_L1"))) - pos(f("GND"));