"use client";
import { useEffect, useState } from "react";
import { apiJson, apiFetch } from "@/lib/api";

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

interface Assessment {
  id: number; building_id: number; owner_phone: string;
  amount_due: number; wa_status: string; payment_ref: string; assessed_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending:        "bg-gray-100 text-gray-600",
  delivered:      "bg-blue-100 text-blue-700",
  reminder_sent:  "bg-yellow-100 text-yellow-700",
  read:           "bg-purple-100 text-purple-700",
  paid:           "bg-green-100 text-green-700",
};

export default function AssessmentsPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [page, setPage] = useState(1);
  const [voicing, setVoicing] = useState<number | null>(null);

  useEffect(() => {
    apiJson<{ assessments: Assessment[] }>(`/billing/lga/${LGA_ID}/assessments?page=${page}&limit=50`)
      .then((d) => setAssessments(d.assessments))
      .catch(console.error);
  }, [page]);

  const sendVoice = async (id: number) => {
    setVoicing(id);
    try { await apiFetch(`/billing/voice-notice/${id}`, { method: "POST" }); }
    finally { setVoicing(null); }
  };

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Assessments</h1>
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>{["ID","Building","Phone","Amount","Status","Date","Voice"].map((h) => (
              <th key={h} className="px-4 py-3 text-left">{h}</th>
            ))}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {assessments.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{a.id}</td>
                <td className="px-4 py-3">{a.building_id}</td>
                <td className="px-4 py-3 text-gray-500">{a.owner_phone ?? "—"}</td>
                <td className="px-4 py-3 font-medium">{fmt(Number(a.amount_due))}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[a.wa_status] ?? "bg-gray-100 text-gray-600"}`}>
                    {a.wa_status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400">{a.assessed_at?.slice(0, 10)}</td>
                <td className="px-4 py-3">
                  <button onClick={() => sendVoice(a.id)} disabled={voicing === a.id}
                    className="text-xs bg-purple-600 text-white px-3 py-1 rounded hover:bg-purple-700 disabled:opacity-50">
                    {voicing === a.id ? "…" : "Voice"}
                  </button>
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
        <button onClick={() => setPage((p) => p + 1)} disabled={assessments.length < 50}
          className="px-3 py-1.5 text-sm border rounded disabled:opacity-40">Next →</button>
      </div>
    </div>
  );
}
