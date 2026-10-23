"""Loopback-only development server; no credentials or request bodies are logged."""
import argparse
import json
import mimetypes
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from engine import InputError, NATIVE, PROVIDERS, evaluate

WEB = Path(__file__).resolve().parent.parent / "web"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_body(self, status, payload, content_type="application/json"):
        body = payload if isinstance(payload,bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.allowed_host():
            return self.send_body(403,{"error":"Use the local workspace URL."})
        if self.path == "/api/status":
            enabled = os.environ.get("ORBITSUM_ENABLE_HOSTED") == "1" and bool(os.environ.get("OPENAI_API_KEY"))
            return self.send_body(200,{"hosted_available":enabled,"provider":PROVIDERS.get(os.environ.get("OPENAI_BASE_URL","https://api.openai.com/v1").rstrip("/"),"Hosted AI"),"version":"0.1.0","scheme":"Paillier","key_bits":2048,"evaluator":"C / OpenSSL BIGNUM" if NATIVE.is_file() else "Python integer arithmetic"})
        path = {"/":"index.html","/app.js":"app.js","/paillier.js":"paillier.js","/style.css":"style.css"}.get(self.path)
        if not path:
            return self.send_body(404,{"error":"Page not found."})
        return self.send_body(200,(WEB/path).read_bytes(),mimetypes.guess_type(path)[0]+"; charset=utf-8")

    def do_POST(self):
        if not self.allowed_host():
            return self.send_body(403,{"error":"Use the local workspace URL."})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}",f"http://localhost:{self.server.server_port}"}:
            return self.send_body(403,{"error":"Requests must originate from this workspace."})
        if self.path != "/api/evaluate":
            return self.send_body(404,{"error":"Route not found."})
        if self.headers.get("Content-Type") != "application/json":
            return self.send_body(415,{"error":"Use application/json."})
        try:
            size = int(self.headers.get("Content-Length","0"))
            if size <= 0 or size > 60000:
                raise InputError("Request size must be between 1 and 60,000 bytes.")
            data = json.loads(self.rfile.read(size))
            result = evaluate(data)
            self.send_body(200,result)
        except (InputError,json.JSONDecodeError,ValueError) as error:
            self.send_body(400,{"error":str(error) if isinstance(error,InputError) else "Use a valid JSON request."})
        except Exception as error:
            # A class name supports local diagnosis without recording request data.
            print("OrbitSum request exception: "+type(error).__name__,flush=True)
            for frame in traceback.extract_tb(error.__traceback__):
                print("  "+Path(frame.filename).name+":"+str(frame.lineno)+" in "+frame.name,flush=True)
            self.send_body(500,{"error":"The workspace could not complete this run. Please try again.","error_code":type(error).__name__})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OrbitSum local encrypted analytics workspace")
    parser.add_argument("--port",type=int,default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
    print(f"OrbitSum: http://127.0.0.1:{args.port}",flush=True)
    server.serve_forever()
