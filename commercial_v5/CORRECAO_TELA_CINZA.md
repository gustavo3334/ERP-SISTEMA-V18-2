# Correção de tela cinza — Fácil Pedido Comercial V5

## Sintoma observado em produção

O sistema abria com cabeçalho amarelo, mas o conteúdo ficava cinza.
A mensagem exibida era `state.balances.filter is not a function`.

## Origem e ajustes

- O frontend fazia `.filter()` em `state.balances` sem garantir que a API entregasse uma lista.
- O gateway tratava um erro de `/stock/balance` devolvendo um objeto HTTP especial de dentro do `balances` do pacote do catálogo, violando o contrato de lista.
- O gateway passa a devolver uma lista real de saldos em caso de sucesso e também a reconhecer envelopes com `items`, `rows`, `results`, `data` ou `balances`.
- Se o ERP não oferecer a rota de saldo detalhado (404/405/501), o gateway entrega **lista vazia** e o Comercial exibe um aviso; os valores gerais passam a ser calculados a partir do cadastro do ERP, **sem garantia de saldo por depósito**.
- Outros erros de estoque são informados como erros HTTP em vez de entrarem no campo `balances`.
- O frontend normaliza respostas de listas, verifica o tipo antes de `.filter()` e alerta quando a integração de estoque não está completa.
- Vendas e confirmação automática permanecem desativadas em produção até homologação.

## Como atualizar o código no GitHub

Este ZIP contém o projeto completo revisado. Para atualizar a versão publicada com **apenas os arquivos afetados**, substitua no repositório:

1. `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/comercial/index.html`
2. `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/gateway/main.py`
3. Opcionalmente, adicione `FACIL-PEDIDO-COMERCIAL-V5-REVISADO-RENDER/tests/test_inventory_compatibility.py`.

Se estiver usando o site do GitHub, entre na pasta correta e use **Add file → Upload files** para enviar a versão atualizada do arquivo de mesmo nome. Confirme o commit na branch usada pelo Render (`master`).

Depois acesse Render → serviço `facil-pedido-comercial` → **Manual Deploy → Deploy latest commit**. Não altere o serviço ERP V18.2 nem as variáveis do Neon.

## Testes executados nesta revisão

- `python -m pytest -q tests/test_inventory_compatibility.py`: 4 testes passaram.
- `python tests/test_e2e_local.py`: passou (com ERP fictício, incluindo login, RH, fotos, estoque, publicação e pedidos).
- `node --check` no script principal embutido: passou.
- Teste Node do adaptador com respostas paginadas e estoque em formato incorreto: passou.

**Limitação:** o comportamento no ERP V18.2 verdadeiro e no Render precisa ser confirmado após o deploy; não foram realizadas operações em produção. A saúde `connected` da API não garante que cada rota do ERP tenha a mesma estrutura.
