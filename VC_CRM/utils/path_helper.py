from pathlib import Path
import sys

class PathHelper:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

    def get(self, *parts):
        return self.base_dir.joinpath(*parts)

    def ensure_dir(self, *parts):
        path = self.get(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_text(self, *parts, encoding='utf-8'):
        path = self.get(*parts)
        return path.read_text(encoding=encoding)

    def write_text(self, *parts, content='', encoding='utf-8'):
        path = self.get(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return path

    def list_dir(self, *parts):
        path = self.get(*parts)
        return list(path.iterdir()) if path.exists() else []

    def is_windows(self):
        return sys.platform.startswith("win")

    def is_linux(self):
        return sys.platform.startswith("linux")

    def is_mac(self):
        return sys.platform == "darwin"