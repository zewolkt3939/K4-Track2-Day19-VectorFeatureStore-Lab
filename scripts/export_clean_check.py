"""Export current tracked source without venv, generated input data or host caches."""
from pathlib import Path
import subprocess
import tarfile
import io

root = Path(__file__).resolve().parent.parent
target = root / ".runtime/clean-check"
target.mkdir(parents=True, exist_ok=True)
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode("utf-8").split("\0")
with tarfile.open(target / "source.tar", "w") as archive:
    for name in paths:
        if not name:
            continue
        path = (root / name).resolve()
        assert path.is_relative_to(root)
        info = archive.gettarinfo(str(path), arcname=name)
        content = path.read_bytes()
        # A Linux git checkout uses LF for source text, unlike this Windows checkout.
        if b"\0" not in content:
            content = content.replace(b"\r\n", b"\n")
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
print(target)
