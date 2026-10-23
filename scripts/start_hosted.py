"""Load one explicitly selected local provider configuration into server memory."""
import argparse
import os
from pathlib import Path
import re
import sys

parser = argparse.ArgumentParser(description="Run OrbitSum with an approved existing API configuration")
parser.add_argument("--env-file",required=True)
parser.add_argument("--provider",choices=["openai","qwen"],required=True)
parser.add_argument("--port",type=int,default=8765)
args = parser.parse_args()
prefix = "QWEN" if args.provider == "qwen" else "OPENAI"
allowed = {prefix+"_API_KEY",prefix+"_BASE_URL",prefix+"_MODEL"}
values = {}
for line in Path(args.env_file).read_text().splitlines():
    match = re.match(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$",line)
    if match and match.group(1) in allowed:
        value = match.group(2)
        if len(value)>1 and value[0]==value[-1] and value[0] in {"'",'"'}:
            value=value[1:-1]
        values[match.group(1)] = value
key=values.get(prefix+"_API_KEY")
if not key:
    sys.exit("The selected configuration does not contain the required provider key.")
base=values.get(prefix+"_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1" if args.provider=="qwen" else "https://api.openai.com/v1").rstrip("/")
expected="https://dashscope.aliyuncs.com/compatible-mode/v1" if args.provider=="qwen" else "https://api.openai.com/v1"
if base != expected:
    sys.exit("The selected provider configuration must use its approved official API endpoint.")
os.environ["OPENAI_API_KEY"]=key
os.environ["OPENAI_BASE_URL"]=base
os.environ["OPENAI_MODEL"]=values.get(prefix+"_MODEL","qwen-plus" if args.provider=="qwen" else "gpt-4.1-mini")
os.environ["ORBITSUM_ENABLE_HOSTED"]="1"
if not os.environ.get("SSL_CERT_FILE") and Path("/etc/ssl/cert.pem").is_file():
    os.environ["SSL_CERT_FILE"]="/etc/ssl/cert.pem"
server=Path(__file__).resolve().parent.parent/"src"/"server.py"
os.execv(sys.executable,[sys.executable,str(server),"--port",str(args.port)])
