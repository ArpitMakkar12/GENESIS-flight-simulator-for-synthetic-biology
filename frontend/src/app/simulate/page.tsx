"use client";

import { useState } from "react";

export default function SimulatePage() {
  const [sequence, setSequence] = useState("");
  const [temperature, setTemperature] = useState(37);
  const [ph, setPh] = useState(7.0);
  const [oxygen, setOxygen] = useState("aerobic");
  const [carbonSource, setCarbonSource] = useState("glucose");
  const [nitrogenSource, setNitrogenSource] = useState("ammonium");

  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold text-white mb-6">Run Simulation</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: DNA Input */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
            <h2 className="text-lg font-semibold text-gray-200 mb-3">
              DNA Sequence Input
            </h2>
            <textarea
              value={sequence}
              onChange={(e) => setSequence(e.target.value)}
              placeholder="Paste DNA sequence here (ATCG only)..."
              className="w-full h-48 p-4 rounded-lg bg-gray-950 border border-gray-700 text-green-400 font-mono text-sm placeholder-gray-600 focus:border-green-500 focus:outline-none resize-none"
            />
            <div className="mt-2 text-xs text-gray-500">
              {sequence.length} bp | GC:{" "}
              {sequence.length > 0
                ? (
                    ((sequence.match(/[GCgc]/g)?.length || 0) /
                      sequence.length) *
                    100
                  ).toFixed(1)
                : "0.0"}
              %
            </div>
          </div>

          {/* Results placeholder */}
          <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
            <h2 className="text-lg font-semibold text-gray-200 mb-3">
              Results
            </h2>
            <p className="text-gray-500 text-sm">
              Run a simulation to see expression predictions and metabolic flux
              here.
            </p>
          </div>
        </div>

        {/* Right: Environment Controls */}
        <div className="space-y-4">
          <div className="p-6 rounded-xl border border-gray-800 bg-gray-900">
            <h2 className="text-lg font-semibold text-gray-200 mb-4">
              Environment
            </h2>

            <div className="space-y-4">
              <SliderControl
                label="Temperature"
                value={temperature}
                onChange={setTemperature}
                min={20}
                max={50}
                unit="°C"
              />
              <SliderControl
                label="pH"
                value={ph}
                onChange={setPh}
                min={4}
                max={9}
                step={0.1}
                unit=""
              />

              <SelectControl
                label="Oxygen"
                value={oxygen}
                onChange={setOxygen}
                options={["aerobic", "microaerobic", "anaerobic"]}
              />
              <SelectControl
                label="Carbon Source"
                value={carbonSource}
                onChange={setCarbonSource}
                options={[
                  "glucose",
                  "lactose",
                  "glycerol",
                  "acetate",
                  "succinate",
                ]}
              />
              <SelectControl
                label="Nitrogen Source"
                value={nitrogenSource}
                onChange={setNitrogenSource}
                options={["ammonium", "glutamine", "nitrate"]}
              />
            </div>

            <button
              className="w-full mt-6 py-3 rounded-lg bg-green-600 hover:bg-green-500 text-white font-semibold transition-colors"
              onClick={() => {
                // TODO: Call /api/v1/simulate
                alert("Simulation endpoint not connected yet");
              }}
            >
              ▶ Run Simulation
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SliderControl({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  unit: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-mono">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-green-500"
      />
    </div>
  );
}

function SelectControl({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="text-sm text-gray-400 block mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full p-2 rounded-lg bg-gray-950 border border-gray-700 text-white text-sm focus:border-green-500 focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt.charAt(0).toUpperCase() + opt.slice(1)}
          </option>
        ))}
      </select>
    </div>
  );
}
