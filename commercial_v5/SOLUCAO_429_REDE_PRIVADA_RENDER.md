# Fácil Pedido Comercial V5 — solucionar 429 persistente no Render

## Diagnóstico

O ERP V18.2 autentica normalmente quando acessado pelo navegador, mas o gateway do Comercial recebe HTTP 429 ao pedir login/dados usando a URL **pública** `https://erp-sistema-v18-2.onrender.com/api/v1`. O gateway já reduziu concorrência, reutilizou sessões e tratou Retry-After; mesmo assim a falha reaparece. Isso indica que a arquitetura HTTP público-para-público merece ser revista; não prova, por si só, qual componente de borda está limitando as requisições.

**Limitação documentada pelo Render:** os serviços web Free podem **enviar**, mas NÃO podem **receber** requisições por rede privada. Para ligar Comercial Free ao ERP via rede privada, **o ERP precisa estar num plano pago compatível** (ex.: Starter). Os dois serviços devem estar na mesma região e workspace. Não faça upgrade sem aprovar previamente o preço no painel.

Fonte: https://render.com/docs/private-network e https://render.com/docs/free

## O que foi implementado no gateway

- Novo parâmetro opcional `ERP_INTERNAL_API_BASE`: permite chamar o ERP via endereço interno Render, sem passar pela URL pública.
- Validação estrita do destino interno: HTTP apenas para hostname interno com hífen e porta 10000, caminho `/api/v1`, sem credenciais na URL.
- Em produção, conexão interna exige execução no Render; não se admite HTTP arbitrário via Internet.
- Não existe fallback automático para a URL pública se o endereço interno falhar (evita expor tokens na URL errada e mascarar erros).
- Diagnóstico `/api/v1/health` inclui `erp_transport: "private"` ou `"public"`, sem revelar URL interna em produção.
- Logs 429 distinguem transporte privado/público e JSON/não-JSON, sem registrar tokens, senhas ou conteúdo sensível.
- Mantidas correções anteriores: nenhum retry automático em login ou operações de escrita, sessões reaproveitadas, limite de concorrência.

## Publicar o patch

1. Extraia o ZIP patch **na raiz do repositório Git já clonado**, preservando a estrutura `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/gateway/main.py`.
2. Faça commit/push de `gateway/main.py` e de `tests/test_private_erp_transport.py`. Não mude o ERP nem as credenciais.
3. Aguarde o deploy do serviço **facil-pedido-comercial** e confira Live. **Sem configurar a conexão interna, a aplicação continua utilizando a URL pública anterior** e o erro pode persistir.

## Configurar rede privada (somente depois de o ERP V18.2 ter plano pago compatível)

1. No Render, abra **ERP-SISTEMA-V18-2** → **Connect** → aba **Internal**.
2. Copie o hostname e porta internos reais. Pode parecer `erp-sistema-v18-2-abc123:10000`; **não invente o identificador**.
3. No Render, abra **facil-pedido-comercial** → **Environment** → Add Environment Variable:
   - KEY: `ERP_INTERNAL_API_BASE`
   - VALUE: `http://SEU-HOST-INTERNO-REAL:10000/api/v1`
4. Salve e faça redeploy do Comercial. Mantenha `ERP_API_BASE=https://erp-sistema-v18-2.onrender.com/api/v1`, usado como referência pública. Não troque `ERP_SERVICE_EMAIL`, `ERP_SERVICE_PASSWORD` ou a conexão Neon.
5. Confira `https://facil-pedido-comercial.onrender.com/api/v1/health`: deve exibir `"erp_transport":"private"`, `"erp":"connected"` e `"catalog_database":"connected"`.
6. Faça um **único login** com conta individual do ERP, não com a conta técnica. Teste catálogo e upload com permissões adequadas.

**Se os serviços estiverem em regiões diferentes** (ex.: um em Ohio e outro em Oregon), a rede privada não funcionará. Corrija a topologia com planejamento de downtime/ambiente antes de mudar região.

## Se você não quiser plano pago

Não configure `ERP_INTERNAL_API_BASE` apontando para um Free ERP — não funcionará. Nesta arquitetura, nenhum aumento de 30/60/120 segundos garante acabar com 429 de borda na URL pública. Opções são manter o sistema em homologação enquanto investiga o rate-limit com o suporte Render, ou redesenhar a integração (evitar o encadeamento de duas APIs públicas, com autenticação segura e autorização por usuário). Essas opções exigem trabalho separado; não afirme que apenas o ZIP elimina o erro no Free.

## Verificações e privacidade

- Rode `python -m pytest -q tests/test_private_erp_transport.py tests/test_rate429.py` e `python tests/test_e2e_local.py`.
- Compartilhe prints de Logs sem credenciais, e evite múltiplas tentativas de login seguidas.
- Acesso RH deve usar conta individual e permissões limitadas; conta `ERP_SERVICE_EMAIL` é técnica.
- Não ative `ENABLE_SALES_WRITES` nem `ENABLE_AUTOMATED_ORDER_CONFIRMATION` para diagnosticar login.
