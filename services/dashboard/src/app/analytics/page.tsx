"use client";
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";
import { apiJson } from "@/lib/api";

interface Projection { month_offset: number; projected_ngn: number; }
interface Forecast {
  lga_id: string; historical_months: number; monthly_slope_ngn: number;
  projections: Projection[]; error?: string;
}
interface Benchmark {
  lga_id: string; total_detected: number; registered: number;
  total_collected_ngn: number; formalization_index: number;
}
interface Alert { id: number; target_id: string; payload: Record<string, number>; logged_at: string; }

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

export default function AnalyticsPage() {
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    Promise.all([
      apiJson<Forecast>(`/audit/lga/${LGA_ID}/forecast`),
      apiJson<Benchmark[]>("/audit/benchmarks"),
      apiJson<Alert[]>("/audit/alerts"),
    ]).then(([f, b, a]) => { setForecast(f); setBenchmarks(b); setAlerts(a); })
      .catch(console.error);
  }, []);

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Analytics & Forecasting</h1>

      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 space-y-2">
          <p className="text-sm font-semibold text-red-700">⚠ {alerts.length} anomaly alert{alerts.length > 1 ? "s" : ""}</p>
          {alerts.slice(0, 3).map((a) => (
            <p key={a.id} className="text-xs text-red-600">
              {a.target_id} — collections dropped {a.payload?.drop_pct}% vs prior month
              <span className="text-gray-400 ml-2">{a.logged_at?.slice(0, 10)}</span>
            </p>
          ))}
        </div>
      )}

      {forecast && !forecast.error && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-1">12-Month IGR Forecast — {forecast.lga_id}</h2>
          <p className="text-xs text-gray-400 mb-4">
            Based on {forecast.historical_months} months · Trend: {fmt(forecast.monthly_slope_ngn)}/month
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={forecast.projections}>
              <XAxis dataKey="month_offset" tickFormatter={(v) => `M+${v}`} tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => `₦${(v / 1e6).toFixed(1)}M`} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => fmt(v)} />
              <Line type="monotone" dataKey="projected_ngn" stroke="#16a34a" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {forecast?.error && (
        <p className="text-sm text-gray-400 bg-white rounded-xl p-6">{forecast.error}</p>
      )}

      {benchmarks.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">LGA Benchmarking — Formalization Index</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={benchmarks.slice(0, 10)} layout="vertical">
              <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="lga_id" width={120} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => `${v}%`} />
              <Bar dataKey="formalization_index" fill="#16a34a" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <table className="w-full text-xs mt-4">
            <thead className="text-gray-400 uppercase">
              <tr>{["LGA","Detected","Registered","Collected","Index"].map((h) => (
                <th key={h} className="text-left py-2 pr-4">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {benchmarks.map((b) => (
                <tr key={b.lga_id}>
                  <td className="py-2 pr-4 font-medium">{b.lga_id}</td>
                  <td className="py-2 pr-4">{b.total_detected.toLocaleString()}</td>
                  <td className="py-2 pr-4">{b.registered.toLocaleString()}</td>
                  <td className="py-2 pr-4">{fmt(b.total_collected_ngn)}</td>
                  <td className="py-2 pr-4 font-semibold text-green-700">{b.formalization_index}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
