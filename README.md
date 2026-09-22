# Fácil Pedido ERP V18.1 — Senior Audit / Vercel Ready

ERP comercial/industrial com **FastAPI + SQLAlchemy + PostgreSQL**, preparado para rodar localmente e para ser publicado na **Vercel** com banco persistente **Supabase PostgreSQL**.

> O núcleo ERP está integrado ao backend. A interface de Marketplace avançado contém áreas demonstrativas que exigem conectores próprios para operação multicanal real.

## Deploy recomendado

- **Hospedagem:** Vercel
- **Front-end:** arquivos estáticos em `public/`, servidos pela CDN da Vercel
- **Backend:** FastAPI pelo entrypoint `index.py`
- **API:** `/api/v1/*` no mesmo domínio
- **Banco:** PostgreSQL persistente; Supabase Pooler preparado para Vercel/serverless
- **Autenticação:** JWT obrigatória no build público
- **Arquivos de RH:** conteúdo persistido no PostgreSQL, sem depender do filesystem efêmero da Function

O passo a passo completo está em **`VERCEL-DEPLOY.md`**.

## Segurança de produção

Quando executado na Vercel ou com `ENVIRONMENT=production`, o backend recusa inicializar se:

- `AUTH_DISABLED=true`;
- `DATABASE_URL` usar SQLite;
- `SECRET_KEY` for curta/padrão;
- o bootstrap de administrador estiver ativo com credenciais fracas.

Isso evita publicar acidentalmente uma instância insegura ou com banco efêmero.

## Primeiro administrador

No primeiro deploy, configure:

```env
SEED_ADMIN=true
ADMIN_EMAIL=seu-email@dominio.com
ADMIN_PASSWORD=uma-senha-forte-com-12-ou-mais-caracteres
ADMIN_NAME=Administrador
```

O bootstrap é idempotente e adequado a cold starts concorrentes. Depois que confirmar o login, você pode alterar `SEED_ADMIN=false`.

## Banco de dados

Em desenvolvimento local, o projeto ainda aceita SQLite. Em produção/Vercel, PostgreSQL é obrigatório.

Exemplo:

```env
DATABASE_URL=postgresql://USUARIO:SENHA@HOST-POOLER/BANCO?sslmode=require
```

Para um banco novo, `AUTO_CREATE_TABLES=true` cria o schema inicial. O projeto também mantém Alembic para evoluções futuras.

## Módulos do backend

A API cobre, entre outros:

- autenticação, usuários, perfis e permissões;
- dashboard;
- clientes e fornecedores;
- produtos, categorias e variações;
- estoque, reservas, transferências e movimentações;
- compras e recebimentos;
- vendas, orçamentos e expedição;
- ficha técnica, PCP e ordens de produção;
- entregas e rotas;
- financeiro;
- RH, documentos e dados operacionais;
- auditoria e configurações.

## Documentos e uploads na Vercel

O disco de uma Function não deve ser tratado como armazenamento permanente. Nesta versão, documentos enviados pelo módulo de RH são persistidos no banco (`content_blob`). A cópia em `storage/uploads` é usada somente quando o sistema roda localmente.

## Rodar localmente

### Windows

Na primeira vez:

```text
INSTALAR-WINDOWS.bat
```

Depois:

```text
ABRIR-SISTEMA-WINDOWS.bat
```

### Terminal

```bash
python -m venv .venv
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Acesse:

- ERP: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api/v1`
- Swagger: `http://127.0.0.1:8000/docs`

## Testes

Execute:

```bash
pytest -q
```

A versão V18.1 foi validada com **54 testes automatizados aprovados**, checagem de sintaxe do front público e teste de persistência após reinício do backend. Use `python -m pytest -q`.

Consulte **`REVISAO-SENIOR-V18.1.md`** para o relatório completo.

## Estrutura relevante

```text
app/                 FastAPI, banco, regras e routers
public/              build estático servido pela Vercel
frontend/            fonte do front para execução local
api/index.py         entrypoint FastAPI para Functions/Vercel
index.py             entrypoint FastAPI alternativo/local
vercel.json          headers e roteamento do deploy
requirements.txt     dependências de runtime
requirements-dev.txt runtime + testes
.env.production.example
VERCEL-DEPLOY.md
```
