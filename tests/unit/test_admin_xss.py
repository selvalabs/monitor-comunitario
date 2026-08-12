from pathlib import Path

ADMIN_JS = (
    Path(__file__).parents[2]
    / "src"
    / "monitor_comunitario"
    / "web"
    / "static"
    / "admin.js"
)

MEMBER_JS = (
    Path(__file__).parents[2]
    / "src"
    / "monitor_comunitario"
    / "web"
    / "static"
    / "member.js"
)


def test_admin_dashboard_does_not_render_dynamic_html() -> None:
    source = ADMIN_JS.read_text(encoding="utf-8")

    assert ".innerHTML" not in source
    assert "textContent" in source
    assert "createElement" in source


def test_member_session_script_does_not_use_browser_storage_or_dynamic_html() -> None:
    source = MEMBER_JS.read_text(encoding="utf-8")

    assert "sessionStorage" not in source
    assert "localStorage" not in source
    assert "innerHTML" in source
    assert 'innerHTML = "<div class=\\"empty-state\\">' in source
    assert "textContent = notification.message" in source
