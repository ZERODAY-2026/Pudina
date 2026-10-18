/**
 * frontend/scripts/sync-fixtures.js
 *
 * Copies docs/fixtures/*.json into src/api/fixtures/ so mock.ts can import
 * them as local TypeScript-resolved JSON modules.
 *
 * Run automatically before `dev` and `build` via npm lifecycle hooks so the
 * local copies can never drift from the contract without a rebuild.
 *
 * Usage: node scripts/sync-fixtures.js
 */

/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("fs");
const path = require("path");

// CWD is frontend/ when called via npm scripts.
const src = path.resolve(__dirname, "..", "..", "docs", "fixtures");
const dst = path.resolve(__dirname, "..", "src", "api", "fixtures");

fs.mkdirSync(dst, { recursive: true });
fs.cpSync(src, dst, { recursive: true });

console.log(`[sync-fixtures] ${src} → ${dst}`);
