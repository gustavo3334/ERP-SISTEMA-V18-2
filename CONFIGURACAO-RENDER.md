# Fácil Pedido unificado — implantação sem contratar serviço extra

**Objetivo:** ERP V18.2 em `https://erp-sistema-v18-2.onrender.com/` e
Comercial V5 em `https://erp-sistema-v18-2.onrender.com/comercial/`, com **um único
Web Service Free** e os **dois bancos PostgreSQL existentes** (ERP / Comercial).

O projeto **não faz merge dos bancos**, não copia dados e não apaga registros.
A integração Comercial → ERP passa a usar loopback `127.0.0.1:$PORT`, evitando
a rota pública `onrender.com` para as consultas internas.

## 1. Preparar cópia do projeto

Baixe o ZIP deste kit, extraia e abra o PowerShell dentro da pasta. Execute:

```powershell
.\preparar-unificado.ps1
```

O script clona o ERP público existente em `Downloads\facil-pedido-erp-unificado`,
adiciona o Comercial e verifica a estrutura. **Não sobrescreve o ERP atual**.
Se já tiver esta pasta, o script interrompe para evitar perda de alterações.

## 2. Antes da migração: conferências e backup

- Guarde os comandos Build e Start atualmente configurados no Render do ERP.
- Faça backup lógico ou snapshot do banco ERP (Supabase/Postgres) e do banco
  Comercial no Neon (backup conforme plano). NÃO cole URLs privadas no GitHub.
- Teste `/api/v1/health` no ERP e `/api/v1/health` no Comercial existente.
- Confirme que a conta técnica de integração tem acesso restrito; não compartilhe
  essa conta com funcionários.
- Não desligue nenhum serviço até validar o Comercial no endereço novo.

## 3. Revisar variáveis no Web Service ERP-SISTEMA-V18-2

MANTENHA os valores atuais do ERP, em particular `DATABASE_URL`, `SECRET_KEY`,
`AUTH_DISABLED`, as configurações de banco, e o eventual `AUTO_CREATE_TABLES`.
O Comercial usa OUTRO banco `CATALOG_DATABASE_URL` e migrará apenas esse banco.

Copie do serviço Comercial existente (Render > Environment) para o serviço do ERP,
pelo painel Render, SEM publicar credenciais em conversa, código ou print:

| Variável no ERP unificado | Valor |
|--|--|
| `COMBINED_DEPLOYMENT` | `true` |
| `ERP_API_BASE` | `https://erp-sistema-v18-2.onrender.com/api/v1` (mantida para validação) |
| `ERP_INTERNAL_API_BASE` | DESCONFIGURE / não defina |
| `CATALOG_DATABASE_URL` | Mesma connection string Neon do Comercial (segredo!) |
| `ERP_SERVICE_EMAIL` | E-mail técnico do ERP (segredo operacional) |
| `ERP_SERVICE_PASSWORD` | Senha atual da conta técnica (segredo!) |
| `CORS_ORIGINS` | Incluir `https://erp-sistema-v18-2.onrender.com` e quaisquer origens legítimas já usadas; separar por vírgula |
| `ENVIRONMENT` | `production` |
| `ENABLE_SALES_WRITES` | `false`, até testes de negócio |
| `ENABLE_AUTOMATED_ORDER_CONFIRMATION` | `false`, até testes de negócio |
| `PORT` | **NÃO fixe**: definido automaticamente pelo Render |

Atenção: `CORS_ORIGINS` é usado pelos dois apps; não perca domínios que o ERP
já tinha configurados. Os dados do usuário no Chrome não são migrados;
favoritos e rascunhos apenas locais podem precisar de exportação manual.

## 4. Build e Start do ERP unificado

Preserve o mesmo serviço ERP `ERP-SISTEMA-V18-2` e a URL atual.

Build Command:
```bash
pip install -r requirements.txt -r commercial_v5/requirements.txt
```
Start Command:
```bash
cd commercial_v5 && alembic -c alembic_gateway.ini upgrade head && cd .. && uvicorn combined_app:app --host 0.0.0.0 --port $PORT --proxy-headers
```

**Observação de segurança:** coloque essas configurações no Render apenas
depois de ter enviado e revisado o projeto unificado ao GitHub. Recomenda-se
criar a branch `unificado` no repositório do ERP, testá-la e então mudar o
Render para essa branch; isso permite retornar à branch `master` rapidamente.
Empurrar para `master` enquanto auto-deploy estiver ativo pode reiniciar o
ERP de produção sem a configuração completa.

## 5. Publicação controlada (na pasta gerada do ERP)

```powershell
cd "$HOME\Downloads\facil-pedido-erp-unificado"
git switch -c unificado
git add combined_app.py commercial_v5 testar_arquitetura.py CONFIGURACAO-RENDER.md
git commit -m "feat: ERP 18.2 e Comercial V5 em um servico"
git push -u origin unificado
```

Alterar `Branch` do serviço ERP no Render para `unificado` SOMENTE depois
que as variáveis e comandos novos estiverem corretos. Se o painel permitir,
desative Auto-Deploy temporariamente até concluir todas as configurações.

## 6. Validar pós-publicação

1. ERP `https://erp-sistema-v18-2.onrender.com/` deve abrir normalmente.
2. ERP health `/api/v1/health` deve reportar banco `connected`.
3. Comercial `https://erp-sistema-v18-2.onrender.com/comercial/` abre login.
4. Comercial `/comercial/api/v1/health` deve mostrar `erp: connected`,
   `catalog_database: connected`, `erp_transport: loopback` (se a chave estiver
   exposta no health). Login de funcionário deve funcionar sem 429.
5. Testar consulta de produtos, criação/consulta de catálogo, upload e leitura
   de foto e permissões, sem lançar pedidos reais.
6. Verificar logs do Render em caso de erros 4xx/5xx. Documentar 429 residual,
   latência e consumo de RAM (serviço Free: 512MB), pois consolidar aumenta
   a carga de memória e pode exigir otimização adicional.
7. Só então compartilhar o NOVO link do Comercial com o RH. O link antigo
   do serviço comercial não terá redirecionamento automático se ele for desligado.
8. Após validação, suspender/deletar o serviço `facil-pedido-comercial`
   antigo, sem excluir o Neon. Faça isso em etapa separada e consciente.

## Reversão se houver problema

Volte a branch Render do ERP para `master`, restaure Build e Start antigos e
as variáveis de ambiente anteriores **sem alterar DATABASE_URL/SECRET_KEY**.
Não exclua bancos, não use `DROP TABLE` nem recrie o Neon. O Comercial antigo
pode continuar disponível temporariamente com sua configuração original.

## Limites da abordagem

- Um único serviço Free pode sofrer sono após inatividade, memória (512MB)
  e limites de requisições externas. A comunicação ERP↔Comercial por loopback
  evita o limite de dois serviços distintos, mas não garante que nunca haverá
  429 quando o usuário acessa publicamente o Render.
- O Comercial usa as contas individuais criadas no ERP, não a conta técnica
  compartilhada como login humano.
- Mudança de URL do Comercial é necessária ao desligar o serviço antigo.
- Não existe sincronização automática de favoritos/rascunhos guardados no
  localStorage entre domínios diferentes.
