"""Tests for the webhook notification hook."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from stackdiff.notify import notify_webhook
from stackdiff.summary import DiffSummary
from stackdiff.diff import DiffReport


def _empty_report() -> DiffReport:
    return DiffReport(entries=[])


def test_webhook_posts_json():
    summary = DiffSummary(total=1, created=1, updated=0, destroyed=0)
    hook = notify_webhook("http://example.com/hook")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        hook(Path("plan.tfplan.txt"), _empty_report(), summary)

    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://example.com/hook"
    assert req.method == "POST"
    assert b"created" in req.data


def test_webhook_handles_error(capsys):
    summary = DiffSummary(total=0, created=0, updated=0, destroyed=0)
    hook = notify_webhook("http://bad-host.invalid/hook", timeout=0.1)

    with patch("urllib.request.urlopen", side_effect=OSError("unreachable")):
        hook(Path("plan.tfplan.txt"), _empty_report(), summary)

    out = capsys.readouterr().out
    assert "Webhook error" in out
