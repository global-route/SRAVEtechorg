"use client";
import { useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

interface Benchmark {
  lga_id: string; total_detected: number; registered: number;
  total_collected_ngn: number; formalization_index: number;
}

const STATES = ["Ogun", "Delta", "Lagos", "Rivers", "Kano"];

export default function StatesPage() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [selectedState, setSelectedState] = useState<string>("all");

  useEffect(() => {
    apiJson<Benchmark[]>("/audit/benchmarks")
      .then(setBenchmarks)
      .catch(console.error);
  }, []);

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(n);

  const grouped = STATES.reduce<Record<string, Benchmark[]>>((acc, s) => {
    acc[s] = benchmarks.filter((b) =>
      selectedState === "all" || b.lga_id.toLowerCase().includes(selectedState.toLowerCase())
    );
    return acc;
  }, {});

  const totals = benchmarks.reduce(
    (acc, b) => ({
      detected: acc.detected + b.total_detected,
      registered: acc.registered + b.registered,
      collected: acc.collected + b.total_collected_ngn,
    }),
    { detected: 0, registered: 0, collected: 0 }
  );

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Multi-State Overview</h1>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Detected", value: totals.detected.toLocaleString() },
          { label: "Total Registered", value: totals.registered.toLocaleString() },
          { label: "Total Collected", value: fmt(totals.collected) },
        ].map((c) => (
          <div key={c.label} className="bg-white rounded-xl shadow-sm p-6">
            <p className="text-xs text-gray-500 uppercase">{c.label}</p>
            <p className="text-2xl font-bold mt-1">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-2 text-sm">
        {["all", ...STATES].map((s) => (
          <button key={s} onClick={() => setSelectedState(s)}
            className={`px-3 py-1 rounded-full border ${
              selectedState === s ? "bg-green-700 text-white border-green-700" : "border-gray-300 text-gray-600"
            }`}>
            {s}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["LGA", "Detected", "Registered", "Collected", "Formalization", "Report"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {benchmarks.map((b) => (
              <tr key={b.lga_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{b.lga_id}</td>
                <td className="px-4 py-3">{b.total_detected.toLocaleString()}</td>
                <td className="px-4 py-3">{b.registered.toLocaleString()}</td>
                <td className="px-4 py-3">{fmt(b.total_collected_ngn)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-green-600 h-1.5 rounded-full"
                        style={{ width: `${Math.min(b.formalization_index, 100)}%` }} />
                    </div>
                    <span className="text-xs">{b.formalization_index}%</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <a href={`/api/v1/audit/lga/${b.lga_id}/report.pdf`} target="_blank"
                    className="text-xs text-green-700 hover:underline">PDF</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-3">
        {STATES.map((s) => (
          <a key={s} href={`/api/v1/audit/state/${s}/report.pdf`} target="_blank"
            className="px-4 py-2 bg-green-700 text-white text-sm rounded hover:bg-green-800">
            {s} State Report
          </a>
        ))}
      </div>
    </div>
  );
}
