"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [clientId, setClientId] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const login = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch("/api/v1/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId, client_secret: secret }),
      });
      if (!res.ok) throw new Error("Invalid credentials");
      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      router.push("/");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-sm p-8 w-full max-w-sm space-y-5">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-green-800">SRAVE</h1>
          <p className="text-sm text-gray-500 mt-1">Municipal Dashboard</p>
        </div>
        <input value={clientId} onChange={(e) => setClientId(e.target.value)}
          placeholder="Client ID" className="w-full border rounded px-3 py-2 text-sm" />
        <input value={secret} onChange={(e) => setSecret(e.target.value)}
          type="password" placeholder="Client Secret" className="w-full border rounded px-3 py-2 text-sm" />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button onClick={login} disabled={loading}
          className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 disabled:opacity-50 text-sm font-medium">
          {loading ? "Signing in…" : "Sign In"}
        </button>
      </div>
    </div>
  );
}
