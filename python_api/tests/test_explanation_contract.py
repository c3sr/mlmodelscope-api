import json
import pathlib
import sys
import unittest

from pydantic import ValidationError


PYTHON_API = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_API))

from api import PredictRequest
from db import result_matches_explanation
from mq import makePredictMessage


class ExplanationContractTest(unittest.TestCase):
    def test_predict_request_defaults_to_disabled(self):
        request = PredictRequest(
            architecture="amd64",
            batchSize=1,
            desiredResultModality="image_classification",
            gpu=False,
            inputs=[{"src": "image.png", "inputType": "image"}],
            model=1,
            traceLevel="NO_TRACE",
        )
        self.assertFalse(request.explanation.enabled)

    def test_rejects_unknown_method_and_invalid_top_k(self):
        base = {
            "architecture": "amd64",
            "batchSize": 1,
            "desiredResultModality": "image_classification",
            "gpu": False,
            "inputs": [{"src": "image.png", "inputType": "image"}],
            "model": 1,
            "traceLevel": "NO_TRACE",
        }
        with self.assertRaises(ValidationError):
            PredictRequest(
                **base,
                explanation={"enabled": True, "method": "other", "topK": 2},
            )
        with self.assertRaises(ValidationError):
            PredictRequest(
                **base,
                explanation={"enabled": True, "method": "grad_cam", "topK": 1},
            )

    def test_serializes_explanation_to_message(self):
        explanation = {"enabled": True, "method": "grad_cam", "topK": 2}
        message = makePredictMessage(
            "amd64",
            1,
            "image_classification",
            False,
            [{"src": "image.png", "inputType": "image"}],
            False,
            {},
            {},
            "TorchVision.ResNet.18",
            "NO_TRACE",
            0,
            "localhost:6831",
            explanation,
        )
        self.assertEqual(message["Explanation"], explanation)

    def test_explanation_aware_reuse(self):
        request = {"enabled": True, "method": "grad_cam", "topK": 2}
        complete = {
            "explanation": {
                "schemaVersion": "1.3",
                "status": "complete",
                "method": "grad_cam",
                "topK": 2,
            }
        }
        self.assertTrue(result_matches_explanation(json.dumps(complete), request))
        self.assertFalse(result_matches_explanation({}, request))
        self.assertFalse(
            result_matches_explanation(
                {"explanation": {**complete["explanation"], "topK": 1}}, request
            )
        )
        self.assertFalse(result_matches_explanation({}, {"enabled": False}))
        self.assertFalse(
            result_matches_explanation(
                {"error": {"code": "inference_failed"}}, {"enabled": False}
            )
        )
        self.assertTrue(
            result_matches_explanation(
                {"responses": [{"features": []}]}, {"enabled": False}
            )
        )


if __name__ == "__main__":
    unittest.main()
