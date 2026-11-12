import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");

export const options = {
  scenarios: {
    field_agents: {
      executor: "constant-vus",
      vus: 100,
      duration: "3m",
      tags: { scenario: "field_agents" },
    },
    ingest_polling: {
      executor: "constant-vus",
      vus: 10,
      duration: "3m",
      startTime: "10s",
      tags: { scenario: "ingest_polling" },
    },
  },
  thresholds: {
    "http_req_duration{scenario:field_agents}": ["p(95)<500"],
    "http_req_duration{scenario:ingest_polling}": ["p(95)<1000"],
    errors: ["rate<0.01"],
  },
};

const BASE = __ENV.API_BASE || "https://api.srave.io/api/v1";
const AGENT_TOKEN = __ENV.AGENT_TOKEN;
const ADMIN_TOKEN = __ENV.ADMIN_TOKEN;
const LGA_ID = __ENV.LGA_ID || "Abeokuta South";
const JOB_ID = __ENV.JOB_ID || "test-job-id";

export default function () {
  const scenario = __ENV.K6_SCENARIO_NAME;

  if (scenario === "ingest_polling") {
    const res = http.get(`${BASE}/spatial/ingest/${JOB_ID}`, {
      headers: { Authorization: `Bearer ${ADMIN_TOKEN}` },
    });
    errorRate.add(!check(res, { "ingest status 200 or 404": (r) => [200, 404].includes(r.status) }));
    sleep(5);
    return;
  }

  const assignRes = http.get(
    `${BASE}/field/assignments/agent_01?lga_id=${encodeURIComponent(LGA_ID)}&limit=10`,
    { headers: { Authorization: `Bearer ${AGENT_TOKEN}` } }
  );
  errorRate.add(!check(assignRes, { "assignments 200": (r) => r.status === 200 }));

  const buildings = assignRes.json("buildings");
  if (buildings && buildings.length > 0) {
    const id = buildings[0].id;
    const verifyRes = http.patch(
      `${BASE}/field/buildings/${id}/verify`,
      JSON.stringify({ verified: true, property_type: "residential_low", photo_url: "https://example.com/photo.jpg" }),
      { headers: { Authorization: `Bearer ${AGENT_TOKEN}`, "Content-Type": "application/json" } }
    );
    errorRate.add(!check(verifyRes, { "verify 200 or 409": (r) => [200, 409].includes(r.status) }));
  }

  sleep(1);
}
