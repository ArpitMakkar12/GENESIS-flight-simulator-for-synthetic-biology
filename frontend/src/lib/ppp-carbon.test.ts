/*
 * The flux map's pentose phosphate arrows, checked against real FBA solutions.
 *
 * __fixtures__/ppp-fluxes.json holds iML1515 solutions for seven cases,
 * including three where the solver was forced down a different route
 * (FBA3 bypass, Entner–Doudoroff, no TKT2). For each, the fixture also
 * holds the carbon that really leaves the PPP sugar pool, worked out from
 * the model itself. The arrow arithmetic must agree with it every time.
 */

import { describe, expect, it } from "vitest";
import fixture from "./__fixtures__/ppp-fluxes.json";
import { fluxReader, pos, pppCarbonForPrecursors, pppCarbonFromGlycolysis } from "./ppp-carbon";

interface Scenario {
  name: string;
  growth: number;
  fluxes: Partial<Record<string, number>>;   // only the reactions the arithmetic reads; absent = 0
  precursorCarbon: number;          // C-mmol/gDW/h, from the model's own balance
}
const scenarios = fixture.scenarios as Scenario[];

const scenario = (name: string) => {
  const s = scenarios.find((x) => x.name === name);
  if (!s) throw new Error(`No fixture scenario "${name}"`);
  return { ...s, f: fluxReader(s.fluxes) };
};

describe("carbon kept for precursors", () => {
  it.each(scenarios.map((s) => s.name))("matches the model's own carbon balance: %s", (name) => {
    const s = scenario(name);
    expect(pppCarbonForPrecursors(s.f)).toBeCloseTo(s.precursorCarbon, 4);
  });
});

describe("the solver's choice of route does not change the arrows", () => {
  it("FBA3 bypass instead of TALA gives the same carbon into the PPP", () => {
    const normal = scenario("glucose");
    const bypass = scenario("glucose, FBA3 bypass forced");
    expect(bypass.f("TALA")).not.toBeCloseTo(normal.f("TALA"), 2);   // a different route really was taken
    expect(pppCarbonFromGlycolysis(bypass.f)).toBeCloseTo(pppCarbonFromGlycolysis(normal.f), 6);
    expect(pppCarbonForPrecursors(bypass.f)).toBeCloseTo(pppCarbonForPrecursors(normal.f), 6);
  });
});

describe("direction of the glycolysis ↔ PPP arrow", () => {
  it("on glucose, carbon flows from glycolysis into the PPP", () => {
    expect(pppCarbonFromGlycolysis(scenario("glucose").f)).toBeGreaterThan(0);
  });

  it.each(["xylose", "arabinose"])("on %s, carbon enters the PPP directly and flows back to glycolysis", (name) => {
    const s = scenario(name);
    expect(pppCarbonFromGlycolysis(s.f)).toBeLessThan(0);
    expect(pppCarbonForPrecursors(s.f)).toBeGreaterThan(0);   // but some is still kept for building blocks
  });
});

describe("helpers", () => {
  it("a reaction the backend did not store reads as 0", () => {
    expect(fluxReader({ GND: 1.5 })("TKT1")).toBe(0);
  });

  it("pos keeps the forward part only", () => {
    expect(pos(2)).toBe(2);
    expect(pos(-2)).toBe(0);
  });

  it("no flux at all gives no carbon", () => {
    const empty = fluxReader({});
    expect(pppCarbonFromGlycolysis(empty)).toBe(0);
    expect(pppCarbonForPrecursors(empty)).toBe(0);
  });
});