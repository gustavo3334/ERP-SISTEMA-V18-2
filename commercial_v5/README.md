# Fácil Pedido Comercial V5 — auditado (visual amarelo)

Versão revisada de **Fácil Pedido Comercial 4.0**, preservando cabeçalho amarelo, logo, banner e foto do sofá. A revisão contempla o frontend, o Gateway FastAPI e configuração de deploy Render.

**LEIA PRIMEIRO:** [AUDITORIA_TECNICA.md](AUDITORIA_TECNICA.md) — problemas corrigidos e riscos restantes. A entrega é para **homologação**, não para liberar vendas reais sem validação.

## Rodar demonstração local no Windows

1. Instale Python 3.11+; extraia todo o ZIP.
2. Execute `INSTALAR.bat`.
3. Execute `INICIAR_TESTE_COMPLETO.bat`.
4. O sistema abrirá em `http://127.0.0.1:8010/`, e a vitrine em `http://127.0.0.1:8010/site-demo.html`.
5. No ERP **fictício e apenas local**, utilize:
   - Admin: `admin@facilpedido.local` / `TroqueEstaSenha123!`
   - RH: `rh@facilpedido.local` / `RHcatalogo123!`
   - Vendas: `vendas@facilpedido.local` / `Vendas123!`
6. O mock tem um produto inicial para teste de fotos. Teste publicar e abrir a vitrine; não reutilize essas credenciais em produção.
7. Para regressão local rode `RODAR_TESTES.bat` ou `python tests/test_e2e_local.py` com dependências instaladas.

## Usar ERP verdadeiro em homologação

Leia `INTEGRACAO.md` e `DEPLOY_RENDER.md`. Copie `.env.real.example` para `.env.real`, preencha localmente e execute `INICIAR_COM_ERP_REAL.bat`. **Não faça isso apontando para a produção sem backup e testes homologados.**

## Executar migração (desenvolvimento isolado)

```bash
pip install -r requirements.txt
# Defina CATALOG_DATABASE_URL para banco NOVO de teste:
AUTO_CREATE_TABLES=false alembic -c alembic_gateway.ini upgrade head
```

No Windows, defina `AUTO_CREATE_TABLES=false` no ambiente antes de executar. No Render isso está automatizado no início do Web Service.

## O que existe na pasta

- `comercial/index.html`: frontend amarelo atualizado, logo e sofá embutidos.
- `gateway/main.py`: API de integração e mídia com autenticação delegada ao ERP.
- `gateway/migrations`: schema versionado (tabelas `commercial_*`).
- `site-demo.html`: vitrine simples de verificação de publicação.
- `mock_erp`: ERP fictício para desenvolvimento, **nunca publicar separadamente**.
- `tests/test_e2e_local.py`: regressão local.
- `render.yaml`, `Dockerfile`, `.env.production.example`: infraestrutura de deploy.
- `AUDITORIA_TECNICA.md`, `DEPLOY_RENDER.md`: diagnóstico e instruções.

**Segurança financeira:** `ENABLE_SALES_WRITES=false` e `ENABLE_AUTOMATED_ORDER_CONFIRMATION=false` por padrão em produção. Esses controles existem porque falta validar as regras de preço e a idempotência de integrações externas com o ERP principal. A interface pode navegar e o RH pode organizar fotos, mas não considere pedidos/financeiro em produção concluídos até a homologação final.
