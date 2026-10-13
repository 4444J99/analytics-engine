"""Deterministic synthetic tests for org-events pagination (issue #15)."""

from datetime import date
from unittest.mock import patch

from src.config import GitHubConfig
from src.github_activity import count_org_events


def _push(event_id, size, created_at="2026-02-20T10:00:00Z"):
    return {
        "id": event_id,
        "type": "PushEvent",
        "created_at": created_at,
        "payload": {"size": size},
    }


def _config():
    return GitHubConfig(token="ghp_test")  # allow-secret


SINCE = date(2026, 2, 17)


class TestPagination:
    @patch("src.github_activity.fetch_github_api")
    def test_full_first_page_fetches_second(self, mock_api):
        page1 = [_push(f"ev-{i}", 1) for i in range(100)]
        page2 = [_push("ev-100", 2)]
        mock_api.side_effect = [page1, page2]

        counts = count_org_events(_config(), "organvm-v-logos", SINCE)

        assert counts["commits"] == 102
        assert mock_api.call_count == 2
        first, second = mock_api.call_args_list
        assert "page=1" in first.args[1]
        assert "page=2" in second.args[1]

    @patch("src.github_activity.fetch_github_api")
    def test_short_first_page_makes_no_second_request(self, mock_api):
        mock_api.side_effect = [[_push("ev-0", 1), _push("ev-1", 2)]]

        counts = count_org_events(_config(), "organvm-v-logos", SINCE)

        assert counts["commits"] == 3
        assert mock_api.call_count == 1

    @patch("src.github_activity.fetch_github_api")
    def test_repeated_event_id_counted_once(self, mock_api):
        page1 = [_push(f"ev-{i}", 1) for i in range(99)] + [_push("dup", 1)]
        page2 = [_push("dup", 5), _push("ev-new", 1)]
        mock_api.side_effect = [page1, page2]

        counts = count_org_events(_config(), "organvm-v-logos", SINCE)

        assert counts["commits"] == 101
        assert mock_api.call_count == 2

    @patch("src.github_activity.fetch_github_api")
    def test_stops_when_page_is_wholly_older(self, mock_api):
        page1 = [_push(f"old-{i}", 1, "2026-02-01T10:00:00Z") for i in range(100)]
        mock_api.side_effect = [page1]

        counts = count_org_events(_config(), "organvm-v-logos", SINCE)

        assert counts == {"commits": 0, "prs": 0, "releases": 0}
        assert mock_api.call_count == 1
