"use client";
import { useEffect, useState } from "react";
import { apiJson, apiFetch } from "@/lib/api";

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

interface Snapshot {
  lga_id: string; snapshot_date: string; total_buildings: number;
  verified_buildings: number; total_collected_ngn: number;
  ledger_entry_hash: string; previous_hash: string;
}

export default function AuditPage() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [chainResult, setChainResult] = useState<{ chain_valid: boolean; snapshots_checked: number } | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    apiJson<Snapshot[]>(`/audit/snapshots/${LGA_ID}`)
      .then((d) => setSnapshots([...d].reverse()))
      .catch(console.error);
  }, []);

  const verify = async () => {
    setVerifying(true);
    try {
      const r = await apiJson<{ chain_valid: boolean; snapshots_checked: number }>(
        `/audit/snapshots/${LGA_ID}/verify-chain`
      );
      setChainResult(r);
    } finally { setVerifying(false); }
  };

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Audit Chain</h1>
        <button onClick={verify} disabled={verifying}
          className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50">
          {verifying ? "Verifying…" : "Verify Chain"}
        </button>
      </div>

      {chainResult && (
        <div className={`rounded-lg px-4 py-3 text-sm font-medium ${chainResult.chain_valid ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          {chainResult.chain_valid
            ? `✓ Chain valid — ${chainResult.snapshots_checked} snapshots checked`
            : `✗ Chain integrity failure at snapshot ${chainResult.snapshots_checked}`}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["Date","Buildings","Verified","Collected","Hash"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {snapshots.map((s) => (
              <tr key={s.ledger_entry_hash} className="hover:bg-gray-50">
                <td className="px-4 py-3">{s.snapshot_date}</td>
                <td className="px-4 py-3">{s.total_buildings.toLocaleString()}</td>
                <td className="px-4 py-3">{s.verified_buildings.toLocaleString()}</td>
                <td className="px-4 py-3">{fmt(s.total_collected_ngn)}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-400 truncate max-w-xs">
                  {s.ledger_entry_hash.slice(0, 24)}…
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
