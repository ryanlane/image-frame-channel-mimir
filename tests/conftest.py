import os
import shutil
import tempfile
from pathlib import Path
import pytest

# Adjust import path to allow direct channel import
CHANNEL_ROOT = Path(__file__).parent.parent / "channels" / "photo_frame"

@pytest.fixture()
def temp_channel_dir():
    tmp_dir = Path(tempfile.mkdtemp(prefix="photoframe_test_"))
    # Copy minimal required runtime assets (config + placeholder if present)
    shutil.copy(CHANNEL_ROOT / "config.json", tmp_dir / "config.json")
    assets_src = CHANNEL_ROOT / "assets"
    if (assets_src / "placeholder.jpg").exists():
        (tmp_dir / "assets" / "uploads").mkdir(parents=True, exist_ok=True)
        shutil.copy(assets_src / "placeholder.jpg", tmp_dir / "placeholder.jpg")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)

@pytest.fixture()
def photoframe_channel(temp_channel_dir):
    # Import channel dynamically from source file to mimic runtime loader
    import importlib.util, sys
    channel_path = CHANNEL_ROOT / "channel.py"
    spec = importlib.util.spec_from_file_location("test_photoframe_channel", channel_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    sys.modules[spec.name] = mod  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    ChannelClass = getattr(mod, "ChannelClass")
    return ChannelClass(str(temp_channel_dir))
