from pathlib import Path

ADMIN_JS = (
    Path(__file__).parents[2]
    / "src"
    / "monitor_comunitario"
    / "web"
    / "static"
    / "admin.js"
)


def test_admin_dashboard_does_not_render_dynamic_html() -> None:
    source = ADMIN_JS.read_text(encoding="utf-8")

    assert ".innerHTML" not in source
    assert "textContent" in source
    assert "createElement" in source
