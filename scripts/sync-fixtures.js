/**
 * scripts/sync-fixtures.js
 * Copies docs/fixtures/*.json into src/api/fixtures/ so mock.ts can import
 * them as local JSON modules (TypeScript resolves JSON imports within the src
 * tree). This is run automatically before `dev` and `build` via npm lifecycle
 * hooks, so the copies can never drift from the contract without a rebuild.
 *
 * Usage: node scripts/sync-fixtures.js
 */

const fs = require("fs");
const path = require("path");

const src = path.resolve(__dirname, "..", "docs", "fixtures");
const dst = path.resolve(__dirname, "..", "frontend", "src", "api", "fixtures");

fs.mkdirSync(dst, { recursive: true });
fs.cpSync(src, dst, { recursive: true });

console.log(`[sync-fixtures] Copied ${src} → ${dst}`);
