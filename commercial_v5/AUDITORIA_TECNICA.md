# Auditoria técnica — Fácil Pedido Comercial amarelo — 19/10/2026

## Escopo auditado

**Origem:** `facil-pedido-comercial-v5-amarelo-admin.zip` (atualização sobre Comercial 4.0 amarelo). Revisão do `comercial/index.html`, `gateway/main.py`, `site-demo.html`, dependências, configuração do Render, banco e testes. **O repositório do ERP principal não foi alterado**. Seu ambiente de produção, usuários reais e banco Neon não foram acessados.

## Arquitetura encontrada

```text
Navegador (Comercial amarelo, RH) — JWT ERP
           |
           v
       Gateway FastAPI (Render)
           |                     |
           |                     +--> PostgreSQL/Neon (tabelas commercial_*)
           |                          catálogo/publicação, fotos binárias, pedidos comerciais
           v
       API do ERP principal (Render) --> dados operacionais do ERP (produtos, estoque, clientes, orçamentos, produção, financeiro)
           |
           v
       Banco primário do ERP
```

O gateway **não representa um segundo ERP completo**: ele adapta APIs do ERP principal e mantém dados comerciais específicos. Publicar dois frontends em serviços isolados não os conecta automaticamente: os valores de configuração e os papéis precisam ser homologados juntos.

## O que foi corrigido nesta revisão

| Área | Risco da versão anterior | Mudança entregue | Situação |
|---|---|---|---|
| Render | Apenas inicialização Windows, sem blueprint de produção | `render.yaml`, `Dockerfile`, mesmo domínio para Comercial + vitrine + API | Configuração criada; **não publicada** |
| Banco | `create_all` em import sem migrations | Alembic 0001 e tabela independente `alembic_version_commercial`; criação automática desativada em produção | Migração validada em SQLite isolado com tabela de outro sistema coexistindo |
| Imagens | MIME declarado e extensão não demonstravam ser imagem válida | Pillow verifica bytes reais, converte em JPEG, limita pixels e tamanho | Teste de arquivo falso passou |
| Upload | Sem limite consistente na quantidade armazenada | Limite de 12 mídias por produto; requisições limitadas a 12 MB | Testes de limites básicos |
| Permissões | Algumas consultas de preço não exigiam login direto | Verificação obrigatória de usuário; ações do RH continuam limitadas no gateway | Testes de acesso não autorizado |
| Catálogo multiusuário | `base_revision` opcional deixava sobrescrever atualizações | `base_revision` obrigatório, conflito HTTP 409/428 | Testado 409 |
| Pedido | `PUT` permitia marcar como Confirmado sem /confirm | Status de confirmação não pode ser forjado; atualização de confirmado bloqueada | Testado |
| Exclusão | Pedido com vínculo no ERP podia ser excluído somente no gateway | Exclusão com espelho ERP é bloqueada até reconciliação | Testado |
| Identificador de pedido | Sequência calculada com `COUNT()+1` podia colidir com dois vendedores | Código com sufixo UUID aleatório | Código adaptado |
| Integração parcial | Nova confirmação podia duplicar ordens, finanças e reservas | Segunda tentativa bloqueada após estado parcial; confirmar na produção desabilitado por padrão | Risco residual de interrupção durante processamento exige outbox |
| Preço | O frontend pode enviar preço/desconto sem autoridade suficiente do ERP | Criação de pedido e mudanças em orçamento bloqueadas em produção por padrão | Bloqueio temporário, precisa regra de preços para liberar |
| Navegador | JWT persistente e snapshot local contendo dados comerciais reais | JWT em `sessionStorage`; remoção de snapshot e token legado; demonstração indisponível no endereço público | Código revisado |
| HTTP | Headers ausentes, CORS aberto em teste | Headers anti-clickjacking e nosniff; HTTPS e CORS restritos obrigatórios em produção | Teste de configuração inválida passou |
| Disponibilidade | Erro no ERP podia resultar em catálogo aparentemente vazio | Catálogo público responde 503 quando ERP indisponível | Código revisado |
| Mensagens de erro | Exceções internas da conexão com ERP podiam retornar detalhes de rede | Resposta externa genérica e registro de erro interno | Código revisado |

## Bloqueios para habilitar vendas em produção

1. **Homologar o ERP verdadeiro e a base de dados**: ainda não foi fornecido acesso/configuração ao Render/Neon de produção; nenhum teste ponta a ponta real foi feito.
2. **Validar preços e descontos no servidor**: a operação de venda precisa recalcular preços por cliente, promoção, limite de desconto e aprovações usando regras do ERP, não somente valores enviados pelo navegador. Para prevenir vendas com preços adulterados, `ENABLE_SALES_WRITES=false` por padrão em produção.
3. **Idempotência transacional**: reservas de estoque, ordens de produção, lançamentos financeiros e entregas precisam registrar identificadores únicos e reprocessamento seguro (`outbox`, idempotency keys e estado por etapa). Por isso, `ENABLE_AUTOMATED_ORDER_CONFIRMATION=false` por padrão em produção. **Não ative essa chave apenas para remover a mensagem de bloqueio.**
4. **Papel exclusivo de Gestão de Catálogo no ERP principal**: a função existente `hr` do ERP possui outras permissões administrativas de RH. É necessário criar/aplicar um papel técnico de `catalog_editor`, se a funcionária não deve ter acesso aos dados administrativos do RH e da folha pelo ERP original. A máscara do Comercial não substitui RBAC no ERP.
5. **Credenciais e provisionamento real**: URL HTTPS do ERP, conta técnica de privilégios mínimos, connection string do PostgreSQL, CORS de domínio e políticas de backup/recuperação precisam ser configuradas no Render por responsável autorizado.

## Riscos residuais e plano de mitigação

| Prioridade | Risco | Mitigação sugerida |
|---|---|---|
| Alta | Mídias são recuperáveis pelo UUID público antes mesmo da publicação, se o URL for conhecido | Objetos privados com URLs temporárias assinadas para rascunhos; URLs públicas apenas após publicação |
| Alta | Fotos guardadas como bytes dentro do PostgreSQL geram crescimento e custo de backup | Migrar mídias para S3/R2/Supabase Storage com RLS e servir versões otimizadas via CDN |
| Alta | Conta técnica do ERP pode ter privilégio amplo; falhas de operação multi-serviço ainda exigem conciliação | Conta com escopos mínimos; auditoria; outbox e rastreamento de operação |
| Alta | API pública de catálogo consulta ERP a cada acesso | Cache curto, limites por IP no gateway/edge e observabilidade de latência/5xx |
| Média | HTML monolítico ~6,7 MB, com imagens codificadas em base64, dificulta cache e manutenção | Separar JS/CSS, comprimir imagens externas e aplicar bundling com hash de ativos |
| Média | JWT ainda acessível ao JavaScript durante a sessão; CSP restritiva não está disponível sem refatorar scripts inline | Migrar auth para sessão `HttpOnly` same-site ou BFF e eliminar scripts inline antes de aplicar CSP rígida |
| Média | Dependências em faixas de versão e teste dependente de ERP fictício | Fixar lockfile e automatizar pip-audit, linters, CI, tests reais em homologação |
| Média | Teste local não avalia LGPD, retenção de documentos, estornos ou carga com usuários simultâneos | Plano de retenção e backup, pentest externo, carga e homologação de fluxos fiscais |

## Testes realmente executados

- ✅ `python -m py_compile gateway/main.py` / `mock_erp/main.py`.
- ✅ `node` verificou sintaxe dos três scripts embutidos do HTML.
- ✅ `python tests/test_e2e_local.py`: autenticação admin/RH/vendas; mascaramento de custo; RBAC; cadastro de produtos e variação; upload real, publicação e catálogo; orçamento espelho, pedido e confirmação em ERP **fictício**; estoque; bloqueio de alterações do pedido confirmado; validação de imagem falsa; arquivo inexistente; consulta sem token; HTML/health.
- ✅ Alembic inicializou banco limpo, coexistiu com `alembic_version` legado sem alterá-la e `alembic check` não indicou discrepâncias no schema isolado.
- ✅ Configuração insegura de produção foi recusada antes de inicializar serviço.
- ✅ Navegador Chromium abriu interface amarela em demonstração instrumentada (substituição de origin e armazenamento exclusivamente no harness de teste), com logo, sofá e sem erros de JS.
- ⚠️ Não realizados: conexão com Render, autenticação real de funcionários, migrations no banco Neon real, teste de concorrência/carga, scan de vulnerabilidades com credenciais, segurança ofensiva, envio de e-mail/SMS, fluxos fiscais e conciliação financeira real.

## Critério de aprovação final

- [ ] Criar ambiente de homologação com ERP de verdade e banco de teste restaurado de backup seguro.
- [ ] Configurar `ERP_API_BASE`, `ERP_SERVICE_*`, `CATALOG_DATABASE_URL`, `CORS_ORIGINS` em segredos no Render.
- [ ] Validar papéis no ERP principal (RH catálogo sem folha e finanças).
- [ ] Importar produtos e testar upload da capa, múltiplos navegadores e publicação/despublicação.
- [ ] Definir preços por cliente/limites de desconto do lado do servidor e passar testes de aprovação.
- [ ] Concluir idempotência dos efeitos colaterais na confirmação antes de habilitá-los em produção.
- [ ] Executar backup e restauração, teste de carga e observabilidade mínima.
- [ ] Executar homologação e aprovar acesso por funcionário.

**Conclusão:** Esta entrega é uma versão **revisada e publicável para homologação**, com **catálogo/RH preparado** e vendas automaticamente desabilitadas em produção enquanto as regras e a integração real não forem validadas. Não é correto classificá-la como pronta para a operação completa da empresa.
