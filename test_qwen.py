"""Optional manual smoke check for an OpenAI-compatible local model server."""
import os
import unittest

import requests

BASE_URL = "http://localhost:1234/v1"


@unittest.skipUnless(os.getenv("RUN_LOCAL_LLM_TESTS") == "1", "local model server is optional")
class LocalModelSmokeTest(unittest.TestCase):
    def test_chat_completion(self):
        models = requests.get(f"{BASE_URL}/models", timeout=3).json()["data"]
        self.assertTrue(models)
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            json={"model": models[0]["id"], "messages": [{"role": "user", "content": "Say hello in one sentence."}], "temperature": 0.7},
            timeout=60,
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
