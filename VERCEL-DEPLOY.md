# Deploy V18.2 — Vercel + Supabase

Esta edição roda **front-end + FastAPI no mesmo projeto Vercel** e usa **Supabase PostgreSQL** como armazenamento persistente.

## 1. Supabase
Crie um projeto e abra **Connect**. Para Vercel/serverless, o **Transaction Pooler (porta 6543)** é suportado diretamente por esta versão. O **Session Pooler (porta 5432)** também funciona.

Copie a connection string completa e mantenha-a secreta.

## 2. Vercel
Importe o repositório/projeto com:
- Framework Preset: `FastAPI`
- Root Directory: `./`
- Branch de produção: `master`

## 3. Environment Variables — primeiro deploy

```text
DATABASE_URL=<connection string do Supabase>
ENVIRONMENT=production
AUTH_DISABLED=false
AUTO_CREATE_TABLES=true
SEED_ADMIN=false
SECRET_KEY=<32+ caracteres aleatórios>
DATABASE_CONNECT_TIMEOUT_SECONDS=10
```

Gere a chave com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## 4. Teste técnico antes do login

Abra:

```text
/api/v1/health
```

Com banco e configuração corretos, a resposta deve indicar:

```json
{
  "status": "ok",
  "backend": "online",
  "database": "connected",
  "database_provider": "supabase",
  "configuration": "ok"
}
```

Também existe:

```text
/api/v1/ready
```

Esse endpoint retorna sucesso somente quando banco e configuração estão prontos.

## 5. Criar o administrador
Depois que `/health` estiver `ok`, configure:

```text
SEED_ADMIN=true
ADMIN_NAME=Administrador
ADMIN_EMAIL=<seu e-mail>
ADMIN_PASSWORD=<senha forte com 12+ caracteres>
```

Faça novo deploy. Depois que o login funcionar, `SEED_ADMIN` pode voltar para `false`; o usuário já está persistido no PostgreSQL.

## 6. Supabase Transaction Pooler
Quando `DATABASE_URL` aponta para Supabase na porta `6543`, a V18.2 configura automaticamente:
- psycopg 3;
- `prepare_threshold=None`;
- `NullPool` no SQLAlchemy para serverless.

Isso evita prepared statements incompatíveis com PgBouncer Transaction Pooler.

## 7. Segurança
Nunca envie ou versione:
- `DATABASE_URL`;
- `SECRET_KEY`;
- `ADMIN_PASSWORD`.

O `.gitignore` já ignora arquivos `.env` locais.
