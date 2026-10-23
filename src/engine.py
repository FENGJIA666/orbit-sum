"""Keyless Paillier evaluation and a narrowly validated LLM planning boundary."""
import hashlib
import json
import math
import os
import re
import secrets
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OPERATIONS = {"total", "average", "difference"}
PROVIDER_URL = "https://api.openai.com/v1/chat/completions"
NATIVE = Path(__file__).resolve().parent.parent / "build" / "aggregate"
PROVIDERS = {"https://api.openai.com/v1":"OpenAI", "https://dashscope.aliyuncs.com/compatible-mode/v1":"Alibaba Cloud Qwen"}
QUESTIONS = {"total":"What is the total event budget across all clubs?", "average":"What is the average event budget per club?", "difference":"How much larger is the North campus event budget than the South campus event budget?"}

class InputError(ValueError):
    pass

def validate_request(data):
    if not isinstance(data, dict) or set(data) != {"mode", "operation", "public_key", "records"}:
        raise InputError("Send only the public key, encrypted records, mode and selected operation.")
    if not isinstance(data["mode"],str) or not isinstance(data["operation"],str) or data["mode"] not in {"local", "hosted"} or data["operation"] not in OPERATIONS:
        raise InputError("Choose a supported planner and operation.")
    raw_n = data["public_key"]
    if not isinstance(raw_n, str) or not re.fullmatch(r"[1-9][0-9]{615,616}", raw_n):
        raise InputError("A 2048-bit Paillier public key is required.")
    n = int(raw_n)
    if n.bit_length() != 2048 or n % 2 == 0:
        raise InputError("A 2048-bit odd Paillier modulus is required.")
    records = data["records"]
    if not isinstance(records, list) or not 2 <= len(records) <= 32:
        raise InputError("Supply between 2 and 32 encrypted records.")
    ids = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != {"id", "group", "ciphertext"}:
            raise InputError("Records contain only an ID, public group and ciphertext.")
        if not isinstance(row["id"], str) or not re.fullmatch(r"site-[0-9]{1,2}", row["id"]) or row["id"] in ids:
            raise InputError("Each site requires a unique public identifier.")
        ids.add(row["id"])
        if not isinstance(row["group"],str) or row["group"] not in {"north", "south"}:
            raise InputError("Choose a public north or south group.")
        raw = row["ciphertext"]
        if not isinstance(raw, str) or not re.fullmatch(r"[1-9][0-9]{0,1233}", raw):
            raise InputError("Ciphertexts must be bounded decimal integers.")
        c = int(raw)
        if not 1 <= c < n*n or math.gcd(c,n) != 1:
            raise InputError("Ciphertext must belong to the Paillier group.")
    if data["operation"] == "difference" and {r["group"] for r in records} != {"north", "south"}:
        raise InputError("Group comparison requires both public groups.")
    return n

def expected_plan(data):
    operation = data["operation"]
    return {"operation":operation,"terms":[{"id":r["id"], "weight":-1 if operation == "difference" and r["group"] == "south" else 1} for r in data["records"]], "divisor":len(data["records"]) if operation == "average" else 1}

def validate_plan(plan, data):
    expected = expected_plan(data)
    if not isinstance(plan, dict) or set(plan) != set(expected):
        raise InputError("Planner response does not match the approved plan schema.")
    if plan["operation"] != expected["operation"] or type(plan["divisor"]) is not int or plan["divisor"] != expected["divisor"]:
        raise InputError("Planner must preserve the selected operation and divisor.")
    terms = plan["terms"]
    if not isinstance(terms,list) or len(terms) != len(expected["terms"]):
        raise InputError("Planner must use each approved site exactly once.")
    for term in terms:
        if not isinstance(term,dict) or set(term) != {"id","weight"} or type(term["weight"]) is not int or not isinstance(term["id"],str):
            raise InputError("Each planner term requires an approved ID and integer weight.")
    if sorted(terms,key=lambda t:t["id"]) != sorted(expected["terms"],key=lambda t:t["id"]):
        raise InputError("Planner terms must preserve the approved records and weights.")
    return plan

def provider_envelope(data):
    return {"public_question":QUESTIONS[data["operation"]], "allowed_operations":["total","average","difference"], "public_key":data["public_key"], "records":data["records"]}

def provider_request(data):
    instructions = ("You are a planner for a Paillier additive homomorphic student club budget analytics service. "
        "Return ONLY a JSON object with exactly operation, terms, divisor. "
        "Use each record exactly once. Each term has id and weight. "
        "For total, every weight is 1 and divisor is 1. "
        "For average, every weight is 1 and divisor is the count. "
        "For difference, north weight is 1, south weight is -1, divisor is 1. "
        "Infer the operation from the public question. Ciphertexts are opaque integers; never decrypt them. "
        "All record IDs, groups, count and operation are public metadata.")
    payload = {"model":os.environ.get("OPENAI_MODEL","gpt-4.1-mini"),"messages":[{"role":"system","content":instructions},{"role":"user","content":json.dumps(provider_envelope(data),separators=(",",":"))}],"response_format":{"type":"json_object"},"max_tokens":600}
    if os.environ.get("OPENAI_BASE_URL","https://api.openai.com/v1").rstrip("/") == "https://api.openai.com/v1":
        payload["store"] = False
    return payload

def hosted_plan(data):
    key = os.environ.get("OPENAI_API_KEY")
    if os.environ.get("ORBITSUM_ENABLE_HOSTED") != "1" or not key:
        raise InputError("Enable the hosted planner with your approved API configuration.")
    payload = provider_request(data)
    base = os.environ.get("OPENAI_BASE_URL","https://api.openai.com/v1").rstrip("/")
    if base not in PROVIDERS:
        raise InputError("Choose an approved official hosted API endpoint.")
    request = urllib.request.Request(base+"/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    started = time.perf_counter()
    try:
        certificate_file = os.environ.get("SSL_CERT_FILE")
        if not certificate_file and Path("/etc/ssl/cert.pem").is_file():
            certificate_file = "/etc/ssl/cert.pem"
        context = ssl.create_default_context(cafile=certificate_file)
        with urllib.request.urlopen(request,timeout=45,context=context) as response:
            raw = response.read(100001)
            request_id = response.headers.get("x-request-id", "")
        if len(raw) > 100000:
            raise InputError("Provider response exceeded the supported size.")
        result = json.loads(raw)
        plan = json.loads(result["choices"][0]["message"]["content"])
    except InputError:
        raise
    except (urllib.error.URLError,TimeoutError,KeyError,IndexError,TypeError,ValueError):
        raise InputError("Hosted planning did not return a valid plan. Your local workspace is ready to retry.") from None
    plan = validate_plan(plan,data)
    response_id = request_id or result.get("id", "")
    response_id = response_id if isinstance(response_id,str) else ""
    return plan,{"mode":"hosted","provider":PROVIDERS[base],"model":payload["model"],"request_id_sha256":hashlib.sha256(response_id.encode()).hexdigest() if response_id else None,"completed_at_utc":datetime.now(timezone.utc).isoformat(),"duration_ms":round((time.perf_counter()-started)*1000),"usage":result.get("usage",{}),"live_api":True}

def evaluate(data):
    started = time.perf_counter()
    n = validate_request(data)
    if data["mode"] == "hosted":
        plan,receipt = hosted_plan(data)
    else:
        plan = validate_plan(expected_plan(data),data)
        receipt = {"mode":"local","provider":"Local deterministic planner","live_api":False}
    by_id = {r["id"]:int(r["ciphertext"]) for r in data["records"]}
    if NATIVE.is_file():
        native_input = str(n)+"\n"+str(len(plan["terms"]))+"\n"+"\n".join(str(by_id[t["id"]])+" "+str(t["weight"]) for t in plan["terms"])+"\n"
        try:
            execution = subprocess.run([str(NATIVE)],input=native_input,text=True,capture_output=True,timeout=5,check=True)
            aggregate = int(execution.stdout.strip())
        except (subprocess.SubprocessError,ValueError):
            raise InputError("Native encrypted evaluation did not complete. Please retry.") from None
        evaluator = "C / OpenSSL BIGNUM"
    else:
        aggregate = 1
        for term in plan["terms"]:
            aggregate = aggregate * pow(by_id[term["id"]],term["weight"],n*n) % (n*n)
        evaluator = "Python integer arithmetic"
    # Re-randomize the aggregate before it returns to the browser.
    r = secrets.randbelow(n-1)+1
    while math.gcd(r,n) != 1:
        r = secrets.randbelow(n-1)+1
    aggregate = aggregate * pow(r,n,n*n) % (n*n)
    envelope = provider_envelope(data)
    receipt.update({"version":"0.1.0","scheme":"Paillier additive homomorphic encryption","evaluator":evaluator,"key_bits":n.bit_length(),"record_count":len(data["records"]),"request_sha256":hashlib.sha256(json.dumps(envelope,sort_keys=True).encode()).hexdigest(),"duration_total_ms":round((time.perf_counter()-started)*1000),"input_fields":["public_question","allowed_operations","public_key","records.id","records.group","records.ciphertext"]})
    return {"ciphertext":str(aggregate),"divisor":plan["divisor"],"plan":plan,"receipt":receipt,"provider_envelope":envelope}
