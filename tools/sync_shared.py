"""Copy the shared, framework-neutral files from spec/ into both twins.

    python3 tools/sync_shared.py          copy
    python3 tools/sync_shared.py --check  only report differences (exit 1 if any)

Each twin keeps its own copy so it stays self-contained (you can zip one
folder and run it on its own). This script is the only place the copies are
made, so they can never drift apart silently.
"""

import filecmp
import shutil
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
SPEC = BUILD / "spec"

# source in spec/  ->  (path in Twin A, path in Twin B)
FILES = {
    "assets/app.css": ("twin-a-flask/static/app.css", "twin-b-express/public/app.css"),
    "assets/favicon.svg": ("twin-a-flask/static/favicon.svg", "twin-b-express/public/favicon.svg"),
    "assets/fonts/geist-latin.woff2": ("twin-a-flask/static/fonts/geist-latin.woff2", "twin-b-express/public/fonts/geist-latin.woff2"),
    "assets/fonts/geist-mono-latin.woff2": ("twin-a-flask/static/fonts/geist-mono-latin.woff2", "twin-b-express/public/fonts/geist-mono-latin.woff2"),
    "assets/fonts/OFL.txt": ("twin-a-flask/static/fonts/OFL.txt", "twin-b-express/public/fonts/OFL.txt"),
    "seed.json": ("twin-a-flask/seed.json", "twin-b-express/seed.json"),
    "scenarios.json": ("twin-a-flask/tests/scenarios.json", "twin-b-express/test/scenarios.json"),
}


def main():
    check = "--check" in sys.argv
    stale = []
    for src, targets in FILES.items():
        source = SPEC / src
        for target in targets:
            dest = BUILD / target
            same = dest.exists() and filecmp.cmp(source, dest, shallow=False)
            if same:
                continue
            stale.append(target)
            if not check:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
    verb = "differ" if check else "updated"
    print("{} file(s) {}{}".format(len(stale), verb, ": " + ", ".join(stale) if stale else ""))
    return 1 if (check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
