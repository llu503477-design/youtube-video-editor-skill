import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVPACK_TEST_PATH = ROOT / "youtube-video-typography-devpack" / "tests" / "test_typography.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module


def load_tests(_loader, _standard_tests, _pattern):
    devpack_tests = _load_module(
        "youtube_video_typography_devpack_tests",
        DEVPACK_TEST_PATH,
    )
    integration = _load_module(
        "tests.test_typography_integration",
        ROOT / "tests" / "test_typography_integration.py",
    )

    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(devpack_tests))
    suite.addTests(loader.loadTestsFromModule(integration))
    return suite
