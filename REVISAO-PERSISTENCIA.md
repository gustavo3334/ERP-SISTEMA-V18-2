# Revisão de persistência — Fácil Pedido ERP

Revisão realizada em 29/07/2026 com foco principal em: **todo cadastro confirmado no sistema continuar disponível após fechar o navegador, reiniciar o serviço ou abrir em outro computador**.

## O que foi reforçado nesta revisão

### 1. Persistência universal no PostgreSQL

O front mantém um snapshot completo do estado operacional em `front_states`, chave `sistema-completo`.

O snapshot cobre, entre outros:

- cadastros empresariais;
- clientes e fornecedores;
- produtos, matérias-primas, pré-fabricados e estoque mantidos pelo front legado;
- engenharia e custos;
- fichas técnicas;
- PCP, produção e entregas;
- vendas e dados operacionais;
- financeiro mantido pelo front;
- marketplace;
- RH;
- valor por peça e apontamentos;
- regras/configurações do front;
- matriz de permissões;
- registros criados em telas genéricas.

O navegador continua mantendo uma cópia local como contingência, mas **quando existe estado no servidor, o PostgreSQL vence o cache local**.

### 2. Proteção contra sobrescrita por navegador antigo

Foi adicionada uma revisão incremental ao estado (`revision`). Cada gravação informa qual revisão foi lida anteriormente.

Se outro computador/aba já tiver gravado uma versão mais nova, uma versão antiga recebe conflito HTTP 409 e não pode apagar silenciosamente os dados atuais.

### 3. Histórico de revisões

Cada gravação do estado completo também gera uma linha em `front_state_revisions`.

Endpoints adicionados:

- `GET /api/v1/front-state/{state_key}/revisions`
- `POST /api/v1/front-state/{state_key}/restore/{revision}`

Isso permite recuperar versões anteriores do snapshot em caso de alteração indevida.

### 4. RH como fonte relacional oficial

O RH continua com sincronização própria em tabelas relacionais e carregamento por:

- `GET /api/v1/employees/front/state`
- `PUT /api/v1/employees/sync/front`

Foram validados os campos solicitados durante o projeto: PF/MEI, CNPJ, documentos pessoais, dois telefones, endereço completo, casa/apartamento/bloco, saúde, contatos de emergência, dependentes, pensão, bancos, PIX, portabilidade, salário, bônus, datas de início/registro, foto/metadados, vale-transporte, valor por peça e apontamentos de produção.

### 5. Anexos de colaboradores

Os anexos agora possuem uma cópia binária persistente dentro do PostgreSQL (`stored_files.content_blob`).

A cópia local ainda pode existir no Windows, mas o download usa o blob do banco caso o arquivo físico não exista mais. Isso evita que um redeploy do serviço apague o único exemplar do documento.

### 6. Endereço padrão da empresa

O endereço padrão permanece configurado como:

`Rodovia João Afonso de Souza Castellano, 1800`

### 7. Cadastro de produto

Categoria e tamanho/medida permanecem opcionais conforme solicitado.

### 8. Dados fictícios

Os valores fictícios apontados pelo cliente nas telas de ficha técnica/custos, vendas/comissões, linha do tempo e DRE permanecem removidos. Os painéis estão preparados para receber dados verdadeiros.

## Observação arquitetural

O RH está conectado de forma relacional ao backend. Diversos outros módulos ainda utilizam componentes legados do front e são persistidos no PostgreSQL pelo snapshot universal. Portanto, os dados permanecem salvos, mas a normalização relacional completa de cada tela deve continuar módulo por módulo.

## Render

Para homologação, o PostgreSQL é a fonte persistente. Arquivos também ficam com cópia no banco nesta versão.

Para uso definitivo da fábrica, não utilizar banco PostgreSQL Free como armazenamento permanente: migrar para uma instância com política de retenção/backup adequada antes de inserir dados oficiais.
