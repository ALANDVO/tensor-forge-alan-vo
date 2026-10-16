// Minimal static file server for the production build. No dependencies.
import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const root = resolve(process.env.STATIC_ROOT || join(__dirname, "dist"));
const port = Number(process.env.PORT || 80);

const index = await readFile(join(root, "index.html"));

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);
    let path = decodeURIComponent(url.pathname);
    if (path === "/" || path === "/index.html") {
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(index);
      return;
    }
    const file = join(root, path);
    const st = await stat(file).catch(() => null);
    if (!st || !st.isFile()) {
      // SPA fallback for client routes
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(index);
      return;
    }
    const data = await readFile(file);
    const ext = path.slice(path.lastIndexOf(".") + 1);
    const types = { js: "application/javascript", css: "text/css", json: "application/json", png: "image/png", svg: "image/svg+xml", ico: "image/x-icon", txt: "text/plain" };
    res.writeHead(200, { "Content-Type": types[ext] || "application/octet-stream" });
    res.end(data);
  } catch {
    res.writeHead(500);
    res.end("internal server error");
  }
});

server.listen(port, () => {
  console.log(`tensor-forge frontend on http://0.0.0.0:${port}`);
});