# Integração ERP principal ↔ Fácil Pedido Comercial V5

## Componentes

ERP principal existente (fonte dos dados) → Gateway `/api/v1` → Comercial amarelo / RH / Catálogo público.

O Gateway não substitui o ERP existente. Produtos, clientes, estoque, produção e financeiro continuam no ERP. O catálogo de fotos/publicação e os pedidos comerciais ficam em tabelas próprias do Gateway: `commercial_catalog_state`, `commercial_product_media`, `commercial_sales_orders`.

## Teste com ERP real (primeiro em ambiente de homologação)

1. Faça backup do banco Neon/PostgreSQL e configure uma instância de homologação sempre que possível.
2. Copie `.env.real.example` para `.env.real`.
3. Preencha `ERP_API_BASE` com a URL do ERP até `/api/v1` (sem barra final).
4. Crie uma conta técnica exclusiva com acesso estritamente necessário a produtos, orçamento, estoque, produção, entrega e financeiro. Preencha `ERP_SERVICE_EMAIL` e `ERP_SERVICE_PASSWORD` localmente.
5. Configure `CATALOG_DATABASE_URL` para um PostgreSQL seguro. Para compartilhar o mesmo banco físico, use o mesmo banco Neon do ERP; as tabelas comerciais usam prefixo `commercial_`. Outra opção é um banco separado para o gateway, mantendo **ERP como fonte de verdade** via API.
6. Execute `INICIAR_COM_ERP_REAL.bat`. O Gateway local abre em `http://127.0.0.1:8010/api/v1`.
7. Abra `http://127.0.0.1:8010/`, informe a API `http://127.0.0.1:8010/api/v1`, entre com uma conta do ERP real e verifique produtos e dados. Teste primeiro sem afetar pedidos da empresa.
8. No RH, envie uma foto, escolha a capa, publique e confira em `http://127.0.0.1:8010/site-demo.html`.

**Não coloque secrets no HTML nem no Git.** O navegador usa apenas o token do usuário; a conexão PostgreSQL e as credenciais da conta técnica ficam no servidor FastAPI.

## Uso por vários funcionários

Para múltiplos computadores, publique o Gateway em um serviço de hospedagem persistente e configure `CORS_ORIGINS` com os domínios HTTPS reais. Defina `ENVIRONMENT=production` para ativar a validação de configuração. Hospede também o frontend (ou abra o arquivo no navegador apontando para a URL pública segura do Gateway). Não use o host local `127.0.0.1` nos demais computadores. Configure SSL e backups/rotina de recuperação.

## Endpoints principais do Gateway

| Método | Endpoint | Uso |
|---|---|---|
| POST | `/api/v1/auth/login` | Autenticação delegada ao ERP |
| GET | `/api/v1/catalog-management/products` | Produtos, variações, categorias e estoque do ERP |
| GET/PUT | `/api/v1/catalog-management/state` | Fotos e informações de apresentação |
| POST | `/api/v1/media` | Foto gravada no banco do Gateway |
| GET | `/api/v1/media/{id}` | Foto exibida no site |
| POST | `/api/v1/catalog-management/products/{id}/publication` | Publicar ou ocultar |
| GET | `/api/v1/public/catalog` | Produtos publicados no site |
| GET/POST | `/api/v1/sales-orders` | Pedidos comerciais |
| POST | `/api/v1/sales-orders/{id}/confirm` | Confirmação e sincronizações de estoque/PCP/financeiro |
| GET | `/api/v1/integration/snapshot` | Resumo integrado, somente gestor |

## Limites e observações

- A confirmação de pedido pode depender de serviços ERP disponíveis e autorizados. Falhas são registradas e devem ser conciliadas antes da expedição.
- O pedido Comercial é espelhado no ERP como **orçamento**, não como `SalesOrder` nativo (o ERP de referência expõe a API de orçamentos). Esta diferença deve ser considerada para relatórios corporativos.
- Os testes automatizados usam um ERP fictício; validação com dados reais exige homologação e participação de quem administra o ERP.
- Em modo de demonstração, fotos são guardadas apenas no navegador e podem atingir a cota de armazenamento. Em modo integrado, fotos passam pelo servidor.
- O projeto preserva a interface antiga; não é uma migração automática dos dados locais antigos.

## Revisão de produção 19/10/2026

O deploy no Render foi incluído nesta edição; veja `DEPLOY_RENDER.md` e `AUDITORIA_TECNICA.md`.

**Vendas e confirmação** ficam bloqueadas por padrão no Render (`ENABLE_SALES_WRITES=false` e `ENABLE_AUTOMATED_ORDER_CONFIRMATION=false`) até aprovar controles de preços, permissões e idempotência no ERP real. A conta `hr` do ERP também pode manter permissões de folha de pagamento no ERP principal: use um papel independente de **editor de catálogo** no ERP, caso o RH deva acessar somente fotos.

O Gateway armazena as mídias no banco do catálogo; para grandes volumes, migre para object storage/CDN e configure URLs temporárias para rascunhos.
