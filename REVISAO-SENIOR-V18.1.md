# Revisão Sênior — Fácil Pedido ERP V18.1

Data da revisão: 17/09/2026  
Versão: **18.1.0-senior-audit**

## Resultado executivo

O projeto foi revisado com foco em **persistência, integridade dos cadastros, CRUD, autenticação, sincronização front/back, JavaScript, Vercel e regressões introduzidas por camadas legadas do front-end**.

Os fluxos centrais estão em condição de deploy **desde que a Vercel esteja ligada a um PostgreSQL persistente e as variáveis de produção estejam configuradas corretamente**. A persistência do snapshot completo foi testada salvando dados, encerrando completamente o processo FastAPI, iniciando um novo processo com o mesmo banco e relendo os dados. O registro permaneceu armazenado.

Não é correto afirmar que cada recurso avançado do sistema possui integração externa completa. Recursos que dependem de serviços de terceiros — por exemplo, recuperação de senha por e-mail, conciliação bancária automática e algumas ações avançadas do Marketplace — continuam dependentes de integrações específicas. Os botões principais deixaram de simular sucesso quando a integração não existe.

## Problemas críticos encontrados e corrigidos

1. **Campos enriquecidos de produtos e fornecedores podiam desaparecer após recarregar.** O snapshot universal era restaurado, mas uma leitura relacional mais enxuta podia sobrescrever os objetos completos. A hidratação agora faz merge e preserva os campos adicionais.
2. **Cadastros ainda não sincronizados podiam sumir se o endpoint relacional retornasse uma lista vazia.** Produtos e fornecedores locais pendentes de sincronização agora são preservados.
3. **Engenharia tinha uma implementação real no backend sendo sobrescrita por um bloco legado local.** Categorias, locais, variações, componentes e roteiros voltaram a utilizar o CRUD real do backend.
4. **IDs locais de fornecedores podiam ser enviados como chaves estrangeiras ao PostgreSQL.** O front agora resolve `_serverId` para produtos, variações e componentes.
5. **Excluir produto, fornecedor ou cliente podia remover apenas da tela e o registro reaparecer no reload.** Exclusões críticas agora aguardam confirmação do backend antes de remover da interface.
6. **Edição de compras detalhadas era apenas em memória.** Fornecedor, previsão, observação, frete e status passam por `PUT /api/v1/purchase-orders/{id}`.
7. **Tabela de compras filtrada podia alterar a linha errada.** O índice de origem é preservado mesmo após filtros.
8. **Orçamentos/pedidos eram gravados no backend, mas as tabelas não eram reidratadas corretamente.** Foi adicionada hidratação comercial real.
9. **O dashboard podia ser zerado novamente por uma rotina antiga depois de receber dados reais.** A limpeza de demonstração não sobrescreve mais dados carregados do backend.
10. **O snapshot universal não incluía todos os estados que tentava restaurar.** RH, produção por peça, auditoria sensível, compras detalhadas e workflow auxiliar passaram a ser coletados e restaurados.
11. **A tela de compras trazia registros fictícios hardcoded.** Os exemplos foram removidos; a lista é alimentada por dados reais.
12. **Alguns modais usavam um ID DOM inexistente (`modal`).** Corrigido para `modalOverlay`.
13. **Criação de orçamento não exigia explicitamente `sales.write`.** A permissão foi adicionada.
14. **O cache do service worker ainda apontava para a V17.5.** Atualizado para V18.1 para reduzir risco de asset antigo após redeploy.
15. **Botões principais que apenas exibiam uma mensagem falsa foram revisados.** Exportação de compras gera CSV; atalhos de calendário/campanha navegam para áreas reais; recuperação de senha e conciliação deixam claro quando a integração externa não está configurada.

## Evidências de validação

- **54 testes automatizados aprovados** (`python -m pytest -q`).
- `python -m compileall -q app api`: aprovado.
- Todos os arquivos JavaScript externos de `frontend/` e `public/`: sintaxe aprovada.
- **20 scripts inline** do HTML em cada build: sintaxe aprovada.
- `frontend/` e `public/`: arquivos críticos validados como equivalentes pelos testes.
- HTML: nenhum ID duplicado detectado.
- Auditoria de eventos: **530 ocorrências de handlers**, **186 chamadas de função distintas** e **0 referências de função não resolvidas**.
- Assets principais (`/`, JS, manifest, service worker e `/api/v1/health`): HTTP 200 em servidor local FastAPI.
- Autenticação real: login JWT testado com `AUTH_DISABLED=false`.
- Persistência após reinício real do servidor: **APROVADA**. O processo FastAPI foi encerrado e iniciado novamente usando o mesmo banco; produto enriquecido, RH e sentinela de teste continuaram presentes.
- Fluxo relacional fornecedor → categoria → local → produto → variação → leitura → exclusão: aprovado.
- Compra: criação, atualização, leitura e persistência de frete/observação/status: aprovada.
- Testes existentes de estoque, produção, vendas, RH, permissões, arquivos, clientes, front-state e Vercel continuam aprovados.

## O que “salvo” significa nesta versão

Com `DATABASE_URL` apontando para PostgreSQL e o usuário autenticado, o front utiliza o backend como camada principal de persistência. O navegador mantém uma cópia local de contingência, mas **o banco é a fonte persistente do sistema**.

O fluxo esperado é:

`alterar → salvar localmente → sincronizar PostgreSQL → fechar navegador → abrir novamente → autenticar → carregar estado do servidor`.

Há controle de revisão no `front-state`, evitando que uma aba/computador antigo sobrescreva silenciosamente uma versão mais nova.

## Pontos que ainda não são integrações externas completas

- **Recuperação de senha por e-mail:** não há provedor SMTP/transacional configurado. O botão não finge mais que enviou e-mail.
- **Conciliação bancária automática:** exige Open Finance/API bancária ou outro provedor; o sistema não marca conciliações automaticamente sem integração.
- **Marketplace avançado:** parte da interface continua sendo uma camada demonstrativa/local. Para operação real multicanal (Mercado Livre/Amazon/Shopee, repasses, chargebacks etc.) é necessário backend/conectores específicos.
- **Mapa/roteirização:** depende de rede e do provedor configurado (OSM/OSRM ou Google Maps).

Esses pontos não impedem o núcleo ERP de funcionar, mas não devem ser vendidos como integrações reais antes de serem implementados.

## Riscos arquiteturais a acompanhar

1. O snapshot `front-state/sistema-completo` é uma camada abrangente de compatibilidade do front. Para um ERP multiempresa/multitenant, deve evoluir para escopo por empresa/tenant e permissões mais granulares.
2. `AUTO_CREATE_TABLES=true` é útil para o primeiro banco, mas alterações futuras de schema devem ser promovidas por **Alembic** em vez de depender apenas de `create_all`.
3. Fotos/objetos muito grandes não devem ser colocados no snapshot universal. Arquivos devem continuar sendo persistidos pelo backend/armazenamento apropriado.
4. O pacote passou por testes automatizados e auditoria estática de handlers, mas **não foi possível executar um robô de navegador Chromium neste ambiente** porque o binário não estava disponível e a instalação externa falhou por rede. Portanto, após o deploy ainda é recomendada uma homologação visual curta em Chrome/Edge real.

## Checklist antes do deploy Vercel

Configure no projeto da Vercel:

```env
ENVIRONMENT=production
AUTH_DISABLED=false
DATABASE_URL=postgresql://...
SECRET_KEY=<chave aleatória com 32+ caracteres>
AUTO_CREATE_TABLES=true
SEED_ADMIN=true
ADMIN_EMAIL=<seu e-mail>
ADMIN_PASSWORD=<senha forte>
ADMIN_NAME=Administrador
```

Após o primeiro login confirmado, `SEED_ADMIN` pode ser alterado para `false`.

Depois do deploy:

1. Abra `/api/v1/health` e confirme HTTP 200.
2. Faça login real.
3. Cadastre um fornecedor e um produto com campos adicionais.
4. Atualize a página e confirme que continuam.
5. Feche totalmente o navegador, abra novamente, faça login e confirme novamente.
6. Edite o produto, feche/abra e valide os novos valores.
7. Crie uma compra, altere fornecedor/previsão/frete e recarregue.
8. Crie categoria/local/variação em Engenharia e recarregue.
9. Exclua um registro de teste e confirme que ele não reaparece.
10. Só então use dados reais de produção.

## Conclusão

A V18.1 corrige os principais mecanismos que podiam causar **“salvei e sumiu”**, **“excluí e voltou”**, perda de campos enriquecidos e salvamento apenas aparente em Engenharia. O núcleo está significativamente mais consistente para deploy com PostgreSQL persistente.
