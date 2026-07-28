"""
Tests for tools.py — run with: pytest test_tools.py -v
"""
from unittest.mock import patch
import tools


# --- _normalize_url ----------------------------------------------------

def test_normalize_known_site():
    assert tools._normalize_url("youtube") == "https://youtube.com"

def test_normalize_known_site_case_insensitive():
    assert tools._normalize_url("YouTube") == "https://youtube.com"

def test_normalize_full_url_passthrough():
    url = "https://github.com/anthropics"
    assert tools._normalize_url(url) == url

def test_normalize_domain_without_scheme():
    assert tools._normalize_url("example.com") == "https://example.com"

def test_normalize_unknown_returns_none():
    assert tools._normalize_url("not a real site!!") is None

def test_normalize_empty_returns_none():
    assert tools._normalize_url("") is None


# --- detect_tool_call ----------------------------------------------------

def test_detect_open_youtube():
    tool, arg = tools.detect_tool_call("open youtube")
    assert tool == "open_site"
    assert arg == "youtube"

def test_detect_go_to_domain():
    tool, arg = tools.detect_tool_call("go to github.com")
    assert tool == "open_site"
    assert "github.com" in arg

def test_detect_full_url():
    tool, arg = tools.detect_tool_call("open https://github.com/foo")
    assert tool == "open_site"
    assert arg == "https://github.com/foo"

def test_detect_take_picture_named():
    tool, arg = tools.detect_tool_call("take a picture named my_photo.jpg")
    assert tool == "capture_webcam"
    assert "my_photo.jpg" in arg

def test_detect_read_image():
    tool, arg = tools.detect_tool_call("read image test.png")
    assert tool == "get_image_info"
    assert arg == "test.png"

def test_detect_no_match_returns_none_none():
    assert tools.detect_tool_call("what's the weather today") == (None, None)

def test_detect_empty_message():
    assert tools.detect_tool_call("") == (None, None)


# --- _run_open_site (mocking webbrowser so nothing actually opens) -------

@patch("tools.webbrowser.open_new_tab")
@patch("tools.is_headless", return_value=False)
def test_open_site_known_site(mock_headless, mock_open):
    result = tools._run_open_site("github")
    mock_open.assert_called_once_with("https://github.com")
    assert "Opened" in result

@patch("tools.webbrowser.open_new_tab")
@patch("tools.is_headless", return_value=False)
def test_open_site_full_url(mock_headless, mock_open):
    result = tools._run_open_site("https://example.org")
    mock_open.assert_called_once_with("https://example.org")
    assert "Opened" in result

@patch("tools.webbrowser.open_new_tab")
@patch("tools.is_headless", return_value=False)
def test_open_site_unknown_falls_back_to_search(mock_headless, mock_open):
    result = tools._run_open_site("some random unknown thing")
    called_url = mock_open.call_args[0][0]
    assert "google.com/search?q=" in called_url
    assert "searched the web" in result

@patch("tools.is_headless", return_value=True)
def test_open_site_headless_no_browser_call(mock_headless):
    result = tools._run_open_site("youtube")
    assert "Headless" in result

def test_open_site_no_arg():
    result = tools._run_open_site(None)
    assert "No site or URL" in result


# --- run_tool / registry --------------------------------------------------

def test_run_tool_unknown_tool_name():
    result = tools.run_tool("not_a_real_tool", "x")
    assert "Unknown tool" in result

def test_run_tool_no_tool_name():
    result = tools.run_tool(None, "x")
    assert "No tool specified" in result

def test_open_site_registered_in_tools_dict():
    assert "open_site" in tools.TOOLS
    assert "get_image_info" in tools.TOOLS
    assert "capture_webcam" in tools.TOOLS