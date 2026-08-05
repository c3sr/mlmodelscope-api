import json
import pathlib
import sys
import unittest

from pydantic import ValidationError


PYTHON_API = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_API))

from api import PredictRequest, normalize_explanation_settings
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
        settings = normalize_explanation_settings(request.explanation)
        self.assertEqual(settings["audience"]["userLevel"], "intermediate")
        self.assertEqual(settings["audience"]["detailLevel"], "standard")

    def test_text_to_text_request_accepts_prompt_input_without_explanation(self):
        request = PredictRequest(
            architecture="amd64",
            batchSize=1,
            desiredResultModality="text_to_text",
            gpu=False,
            inputs=[{"src": "Once upon a time", "inputType": "TEXT"}],
            model=10000,
            traceLevel="NO_TRACE",
        )

        self.assertEqual(request.desiredResultModality, "text_to_text")
        self.assertEqual(request.inputs[0]["src"], "Once upon a time")
        self.assertFalse(request.explanation.enabled)

    def test_text_to_text_request_accepts_token_probability_explanation(self):
        request = PredictRequest(
            architecture="amd64",
            batchSize=1,
            desiredResultModality="text_to_text",
            gpu=False,
            inputs=[{"src": "Once upon a time", "inputType": "TEXT"}],
            model=10000,
            traceLevel="NO_TRACE",
            explanation={"enabled": True, "method": "token_probability", "topK": 5},
        )
        settings = normalize_explanation_settings(request.explanation)

        self.assertEqual(settings["method"], "token_probability")
        self.assertEqual(settings["topK"], 5)

    def test_rejects_unknown_method_invalid_top_k_and_unknown_user_level(self):
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
        with self.assertRaises(ValidationError):
            PredictRequest(
                **base,
                explanation={
                    "enabled": True,
                    "method": "grad_cam",
                    "topK": 2,
                    "userLevel": "expert",
                },
            )

    def test_normalizes_user_level_to_presentation_profile(self):
        request = PredictRequest(
            architecture="amd64",
            batchSize=1,
            desiredResultModality="image_classification",
            gpu=False,
            inputs=[{"src": "image.png", "inputType": "image"}],
            model=1,
            traceLevel="NO_TRACE",
            explanation={
                "enabled": True,
                "method": "grad_cam",
                "topK": 2,
                "userLevel": "beginner",
            },
        )

        settings = normalize_explanation_settings(request.explanation)

        self.assertEqual(settings["audience"]["userLevel"], "beginner")
        self.assertEqual(settings["audience"]["terminology"], "plain")
        self.assertFalse(settings["audience"]["includeTechnicalDetails"])

    def test_allows_profile_overrides(self):
        request = PredictRequest(
            architecture="amd64",
            batchSize=1,
            desiredResultModality="image_classification",
            gpu=False,
            inputs=[{"src": "image.png", "inputType": "image"}],
            model=1,
            traceLevel="NO_TRACE",
            explanation={
                "enabled": True,
                "method": "grad_cam",
                "topK": 2,
                "userLevel": "advanced",
                "detailLevel": "standard",
                "evidenceView": "focus",
            },
        )

        settings = normalize_explanation_settings(request.explanation)

        self.assertEqual(settings["audience"]["userLevel"], "advanced")
        self.assertEqual(settings["audience"]["detailLevel"], "standard")
        self.assertEqual(settings["audience"]["terminology"], "technical")
        self.assertEqual(settings["audience"]["evidenceView"], "focus")

    def test_serializes_explanation_to_message(self):
        explanation = normalize_explanation_settings(
            PredictRequest(
                architecture="amd64",
                batchSize=1,
                desiredResultModality="image_classification",
                gpu=False,
                inputs=[{"src": "image.png", "inputType": "image"}],
                model=1,
                traceLevel="NO_TRACE",
                explanation={
                    "enabled": True,
                    "method": "grad_cam",
                    "topK": 2,
                    "userLevel": "intermediate",
                },
            ).explanation
        )
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
        self.assertEqual(
            message["Explanation"]["audience"]["userLevel"], "intermediate"
        )

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
