import json
import os

from src.aggregator import aggregate
from src.dashboard import generate_dashboard
from src.signals import generate_signals


def test_pipeline_smoke_and_status(tmp_path):
    """End-to-end smoke check for pipeline execution and artifact schema/status verification."""
    raw_dir = tmp_path / "data" / "raw"
    data_dir = tmp_path / "data"
    history_dir = tmp_path / "data" / "history"
    docs_dir = tmp_path / "docs" / "dashboard"

    raw_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    with open(os.path.join(fixtures_dir, "goatcounter_pages.json")) as f:
        gc_data = json.load(f)
    gc_data["available"] = True
    gc_data["period"] = {"start": "2026-02-10", "end": "2026-02-17"}
    gc_data["site_totals"] = {"page_views": 1045, "unique_visitors": 782}
    gc_data["pages"] = gc_data.get("hits", [])
    with open(raw_dir / "goatcounter-2026-02-17.json", "w") as f:
        json.dump(gc_data, f)

    with open(os.path.join(fixtures_dir, "github_activity.json")) as f:
        gh_data = json.load(f)
    with open(raw_dir / "github-activity-2026-02-17.json", "w") as f:
        json.dump(gh_data, f)

    kpi_config_path = os.path.join(os.path.dirname(__file__), "..", "config", "outcome-kpis.yaml")

    # 1. Run Aggregator
    agg_summary = aggregate(str(raw_dir), str(data_dir), str(history_dir))
    assert agg_summary["goatcounter_available"] is True
    assert agg_summary["github_available"] is True

    engagement_path = data_dir / "engagement-metrics.json"
    system_report_path = data_dir / "system-engagement-report.json"

    assert engagement_path.exists()
    assert system_report_path.exists()

    with open(engagement_path) as f:
        eng_data = json.load(f)
        assert "generated_at" in eng_data
        assert "site_totals" in eng_data

    with open(system_report_path) as f:
        sys_data = json.load(f)
        assert "generated_at" in sys_data
        assert "web_engagement" in sys_data
        assert "github_activity" in sys_data
        assert "status" in sys_data
        assert sys_data["status"] == "ok"

    # 2. Run Dashboard Generator
    dash_path = generate_dashboard(str(data_dir), str(docs_dir))
    assert os.path.exists(dash_path)

    dashboard_html_path = docs_dir / "index.html"
    assert dashboard_html_path.exists()
    with open(dashboard_html_path) as f:
        html_content = f.read()
        assert "<!DOCTYPE html>" in html_content or "<html" in html_content

    # 3. Run Weekly Signals
    if os.path.exists(kpi_config_path):
        sig_result = generate_signals(str(data_dir), str(data_dir), kpi_config_path)
        assert os.path.exists(sig_result["json"])
        assert os.path.exists(sig_result["markdown"])
