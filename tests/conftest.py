from __future__ import annotations

import os
import shutil
from pathlib import Path

TEST_DB = Path("data/test_facil_pedido.db")
TEST_UPLOADS = Path("data/test_uploads")
TEST_BACKUPS = Path("data/test_backups")

TEST_DB.unlink(missing_ok=True)
shutil.rmtree(TEST_UPLOADS, ignore_errors=True)
shutil.rmtree(TEST_BACKUPS, ignore_errors=True)

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_facil_pedido.db")
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
os.environ.setdefault("UPLOAD_DIR", "./data/test_uploads")
os.environ.setdefault("BACKUP_DIR", "./data/test_backups")
