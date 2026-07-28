# tests/test_memory.py
import os
import importlib
import pytest


@pytest.fixture
def memory_module(tmp_path, monkeypatch):
    monkeypatch.setenv("SACHA_DB_PATH", str(tmp_path / "test.db"))
    import memory
    importlib.reload(memory)
    return memory


def test_save_and_get_history(memory_module):
    memory_module.init_db()
    memory_module.save_message("user", "hello")
    history = memory_module.get_history()
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"


def test_history_order_oldest_first(memory_module):
    memory_module.init_db()
    memory_module.save_message("user", "first")
    memory_module.save_message("assistant", "second")
    history = memory_module.get_history()
    assert history[0]["content"] == "first"
    assert history[1]["content"] == "second"


def test_count_messages(memory_module):
    memory_module.init_db()
    memory_module.save_message("user", "one")
    memory_module.save_message("user", "two")
    assert memory_module.count_messages() == 2


def test_delete_message(memory_module):
    memory_module.init_db()
    mid = memory_module.save_message("user", "to delete")
    assert memory_module.delete_message(mid) is True
    assert memory_module.count_messages() == 0


def test_clear_history(memory_module):
    memory_module.init_db()
    memory_module.save_message("user", "a")
    memory_module.save_message("user", "b")
    memory_module.clear_history()
    assert memory_module.count_messages() == 0


def test_save_message_empty_role_raises(memory_module):
    memory_module.init_db()
    with pytest.raises(ValueError):
        memory_module.save_message("", "hello")


def test_db_path_uses_env_var(monkeypatch, tmp_path):
    custom_path = tmp_path / "custom.db"
    monkeypatch.setenv("SACHA_DB_PATH", str(custom_path))
    import memory
    importlib.reload(memory)
    assert memory.DB_PATH == custom_path


def test_db_path_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("SACHA_DB_PATH", raising=False)
    import memory
    importlib.reload(memory)
    # regression check for the bug where Path("") silently became "."
    assert str(memory.DB_PATH) != "."
    assert memory.DB_PATH.name == "sacha.db"