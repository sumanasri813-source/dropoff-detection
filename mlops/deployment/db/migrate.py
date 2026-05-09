from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db.connection import get_database_url, init_database


def main() -> None:
    db_url = get_database_url()
    init_database()
    print(f"Database migration complete. Initialized schema at: {db_url}")


if __name__ == "__main__":
    main()
