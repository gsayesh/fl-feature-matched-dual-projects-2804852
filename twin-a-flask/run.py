"""Start Twin A:  python run.py   ->  http://127.0.0.1:5001

Environment (all optional):
  PORT          port to listen on (default 5001)
  LEDGER_DATA   path of the JSON data file (default data/ledger.json)
  LEDGER_DATA_LABEL  text the Data screen shows for that file (default: the path)
  LEDGER_TODAY  pin today's date, e.g. 2026-11-25 (used by tests and the parity check)
"""

import os

from ledger import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    print("Expense Ledger, Twin A (Python/Flask): http://127.0.0.1:{}".format(port))
    app.run(host="127.0.0.1", port=port, debug=False)
