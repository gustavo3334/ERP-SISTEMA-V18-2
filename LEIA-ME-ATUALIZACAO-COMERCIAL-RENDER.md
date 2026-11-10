# Atualização: Comercial + Fotos & Studio + Performance (unificado)

Este pacote **mantém o ERP V18.2 intacto** na raiz (`combined_app.py`, `app/`, `alembic/`, `requirements.txt`). A interface amarela mais leve e a galeria ficam em `commercial_v5/`.

## O que foi integrado
- Catálogo original: `commercial_v5/pv_catalog_manifest.json` (1.107 registros) + 894 imagens JPG existentes, **preservadas**.
- Galeria opcional: 888 imagens WebP novas (296 páginas x três recortes), índice da tabela e elementos visuais do painel.
- Fotos no banco: API unificada POST `/comercial/api/v1/media`, POST `/comercial/api/v1/media/replace`, DELETE; com persistência no PostgreSQL `CATALOG_DATABASE_URL`.
- Fotos, nomes e descrições editáveis no Studio; preços oficiais continuam geridos pelo ERP principal.
- Front-end inicial compacto; compressão GZip seletiva para JSON/HTML; lazy-loading de imagens.

## O que NÃO acontece ao publicar este código
- Não importa automaticamente 1.107 produtos, nem substitui preços, fotos personalizadas ou estoque de produção.
- Não altera automaticamente o banco, usuários nem pedidos existentes (as migrações versionadas do Render continuam conforme a configuração já vigente).
- Para associar catálogo ao ERP com novos SKUs use `commercial_v5/scripts/importar_porto_velho.py` **primeiro em modo de prévia** (sem `--apply`). Faça backup e homologação antes de qualquer aplicação.

## Publicação segura
1. Faça backup do PostgreSQL do ERP e do catálogo e confirme variáveis existentes sem divulgar senhas.
2. Atualize SOMENTE a branch `unificado` de `gustavo3334/ERP-SISTEMA-V18-2`. Não copie o conteúdo dentro de uma subpasta adicional; respeite a raiz do Git.
3. **Não altere o Start Command** em produção: `cd commercial_v5 && alembic -c alembic_gateway.ini upgrade head && cd .. && uvicorn combined_app:app --host 0.0.0.0 --port $PORT --proxy-headers`. Mantenha também `COMBINED_DEPLOYMENT=true`.
4. Faça commit e push. O Render está com auto deploy desligado; execute `Deploy latest commit` no serviço `ERP-SISTEMA-V18-2`.
5. Confirme `/comercial/`, `/comercial/pv-assets/pv_pagina_005_principal.webp`, `/comercial/pv-assets/cover-005.jpg` e `/comercial/assets/facil-pedido-marca.png`.
6. Faça login com credenciais reais e teste trocar foto, editar descrição e preço, salvar, dar F5 e reiniciar; confira se ficou em **banco persistente**.

## Cuidado com ambiente de testes
O endereço `127.0.0.1` do pacote anterior abria um catálogo fictício. Números de produtos e estoque de teste não são usados no Render. **Jamais** use a senha de teste como credencial de produção.
