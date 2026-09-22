# Vercel Fix V17

Esta versão adiciona `api/index.py`, o entrypoint esperado pela Vercel para FastAPI em rotas `/api/*`.

Após atualizar o GitHub, configure na Vercel:
- ENVIRONMENT=production
- AUTH_DISABLED=false
- DATABASE_URL=<Neon pooled connection string>
- SECRET_KEY=<32+ caracteres aleatórios>
- AUTO_CREATE_TABLES=true
- SEED_ADMIN=false
- CORS_ORIGINS=https://erpp-delta.vercel.app

Depois faça Redeploy e teste `/api/v1/health`.
