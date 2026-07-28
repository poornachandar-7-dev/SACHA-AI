# tests/test_app.py
from unittest.mock import patch
from fastapi.testclient import TestClient
import app as app_module

client = TestClient(app_module.app)


# --- / (health check) ------------------------------------------------------

def test_health_check():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "SACHA backend is running"}


# --- /history ----------------------------------------------------------

@patch("app.get_history")
def test_history_endpoint(mock_get_history):
    mock_get_history.return_value = [
        {"id": 1, "role": "user", "content": "hi", "timestamp": "2026-01-01T00:00:00"}
    ]
    resp = client.get("/history")
    assert resp.status_code == 200
    assert resp.json() == {"history": mock_get_history.return_value}
    mock_get_history.assert_called_once_with()


# --- /chat: tool path ----------------------------------------------------

@patch("app.save_message")
@patch("app.run_tool")
@patch("app.detect_tool_call")
def test_chat_triggers_tool(mock_detect, mock_run_tool, mock_save):
    mock_detect.return_value = ("open_site", "youtube")
    mock_run_tool.return_value = "Opened https://youtube.com in your web browser."

    resp = client.post("/chat", json={"message": "open youtube"})

    assert resp.status_code == 200
    assert resp.json() == {"reply": "Opened https://youtube.com in your web browser."}
    mock_detect.assert_called_once_with("open youtube")
    mock_run_tool.assert_called_once_with("open_site", "youtube")
    # saves both the user message and the assistant's reply
    assert mock_save.call_count == 2
    mock_save.assert_any_call("user", "open youtube")
    mock_save.assert_any_call("assistant", "Opened https://youtube.com in your web browser.")


# --- /chat: AI path (no tool detected) ------------------------------------

@patch("app.save_message")
@patch("app.get_history")
@patch("app.generate_reply")
@patch("app.detect_tool_call")
def test_chat_falls_back_to_ai(mock_detect, mock_generate, mock_get_history, mock_save):
    mock_detect.return_value = (None, None)
    mock_get_history.return_value = [{"role": "user", "content": "earlier msg"}]
    mock_generate.return_value = "Hello! How can I help?"

    resp = client.post("/chat", json={"message": "hello"})

    assert resp.status_code == 200
    assert resp.json() == {"reply": "Hello! How can I help?"}
    mock_generate.assert_called_once_with("hello", context=mock_get_history.return_value)
    mock_save.assert_any_call("user", "hello")
    mock_save.assert_any_call("assistant", "Hello! How can I help?")


# --- /chat: request validation ------------------------------------------

def test_chat_missing_message_field_returns_422():
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_chat_non_string_message_returns_422():
    resp = client.post("/chat", json={"message": 12345})
    assert resp.status_code == 422


# Note: /shutdown is intentionally not tested here since it kills the
# running process via os.kill(os.getpid(), signal.SIGINT) — not safe to
# exercise in a normal test run without mocking os.kill as well.