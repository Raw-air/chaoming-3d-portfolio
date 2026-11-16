"""本機預覽伺服器：python serve.py [資料夾] [port]
固定正確的 MIME 類型（.js / .glb / .wasm），並關閉快取方便開發。"""
import sys, os, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "site")
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5173
SNAP = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("SNAP_DIR")


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
        ".html": "text/html; charset=utf-8", ".json": "application/json",
        ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".wasm": "application/wasm",
        ".webp": "image/webp", ".svg": "image/svg+xml", ".hdr": "application/octet-stream",
        ".ktx2": "image/ktx2", ".woff2": "font/woff2",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        # 開發用：啟動時給第三個參數（或環境變數 SNAP_DIR）後，網頁可把畫面截圖 POST 到 /__snap/<檔名> 存檔
        snap = SNAP
        if not snap or not self.path.startswith("/__snap/"):
            self.send_error(404); return
        name = os.path.basename(self.path)[:40]
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        os.makedirs(snap, exist_ok=True)
        with open(os.path.join(snap, name), "wb") as fh:
            fh.write(data)
        self.send_response(204); self.end_headers()

    def log_message(self, fmt, *args):
        if args and str(args[1])[:1] in "45":
            super().log_message(fmt, *args)


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=root)
    print(f"Serving {root} at http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
