# Fácil Pedido Comercial V5 — Correção de HTTP 429 (20/10/2026)

## Sintoma
No Render, `POST /api/v1/auth/login` e `GET /api/v1/{products,categories,inventory/balances...}` retornavam **429 Too Many Requests** de forma recorrente. O ERP V18.2 aceitava login diretamente. Isso aponta para bloqueio em chamadas efetuadas pelo Comercial, mas não identifica por si só qual camada de infraestrutura aplica o limite.

## Mudanças

### `gateway/main.py`
- Reduz o número de verificações repetidas de `/auth/me`: memória por requisição, cache **somente para GET** com TTL de 12s. POST/PUT/PATCH/DELETE validam o usuário novamente no ERP.
- Limita concorrência de chamadas externas ao ERP a duas por processo de gateway (`ERP_MAX_PARALLEL_CALLS`, padrão 2).
- Interpreta `Retry-After` em segundos ou formato de data e estabelece uma espera compartilhada após HTTP 429.
- Reenvia **somente GET idempotente**, no máximo **uma vez**, se o tempo indicado for curto (até 3s por padrão). Em outros casos, retorna 429 com cabeçalho `Retry-After`. **NUNCA** repete login, vendas, pagamentos ou alterações automaticamente.
- Evita múltiplos logins simultâneos da conta técnica quando um token de serviço precisa ser renovado.
- Mantém metadados de Retry-After nas respostas importantes do gateway; registra método/caminho e tempo de espera sem registrar senha ou token.
- Executa a chamada de login síncrona em thread separada para não bloquear o loop do FastAPI.

### `comercial/index.html`
- No máximo duas leituras GET simultâneas por navegador.
- Agrupa requisições GET idênticas que estejam em andamento.
- Desabilita o botão durante a tentativa de login, evitando duplo clique.
- Mostra erro HTTP 429 explicativo e o tempo de espera, quando informado.
- Não altera a identidade visual amarela, a logo nem a imagem do sofá.

## Arquivos a atualizar no GitHub
Somente:

- `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/gateway/main.py`
- `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/comercial/index.html`

**Não** mudar `.env`, senhas, variável `CATALOG_DATABASE_URL`, banco Neon ou código do ERP V18.2.

## Como publicar
1. Substitua os dois arquivos, mantendo os caminhos acima.
2. No repositório `facil-pedido-comercial` (branch `master`), execute:
   ```powershell
   git add FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/gateway/main.py FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/comercial/index.html
   git commit -m "fix: controlar chamadas e rate limit HTTP 429 no comercial"
   git push origin master
   ```
3. No Render, abra **facil-pedido-comercial > Manual Deploy > Deploy latest commit** (se o deploy automático estiver desligado).
4. Aguarde `Live`; abra `https://facil-pedido-comercial.onrender.com` e recarregue sem cache (`Ctrl+Shift+R`).
5. Teste uma conta pessoal e outra do RH, **cada uma com seu próprio login**, evitando usar a conta técnica de integração na interface.
6. Confira Logs do **Comercial** e do **ERP** para eventuais novos 429. Caso persistam, consulte Response Headers e limitações de tráfego/Edge em Render; estas correções diminuem o consumo, mas não podem eliminar uma restrição externa da plataforma.

## Testes locais efetuados
- `pytest -q tests/test_inventory_compatibility.py tests/test_rate429.py` — 8 testes aprovados.
- `python tests/test_e2e_local.py` — integração ponta a ponta aprovada usando **ERP fictício** local.
- `node --check` nos scripts inline do frontend — sintaxe aprovada.

## Limites e segurança
- Não foram feitas mudanças no Render nem no GitHub remoto nesta entrega.
- A homologação contra o ERP de produção e a confirmação da ausência de 429 **continuam pendentes**, pois dependem do deploy e da observação do serviço online.
- `ENABLE_SALES_WRITES=false` e `ENABLE_AUTOMATED_ORDER_CONFIRMATION=false` devem permanecer desativadas enquanto operações comerciais não forem homologadas.
- A conta de integração precisa voltar ao princípio do menor privilégio antes de uso definitivo pela empresa.
