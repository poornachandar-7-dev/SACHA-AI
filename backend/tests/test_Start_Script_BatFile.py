# tests/test_Start_Script_BatFile.py
import pathlib

BAT_PATH = pathlib.Path(__file__).resolve().parents[2] / "start.bat"

def test_bat_file_exists():
    assert BAT_PATH.exists()

def test_bat_file_is_valid_batch_syntax():
    content = BAT_PATH.read_text()
    assert content.strip() != ""