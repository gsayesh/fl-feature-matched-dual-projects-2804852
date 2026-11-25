"""JSON file storage (FR-17). Mirrors twin-b-express/src/store.js.

File layout (identical in both builds, so both can even share one file):

    {"version": 1, "next_id": 37, "expenses": [{"id", "date", "description",
     "category", "amount", "notes"}, ...]}

The file is read on every request and written atomically (temp file + rename).
"""

import json
import os
import threading
from pathlib import Path


class Store:
    def __init__(self, path, seed_path):
        self.path = Path(path)
        self.seed_path = Path(seed_path)
        self._lock = threading.Lock()  # Flask's dev server is threaded; Node's event loop needs no lock

    # -- low level ---------------------------------------------------------

    def _seed(self):
        return json.loads(self.seed_path.read_text(encoding="utf-8"))

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)  # atomic on POSIX and Windows

    def _read(self):
        if not self.path.exists():
            self._write(self._seed())  # first run: start from the sample data
        return json.loads(self.path.read_text(encoding="utf-8"))

    # -- queries -------------------------------------------------------------

    def expenses(self):
        """All expenses in entry order (ascending id)."""
        with self._lock:
            return list(self._read()["expenses"])

    def get(self, expense_id):
        for row in self.expenses():
            if row["id"] == expense_id:
                return row
        return None

    # -- commands ------------------------------------------------------------

    def add(self, record):
        """Append a validated record and return its new id (ids are never reused)."""
        with self._lock:
            data = self._read()
            new_id = data["next_id"]
            data["expenses"].append(_row(new_id, record))
            data["next_id"] = new_id + 1
            self._write(data)
            return new_id

    def update(self, expense_id, record):
        with self._lock:
            data = self._read()
            for i, row in enumerate(data["expenses"]):
                if row["id"] == expense_id:
                    data["expenses"][i] = _row(expense_id, record)
                    self._write(data)
                    return True
            return False

    def delete(self, expense_id):
        with self._lock:
            data = self._read()
            kept = [row for row in data["expenses"] if row["id"] != expense_id]
            if len(kept) == len(data["expenses"]):
                return False
            data["expenses"] = kept
            self._write(data)
            return True

    def reset(self):
        """FR-16: replace everything with the sample data."""
        with self._lock:
            self._write(self._seed())

    def clear(self):
        """FR-16: delete every expense but keep next_id, so ids are never reused."""
        with self._lock:
            data = self._read()
            data["expenses"] = []
            self._write(data)


def _row(expense_id, record):
    """Fixed key order keeps the file byte-identical between the two builds."""
    return {
        "id": expense_id,
        "date": record["date"],
        "description": record["description"],
        "category": record["category"],
        "amount": record["amount"],
        "notes": record["notes"],
    }
