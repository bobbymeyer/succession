// The built site under /succession, the way the Netlify proxy in
// docs/EMBED.md serves it on bobbymeyer.com: both /succession and
// /succession/... answer with the site's files, and nothing redirects.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const TYPES = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".wasm": "application/wasm", ".zip": "application/zip", ".webp": "image/webp",
};

createServer((req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (path !== "/succession" && !path.startsWith("/succession/")) {
    res.writeHead(404).end();
    return;
  }
  let file = normalize(join(dist, path.slice("/succession".length) || "/"));
  if (!file.startsWith(dist)) return res.writeHead(403).end();
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!existsSync(file)) return res.writeHead(404).end();
  res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" });
  createReadStream(file).pipe(res);
}).listen(Number(process.env.PORT ?? 4175), "127.0.0.1");
