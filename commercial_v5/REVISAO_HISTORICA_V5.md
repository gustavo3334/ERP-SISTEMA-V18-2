# Revisão / testes V5 Comercial Amarelo

Executados em 19/10/2026 neste ambiente:

**Verificações estáticas:**
- Sintaxe Python do Gateway validada com `py_compile`.
- Scripts inline do HTML validados com `node --check`.
- Mantidos cabeçalho amarelo, logo Fácil Pedido e foto do sofá, sem as duas etiquetas sobre a foto.

**Teste automatizado de integração local** (`tests/test_e2e_local.py`, ERP fictício e bancos temporários):
- Autenticação admin, RH e vendas.
- RH recebe produtos sem campo de custo e é impedido de alterar cadastro técnico e estoque.
- RH é impedido de ver snapshot administrativo e lista de vendas.
- Admin cadastra produto; cria variação; RH consegue consultar apenas os campos comerciais.
- RH envia imagem para API; imagem é recuperada; catálogo salva; produto é publicado no endpoint público.
- Proteção contra gravação concorrente de versão desatualizada do catálogo.
- RH não consegue modificar dados financeiros e configurações pelo payload compartilhado.
- Vendedor cadastra cliente e pedido; pedido é confirmado via Gateway/ERP de teste; snapshot gestor retorna os dados.

**Verificação da interface em navegador Chromium automatizado (HTML carregado localmente para teste, sem tráfego de produção):**
- Login demonstrativo e tela amarela renderizados sem erros de JavaScript.
- Cadastro demonstrativo de sofá com SKU, preço e variação.
- Studio abre com produto cadastrado, prévia e controles visíveis.

**Ainda não validado:**
- Banco Neon e ERP de produção: exigem URL e credenciais válidas.
- Testes completos de múltiplos usuários simultâneos e recuperação de falhas parciais de integração no ambiente real.
- Expedição e pagamentos reais. Confirmar disponibilidade dos endpoints do ERP implantado antes de liberar operação comercial.
