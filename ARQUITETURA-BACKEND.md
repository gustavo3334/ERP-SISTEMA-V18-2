# Fácil Pedido ERP — Backend completo

## Arquitetura

Front-end → FastAPI → serviços de negócio → SQLAlchemy → SQLite/PostgreSQL.

### Módulos implementados

- autenticação JWT;
- perfis e permissões (RBAC);
- auditoria;
- clientes, fornecedores e produtos;
- categorias e locais de estoque;
- estoque com saldo, reserva e histórico de movimentação;
- compras, recebimento e geração de conta a pagar;
- vendas, reserva, produção automática, expedição e entrega;
- engenharia e fichas técnicas;
- PCP e ordens de produção;
- modos Produzir do zero / Baú blindado / Retirar estoque vazado;
- entrega e cálculo de rotas;
- financeiro;
- RH relacional completo;
- PF e MEI;
- endereços, contatos e emergências;
- ficha de saúde;
- dependentes e pensão alimentícia;
- contas bancárias, portabilidade e PIX;
- bônus, salário e produção por peça;
- documentos e upload de arquivos;
- fechamento administrativo de folha;
- backup;
- snapshot de compatibilidade do front.

## Tabelas principais do RH

`employees`, `employee_addresses`, `employee_contacts`, `employee_health`,
`employee_mei`, `employee_dependents`, `employee_alimony`,
`employee_bank_accounts`, `employee_bonuses`, `employee_transport_plans`,
`employee_transport_legs`, `employee_piece_rates`,
`employee_production_entries`, `employee_payroll_statements`,
`employee_advances`, `employee_document_records`, `stored_files`.

## Estoque

Todo movimento pode gerar registro em `stock_movements`. O saldo por local fica em
`stock_balances`. Compras, vendas e produção usam a mesma camada de estoque.

## Segurança

Durante desenvolvimento, o projeto mantém `AUTH_DISABLED=true` porque o front atual
não possui tela de login definitiva. Antes de produção, altere para `false`, configure
`SECRET_KEY`, crie usuários e perfis e utilize HTTPS.

## Banco

SQLite é adequado para desenvolvimento em um computador. Para vários computadores e
uso real simultâneo, use PostgreSQL.
