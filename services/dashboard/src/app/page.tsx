"use client";
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiJson } from "@/lib/api";

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

interface GapAnalysis {
  lga_id: string;
  total_detected_buildings: number;
  registered_tax_payers: number;
  unregistered_gap: number;
  estimated_annual_revenue_gap_ngn: number;
  compliance_percentage: number;
}

interface DailyCollection { date: string; total_ngn: number; paid_count: number; }

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-3xl font-bold">{value}</span>
      {sub && <span className="text-sm text-gray-400">{sub}</span>}
    </div>
  );
}

export default function OverviewPage() {
  const [gap, setGap] = useState<GapAnalysis | null>(null);
  const [collections, setCollections] = useState<DailyCollection[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiJson<GapAnalysis>(`/audit/lga/${LGA_ID}/gap-analysis`),
      apiJson<DailyCollection[]>(`/audit/lga/${LGA_ID}/collections`),
    ])
      .then(([g, c]) => { setGap(g); setCollections(c.slice(0, 14).reverse()); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-500">{error}</p>;
  if (!gap) return <p className="text-gray-400">Loading…</p>;

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">{gap.lga_id} — Revenue Overview</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Detected Buildings"   value={gap.total_detected_buildings.toLocaleString()} />
        <StatCard label="Registered Taxpayers" value={gap.registered_tax_payers.toLocaleString()} />
        <StatCard label="Unregistered Gap"     value={gap.unregistered_gap.toLocaleString()} />
        <StatCard
          label="Est. Annual Gap"
          value={fmt(gap.estimated_annual_revenue_gap_ngn)}
          sub={`${gap.compliance_percentage}% compliance`}
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-sm font-medium text-gray-500 mb-4">Daily Collections — Last 14 Days</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={collections}>
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `₦${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => fmt(v)} />
            <Bar dataKey="total_ngn" fill="#16a34a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
