"""
Servidor de desenvolvimento local — serve estáticos + /api/index.
Uso: python dev_server.py [porta]
"""
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

ROOT = os.path.dirname(__file__)
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault(
    "TSE_DB_PATH",
    os.path.join(ROOT, "tse_core", "dados", "tse.sqlite"),
)

from api.index import handler as APIHandler  # noqa: E402


# Herança múltipla: APIHandler fornece _send_json/_garantir_db;
# SimpleHTTPRequestHandler fornece send_head/translate_path para servir arquivos.
class DevHandler(APIHandler, SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api"):
            # Usa o handler serverless
            APIHandler.do_GET(self)
        else:
            if path == "/":
                self.path = "/index.html"
            SimpleHTTPRequestHandler.do_GET(self)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    server = ThreadingHTTPServer(("", port), DevHandler)
    print(f"Servidor rodando em http://localhost:{port}")
    server.serve_forever()
