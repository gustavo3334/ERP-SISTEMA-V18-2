from pathlib import Path
import os

root = Path(__file__).resolve().parent.parent
env_path = root / ".env.real"
if not env_path.exists():
    raise SystemExit("Arquivo .env.real não encontrado. Copie .env.real.example para .env.real e preencha os dados do ERP/Neon.")
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    os.environ[key.strip()] = value.strip()

import uvicorn
uvicorn.run("main:app", host="127.0.0.1", port=8010, reload=False)
