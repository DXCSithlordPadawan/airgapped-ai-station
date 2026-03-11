"""
test_smoke_test.py — Tests for smoke_test_agent.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import smoke_test_agent as sut


class TestVerifyInferenceReachable:
    def test_returns_true_on_200(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        with patch("smoke_test_agent.requests.post", return_value=mock_resp):
            assert sut.verify_inference_reachable() is True

    def test_returns_false_on_connection_error(self) -> None:
        import requests
        with patch("smoke_test_agent.requests.post", side_effect=requests.exceptions.ConnectionError):
            assert sut.verify_inference_reachable() is False

    def test_returns_false_on_timeout(self) -> None:
        import requests
        with patch("smoke_test_agent.requests.post", side_effect=requests.exceptions.Timeout):
            assert sut.verify_inference_reachable() is False


class TestVerifyModelLoaded:
    def test_returns_true_when_model_present(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "models": [{"name": "qwen2.5-coder:32b"}, {"name": "other:7b"}]
        }
        with patch("smoke_test_agent.requests.get", return_value=mock_resp):
            assert sut.verify_model_loaded() is True

    def test_returns_false_when_model_absent(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"models": [{"name": "llama3:8b"}]}
        with patch("smoke_test_agent.requests.get", return_value=mock_resp):
            assert sut.verify_model_loaded() is False

    def test_returns_false_on_connection_error(self) -> None:
        import requests
        with patch("smoke_test_agent.requests.get", side_effect=requests.exceptions.ConnectionError):
            assert sut.verify_model_loaded() is False

    def test_returns_false_on_malformed_response(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"unexpected_key": []}
        with patch("smoke_test_agent.requests.get", return_value=mock_resp):
            assert sut.verify_model_loaded() is False


class TestVerifyPodmanSandbox:
    def test_returns_true_on_success(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "sandbox-ok\n"
        with patch("smoke_test_agent.subprocess.run", return_value=mock_result):
            assert sut.verify_podman_sandbox() is True

    def test_returns_false_on_nonzero_exit(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        with patch("smoke_test_agent.subprocess.run", return_value=mock_result):
            assert sut.verify_podman_sandbox() is False

    def test_returns_false_when_podman_not_found(self) -> None:
        with patch("smoke_test_agent.subprocess.run", side_effect=FileNotFoundError):
            assert sut.verify_podman_sandbox() is False
