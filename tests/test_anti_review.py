"""Independent local privacy-boundary checks. Never invokes a hosted API.

Synthetic private values and ephemeral test decryption parameters remain in memory.
The browser module generates the test key; the native worker sees public values only.
"""
import copy
import http.client
import json
import subprocess
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
from server import Handler, ThreadingHTTPServer


class AntiManagerReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = """
import {generateKey, encrypt} from './web/paillier.js';
const key = await generateKey();
const values = [1700,2350,800,1150,0,1000000];
const ciphertexts = values.map(value => encrypt(value,key).toString());
const repeat = encrypt(values[0],key).toString();
process.stdout.write(JSON.stringify({n:key.n.toString(),lambda:key.lambda.toString(),mu:key.mu.toString(),ciphertexts,repeat}));
"""
        completed = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT,
                                   text=True, capture_output=True, check=True, timeout=30)
        cls.fixture = json.loads(completed.stdout)
        cls.n = int(cls.fixture["n"])
        cls.base = {"mode": "local", "operation": "total", "public_key": cls.fixture["n"],
                    "records": [{"id": f"site-{i+1}", "group": "north" if i < 2 else "south",
                                 "ciphertext": c} for i, c in enumerate(cls.fixture["ciphertexts"][:4])]}

    def reveal(self, raw):
        n = self.n
        c = int(raw)
        m = (((pow(c, int(self.fixture["lambda"]), n*n)-1)//n)*int(self.fixture["mu"])) % n
        return m-n if m > n//2 else m

    def test_browser_generated_paillier_is_randomized(self):
        self.assertNotEqual(self.fixture["ciphertexts"][0], self.fixture["repeat"])
        self.assertEqual(self.reveal(self.fixture["repeat"]), 1700)

    def test_browser_range_endpoints_roundtrip(self):
        self.assertEqual(self.reveal(self.fixture["ciphertexts"][4]), 0)
        self.assertEqual(self.reveal(self.fixture["ciphertexts"][5]), 1000000)

    def test_total_average_and_difference(self):
        for operation, numerator, divisor in [("total",6000,1),("average",6000,4),("difference",2100,1)]:
            with self.subTest(operation=operation):
                request = copy.deepcopy(self.base)
                request["operation"] = operation
                result = engine.evaluate(request)
                self.assertEqual(self.reveal(result["ciphertext"]), numerator)
                self.assertEqual(result["divisor"], divisor)
                self.assertFalse(result["receipt"]["live_api"])
                self.assertEqual(result["receipt"]["evaluator"], "C / OpenSSL BIGNUM")

    def test_negative_difference(self):
        request = copy.deepcopy(self.base)
        request["operation"] = "difference"
        for row in request["records"]:
            row["group"] = "south" if row["group"] == "north" else "north"
        self.assertEqual(self.reveal(engine.evaluate(request)["ciphertext"]), -2100)

    def test_32_records_have_exact_bounded_total(self):
        request = copy.deepcopy(self.base)
        request["records"] = [{"id":f"site-{i+1}", "group":"north", "ciphertext":self.fixture["ciphertexts"][5]} for i in range(32)]
        self.assertEqual(self.reveal(engine.evaluate(request)["ciphertext"]), 32000000)

    def test_aggregate_is_rerandomized(self):
        first, second = engine.evaluate(self.base), engine.evaluate(self.base)
        self.assertNotEqual(first["ciphertext"], second["ciphertext"])
        self.assertEqual(self.reveal(first["ciphertext"]), self.reveal(second["ciphertext"]))

    def test_native_signed_cancellation(self):
        c = self.fixture["ciphertexts"][0]
        completed = subprocess.run([str(engine.NATIVE)], input=f"{self.n}\n2\n{c} 1\n{c} -1\n",
                                   text=True, capture_output=True, timeout=5)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), "1")

    def test_native_rejects_malformed_group_elements(self):
        valid = self.fixture["ciphertexts"][0]
        for invalid in ["0", str(self.n), str(self.n*self.n), "-1", "bad"]:
            with self.subTest(kind="malformed ciphertext"):
                completed = subprocess.run([str(engine.NATIVE)], input=f"{self.n}\n2\n{invalid} 1\n{valid} 1\n",
                                           text=True, capture_output=True, timeout=5)
                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(completed.stdout, "")

    def test_private_parameters_and_extra_fields_rejected(self):
        for field in ["lambda", "mu", "plaintext", "api_key", "instructions"]:
            request = copy.deepcopy(self.base)
            request[field] = "synthetic-rejection-canary"
            with self.subTest(field=field), self.assertRaises(engine.InputError):
                engine.validate_request(request)

    def test_planner_rejects_unapproved_terms(self):
        original = engine.expected_plan(self.base)
        candidates = []
        bad = copy.deepcopy(original); bad["terms"][0]["weight"] = True; candidates.append(bad)
        bad = copy.deepcopy(original); bad["terms"][0]["weight"] = 2; candidates.append(bad)
        bad = copy.deepcopy(original); bad["terms"][0]["id"] = "site-99"; candidates.append(bad)
        bad = copy.deepcopy(original); bad["terms"][0] = copy.deepcopy(bad["terms"][1]); candidates.append(bad)
        bad = copy.deepcopy(original); bad["execute"] = "decrypt-and-export"; candidates.append(bad)
        bad = copy.deepcopy(original); bad["divisor"] = True; candidates.append(bad)
        for index, bad in enumerate(candidates):
            with self.subTest(case=index), self.assertRaises(engine.InputError):
                engine.validate_plan(bad, self.base)

    def test_malformed_json_types_are_input_errors(self):
        for field in ["mode", "operation"]:
            for value in [[], {}]:
                request = copy.deepcopy(self.base); request[field] = value
                with self.subTest(field=field, kind=type(value).__name__), self.assertRaises(engine.InputError):
                    engine.validate_request(request)
        for value in [[], {}]:
            request = copy.deepcopy(self.base); request["records"][0]["group"] = value
            with self.subTest(field="group", kind=type(value).__name__), self.assertRaises(engine.InputError):
                engine.validate_request(request)

    def test_provider_payload_contains_public_fields_only(self):
        payload = engine.provider_request(self.base)
        envelope = json.loads(payload["messages"][-1]["content"])
        self.assertEqual(set(envelope), {"public_question", "allowed_operations", "public_key", "records"})
        self.assertNotIn("operation", envelope)
        self.assertIsInstance(envelope["public_question"], str)
        self.assertTrue(envelope["public_question"].endswith("?"))
        self.assertEqual(envelope["records"], self.base["records"])
        serialized = json.dumps(payload)
        for secret in [self.fixture["lambda"], self.fixture["mu"]]:
            self.assertNotIn(secret, serialized)

    def test_displayed_envelope_matches_provider_user_message(self):
        for operation in ["total", "average", "difference"]:
            request = copy.deepcopy(self.base); request["operation"] = operation
            expected = json.loads(engine.provider_request(request)["messages"][-1]["content"])
            with self.subTest(operation=operation):
                self.assertEqual(engine.evaluate(request)["provider_envelope"], expected)

    def test_loopback_http_boundary(self):
        server = ThreadingHTTPServer(("127.0.0.1",0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        cases = [
            ({"Host":"untrusted.invalid", "Content-Type":"application/json"}, 403),
            ({"Host":f"127.0.0.1:{port}", "Origin":"https://untrusted.invalid", "Content-Type":"application/json"}, 403),
            ({"Host":f"127.0.0.1:{port}", "Content-Type":"text/plain"}, 415),
        ]
        try:
            for headers, expected in cases:
                connection = http.client.HTTPConnection("127.0.0.1",port,timeout=5)
                connection.request("POST","/api/evaluate",body="{}",headers=headers)
                response = connection.getresponse()
                self.assertEqual(response.status,expected)
                self.assertNotIn("Access-Control-Allow-Origin", dict(response.getheaders()))
                response.read()
                connection.close()
            connection = http.client.HTTPConnection("127.0.0.1",port,timeout=5)
            connection.request("POST","/api/evaluate",body=json.dumps(self.base),
                               headers={"Content-Type":"application/json", "Origin":f"http://127.0.0.1:{port}"})
            response = connection.getresponse()
            self.assertEqual(response.status,200)
            result = json.loads(response.read())
            self.assertEqual(self.reveal(result["ciphertext"]),6000)
            self.assertEqual(response.getheader("Cache-Control"),"no-store")
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
