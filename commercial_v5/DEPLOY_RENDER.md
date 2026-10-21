# Implantação no Render — Fácil Pedido Comercial V5 revisado

## Estrutura

O mesmo Web Service serve:
- `/`: interface amarela do Comercial;
- `/site-demo.html`: vitrine de publicação (demonstração, não uma loja final);
- `/api/v1`: Gateway FastAPI;
- `/api/v1/health/live`: liveness, não depende do ERP;
- `/api/v1/health`: verifica comunicação com ERP.

## Passos

1. **Faça backup** do ERP e do Neon atuais. Suba antes em um banco de homologação novo, não diretamente no banco de produção.
2. Envie a pasta deste projeto para um repositório **privado** do GitHub, sem os arquivos `.env.real` ou `.db`. `render.yaml` está na raiz.
3. No painel Render, use **New → Blueprint**, selecione o repositório e revise `render.yaml`. Escolha/aceite o plano de Web Service (pode ter custo).
4. Nas variáveis privadas, preencha:
   - `ERP_API_BASE`: URL HTTPS terminada em `/api/v1` do ERP principal.
   - `ERP_SERVICE_EMAIL`: usuário técnico dedicado no ERP.
   - `ERP_SERVICE_PASSWORD`: senha forte da conta técnica.
   - `CATALOG_DATABASE_URL`: PostgreSQL via Neon/Render, `postgresql+psycopg://...` com SSL. Prefira banco/schema de homologação isolado.
   - `CORS_ORIGINS`: domínio HTTPS final do Comercial, como `https://facil-pedido-comercial.onrender.com`. **Não use `*`**.
5. O `startCommand` roda a migração Alembic do catálogo e sobe Uvicorn. Confira logs e o resultado de `/api/v1/health`. Migração usa versão `alembic_version_commercial` e **não deve editar tabelas operacionais do ERP**.
6. Acesse a URL inicial do Web Service. A demonstração local não é exibida no endereço público; entre com conta legítima do ERP, não as contas fictícias do ZIP.
7. Teste o perfil RH na gestão de catálogo e `site-demo.html`; teste se um vendedor consegue ver produto, cliente e estoque no ambiente homologado.
8. **Não habilite** `ENABLE_SALES_WRITES` ou `ENABLE_AUTOMATED_ORDER_CONFIRMATION` até implementar e testar validação de preços, aprovação, idempotência e conciliação no ERP.

### Segurança e operação

- `ENVIRONMENT=production`; `AUTO_CREATE_TABLES=false`. O serviço se recusa a iniciar com API HTTP, SQLite, credencial de demonstração ou CORS aberto.
- Nenhuma chave ou senha real deve ficar em arquivos versionados ou dentro de HTML.
- O segredo do ERP é guardado **exclusivamente** no ambiente do serviço.
- Considere proxy de proteção DDoS/rate-limit e monitoramento de logs/alertas 5xx; upload foi limitado, mas não há WAF na aplicação.
- Fazer backup recorrente do banco do catálogo, testar restauração e controlar custos das imagens armazenadas em binário.
- Em produção a área pública de catálogo busca dados atuais no ERP; quando ele falhar, retorna 503, não uma lista artificialmente vazia.

## Volta rápida (rollback)

Mantenha o commit anterior no GitHub. Para reverter, volte o serviço ao último deploy estável no Render. **Não execute `alembic downgrade` em produção com dados reais** sem backup e validação, porque destrói as tabelas do catálogo. No primeiro uso, teste migração em banco novo.
