import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".vendor"))
from packages.integrations.typesafe import client as module

SDK_AVAILABLE = importlib.util.find_spec("typesafe_sdk") is not None


class Handler(BaseHTTPRequestHandler):
    attempts = 0

    def do_POST(self):  # noqa: N802
        Handler.attempts += 1
        if Handler.attempts == 1:
            self.send_response(429)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.assertions = body
        response = {
            "model": "jev-test",
            "answers": {
                "route": {"type": "choice", "choice": "technical", "confidence": 0.9,
                           "probabilities": {"technical": 0.9, "billing": 0.1}},
                "severity": {"type": "score", "score": 1.2, "confidence": 0.8,
                              "legend": {"0": "low", "1": "medium", "2": "high"},
                              "probabilities": {"0": 0.1, "1": 0.6, "2": 0.3}},
                "urgent": {"type": "noul", "noul": 0.95}
            },
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }
        encoded = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        pass


@unittest.skipUnless(SDK_AVAILABLE, "typesafe-sdk is installed in the container")
class BridgeTests(unittest.TestCase):
    def test_all_primitives_and_retry(self):
        Handler.attempts = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = json.loads((ROOT / "examples/basic_request.json").read_text())
            result = module.evaluate(request, api_key="test-key",
                                      url=f"http://127.0.0.1:{server.server_port}",
                                      retries=2)
            self.assertEqual(result["answers"]["route"]["choice"], "technical")
            self.assertEqual(result["answers"]["severity"]["type"], "score")
            self.assertEqual(result["answers"]["urgent"]["noul"], 0.95)
            self.assertEqual(Handler.attempts, 2)
        finally:
            server.shutdown()
            server.server_close()

    def test_validation_rejects_bad_question(self):
        with self.assertRaises(module.InputError):
            module.evaluate({"state": "x", "questions": {"q": {"type": "wat"}}},
                            api_key="test-key", url="http://127.0.0.1:1")


if __name__ == "__main__":
    unittest.main()
