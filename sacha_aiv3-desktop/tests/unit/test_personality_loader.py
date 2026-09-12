"""Unit tests — personality/loader.py."""

import pytest

from personality.loader import PersonalityError, PersonalityLoader


def test_system_prompt_contains_identity(personality):
    prompt = personality.system_prompt()
    assert "SACHA" in prompt
    assert "Smart Autonomous Cognitive Helper Assistant" in prompt


def test_presets_are_enumerated(personality):
    presets = personality.list_presets()
    assert "professional" in presets
    assert "casual" in presets
    assert "default" in presets


def test_load_preset_content(personality):
    content = personality.load_preset("professional")
    assert "Use case: work" in content


def test_unknown_preset_raises(personality):
    with pytest.raises(PersonalityError):
        personality.load_preset("not_a_real_preset")


def test_apply_preset_backs_up_and_changes_soul(personality, tmp_path):
    import shutil

    loader = PersonalityLoader(
        soul_path=tmp_path / "SOUL.md",
        history_dir=tmp_path / "history",
    )
    shutil.copyfile(personality.soul_path, loader.soul_path)  # start from the real SOUL

    snapshot = loader.apply_preset("professional")
    assert snapshot.exists()
    assert "Use case: work" in loader.system_prompt()

    # history now has the backup
    snapshots = loader.list_snapshots()
    assert snapshots and snapshot in snapshots


def test_save_snapshot_requires_soul(personality, tmp_path):
    loader = PersonalityLoader(soul_path=tmp_path / "missing.md", history_dir=tmp_path / "history")
    with pytest.raises(PersonalityError):
        loader.save_snapshot()
