/**
 * Inject Railway API URL into public/js/config.js for Vercel static deploy.
 * Set RAILWAY_API_URL in Vercel project env (or use /api proxy in vercel.json).
 */
const fs = require("fs");
const path = require("path");

const isVercel = Boolean(process.env.VERCEL);
// Browser must use same-origin /api proxy on Vercel (avoids mobile CORS/network issues).
// RAILWAY_API_URL is for server-side tooling only — never inject into client config on deploy.
const apiUrl = isVercel
  ? ""
  : process.env.RAILWAY_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
const runId = process.env.INSIGHTS_RUN_ID || "run_phase4_final";

const configPath = path.join(__dirname, "..", "public", "js", "config.js");
const templatePath = path.join(__dirname, "..", "public", "js", "config.template.js");
let content = fs.readFileSync(templatePath, "utf8");
content = content.replace("__API_URL__", apiUrl.replace(/\/$/, ""));
content = content.replace("__RUN_ID__", runId);
fs.writeFileSync(configPath, content);

console.log(`Injected API_URL=${apiUrl || "(empty — use vercel.json /api proxy)"}`);
