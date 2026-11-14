"use client";
import { useEffect, useState } from "react";
import { apiJson, apiFetch } from "@/lib/api";

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

interface Building {
  id: number; lga_id: string; confidence_score: number;
  property_type: string; verified: boolean; scan_date: string;
}

export default function BuildingsPage() {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [page, setPage] = useState(1);
  const [verified, setVerified] = useState<"all" | "true" | "false">("all");
  const [assessing, setAssessing] = useState<number | null>(null);

  const load = () => {
    const params = new URLSearchParams({ page: String(page), limit: "50" });
    if (verified !== "all") params.set("verified", verified);
    apiJson<{ buildings: Building[] }>(`/audit/lga/${LGA_ID}/buildings?${params}`)
      .then((d) => setBuildings(d.buildings))
      .catch(console.error);
  };

  useEffect(load, [page, verified]);

  const assess = async (id: number) => {
    setAssessing(id);
    try {
      await apiFetch(`/billing/assess/${id}`, { method: "POST" });
      load();
    } finally { setAssessing(null); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Buildings</h1>
        <select className="border rounded px-3 py-1.5 text-sm" value={verified}
          onChange={(e) => { setVerified(e.target.value as typeof verified); setPage(1); }}>
          <option value="all">All</option>
          <option value="true">Verified</option>
          <option value="false">Unverified</option>
        </select>
      </div>
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["ID","Type","Confidence","Verified","Scan Date","Action"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {buildings.map((b) => (
              <tr key={b.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{b.id}</td>
                <td className="px-4 py-3">{b.property_type}</td>
                <td className="px-4 py-3">{(b.confidence_score * 100).toFixed(0)}%</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${b.verified ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                    {b.verified ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400">{b.scan_date?.slice(0, 10) ?? "—"}</td>
                <td className="px-4 py-3">
                  {b.verified && (
                    <button onClick={() => assess(b.id)} disabled={assessing === b.id}
                      className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 disabled:opacity-50">
                      {assessing === b.id ? "…" : "Assess"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
          className="px-3 py-1.5 text-sm border rounded disabled:opacity-40">← Prev</button>
        <span className="px-3 py-1.5 text-sm">Page {page}</span>
        <button onClick={() => setPage((p) => p + 1)} disabled={buildings.length < 50}
          className="px-3 py-1.5 text-sm border rounded disabled:opacity-40">Next →</button>
      </div>
    </div>
  );
}
