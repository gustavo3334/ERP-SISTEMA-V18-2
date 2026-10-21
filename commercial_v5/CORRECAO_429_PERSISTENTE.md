# Correção complementar — HTTP 429 persistente (Comercial V5)

## Causa comprovada no código
A versão anterior mantinha um _cooldown global_ de chamadas ao ERP. Um HTTP 429 numa leitura de estoque ou produto podia impedir tentativas de login subsequentes, mesmo sem ter feito outra solicitação de login ao ERP. Quando o ERP não mandava `Retry-After`, a aplicação sugeria apenas 3 segundos, sem evidência de que isso bastava.

O formulário também refazia o POST de autenticação se o login tivesse funcionado, mas a carga posterior dos dados tivesse falhado. Isso gerava novas requisições desnecessárias e podia piorar o rate limit.

## Mudanças
- Bloqueio de leitura limitado apenas às consultas GET; não impede novas tentativas legítimas de login.
- Autenticação e operações de escrita continuam **sem retry automático**.
- Fallback conservador de 30 segundos quando o ERP responde 429 sem informar `Retry-After`; é uma orientação de espera, **não** um prazo garantido de desbloqueio.
- Cada HTTP 429 respondido pelo gateway inclui cabeçalho `X-FP-429-Origin`:
  - `erp-response`: o gateway realizou uma chamada ao ERP e recebeu 429. A restrição pode ser da aplicação ERP ou da camada de entrada do Render; só o cabeçalho não diferencia essas duas possibilidades.
  - `read-cooldown`: o gateway não chamou novamente o ERP por existir uma pausa temporária para leituras.
- O gateway registra o método, o caminho e a presença do cabeçalho `Retry-After` no log, sem registrar senhas, tokens ou dados de clientes.
- O frontend reutiliza a sessão do mesmo usuário quando o login foi aceito, mas a sincronização dos dados falhou com 429. Não faz um novo POST de login a cada tentativa de sincronização.

## Publicar (somente Comercial; não alterar ERP nem Neon)
1. Atualize os arquivos `gateway/main.py` e `comercial/index.html` na pasta `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER` do repositório `facil-pedido-comercial`.
2. Dentro da cópia local do repositório Git, execute:
   ```powershell
   git add FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/gateway/main.py FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/comercial/index.html
   git commit -m "fix: separar rate limit de login e consultas do ERP"
   git push origin master
   ```
3. No Render, serviço `facil-pedido-comercial`: caso não esteja ativado auto-deploy, **Manual Deploy > Deploy latest commit**. Aguarde `Live`.
4. No navegador, `Ctrl+Shift+R`. Aguarde pelo menos o tempo sugerido no erro **sem fazer cliques repetidos**; tente logar uma vez com uma conta pessoal (não a conta técnica do ERP).
5. Se voltar o HTTP 429, vá aos logs do Comercial e busque `ERP HTTP 429`:
   - Com esse registro, uma chamada externa ao ERP recebeu 429.
   - Sem esse registro, examine se o 429 foi gerado antes do app (camada Render) ou durante um cooldown de leitura.
   - Para ver o cabeçalho de origem, abra DevTools > Network > requisição com status 429 > Response Headers > `X-FP-429-Origin`.

## Bloqueio externo: limites do Render Free
O código ajuda a reduzir erros causados por rajadas e elimina bloqueios internos cruzados, mas **não pode contornar um rate limit imposto pelo Render**. A documentação do Render reconhece que serviços Free têm limites de tráfego de entrada inferiores e podem retornar HTTP 429; veja https://render.com/docs/troubleshooting-deploys e https://render.com/docs/free.

Se o 429 continuar acontecendo em `POST /auth/login` com `X-FP-429-Origin: erp-response` quando o login direto ao ERP funciona, investigue os limites de entrada do serviço do ERP e as diferenças entre chamadas de navegador e chamadas servidor-servidor. Consulte suporte Render com horário, caminho e IDs de requisição (sem segredos). Avalie um teste controlado em plano pago **somente se essa origem estiver confirmada**, não antes.

## Segurança
- Nunca compartilhar `ERP_SERVICE_PASSWORD`, senhas do usuário ou `CATALOG_DATABASE_URL` em prints ou no GitHub.
- Contas de colaboradores precisam ser individuais. A conta técnica é exclusiva do gateway e deve ter privilégios mínimos.
- Não mude `ENABLE_SALES_WRITES=false` nem `ENABLE_AUTOMATED_ORDER_CONFIRMATION=false` para testes de autenticação.
- O resultado em produção precisa ser confirmado após deploy; estes testes ocorreram em ambiente local simulado.
