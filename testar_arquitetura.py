"""Testes estáticos que não tocam no Neon/Supabase ou ERP publicado."""
from pathlib import Path
import ast
import re
base = Path(__file__).parent
g = (base / 'commercial_v5/gateway/main.py').read_text('utf-8')
f = (base / 'commercial_v5/comercial/index.html').read_text('utf-8')
c = (base / 'combined_app.py').read_text('utf-8')
ast.parse(g); ast.parse(c)
assert 'COMBINED_DEPLOYMENT' in g
assert 'http://127.0.0.1:{COMBINED_PORT}/api/v1' in g
assert 'ERP_CONNECTION_TYPE = "loopback"' in g
assert 'location.origin}/comercial/api/v1' in f
assert c.index('app.mount("/comercial"') < c.index('app.mount("/",')
assert 'erp_app.router.lifespan_context' in c
assert 'commercial_app.router.lifespan_context' in c
print('OK: entrypoint, mounts, banco separado, frontend e rota loopback.')
