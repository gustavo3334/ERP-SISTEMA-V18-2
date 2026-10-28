#!/usr/bin/env python3
"""Importação idempotente dos produtos Porto Velho para o ERP unificado.

Padrão: SOMENTE ANÁLISE. --apply grava alterações no ERP e estado do catálogo,
sempre autenticado como administrador. Sem senha no script ou no Git.
"""
from __future__ import annotations
import argparse,copy,datetime,json,os,re,sys,time,unicodedata
from pathlib import Path
from urllib.parse import urljoin
import httpx

ROOT=Path(__file__).resolve().parent.parent
MANIFEST=ROOT/'pv_catalog_manifest.json'
DEFAULT_BASE='https://erp-sistema-v18-2.onrender.com/comercial'
CHECKPOINT=Path.home()/'.facil_pedido_pv_import_checkpoint.json'

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(s or '').upper()) if not unicodedata.combining(c)).strip()

def load_json(p, default):
    try:return json.loads(Path(p).read_text(encoding='utf-8'))
    except FileNotFoundError:return copy.deepcopy(default)

def save_json(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

class API:
    def __init__(self,base,delay=.8):
        self.base=base.rstrip('/')+'/api/v1/'
        self.token='';self.delay=delay;self.last=0
        self.client=httpx.Client(timeout=85,follow_redirects=False,verify=True)
    def req(self,method,path,params=None,data=None,auth=True):
        url=urljoin(self.base,path.lstrip('/'))
        headers={'Accept':'application/json'}
        if auth and self.token:headers['Authorization']='Bearer '+self.token
        for attempt in range(9):
            if self.last:
                delta=time.monotonic()-self.last
                if delta<self.delay:time.sleep(self.delay-delta)
            try:resp=self.client.request(method,url,params=params,json=data,headers=headers)
            except (httpx.ReadTimeout,httpx.ConnectError,httpx.RemoteProtocolError) as exc:
                if method.upper() != 'GET' or attempt==8:
                    raise RuntimeError('Falha de rede na operação '+method+' '+path+'. Verifique se o registro foi criado antes de repetir.') from exc
                time.sleep(min(2**attempt,30));continue
            self.last=time.monotonic()
            if resp.status_code in (429,502,503,504):
                if method.upper() != 'GET':
                    raise RuntimeError(f'{method} {path}: HTTP {resp.status_code}. Escrita não repetida automaticamente. Reexecute após conferir no ERP.')
                ra=resp.headers.get('retry-after','')
                try:delay=min(max(int(ra),2),90)
                except ValueError:delay=min(5*(attempt+1),60)
                if attempt==8:raise RuntimeError(f'{method} {path}: HTTP {resp.status_code} após novas tentativas')
                print(f'  HTTP {resp.status_code} — aguardando {delay}s antes de tentar novamente.',flush=True)
                time.sleep(delay);continue
            if resp.status_code>=400:
                raise RuntimeError(f'{method} {path}: HTTP {resp.status_code} — {resp.text[:450]}')
            if resp.status_code==204:return None
            try:return resp.json()
            except ValueError:raise RuntimeError(f'{method} {path}: resposta não JSON ({resp.status_code})')
        raise RuntimeError('Número máximo de tentativas excedido')
    def login(self,email,password):
        data=self.req('POST','auth/login',data={'email':email,'password':password},auth=False)
        self.token=data.get('access_token') or data.get('token') or ''
        if not self.token:raise RuntimeError('Login respondeu sem token')
        user=data.get('user') or {}
        role=norm(user.get('role'))
        if role not in ('ADMINISTRATOR','ADMIN','MANAGER','GERENTE'):
            raise RuntimeError('Faça login com usuário administrador ou gerente autorizado')
        print('Conectado como '+str(user.get('email') or user.get('full_name') or role),flush=True)
    def list_all(self,collection,limit=500):
        rows=[]
        for offset in range(0,20000,limit):
            result=self.req('GET',collection,params={'limit':limit,'offset':offset})
            chunk=result if isinstance(result,list) else (result.get('items') or result.get('data') or result.get('results') or [])
            if not isinstance(chunk,list):raise RuntimeError('Resposta inesperada em '+collection)
            rows.extend(chunk)
            if len(chunk)<limit:break
        return rows

def main():
    ap=argparse.ArgumentParser(description='Catálogo Porto Velho → ERP + imagens persistentes do Comercial')
    ap.add_argument('--apply',action='store_true',help='executa gravações reais (sem esta opção apenas prévia)')
    ap.add_argument('--base',default=DEFAULT_BASE,help='URL do Comercial unificado (terminando em /comercial)')
    ap.add_argument('--delay',type=float,default=1.0,help='intervalo mínimo entre requisições ao Render, em segundos')
    ap.add_argument('--limit',type=int,default=0,help='limitar número de produtos; 0 = todos')
    ap.add_argument('--include-review',action='store_true',help='incluir itens marcados para revisão')
    ap.add_argument('--update-prices',action='store_true',help='atualizar valores de SKUs já existentes (padrão: preservar)')
    ap.add_argument('--public-prefix',default='',help='URL pública /comercial das imagens, se diferente de --base')
    ap.add_argument('--checkpoint',default=str(CHECKPOINT))
    args=ap.parse_args()
    if not args.base.startswith('https://') and not args.base.startswith('http://127.0.0.1'):
        raise SystemExit('Use HTTPS para o servidor de produção')
    data=load_json(MANIFEST,{})
    records=data.get('records') or []
    if not args.include_review:records=[r for r in records if not r.get('review_needed')]
    if args.limit>0:records=records[:args.limit]
    page_url=(args.public_prefix or args.base).rstrip('/')
    sample=records[0] if records else {}
    print('Arquivo:',MANIFEST.name,'| registros selecionados:',len(records))
    print('Preços: tabela de 29/09/2026 | servidor:',args.base)
    print('Galeria: exemplo', page_url+'/'+sample.get('cover',''))
    if not args.apply:
        print('PRÉVIA: nenhuma alteração feita. Execute com --apply quando aprovar e publicar as fotos no Render.')
        return
    email=os.getenv('PV_IMPORT_EMAIL','').strip()
    password=os.getenv('PV_IMPORT_PASSWORD','')
    if not email or not password:raise SystemExit('Configure PV_IMPORT_EMAIL e PV_IMPORT_PASSWORD no terminal. Nunca inclua senhas no Git.')
    client=API(args.base,max(.1,args.delay));client.login(email,password)
    # Fail safe: static images must be published before import.
    probe=page_url+'/'+sample.get('cover','')
    try:
        result=client.client.get(probe,timeout=80)
        if result.status_code!=200 or not result.headers.get('content-type','').startswith('image/'):
            raise RuntimeError(f'Imagem não publicada: {probe} -> HTTP {result.status_code}')
    except httpx.HTTPError as exc:raise RuntimeError('Não foi possível validar a galeria publicada') from exc
    existing_categories={norm(x.get('name')):x for x in client.list_all('categories') if isinstance(x,dict)}
    existing_products={str(x.get('code') or '').upper():x for x in client.list_all('products') if isinstance(x,dict)}
    cp=load_json(args.checkpoint,{'products':{},'completed_media':[]})
    cp.setdefault('products',{});cp.setdefault('completed_media',[])
    today=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    state=client.req('GET','catalog-management/state')
    out=Path.home()/'.facil_pedido_pv_backups'/f'backup-catalogo-antes-pv-{today}.json'
    save_json(out,state)
    print('Backup do estado comercial criado localmente:',out)
    created=0;skipped=0;updated=0
    for n,r in enumerate(records,1):
        cat_name=r['category'] or 'Não classificado'
        key=norm(cat_name)
        if key not in existing_categories:
            created_cat=client.req('POST','categories',data={'name':cat_name,'description':'Importado do Catálogo Porto Velho','active':True,'item_type':'Produto acabado'})
            if not isinstance(created_cat,dict) or not created_cat.get('id'):
                raise RuntimeError('ERP não retornou ID ao criar categoria '+cat_name)
            existing_categories[key]=created_cat
        sku=r['sku'].upper();p=existing_products.get(sku)
        # O checkpoint apenas registra o progresso; nunca é prova de que o
        # cadastro ainda existe no ERP. A consulta real pelo SKU prevalece.
        payload={
          'code':sku,'name':r['name'],'description':r['description'],
          'color':r['color'],'category_id':existing_categories[key]['id'],
          'item_type':'Produto acabado','unit':'UN','size':'','price':r['price'],
          'cost':0,'technical_cost':0,'stock':0,'reserved_stock':0,
          'min_stock':0,'base_stock':0,'manufacturing_enabled':False,'active':True,
        }
        if not p:
            new=client.req('POST','products',data=payload)
            if not isinstance(new,dict) or not new.get('id'):
                raise RuntimeError(f'Produto {sku}: ERP não devolveu o ID')
            pid=str(new['id']);created+=1
            existing_products[sku]={'id':pid,'code':sku}
        else:
            pid=str(p['id']);skipped+=1
            if args.update_prices:
                client.req('PUT','products/'+pid,data={'price':r['price']});updated+=1
        cp['products'][sku]=pid
        if n%15==0 or n==len(records):
            save_json(args.checkpoint,cp)
            print(f'[{n}/{len(records)}] novos={created} existentes={skipped} atualizados={updated}',flush=True)
    save_json(args.checkpoint,cp)
    # Merge latest live state, preserving user-created product galleries and other metadata.
    for attempt in range(5):
        state=client.req('GET','catalog-management/state')
        revision=state.get('revision',0)
        full=dict(state.get('payload') or {})
        gallery=dict(full.get('media') or {})
        present=dict(full.get('presentation') or {})
        for r in records:
            pid=cp['products'][r['sku'].upper()]
            urls=[page_url+'/'+x for x in r.get('photos', [r['cover'],r['datasheet']])]
            old=dict(gallery.get(pid) or {})
            existing_urls=list(old.get('photos') or [])
            # Keep personal photos first, add source photos exactly once.
            merged=list(dict.fromkeys(existing_urls+urls))[:12]
            old['photos']=merged
            gallery[pid]=old
            pr=dict(present.get(pid) or {})
            pr.setdefault('title',r['title'])
            pr.setdefault('subtitle',r['color'])
            pr.setdefault('description',r['description'])
            pr.setdefault('published',True)
            present[pid]=pr
        try:
            client.req('PUT','catalog-management/state',data={'base_revision':revision,'payload':{'media':gallery,'presentation':present}})
            print(f'CONCLUÍDO: {len(records)} registros com imagens vinculadas. Novos={created}; existentes={skipped}.')
            print('As fotos são públicas, estáveis e compartilhadas entre computadores; registros existentes foram preservados.')
            break
        except RuntimeError as e:
            if 'HTTP 409' not in str(e) or attempt==4:raise
            time.sleep(2)

if __name__=='__main__':
    try:main()
    except (RuntimeError,KeyboardInterrupt) as e:
        print('\nIMPORTAÇÃO INTERROMPIDA:',str(e),file=sys.stderr)
        print('Os SKUs importados podem ser retomados executando o mesmo comando; não exclua o checkpoint.',file=sys.stderr)
        sys.exit(1)
