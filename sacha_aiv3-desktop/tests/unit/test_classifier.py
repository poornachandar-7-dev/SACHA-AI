"""Unit tests — core/router/classifier.py."""

from core.router.classifier import KeywordClassifier


def test_private_message_stays_local():
    intent = KeywordClassifier().classify("my account password for github is 123")
    assert intent.privacy_sensitive is True
    assert intent.provider_hint == "local"
    assert intent.category == "private"


def test_tool_call_syntax():
    intent = KeywordClassifier().classify("!weather in Paris today", available_tools=("weather",))
    assert intent.category == "tool"
    assert intent.tool_hint == "weather"


def test_tool_call_unknown_tool_passes_through():
    intent = KeywordClassifier().classify("!frobnicate the widgets", available_tools=("weather",))
    # "!frobnicate" is not registered in available_tools, so it is not a tool call.
    assert intent.tool_hint is None


def test_short_greeting_is_simple():
    intent = KeywordClassifier().classify("hi")
    assert intent.complexity == "simple"
    assert intent.category == "chat"


def test_complex_question_is_complex():
    intent = KeywordClassifier().classify("explain the architecture and analyze the tradeoffs please")
    assert intent.complexity == "complex"


def test_reminder_category():
    intent = KeywordClassifier().classify("remind me to call mom every morning at 8")
    assert intent.category == "reminder"
    assert intent.provider_hint == "local"


def test_code_category():
    intent = KeywordClassifier().classify("help me debug this python traceback")
    assert intent.category == "code"


def test_long_text_is_complex():
    long_text = "please " + "analyze details, compare options, and research everything. " * 20
    intent = KeywordClassifier().classify(long_text)
    assert intent.complexity == "complex"
