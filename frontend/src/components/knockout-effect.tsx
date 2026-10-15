"use client";

/*
 * What a knockout changed, on the results page of a knockout run.
 *
 * The backend solved the wild type in the same run (same regulators,
 * expression, bounds and medium), so every difference shown here comes
 * from the deleted genes alone:
 *   1. growth, wild type vs knockout
 *   2. the deleted genes, each with its track record from the essential-gene check
 *   3. pathways the deletion switched on or off, or shifted a lot
 */

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { GROWTH_UNIT } from "@/lib/sim-format";
import { FLUX_UNIT } from "@/lib/flux-summary";
import { pathwayDiff, fmtPathway, PathwayRow } from "@/lib/pathway-diff";
import { KnockoutBlock, geneLabel, percentChange, trackRecord } from "@/lib/knockout";

const WT_COLOR = "#8cc3d4";
const KO_COLOR = "#ff8b6e";

export function KnockoutEffect({ knockout, growthRate, pathwayFluxes, medium }: {
  knockout: KnockoutBlock;
  growthRate: number;
  pathwayFluxes?: Record<string, number>;
  medium: string;  // e.g. "glucose, aerobic" — said next to the LB caveat
}) {
  const wt = knockout.wild_type;
  const top = Math.max(wt.growth_rate, growthRate, 0.001);
  const genesText = knockout.genes.map((g) => `Δ${geneLabel(g)}`).join(" ");

  const diff = pathwayDiff([
    { growth_rate: wt.growth_rate, fba_results: { pathway_fluxes: wt.pathway_fluxes ?? {} } },
    { growth_rate: growthRate, fba_results: { pathway_fluxes: pathwayFluxes ?? {} } },
  ]);

  return (
    <Card className="p-6 space-y-6 border-[#ff8b6e]/20">
      <div>
        <h2 className="text-lg font-semibold text-[#eaffff]">Knockout effect: {genesText}</h2>
        <p className="text-sm text-[#8cc3d4] mt-1">
          Compared with the wild type solved in the same run, so every difference below comes from the deletion alone.
        </p>
      </div>

      {/* 1. Growth */}
      <section>
        <div className="flex items-baseline justify-between mb-2">
          <h3 className="text-sm font-semibold text-[#d9f7ff]">Growth</h3>
          <span className="font-mono-readout text-2xl" style={{ color: growthRate < wt.growth_rate * 0.99 ? KO_COLOR : WT_COLOR }}>
            {percentChange(wt.growth_rate, growthRate)}
          </span>
        </div>
        <div className="space-y-2">
          {[
            { label: "Wild type", value: wt.growth_rate, color: WT_COLOR },
            { label: genesText, value: growthRate, color: KO_COLOR },
          ].map((row) => (
            <div key={row.label} className="grid grid-cols-[7rem_1fr_6.5rem] items-center gap-3 text-sm">
              <span className="truncate text-[#8cc3d4]" title={row.label}>{row.label}</span>
              <span className="h-2.5 rounded-full bg-white/[0.06]">
                <span className="block h-full rounded-full" style={{ width: `${(row.value / top) * 100}%`, background: row.color }} />
              </span>
              <span className="text-right font-mono-readout text-[#eaffff]">{row.value.toFixed(3)} {GROWTH_UNIT}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 2. The deleted genes and their track record */}
      <section>
        <h3 className="text-sm font-semibold text-[#d9f7ff] mb-2">Deleted genes</h3>
        <ul className="space-y-2">
          {knockout.genes.map((g) => (
            <li key={g.locus_tag} className="text-sm">
              <Link href={`/library?tab=genes&gene=${encodeURIComponent(g.locus_tag)}`} className="text-[#ffd2c4] hover:underline underline-offset-2">
                Δ{geneLabel(g)}
              </Link>
              <span className="ml-2 font-mono-readout text-xs text-[#5c8494]">{g.locus_tag}</span>
              <p className="text-xs text-[#8cc3d4] mt-0.5">{trackRecord(g.record)}</p>
            </li>
          ))}
        </ul>
        <p className="text-xs text-[#5c8494] mt-3 leading-relaxed">
          The lab data and the screen are for rich LB broth, where the cell can import amino acids and vitamins. This run is on {medium},
          so a gene that is harmless to lose in broth can still stop growth here — genes that make amino acids are the usual case.
        </p>
      </section>

      {/* 3. Pathways. A cell that cannot grow has no growth fluxes to compare:
          the solver only keeps maintenance running, so every pathway looks
          "switched off" and the shift ratios are meaningless. */}
      {growthRate < 0.01 ? (
        <section>
          <h3 className="text-sm font-semibold text-[#d9f7ff]">Pathways</h3>
          <p className="text-sm text-[#8cc3d4] mt-1">
            Not compared. The knockout cannot grow, so its only fluxes are the cell&apos;s maintenance cost; set against
            the wild type, every pathway would look switched off.
          </p>
        </section>
      ) : (
      <section>
        <h3 className="text-sm font-semibold text-[#d9f7ff]">Pathways switched on or off</h3>
        <p className="text-xs text-[#5c8494] mb-2">Total flux through each pathway ({FLUX_UNIT}); — means no flux.</p>
        {diff.switched.length > 0
          ? <PathwayTable rows={diff.switched} exact={diff.exact} />
          : <p className="text-sm text-[#5c8494]">None. The cell routes around the deletion with the pathways it was already using.</p>}

        {diff.bigChanges.length > 0 && (
          <>
            <h3 className="text-sm font-semibold text-[#d9f7ff] mt-5">Biggest shifts</h3>
            <p className="text-xs text-[#5c8494] mb-2">
              Running in both, but at least 2× apart even after allowing for the change in growth. The last column is that growth-adjusted difference.
            </p>
            <PathwayTable rows={diff.bigChanges} exact showRatio />
          </>
        )}
        </section>
      )}
    </Card>
  );
}

function PathwayTable({ rows, exact, showRatio = false }: { rows: PathwayRow[]; exact: boolean; showRatio?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-[#5c8494] border-b border-white/[0.07]">
            <th className="py-1.5 pr-3 text-left font-medium">Pathway</th>
            <th className="py-1.5 px-3 text-right font-medium" style={{ color: WT_COLOR }}>Wild type</th>
            <th className="py-1.5 px-3 text-right font-medium" style={{ color: KO_COLOR }}>Knockout</th>
            {showRatio && <th className="py-1.5 pl-3 text-right font-medium">Shift</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.pathway} className="border-b border-white/[0.04] last:border-0">
              <td className="py-1.5 pr-3 text-[#d9f7ff]">{r.pathway}</td>
              {r.values.map((v, i) => (
                <td key={i} className="py-1.5 px-3 text-right font-mono-readout text-[#eaffff]">{fmtPathway(v, exact)}</td>
              ))}
              {showRatio && <td className="py-1.5 pl-3 text-right font-mono-readout text-[#ffcf66]">{r.ratio?.toFixed(1)}×</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}