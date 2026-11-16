(() => {
"use strict";
const API=window.CommercialAPI,CFG=window.FP_COMMERCIAL_CONFIG;
const fmtBRL=v=>new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(v)||0);
const esc=v=>String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
const norm=v=>String(v??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const initials=n=>String(n||"FP").split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("").toUpperCase();
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`};
const addDays=(d,n)=>{const x=new Date(d);x.setDate(x.getDate()+n);return x.toISOString().slice(0,10)};
const daysSince=v=>v?Math.floor((Date.now()-new Date(v).getTime())/86400000):0;
const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
const clone=v=>JSON.parse(JSON.stringify(v));

const state={
  demo:false,user:null,permissions:[],health:null,
  products:[],variants:[],categories:[],locations:[],balances:[],clients:[],clientStates:[],quotes:[],orders:[],
  catalog:{media:{},presentation:{},promotions:[],crm:{},quoteMeta:{},settings:{},history:[],operations:{}},
  catalogRevision:0,cart:[],selectedClient:null,favorites:new Set(),recent:[],
  route:"inicio",filters:{source:"all",q:"",category:"",stock:"all",sort:"relevance",favorites:false,page:1},systemUsers:[],
  studioProductId:null,presentationIds:[],clientPriceCache:{},online:navigator.onLine,access:{permissions:[]},catalogManagerFilter:"all",catalogManagerQuery:""
};

const modern={homePage:1,documents:[],documentsLoaded:false,documentsError:'',cartDocument:null,dirty:false,mutation:0,quoteSeq:0,clientSeq:0,busy:false,saving:false,lastQuote:null,policy:null,shares:{},priceSources:{},undo:null,documentFilter:{q:'',kind:'',status:'',start:'',end:''},reportFilter:{start:'',end:'',client_id:'',status:'',seller:''}};

function ensureCatalog(){
  state.catalog ||= {};
  state.catalog.media ||= {};state.catalog.presentation ||= {};state.catalog.promotions ||= [];
  state.catalog.crm ||= {};state.catalog.quoteMeta ||= {};state.catalog.history ||= [];state.catalog.productExtras ||= {};
  state.catalog.operations ||= {};
  state.catalog.operations.production ||= [];
  state.catalog.operations.deliveries ||= [];
  state.catalog.operations.receivables ||= [];
  state.catalog.operations.payables ||= [];
  state.catalog.operations.users ||= [];
  state.catalog.operations.approvals ||= [];
  state.catalog.operations.stockMovements ||= [];
  state.catalog.operations.followups ||= [];
  state.catalog.quoteMeta.preliminary ||= [];

  state.catalog.settings={companyName:"Fácil Pedido",whatsapp:"",pixDiscount:0,installments:1,installmentFee:0,minimumMargin:20,autoCreateProduction:true,autoCreateReceivable:true,autoCreateDelivery:true,defaultWarrantyMonths:12,requireDiscountApproval:true,...(state.catalog.settings||{})};
}
function toast(msg,type="ok"){const e=document.createElement("div");e.className=`toast ${type}`;e.textContent=msg;$("#toastRoot").appendChild(e);setTimeout(()=>e.remove(),3200)}
function hasPermission(permission){
  if(state.demo)return true;
  if(["administrator","admin"].includes(String(state.user?.role||"").toLowerCase()))return true;
  const perms=state.access?.permissions||[];
  return perms.includes("*")||perms.includes(permission);
}
function canManageCatalog(){return hasPermission("catalog.write")}
function canPublishCatalog(){return hasPermission("catalog.publish")}
function canReadCatalog(){return hasPermission("catalog.read")}
function canUseSales(){return hasPermission("sales.read")}
function canWriteSales(){return hasPermission("sales.write")}
function canSeeClients(){return hasPermission("clients.read")}
function canSeeCost(){if(modern.presentationMode)return false;return state.demo||hasPermission("settings.write")||hasPermission("finance.read")}
function canConfirmSale(){return canWriteSales()}
function demoPhoto(label,accent="#cfd6de"){
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="720"><defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#f2f4f7"/><stop offset="1" stop-color="${accent}"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/><rect x="170" y="285" width="660" height="205" rx="40" fill="#fff" opacity=".94"/><rect x="210" y="205" width="240" height="145" rx="30" fill="#fff" opacity=".9"/><rect x="550" y="205" width="240" height="145" rx="30" fill="#fff" opacity=".9"/><rect x="205" y="485" width="38" height="70" rx="10" fill="#9ca3af"/><rect x="757" y="485" width="38" height="70" rx="10" fill="#9ca3af"/><text x="500" y="625" font-family="Arial" font-size="32" text-anchor="middle" fill="#344054">${label}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
function demoData(){
  state.categories=["Sofás","Boxes e baús","Poltronas","Cabeceiras","Colchões","Mesas","Cadeiras","Acessórios"].map((name,i)=>({id:`CAT-${i+1}`,name}));
  state.locations=["Loja","Depósito","Fábrica","Quarentena / Avarias"].map((name,i)=>({id:`LOC-${i+1}`,name,address_code:name}));
  state.products=[];
  state.variants=[];
  state.balances=[];
  state.clients=[];
  state.clientStates=[];
  state.quotes=[];
  state.orders=[];
  state.selectedClient=null;
  state.cart=[];
  state.clientPriceCache={};
  state.catalog={media:{},presentation:{},promotions:[],crm:{},quoteMeta:{},settings:{},history:[],operations:{production:[],deliveries:[],receivables:[],payables:[],users:[],approvals:[],stockMovements:[],followups:[]}};
  ensureCatalog();
}

// Vitrine de consulta: produtos da tabela Porto Velho ainda não cadastrados no ERP.
// Nenhum item PV-CAT é enviado ao carrinho, estoque, pedidos ou gravação no ERP.
const pvShowcase={ready:false,loading:false,rows:[],error:"",sourceDate:"2026-09-29"};
function pvShowcaseRows(){
  const registered=new Set(state.products.map(p=>pvNorm(p.code||p.sku)).filter(Boolean));
  const unmatched=pvShowcase.rows.filter(p=>!registered.has(pvNorm(p.code)));
  // Na primeira página mostrar modelos diferentes antes das variações de cor.
  const seen=new Set(),first=[],variations=[];
  for(const p of unmatched){
    if(!seen.has(p.catalog_page)){first.push(p);seen.add(p.catalog_page)}
    else variations.push(p);
  }
  return first.concat(variations);
}
function pvReferenceSourcePhotos(p){
  return [...new Set([p.cover,...(p.photos||[])].filter(path=>pvAssetLocation(path)))];
}
function pvReferenceVisiblePhotos(p){
  const hidden=new Set(state.catalog?.media?.[p.id]?.hiddenReferencePhotos||[]);
  return pvReferenceSourcePhotos(p).filter(path=>!hidden.has(path));
}
function pvReferenceCover(p){return pvReferenceVisiblePhotos(p)[0]||""}
async function pvHidePhoto(id,path){
  if(!canManageCatalog())throw new Error("Você não tem permissão para excluir fotos.");
  const p=pvShowcase.rows.find(x=>x.id===id);
  if(!p||!pvReferenceSourcePhotos(p).includes(path))throw new Error("Foto inválida ou não encontrada.");
  if(!confirm(`Excluir esta foto da vitrine do produto "${p.name}"?\n\nO arquivo original do PDF será preservado e poderá ser restaurado.`))return;
  ensureCatalog();
  const current=state.catalog.media[id]||{};
  const old=[...(current.hiddenReferencePhotos||[])];
  current.hiddenReferencePhotos=[...new Set([...old,path])];
  state.catalog.media[id]=current;
  try{await saveCatalogState()}
  catch(err){current.hiddenReferencePhotos=old;throw err}
  toast("Foto excluída da vitrine. Original preservado.");
  if(document.querySelector(".pv-showcase-detail"))pvReferenceDetail(id);
  else render();
}
async function pvRestorePhotos(id){
  if(!canManageCatalog())throw new Error("Sem permissão para restaurar fotos.");
  const p=pvShowcase.rows.find(x=>x.id===id);
  if(!p)throw new Error("Produto não encontrado.");
  if(!confirm(`Restaurar todas as fotos originais de "${p.name}" na vitrine?`))return;
  ensureCatalog();
  const entry=state.catalog.media[id]||{};
  const old=[...(entry.hiddenReferencePhotos||[])];
  entry.hiddenReferencePhotos=[];state.catalog.media[id]=entry;
  try{await saveCatalogState()}catch(err){entry.hiddenReferencePhotos=old;throw err}
  toast("Fotos originais restauradas.");
  if(document.querySelector(".pv-showcase-detail"))pvReferenceDetail(id);
  else render();
}
function pvShowcaseHomeRows(limit=8){
  const used=new Set();const rows=[];
  for(const p of pvShowcaseRows()){
    if(p.review_needed||used.has(p.catalog_page)||!pvReferenceCover(p))continue;
    used.add(p.catalog_page);rows.push(p);
    if(rows.length>=limit)break;
  }
  return rows;
}
function pvAssetLocation(src){
  const path=String(src||"");
  if(!/^pv-assets\/(cover|page|inset)-\d{3}\.jpg$/.test(path))return "";
  const prefix=location.pathname.startsWith("/comercial")?"/comercial/":"/";
  return prefix+path;
}
async function loadPvShowcase(){
  if(pvShowcase.ready||pvShowcase.loading||state.demo)return;
  pvShowcase.loading=true;
  try{
    const data=await API.request("/porto-velho/vitrine");
    if(!Array.isArray(data.products))throw new Error("Formato inválido do catálogo Porto Velho");
    pvShowcase.sourceDate=String(data.price_date||"2026-09-29");
    pvShowcase.rows=data.products.filter(r=>r.name && pvAssetLocation(r.cover)).map(r=>({
      id:`PV-CAT-${r.id}`,code:String(r.sku||""),name:String(r.name),category_id:`PV::${String(r.category||"Sem categoria").trim()||"Sem categoria"}`,
      category_name:String(r.category||"Sem categoria").trim()||"Sem categoria",color:String(r.color||""),price:Number(r.price||0),
      description:String(r.description||""),catalog_page:Number(r.catalog_page),
      cover:String(r.cover),photos:Array.isArray(r.photos)?r.photos.filter(x=>pvAssetLocation(x)):[],
      review_needed:!!r.review_needed,_pvReference:true
    }));
    pvShowcase.ready=true;pvShowcase.error="";
    const requested=new URLSearchParams(location.search).get("pv_product");if(requested&&!window._fpSharedLinkOpened){window._fpSharedLinkOpened=true;setTimeout(()=>pvReferenceDetail(requested),30)}

  }catch(err){pvShowcase.error=String(err.message||err);console.warn("Vitrine Porto Velho indisponível:",err)}
  finally{
    pvShowcase.loading=false;
    if(state.route==='inicio')renderHomeProducts();
    else if(state.route==='catalogo')refreshCatalogPreservingFocus();
  }
}
function pvReferencePrice(p){return p.review_needed||!(p.price>0)?"Valor a conferir":fmtBRL(p.price)}
function pvReferenceDetail(id){
  const p=pvShowcase.rows.find(x=>x.id===id);if(!p)return;
  const photos=pvReferenceVisiblePhotos(p),imgs=photos.map(pvAssetLocation);
  const removed=(state.catalog?.media?.[p.id]?.hiddenReferencePhotos||[]).length;
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card wide pv-showcase-detail"><div class="modal-head"><div><h3>${esc(p.name)}</h3><p>${esc(p.category_name)} • Ref. ${esc(p.code)} • Página ${p.catalog_page}</p></div><button class="icon-btn" data-close-modal>×</button></div>
    <div class="modal-body"><div class="product-detail"><div><div class="gallery-main" id="galleryMain">${imgs.length?`<img src="${esc(imgs[0])}" alt="${esc(p.name)}">`:`<div class="pv-no-image">Este modelo está sem fotos na vitrine.</div>`}</div><div class="gallery-thumbs">${photos.map(path=>`<div class="pv-ref-thumb-group"><button class="gallery-thumb" data-gallery-src="${esc(pvAssetLocation(path))}"><img loading="lazy" decoding="async" src="${esc(pvAssetLocation(path))}" alt="Foto de ${esc(p.name)}"></button>${canManageCatalog()?`<button class="pv-delete-photo" data-action="pv-hide-photo" data-id="${esc(p.id)}" data-photo="${esc(path)}">Excluir foto</button>`:""}</div>`).join("")}</div>${canManageCatalog()&&removed?`<div class="actions" style="margin-top:12px"><button class="secondary-btn" data-action="pv-restore-photos" data-id="${esc(p.id)}">Restaurar fotos (${removed})</button></div>`:""}</div>
    <div class="detail-info"><span class="chip blue">Porto Velho · referência do catálogo</span><h2>${esc(p.name)}</h2><div class="detail-price">${esc(pvReferencePrice(p))}</div><div class="pv-showcase-price-label">Tabela de 29/09/2026; confirme o preço de venda no ERP</div><p class="pv-showcase-note">${esc(p.description)}</p><p class="pv-showcase-note">Este modelo está disponível para consulta visual, mas ainda não possui cadastro de venda vinculado ao ERP. Estoque, preço final e pedido só poderão ser usados após o cadastro.</p><div class="quote-price-toggle"><button data-action="reference-price-eye" data-id="${esc(p.id)}" aria-label="Exibir condições e custo">👁 Ver preço à vista e V.C.</button></div><div class="quote-price-info hidden" id="pvPriceInfo">Preço de referência: ${esc(pvReferencePrice(p))}. À vista (PIX, condição indicativa): ${p.review_needed||!(p.price>0)?"Valor a conferir":fmtBRL(p.price*(1-Number(pricePolicy().pixDiscount||0)/100))} (desconto não aplicado automaticamente). V.C./custo: não cadastrado nesta referência.</div><div class="actions"><button class="success-btn" data-action="pv-add" data-id="${esc(p.id)}">＋ Adicionar ao orçamento</button><button class="secondary-btn" data-action="pv-share" data-id="${esc(p.id)}">Copiar link do produto</button><button class="secondary-btn" data-close-modal>Fechar</button>${canManageCatalog()?`<button class="primary-btn" data-action="pv-go-manager">Gerenciar cadastro no ERP</button>`:""}</div></div></div></div></div></div>`;
  $("#modalRoot").classList.add("show");
}
function pvReferenceCard(p){
  const cover=pvReferenceCover(p),source=pvAssetLocation(cover);
  return `<article class="product-card pv-showcase-card"><div class="product-photo" data-action="pv-reference-detail" data-id="${esc(p.id)}">${source?`<img loading="lazy" decoding="async" src="${esc(source)}" alt="${esc(p.name)}">`:`<div class="pv-no-image">Sem foto • restaurável</div>`}</div><div class="product-card-body"><div class="product-meta"><span class="chip blue">${esc(p.category_name)}</span><span class="chip">Consulta Porto Velho</span></div><h3>${esc(p.name)}</h3><div class="product-sub">${esc(p.color||p.code)}</div><div class="product-price">${esc(pvReferencePrice(p))}</div><div class="pv-showcase-price-label">Referência da tabela · 29/09/2026</div><div class="product-actions"><button class="secondary-btn" data-action="pv-reference-detail" data-id="${esc(p.id)}">👁 Ver detalhes</button><button class="success-btn" data-action="pv-add" data-id="${esc(p.id)}">＋ Orçamento</button>${canManageCatalog()&&cover?`<button class="pv-delete-photo" data-action="pv-hide-photo" data-id="${esc(p.id)}" data-photo="${esc(cover)}">Excluir foto</button>`:""}${canManageCatalog()&&!cover?`<button class="secondary-btn" data-action="pv-restore-photos" data-id="${esc(p.id)}">Restaurar fotos</button>`:""}</div></div></article>`;
}

// Banco de referências Porto Velho extraído dos PDFs. As sugestões não alteram preço/estoque no ERP.
const pvRef={ready:false,rows:[],byCode:new Map(),byName:new Map(),suggestions:new Map()};
const pvNorm=value=>norm(value).replace(/[^a-z0-9]+/g," ").trim().replace(/\s+/g," ");
const pvUrl=(page,part="principal")=>`${location.origin}${location.pathname.startsWith("/comercial")?"/comercial":""}/pv-assets/pv_pagina_${String(page).padStart(3,"0")}_${part}.webp`;
async function loadPvReference(){
  if(pvRef.ready||state.demo)return;
  try{
    const data=await API.request("/porto-velho/referencias");
    if(!Array.isArray(data.rows))return;
    pvRef.rows=data.rows;
    for(const r of pvRef.rows){
      const c=pvNorm(r.code),n=pvNorm(r.name);
      if(c){if(!pvRef.byCode.has(c))pvRef.byCode.set(c,[]);pvRef.byCode.get(c).push(r)}
      if(n){if(!pvRef.byName.has(n))pvRef.byName.set(n,[]);pvRef.byName.get(n).push(r)}
    }
    pvRef.ready=true;pvRef.suggestions.clear();
    if(["catalogo","catalog-manager","inicio"].includes(state.route) && !["INPUT","TEXTAREA"].includes(document.activeElement?.tagName))render();
  }catch(err){console.info("Referências Porto Velho indisponíveis:",err.message)}
}
function pvCandidates(product){
  if(!product||!pvRef.ready)return [];
  const key=String(product.id)+":"+String(product.code)+":"+String(product.name);
  if(pvRef.suggestions.has(key))return pvRef.suggestions.get(key);
  const code=pvNorm(product.code||product.sku),name=pvNorm(product.name),found=new Map();
  function include(r,score){
    const page=Number(r.page);
    if(page<5||page>300)return;
    const previous=found.get(page);
    if(!previous||score>previous.score)found.set(page,{page,score,name:r.name,price:r.price_reference,code:r.code,variant:r.variant,distance:r.distance});
  }
  for(const r of pvRef.byCode.get(code)||[])include(r,110);
  for(const r of pvRef.byName.get(name)||[])include(r,95);
  // Produto do ERP pode conter a cor após o nome. Requer nome-base grande e início exato.
  if(found.size===0&&name.length>=12){
    for(const r of pvRef.rows){
      const other=pvNorm(r.name);
      if(other.length>=12 && name.startsWith(other+" "))include(r,78);
    }
  }
  const items=[...found.values()].sort((a,b)=>b.score-a.score||a.distance-b.distance||a.page-b.page).slice(0,12);
  pvRef.suggestions.set(key,items);return items;
}
function pvAutoCandidate(p){
  if(!p || state.catalog.media?.[p.id]?.disableReference)return null;
  const a=pvCandidates(p);if(!a.length||a[0].score<95||Number(a[0].distance)>28)return null;
  if(a.length>1 && a[1].score===a[0].score && a[1].page!==a[0].page)return null;
  return a[0];
}
function pvAutoPhoto(p){
  if(!p||state.catalog.media?.[p.id]?.disableReference)return "";
  // Produtos do ERP mock têm página de referência explícita, mesmo antes do índice carregar.
  const mockPage=Number(p.pv_catalog_page);
  if(String(p.id||"").startsWith("PVTEST-")&&Number.isInteger(mockPage)&&mockPage>=5&&mockPage<=300)return pvUrl(mockPage);
  const c=pvAutoCandidate(p);return c?pvUrl(c.page):"";
}
function pvStudioControls(p){
  if(!p)return "";
  const entries=pvCandidates(p),disabled=state.catalog.media?.[p.id]?.disableReference;
  return `<section class="pv-ref-panel" style="margin-top:18px;border:1px solid #dce6ed;border-radius:12px;padding:14px;background:#f7fafc">
    <strong>Fotografias do catálogo Porto Velho</strong>
    <p class="help">Fotos retiradas do PDF, sugestões por código/nome. Confira a imagem antes de vincular. Preços da tabela são apenas referência, não alteram o ERP.</p>
    ${pvRef.ready?`<div class="pv-ref-images">${entries.slice(0,4).map(r=>`<div class="pv-ref-card"><img loading="lazy" decoding="async" src="${pvUrl(r.page)}" alt="Foto da página ${r.page}"><small>Página ${r.page}${r.price?` • ref. R$ ${esc(r.price)}`:""}</small><button class="secondary-btn" data-action="pv-attach" data-page="${r.page}" data-kind="principal">Usar foto</button></div>`).join("")||`<small>Sem correspondência segura para este produto. Escolha manualmente pelo número da página.</small>`}</div>`:`<p class="help">Referências carregam depois do login.</p>`}
    <div class="actions" style="margin-top:12px;flex-wrap:wrap"><button class="secondary-btn" data-action="pv-picker" data-page="1">Procurar nas 296 páginas</button>${disabled?`<button class="secondary-btn" data-action="pv-enable">Reativar sugestões</button>`:`<button class="secondary-btn" data-action="pv-disable">Ocultar foto sugerida</button>`}${hasPermission("settings.write")?`<button class="secondary-btn" data-action="open-product-form" data-id="${esc(p.id)}">Editar preço oficial no ERP</button>`:""}</div>
    </section>`;
}
async function pvAttachPhoto(page,kind="principal"){
  if(!canManageCatalog())throw new Error("Sem permissão para fotos");
  page=Number(page);
  if(!Number.isInteger(page)||page<5||page>300||!["principal","detalhe_1","detalhe_2"].includes(kind))throw new Error("Página ou recorte inválido");
  const id=state.studioProductId,product=state.products.find(p=>p.id===id);if(!product)throw new Error("Selecione um produto");
  const item=state.catalog.media[id]||={photos:[],variantPhotos:{}};
  if(item.photos.length>=CFG.MAX_PHOTOS_PER_PRODUCT)throw new Error("Máximo de 12 fotos por produto");
  const url=pvUrl(page,kind);
  if(item.photos.includes(url))throw new Error("Esta imagem já está no produto");
  item.photos.push(url);item.disableReference=false;
  await saveCatalogState();toast("Foto vinculada. Você ainda pode substituir ou remover pelo Studio.");closeModal();renderStudio();
}
async function pvBulkLink(){
  if(!canManageCatalog()||!pvRef.ready)throw new Error("Aguarde o carregamento da referência Porto Velho");
  const candidate=state.products.map(p=>[p,pvAutoCandidate(p)]).filter(([p,c])=>c&&!(state.catalog.media[p.id]?.photos||[]).length);
  if(!candidate.length){toast("Nenhuma correspondência segura sem foto encontrada");return}
  if(!confirm(`Associar ${candidate.length} fotos sugeridas aos produtos correspondentes? Isso não altera preços, descrições técnicas ou estoque.`))return;
  for(const [p,c] of candidate){const media=state.catalog.media[p.id]||={photos:[],variantPhotos:{}};media.photos.push(pvUrl(c.page))}
  try{await saveCatalogState();toast(`${candidate.length} foto(s) vinculada(s)`);renderCatalogManager()}
  catch(err){for(const [p,c] of candidate){const a=state.catalog.media[p.id]?.photos||[];const i=a.indexOf(pvUrl(c.page));if(i>=0)a.splice(i,1)}throw err}
}
function pvPicker(page=1,query=""){
  const q=pvNorm(query),matches=[];
  for(let n=5;n<=300;n++){
    const candidates=pvRef.rows.filter(r=>r.page===n);
    if(!q||String(n).includes(q)||candidates.some(r=>pvNorm(r.name+" "+r.code).includes(q)))matches.push(n);
  }
  const last=Math.max(1,Math.ceil(matches.length/16));page=clamp(Number(page)||1,1,last);
  const results=matches.slice((page-1)*16,page*16);
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card wide" style="max-width:1050px"><div class="modal-head"><div><h3>Fotos do catálogo Porto Velho</h3><p>${matches.length} páginas encontradas • escolha a foto principal ou um detalhe</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="actions"><input id="pvSearchInput" placeholder="Produto, código ou página" value="${esc(query)}"><button class="secondary-btn" data-action="pv-search">Buscar</button></div><div class="pv-ref-images pv-modal-grid" style="margin-top:12px">${results.map(n=>`<div class="pv-ref-card"><img loading="lazy" decoding="async" src="${pvUrl(n)}" alt="Catálogo página ${n}"><small>Página ${n}</small><button data-action="pv-attach" data-page="${n}" data-kind="principal" class="primary-btn">Foto principal</button><button data-action="pv-attach" data-page="${n}" data-kind="detalhe_1" class="secondary-btn">Detalhe 1</button><button data-action="pv-attach" data-page="${n}" data-kind="detalhe_2" class="secondary-btn">Detalhe 2</button></div>`).join("")||"Nenhuma página encontrada"}</div><div class="actions" style="margin-top:16px"><button class="secondary-btn" data-action="pv-picker-page" data-page="${page-1}" ${page===1?"disabled":""}>Anterior</button><small>Página ${page} de ${last}</small><button class="secondary-btn" data-action="pv-picker-page" data-page="${page+1}" ${page===last?"disabled":""}>Próxima</button></div></div></div></div>`;
  $("#modalRoot").classList.add("show");
}


function pvGallery(page=1,query=""){
  const q=pvNorm(query),matches=[];
  for(let n=5;n<=300;n++){
    const candidates=pvRef.rows.filter(r=>r.page===n);
    if(!q||String(n).includes(q)||candidates.some(r=>pvNorm(r.name+" "+r.code+" "+r.category).includes(q)))matches.push(n);
  }
  const total=Math.max(1,Math.ceil(matches.length/8));page=clamp(Number(page)||1,1,total);
  const current=matches.slice((page-1)*8,page*8);
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card wide" style="max-width:1120px"><div class="modal-head"><div><h3>Galeria Porto Velho — 888 imagens</h3><p>296 páginas com foto principal e dois recortes por página. Confira cada produto antes de vincular.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="actions"><input id="pvGallerySearchInput" placeholder="Nome do móvel, categoria, código ou página" value="${esc(query)}"><button class="secondary-btn" data-action="pv-gallery-search">Buscar</button></div><div class="pv-gallery-grid">${current.map(n=>`<section class="pv-gallery-page"><strong>Página ${n}</strong><small>${esc((pvRef.rows.find(r=>r.page===n)||{}).name||'Catálogo Porto Velho')}</small><div class="pv-gallery-triplet">${["principal","detalhe_1","detalhe_2"].map(kind=>`<a href="${pvUrl(n,kind)}" target="_blank" rel="noopener" title="Abrir imagem original"><img loading="lazy" decoding="async" src="${pvUrl(n,kind)}" alt="Página ${n} - ${kind}"></a>`).join("")}</div></section>`).join("")||"<p>Nenhuma página encontrada.</p>"}</div><div class="actions" style="margin-top:15px;justify-content:center"><button class="secondary-btn" data-action="pv-gallery-page" data-page="${page-1}" ${page===1?"disabled":""}>Anterior</button><small>${matches.length} páginas encontradas — ${page}/${total}</small><button class="secondary-btn" data-action="pv-gallery-page" data-page="${page+1}" ${page===total?"disabled":""}>Próxima</button></div></div></div></div>`;
  $("#modalRoot").classList.add("show");
}
function normalizedPhotoLocation(src){
  const raw=String(src||"");
  try{
    const u=new URL(raw,location.href);
    // Em execução local o iniciador troca a porta. URLs antigas passam a usar a porta atual.
    const local=["127.0.0.1","localhost"].includes(u.hostname) && ["127.0.0.1","localhost"].includes(location.hostname);
    if(local && (/^\/pv-assets\/pv_pagina_\d{3}_(principal|detalhe_[12])\.webp$/.test(u.pathname)||/^\/api\/v1\/media\/[a-f0-9-]{36}$/.test(u.pathname))){
      return u.pathname+u.search;
    }
  }catch{}
  return raw;
}
function mediaFor(id){
  ensureCatalog();const photos=state.catalog.media[id]?.photos||[];
  for(let i=0;i<photos.length;i++)photos[i]=normalizedPhotoLocation(photos[i]);
  return photos;
}
function mediaForVariant(productId,variantId){return state.catalog.media[productId]?.variantPhotos?.[variantId]||[]}
function safePhotoUrl(value){
  const src=String(value||"").trim();
  if(src.startsWith("data:image/jpeg;base64,")||src.startsWith("data:image/png;base64,")||src.startsWith("data:image/webp;base64,")||src.startsWith("data:image/svg+xml;charset=utf-8,"))return esc(src);
  try{const url=new URL(src,location.href);if(["https:","http:"].includes(url.protocol))return esc(url.href)}catch{}
  return "";
}
function photoFor(p,variantId=null){if(p._pvReference)return safePhotoUrl(pvAssetLocation(pvReferenceCover(p)));return safePhotoUrl((variantId?mediaForVariant(p.id,variantId)[0]:null)||mediaFor(p.id)[0]||pvAutoPhoto(p)||demoPhoto("Sem foto cadastrada"))}
function presentationFor(id){ensureCatalog();return state.catalog.presentation[id]||{}}
function categoryName(p){return p.category_name||state.categories.find(c=>c.id===p.category_id)?.name||"Sem categoria"}
function locationName(id){const x=state.locations.find(l=>l.id===id);return x?.name||x?.address_code||"Não informado"}
function available(p,variantId=null){
  if(variantId){const rows=stockRows().filter(b=>b.product_id===p.id&&b.variant_id===variantId);if(rows.length)return rows.reduce((n,b)=>n+Number(b.available_quantity??(Number(b.quantity||0)-Number(b.reserved_quantity||0))),0);const v=state.variants.find(x=>x.id===variantId);return v?Math.max(0,Number(v.stock||0)-Number(v.reserved_stock||0)):0}
  const rows=stockRows().filter(b=>b.product_id===p.id&&!b.variant_id);
  if(rows.length)return rows.reduce((s,b)=>s+Number(b.available_quantity??(Number(b.quantity||0)-Number(b.reserved_quantity||0))),0);
  return Math.max(0,Number(p.stock||0)-Number(p.reserved_stock||0));
}
function bestStockLocation(p,qty=1){
  const rows=stockRows().filter(b=>b.product_id===p.id).map(b=>({...b,avail:Number(b.available_quantity??(Number(b.quantity||0)-Number(b.reserved_quantity||0)))})).sort((a,b)=>b.avail-a.avail);
  return rows.find(x=>x.avail>=qty)||rows[0]||null;
}
function activePromo(p){
  ensureCatalog();const now=today();
  return state.catalog.promotions.find(x=>x.active!==false&&x.productIds?.includes(p.id)&&(!x.start||x.start<=now)&&(!x.end||x.end>=now))||null;
}
function promoPrice(p){
  const promo=activePromo(p);const base=Number(p.price||0);
  if(!promo)return base;
  return promo.type==="fixed"?Math.max(0,base-Number(promo.value||0)):Math.max(0,base*(1-Number(promo.value||0)/100));
}
async function clientPrice(p,client=state.selectedClient){
  if(!client)return promoPrice(p);
  const key=`${client.id}:${p.id}`;
  if(state.clientPriceCache[key]!=null)return state.clientPriceCache[key];
  const local=state.clientStates.find(c=>(c.server?.id||c.id)===client.id);
  const item=local?.price_table?.find(r=>[p.id,p.code,p.name].includes(r.product_ref)||r.product_name===p.name);
  if(item){state.clientPriceCache[key]=Number(item.price);modern.priceSources[key]='client_price_table';return Number(item.price)}
  if(state.demo)return promoPrice(p);
  const result=await API.request(`/client-management/${encodeURIComponent(client.id)}/product-price/${encodeURIComponent(p.id)}`);
  if(result.source==='not_found')throw Error('Produto não encontrado na consulta de preços.');
  state.clientPriceCache[key]=Number(result.price);modern.priceSources[key]=result.source;
  return Number(result.price);
}
function stockClass(p){const a=available(p);return a<=0?"red":a<=Number(p.min_stock||2)?"orange":"green"}
function cartProductsTotal(){try{return cartCalculation().subtotal}catch{return 0}}
function cartTotal(){try{return cartCalculation().total}catch{return 0}}
function cartHasReference(){return state.cart.some(i=>i.product?._pvReference)}
function cartAllPriced(){return state.cart.length>0&&state.cart.every(i=>Number(i.unitPrice)>0)}
function cartPhoto(p,variantId){return p?._pvReference?(pvAssetLocation(pvReferenceCover(p))||demoPhoto("Sem foto")):photoFor(p,variantId)}
function cartMeta(){
  state.cartMeta ||= {freight:0,assembly:0,orderDiscount:0,discountType:'amount',payment:'PIX',payments:[],notes:'',cep:'',number:'',complement:'',street:'',district:'',city:'',uf:'',deliveryAddress:'',deliveryDate:'',validUntil:addDays(new Date(),7),freightSource:'manual'};
  state.cartMeta.payments ||= [];return state.cartMeta;
}
function cartShippingAddress(){const m=cartMeta(),parts=[m.street,[m.number,m.complement].filter(Boolean).join(" - "),m.district,[m.city,m.uf].filter(Boolean).join("/")].filter(Boolean);return parts.length?`${parts.join(", ")} • CEP ${m.cep||"não informado"}`:(m.deliveryAddress||state.selectedClient?.address||"")}
function paymentPlanned(){return cartMeta().payments.reduce((sum,p)=>sum+Math.max(0,Number(p.amount)||0),0)}

function cartQty(){return state.cart.reduce((sum,i)=>sum+(Number(i.qty)||0),0)}
function getFavorites(){try{return new Set(JSON.parse(localStorage.getItem(`fp_favorites_${state.user?.id||"demo"}`)||"[]"))}catch{return new Set()}}
function persistFavorites(){localStorage.setItem(`fp_favorites_${state.user?.id||"demo"}`,JSON.stringify([...state.favorites]))}
function logHistory(action,entity,details=""){ensureCatalog();state.catalog.history.unshift({id:crypto.randomUUID?.()||String(Date.now()),at:new Date().toISOString(),user:state.user?.full_name||"Usuário",action,entity,details});state.catalog.history=state.catalog.history.slice(0,500)}
function notifications(){
  ensureCatalog();const out=[],ops=opData(),tom=addDays(new Date(),1),now=today();
  state.products.filter(p=>available(p)<=Number(p.min_stock||0)).slice(0,8).forEach(p=>out.push({title:`Estoque crítico: ${p.name}`,text:`${available(p)} unidade(s) disponível(is).`,type:"stock"}));
  state.quotes.filter(q=>!["Aprovado","Perdido"].includes(q.status||"")&&daysSince(q.created_at)>=3).slice(0,8).forEach(q=>out.push({title:`Follow-up: ${q.code||q.id}`,text:`${q.client_name||"Cliente"} • ${daysSince(q.created_at)} dias sem avanço.`,type:"quote"}));
  ops.receivables.filter(x=>x.status!=="Pago"&&x.due_date&&x.due_date<now).slice(0,8).forEach(x=>out.push({title:"Conta vencida",text:`${x.description} • ${fmtBRL(x.amount)} • ${x.due_date}`,type:"finance"}));
  ops.receivables.filter(x=>x.status!=="Pago"&&x.due_date===tom).slice(0,6).forEach(x=>out.push({title:"Recebimento amanhã",text:`${x.description} • ${fmtBRL(x.amount)}`,type:"finance"}));
  ops.deliveries.filter(x=>x.status!=="Concluída"&&x.date===tom).slice(0,6).forEach(x=>out.push({title:"Entrega amanhã",text:`${x.code} • ${x.client_name||"Cliente"}`,type:"delivery"}));
  ops.production.filter(x=>x.status!=="Finalizado"&&x.due_date&&x.due_date<now).slice(0,6).forEach(x=>out.push({title:"Produção atrasada",text:`${x.code} • ${x.product_name||"Produto"} • prazo ${x.due_date}`,type:"production"}));
  state.catalog.promotions.filter(p=>p.active&&p.end&&p.end>=now&&p.end<=addDays(new Date(),2)).forEach(p=>out.push({title:"Promoção terminando",text:`${p.name} encerra em ${p.end}.`,type:"promo"}));
  return out;
}
function updateTop(){
  $("#cartCount").textContent=cartQty();$("#cartTotalMini").textContent=fmtBRL(cartTotal());
  if(state.user){$("#userName").textContent=state.user.full_name||state.user.email||"Usuário";$("#userRole").textContent=state.user.role||"Comercial";$("#userAvatar").textContent=initials(state.user.full_name||state.user.email)}
  ensureCatalog();$("#brandNameSide").textContent=state.catalog.settings.companyName||"Fácil Pedido";const topBrand=$("#brandNameTop");if(topBrand)topBrand.textContent=state.catalog.settings.companyName||"Fácil Pedido";
  const ctx=$("#headerContext");if(ctx)ctx.innerHTML=state.selectedClient?`<span>📍</span><div><small>Cliente atual</small><strong>${esc(state.selectedClient.name)}</strong></div>`:`<span>📍</span><div><small>Atendimento</small><strong>Selecione um cliente</strong></div>`;
  const sync=$("#sidebarSync");const online=!state.demo&&((state.health?.erp==="connected"&&state.health?.catalog_database==="connected")||state.health?.database==="connected");sync.classList.toggle("online",online);sync.querySelector("span").textContent=state.demo?"Modo demonstração":online?"ERP sincronizado":navigator.onLine?"ERP parcial":"Offline";
  $("#notificationCount").textContent=notifications().length;
}
async function login(email,password){const d=await API.request("/auth/login",{method:"POST",body:JSON.stringify({email,password})});API.setToken(d.token);state.user=d.user;state.permissions=d.permissions||[];return d}
async function loadAccess(){
  if(state.demo){
    state.access={permissions:["*"],can_read:true,can_write:true,can_publish:true};
    return state.access;
  }
  try{
    state.access=await API.request("/catalog-management/access");
  }catch{
    state.access={permissions:state.user?.role==="administrator"?["*"]:[]};
  }
  return state.access;
}
function defaultRoute(){
  if(canManageCatalog()&&!canUseSales())return "catalog-manager";
  return "inicio";
}
function applyAccessUI(){
  const hide=(route,hidden)=>$$(`[data-route="${route}"]`).forEach(x=>x.classList.toggle("hidden",!!hidden));
  hide("catalog-manager",!canManageCatalog());hide("studio",!canManageCatalog());hide("promocoes",!canManageCatalog());
  hide("clientes",!canSeeClients());hide("orcamentos",!canUseSales());hide("pedidos",!canUseSales());hide("relatorios",!canUseSales());
  ["estoque","producao","entregas","financeiro","equipe","auditoria"].forEach(r=>hide(r,!state.demo&&!hasPermission("settings.write")&&!canUseSales()));
  hide("configuracoes",!hasPermission("settings.write"));hide("integracao",!hasPermission("settings.write"));
}
async function loadCatalogState(){
  try{
    let d;
    try{d=await API.request("/catalog-management/state")}
    catch{d=await API.request(`/front-state/${encodeURIComponent(CFG.STATE_KEY)}`)}
    state.catalog=d.payload&&Object.keys(d.payload).length?d.payload:{};state.catalogRevision=d.revision||0;ensureCatalog();
  }catch(e){console.warn(e);ensureCatalog()}
}
async function saveCatalogState(){
  ensureCatalog();
  if(state.demo){
    const payload={products:state.products,variants:state.variants,categories:state.categories,locations:state.locations,balances:state.balances,clients:state.clients,clientStates:state.clientStates,quotes:state.quotes,orders:state.orders,catalog:state.catalog,selectedClientId:state.selectedClient?.id||null};
    try{localStorage.setItem("fp_commercial_v5_demo_state",JSON.stringify(payload))}catch(e){toast("O navegador atingiu o limite de armazenamento. Remova fotos muito pesadas ou conecte o backend.","error")}
    return;
  }
  const payload={payload:state.catalog,version:5,base_revision:state.catalogRevision};
  let d;
  try{d=await API.request("/catalog-management/state",{method:"PUT",body:JSON.stringify(payload)})}
  catch(err){if(!/404|não encontrada|not found/i.test(String(err.message||"")))throw err;d=await API.request(`/front-state/${encodeURIComponent(CFG.STATE_KEY)}`,{method:"PUT",body:JSON.stringify(payload)})}
  state.catalogRevision=d.revision||state.catalogRevision+1;
}
// O sistema real não persiste clientes, custos ou pedidos em localStorage.
function saveOfflineSnapshot(){}
function loadOfflineSnapshot(){return false}
// Adequa respostas de diferentes versões do ERP sem quebrar a renderização.
function erpRows(input, label){
  if(Array.isArray(input)) return input;
  if(input && typeof input==="object"){
    for(const key of ["items","results","rows","data"]){
      if(Array.isArray(input[key]))return input[key];
    }
  }
  console.warn(`[Fácil Pedido] ${label}: resposta de lista incompatível`,input);
  throw new Error(`O ERP devolveu o formato inválido para ${label}. Confira a compatibilidade da API.`);
}
function stockRows(){return Array.isArray(state.balances)?state.balances:[]}
async function loadAll(){
  if(state.demo){
    demoData();
    const saved=localStorage.getItem("fp_commercial_v5_demo_state");
    if(saved){try{const x=JSON.parse(saved);Object.assign(state,{products:x.products||[],variants:x.variants||[],categories:x.categories||state.categories,locations:x.locations||state.locations,balances:x.balances||[],clients:x.clients||[],clientStates:x.clientStates||[],quotes:x.quotes||[],orders:x.orders||[],catalog:x.catalog||state.catalog});ensureCatalog();state.selectedClient=state.clients.find(c=>c.id===x.selectedClientId)||null}catch(e){console.warn(e)}}
    for(const key of ["products","variants","categories","locations","balances","clients","clientStates","quotes","orders"]){
      if(!Array.isArray(state[key]))state[key]=[];
    }
    state.health={database:"demo",status:"ok"};state.favorites=getFavorites();await loadAccess();return;
  }
  try{
    await loadAccess();
    let bundle=null;
    try{bundle=await API.request("/catalog-management/products?limit=500")}catch{}
    if(bundle){
      state.products=erpRows(bundle.products??[],"produtos");
      state.variants=erpRows(bundle.variants??[],"variações");
      state.categories=erpRows(bundle.categories??[],"categorias");
      state.locations=erpRows(bundle.locations??[],"locais");
      // Uma versão anterior do gateway incluía a mensagem HTTP de erro neste campo.
      // Nunca atribuir essa mensagem a state.balances, pois ela não é uma lista.
      if(Array.isArray(bundle.balances)){
        state.balances=bundle.balances;
      }else{
        state.balances=[];
        state.inventoryWarning="O ERP não retornou saldos de estoque em formato válido. Confira o estoque no sistema principal.";
        console.warn("[Fácil Pedido] Resposta de estoque incompatível",bundle.balances);
      }
      state.inventoryWarning ||= bundle.inventory_warning||"";
    }else{
      const [products,variants,categories,locations,balances]=await Promise.all([
        API.request("/products?limit=500"),API.request("/product-variants?limit=500"),API.request("/categories?limit=500"),
        API.request("/stock-locations?limit=500"),API.request("/inventory/balances")
      ]);
      Object.assign(state,{
        products:erpRows(products??[],"produtos"),
        variants:erpRows(variants??[],"variações"),
        categories:erpRows(categories??[],"categorias"),
        locations:erpRows(locations??[],"locais"),
        balances:erpRows(balances??[],"saldos")
      });
    }
    const pendingHealth=API.request("/health").then(h=>{state.health=h;updateTop()}).catch(()=>{});
    const pendingCatalog=loadCatalogState();
    const optionalJobs=[];
    if(canSeeClients()){
      optionalJobs.push((async()=>{const [clients,clientStates]=await Promise.all([
        API.request("/clients?limit=500").catch(()=>[]),
        API.request("/client-management/front/state").catch(()=>[])
      ]);
      state.clients=erpRows(clients??[],"clientes");
      state.clientStates=erpRows(clientStates?.clients??clientStates??[],"dados complementares dos clientes");})());
    }else{state.clients=[];state.clientStates=[]}
    if(canUseSales()){
      optionalJobs.push((async()=>{const [quotes,orders]=await Promise.all([API.request("/quotes").catch(()=>[]),API.request("/sales-orders").catch(()=>[])]);
      state.quotes=erpRows(quotes??[],"orçamentos");state.orders=erpRows(orders??[],"pedidos");})());
    }else{state.quotes=[];state.orders=[]}
    await Promise.all([pendingCatalog,...optionalJobs]);
    for(const product of state.products){const extra=state.catalog.productExtras?.[product.id]||{};for(const field of ["barcode","brand","supplier","material","width_cm","height_cm","depth_cm","warranty_months"]){if(extra[field]!=null)product[field]=extra[field]}}
    state.systemUsers=[];
    if(hasPermission("users.write"))API.request("/users").then(data=>{state.systemUsers=erpRows(data||[],"usuários")}).catch(()=>{});
    if(state.inventoryWarning)toast(state.inventoryWarning,"error");
    saveOfflineSnapshot();
  }catch(e){
    if(!loadOfflineSnapshot())throw e;
    await loadAccess().catch(()=>{});
    toast("ERP offline: catálogo salvo somente para consulta. Não serão gravadas vendas nesta condição.","error");
  }
  state.favorites=getFavorites();
}
function showApp(){
  $("#loginScreen").classList.add("hidden");$("#appShell").classList.remove("hidden");
  updateTop();applyAccessUI();
  const requested=location.hash.replace("#/","");
  go(requested&&document.querySelector(`[data-route="${requested}"]:not(.hidden)`)?requested:defaultRoute());
  loadCommercialDocuments().then(()=>{if(state.route==="inicio")renderInicio()});
  if(new URLSearchParams(location.search).has("pv_product")){loadPvReference();loadPvShowcase()}
  const shared=new URL(location.href).searchParams.get("catalog");
  if(shared){state.presentationIds=shared.split(",").filter(id=>state.products.some(p=>p.id===id));if(state.presentationIds.length)setTimeout(()=>startPresentation(state.presentationIds),150)}
}
function logout(){if(modern.dirty&&state.cart.length&&!confirm("Sair sem salvar as alterações do atendimento?"))return;API.setToken("");state.user=null;state.demo=false;state.cart=[];state.cartMeta=null;state.quotes=[];state.orders=[];state.clients=[];state.products=[];modern.documents=[];modern.cartDocument=null;modern.dirty=false;modern.shares={};modern.policy=null;closeCart();closeModal();$("#appShell").classList.add("hidden");$("#loginScreen").classList.remove("hidden")}
function routeAllowed(route){
  if(state.demo)return true;
  if(["inicio","catalogo"].includes(route))return canReadCatalog();
  if(["catalog-manager","studio","promocoes"].includes(route))return canManageCatalog();
  if(route==="clientes")return canSeeClients();
  if(["orcamentos","pedidos","relatorios","estoque","producao","entregas","financeiro"].includes(route))return canUseSales()||hasPermission("settings.write");
  if(["equipe","auditoria","configuracoes","integracao"].includes(route))return hasPermission("settings.write");
  return true;
}
function go(route){
  route=route||defaultRoute();
  if(!routeAllowed(route)){toast("Seu perfil não possui acesso a esta área.","error");route=defaultRoute()}
  const changedRoute=state.route!==route;if(changedRoute)clearTimeout(window._fpCatalogSearchTimer);state.route=route;location.hash=`#/${state.route}`;$$('.nav-item').forEach(b=>b.classList.toggle("active",b.dataset.route===state.route));$("#sidebar").classList.remove("open");render();if(changedRoute)window.scrollTo({top:0,behavior:"auto"})
}
function pageHead(eyebrow,title,desc,actions=""){return `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${desc}</p></div><div class="actions">${actions}</div></div>`}
function priceDisplay(p){
  const current=promoPrice(p),promo=activePromo(p),clientKey=state.selectedClient?`${state.selectedClient.id}:${p.id}`:null,clientV=clientKey?state.clientPriceCache[clientKey]:null;
  const cs=state.selectedClient?state.clientStates.find(c=>(c.server?.id||c.id)===state.selectedClient.id):null,row=cs?.price_table?.find(r=>[p.id,p.code,p.name].some(ref=>norm(ref)===norm(r.product_ref))||norm(r.product_name)===norm(p.name));
  const resolved=row?Number(row.price):clientV,final=resolved??current;return {base:Number(p.price||0),final,promo,client:resolved!=null,source:row?'client_price_table':'product_default'}
}
function productCard(p){
  if(p._pvReference)return pvReferenceCard(p);
  const pres=presentationFor(p.id),fav=state.favorites.has(p.id),a=available(p),pr=priceDisplay(p),status=pres.status||"Ativo";
  return `<article class="product-card">
    <button class="favorite ${fav?"active":""}" data-action="favorite" data-id="${esc(p.id)}">${fav?"♥":"♡"}</button>
    <div class="product-photo" data-action="detail" data-id="${esc(p.id)}"><img loading="lazy" decoding="async" src="${photoFor(p)}" alt="${esc(p.name)}"></div>
    <div class="product-card-body">
      <div class="product-meta"><span class="chip">${esc(categoryName(p))}</span><span class="chip ${stockClass(p)}">${state.inventoryWarning?"Consultar saldo":a>0?`${a} disponível`:"Sem estoque"}</span>${status!=="Ativo"?`<span class="chip violet">${esc(status)}</span>`:""}</div>
      <h3>${esc(pres.title||p.name)}</h3><small class="product-sub">${esc(p.code||"Sem código")} · Produto oficial</small><div class="product-sub">${esc(pres.subtitle||[p.color,p.size].filter(Boolean).join(" • ")||p.code)}</div>
      ${pr.final<pr.base?`<div class="old-price">${fmtBRL(pr.base)}</div>`:""}<div class="product-price">${fmtBRL(pr.final)}</div><small class="product-sub">${pr.client?"Tabela do cliente":"Preço padrão / promoção"}</small><small class="modern-cash-price">À vista: ${fmtBRL(pr.final*(1-Number(pricePolicy().pixDiscount||0)/100))} · simulação</small>
      <div class="product-actions"><button class="secondary-btn" data-action="detail" data-id="${esc(p.id)}">Ver produto</button><button class="primary-btn" data-action="add" data-id="${esc(p.id)}">Adicionar</button></div>
    </div></article>`;
}
function catalogReadiness(p){
  const photos=mediaFor(p.id),pres=presentationFor(p.id);
  const hasPhoto=photos.length>0||!!pvAutoPhoto(p),hasDescription=!!String(pres.description||p.description||"").trim();
  const hasTitle=!!String(pres.title||p.name||"").trim();
  const score=[hasPhoto,hasDescription,hasTitle].filter(Boolean).length/3*100;
  const published=pres.published===true;
  let status="incomplete";
  if(!hasPhoto)status="no-photo";
  else if(score>=100)status=published?"published":"ready";
  return {photos:photos.length,score:Math.round(score),published,status};
}
function catalogManagerRows(){
  let rows=state.products.filter(p=>p.active!==false);
  const q=norm(state.catalogManagerQuery);
  if(q)rows=rows.filter(p=>norm([p.code,p.name,categoryName(p),p.color,p.size].join(" ")).includes(q));
  if(state.catalogManagerFilter!=="all")rows=rows.filter(p=>catalogReadiness(p).status===state.catalogManagerFilter);
  return rows.sort((a,b)=>String(a.name).localeCompare(String(b.name),"pt-BR"));
}
function catalogStatusLabel(status){
  return {"no-photo":"Sem foto",incomplete:"Incompleto",ready:"Pronto para publicar",published:"Publicado"}[status]||status;
}
async function setCatalogPublished(productId,published){
  if(state.demo){
    state.catalog.presentation[productId]={...(presentationFor(productId)),published};
    logHistory(published?"PUBLICAR":"OCULTAR","Produto",state.products.find(p=>p.id===productId)?.name||productId);
    await saveCatalogState();return;
  }
  const result=await API.request(`/catalog-management/products/${encodeURIComponent(productId)}/publication`,{
    method:"POST",body:JSON.stringify({published})
  });
  state.catalog=result.payload||state.catalog;state.catalogRevision=result.revision||state.catalogRevision;ensureCatalog();
}
function managerDashboardHtml(){
  ensureCatalog();
  const ops=state.catalog.operations;
  const revenue=state.orders.reduce((a,o)=>a+Number(o.total||0),0);
  const openQuotes=state.quotes.filter(q=>!["Aprovado","Perdido"].includes(q.status)).length;
  const pendingProduction=ops.production.filter(x=>x.status!=="Finalizado").length;
  const pendingDelivery=ops.deliveries.filter(x=>x.status!=="Concluída").length;
  const receivable=ops.receivables.filter(x=>x.status!=="Pago").reduce((a,x)=>a+Number(x.amount||0),0);
  const low=state.products.filter(p=>available(p)<=Number(p.min_stock||0)).length;
  return `${roleDashboardHtml()}<div class="zero-banner"><strong>Base inicial zerada:</strong> produtos, estoque, preços, pedidos e financeiro começam em R$ 0,00 / 0. Cadastre os móveis e informe preço de venda, custo e estoque conforme a operação real.</div>
  <div class="ops-dashboard">
    <div class="ops-kpi"><small>Faturamento</small><strong>${fmtBRL(revenue)}</strong><em>Pedidos cadastrados</em></div>
    <div class="ops-kpi"><small>Orçamentos abertos</small><strong>${openQuotes}</strong><em>Follow-up comercial</em></div>
    <div class="ops-kpi"><small>Produção pendente</small><strong>${pendingProduction}</strong><em>Ordens em andamento</em></div>
    <div class="ops-kpi"><small>Entregas pendentes</small><strong>${pendingDelivery}</strong><em>Frete e montagem</em></div>
    <div class="ops-kpi"><small>A receber</small><strong>${fmtBRL(receivable)}</strong><em>Financeiro</em></div>
    <div class="ops-kpi"><small>Estoque crítico</small><strong>${low}</strong><em>Itens no mínimo</em></div>
  </div>
  <div class="dashboard-quick">${hasPermission("settings.write")?`<button class="primary-btn" data-action="open-product-form">＋ Cadastrar móvel</button>`:""}<button class="secondary-btn" data-action="new-client">＋ Cadastrar cliente</button><button class="secondary-btn" data-route="estoque">Estoque</button><button class="secondary-btn" data-route="producao">Produção</button><button class="secondary-btn" data-route="financeiro">Financeiro</button><button class="secondary-btn" data-route="entregas">Entregas</button></div>`;
}
function renderHomeProducts(){
  const root=$('#homeProducts');if(!root||state.route!=='inicio')return;
  const official=officialCatalogProducts();
  const references=pvShowcaseRows(),all=[...official,...references],pageSize=12;
  const pages=Math.max(1,Math.ceil(all.length/pageSize));
  modern.homePage=clamp(Number(modern.homePage)||1,1,pages);
  const start=(modern.homePage-1)*pageSize,rows=all.slice(start,start+pageSize);
  const loading=!state.demo&&!pvShowcase.ready&&!pvShowcase.error;
  root.innerHTML=`<div class="panel-head"><div><h2>Produtos para o atendimento</h2><p class="help">Produtos oficiais e referências com fotos, disponíveis sem sair da tela inicial.</p></div><button class="text-btn" data-action="home-open-catalog">Ver catálogo completo →</button></div>
    ${loading?'<p class="modern-home-load-status" role="status">Carregando as fotos e referências do catálogo…</p>':''}
    ${pvShowcase.error?`<div class="modern-home-load-status error" role="status"><span>Não foi possível carregar as referências com fotos. Os produtos oficiais continuam disponíveis.</span><button class="secondary-btn" data-action="home-retry-products">Tentar novamente</button></div>`:''}
    <p class="result-meta" id="homeProductsCount">Mostrando ${rows.length?start+1:0}–${start+rows.length} de ${all.length} opções · ${official.length} produto(s) oficial(is) · ${references.length} referência(s)</p>
    <div class="catalog-grid modern-home-products">${rows.map(productCard).join('')||'<div class="empty-state">Nenhum produto disponível no momento.</div>'}</div>
    <div class="modern-home-pagination"><button class="secondary-btn" data-action="home-page" data-page="${modern.homePage-1}" ${modern.homePage<=1?'disabled':''}>← Anterior</button><span>Página ${modern.homePage} de ${pages}</span><button class="secondary-btn" data-action="home-page" data-page="${modern.homePage+1}" ${modern.homePage>=pages?'disabled':''}>Próxima →</button></div>`;
}
function renderInicio(){
  const quotes=state.quotes.filter(q=>!q.converted_order_id&&q.status!=='Perdido'),drafts=modern.documents.filter(q=>q.kind==='draft');
  const confirmed=state.orders.filter(o=>['Confirmado','Produção','Pronto','Em rota','Entregue'].includes(o.status));
  $('#appContent').innerHTML=`<section class="modern-welcome"><div><span class="eyebrow">FÁCIL PEDIDO COMERCIAL V5</span><h1>Seu próximo atendimento começa aqui.</h1><p>Produtos, condições e propostas organizados em um só lugar.</p></div><button class="primary-btn" data-action="new-commercial-cart">＋ Novo atendimento</button></section><div class="grid modern-home-stats"><div class="stat-card"><small>Produtos oficiais</small><strong>${state.products.length}</strong><em>Cadastro do ERP</em></div><div class="stat-card"><small>Propostas em aberto</small><strong>${quotes.length}</strong><em>Sem contar as convertidas</em></div><div class="stat-card"><small>Rascunhos salvos</small><strong>${drafts.length}</strong><em>Retome de onde parou</em></div><div class="stat-card"><small>Pedidos confirmados</small><strong>${fmtBRL(confirmed.reduce((n,o)=>n+Number(o.total||0),0))}</strong><em>Rascunhos não entram neste valor</em></div></div>${state.inventoryWarning?`<p class="quote-notice" role="status">${esc(state.inventoryWarning)}</p>`:''}<div class="modern-home-links"><button class="secondary-btn" data-action="show-official-products">Explorar produtos oficiais</button><button class="secondary-btn" data-route="orcamentos">Rascunhos e propostas</button><button class="secondary-btn" data-route="clientes">Clientes e condições</button><button class="secondary-btn" data-action="show-references">Consultar referências</button></div><section class="panel modern-home-catalog" id="homeProducts"></section><section class="panel modern-recent"><div class="panel-head"><h2>Atendimentos recentes</h2><button class="text-btn" data-route="orcamentos">Ver todos →</button></div>${modern.documents.filter(d=>['quote','draft'].includes(d.kind)).slice(0,5).map(d=>`<button class="modern-recent-row" data-action="open-commercial-document" data-id="${esc(d.id)}"><strong>${esc(d.code)}</strong><span>${esc(d.client_name||'Cliente a definir')}</span><span>${esc(d.status)} · v${d.revision}</span><b>${fmtBRL(d.total)}</b></button>`).join('')||'<p class="help">Os rascunhos salvos aparecerão aqui.</p>'}</section>`;
  renderHomeProducts();
  if(!pvShowcase.ready&&!pvShowcase.loading&&!pvShowcase.error&&!state.demo){
    void loadPvReference();void loadPvShowcase();
  }
}
function officialCatalogProducts(){
  return state.products.filter(p=>p.active!==false&&presentationFor(p.id).published!==false);
}
function catalogProductPool(source=state.filters.source||'all'){
  const official=officialCatalogProducts(),references=source==='official'?[]:pvShowcaseRows();
  return source==='references'?references:[...official,...references];
}
function catalogCategoryLabel(product){return String(categoryName(product)||'').trim()||'Sem categoria'}
function catalogCategoryKey(label){return norm(label).replace(/\s+/g,' ')}
function selectedCategoryLabel(value){
  if(!value)return '';
  if(value==='__uncategorized__')return 'Sem categoria';
  if(value.startsWith('PV::'))return value.slice(4).trim()||'Sem categoria';
  const category=state.categories.find(c=>String(c.id)===value);
  if(String(category?.name||'').trim())return String(category.name).trim();
  const product=state.products.find(p=>String(p.category_id||'')===value);
  return product?catalogCategoryLabel(product):'';
}
function catalogCategories(pool){
  const groups=new Map();
  for(const product of pool){
    const name=catalogCategoryLabel(product),key=catalogCategoryKey(name);
    if(!groups.has(key))groups.set(key,{id:String(product.category_id||'__uncategorized__'),name,count:0});
    groups.get(key).count++;
  }
  return [...groups.values()].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));
}
function reconcileCatalogCategory(categories){
  const selected=String(state.filters.category||'');if(!selected)return;
  if(selected.startsWith('PV::')&&state.filters.source!=='official'&&!pvShowcase.ready)return;
  const name=catalogCategoryKey(selectedCategoryLabel(selected));
  const match=categories.find(c=>c.id===selected||(name&&catalogCategoryKey(c.name)===name));
  state.filters.category=match?.id||'';
}
function refreshCatalogPreservingFocus(){
  const active=document.activeElement,restore=active?.closest?.('#appContent')&&active.id;
  const start=active?.selectionStart,end=active?.selectionEnd;
  renderCatalogo();
  const target=restore&&document.getElementById(restore);
  if(target){target.focus({preventScroll:true});if(typeof start==='number'){try{target.setSelectionRange(start,end)}catch{}}}
}
function filteredProducts(){
  let rows=catalogProductPool();
  const q=norm(state.filters.q);if(q)rows=rows.filter(p=>norm([p.name,p.code,p.color,p.size,categoryName(p),presentationFor(p.id).subtitle,(presentationFor(p.id).tags||[]).join(" ")].join(" ")).includes(q));
  if(state.filters.category){
    const selected=String(state.filters.category),label=catalogCategoryKey(selectedCategoryLabel(selected));
    rows=rows.filter(p=>String(p.category_id||'__uncategorized__')===selected||(label&&catalogCategoryKey(catalogCategoryLabel(p))===label));
  }
  if(state.filters.stock==="available")rows=rows.filter(p=>!p._pvReference&&available(p)>0);
  if(state.filters.stock==="critical")rows=rows.filter(p=>!p._pvReference&&available(p)<=Number(p.min_stock||2));
  if(state.filters.favorites)rows=rows.filter(p=>state.favorites.has(p.id));
  if(state.filters.sort==="priceAsc")rows.sort((a,b)=>promoPrice(a)-promoPrice(b));
  if(state.filters.sort==="priceDesc")rows.sort((a,b)=>promoPrice(b)-promoPrice(a));
  if(state.filters.sort==="name")rows.sort((a,b)=>String(a.name).localeCompare(String(b.name),"pt-BR"));
  return rows;
}
function renderCatalogo(){
  if(!['all','official','references'].includes(state.filters.source))state.filters.source='all';
  const categories=catalogCategories(catalogProductPool());reconcileCatalogCategory(categories);
  const loading=state.filters.source!=='official'&&!state.demo&&!pvShowcase.ready&&!pvShowcase.error;
  const all=filteredProducts(),pages=Math.max(1,Math.ceil(all.length/CFG.PAGE_SIZE));state.filters.page=clamp(state.filters.page,1,pages);const start=(state.filters.page-1)*CFG.PAGE_SIZE,rows=all.slice(start,start+CFG.PAGE_SIZE);
  $("#appContent").innerHTML=pageHead("CATÁLOGO","Encontre o produto ideal",state.selectedClient?`Preço personalizado para ${state.selectedClient.name}.`:"Selecione um cliente para aplicar tabela de preço específica.",`<button class="primary-btn" data-action="open-product-form">＋ Cadastrar móvel</button><button class="secondary-btn" data-action="toggle-favorites">${state.filters.favorites?"Ver todos":"Favoritos"}</button>${canManageCatalog()?`<button class="primary-btn" data-route="studio">＋ Produto / fotos</button>`:""}`)+`
  <div class="catalog-layout"><aside class="filter-panel">
    <div class="filter-section"><strong>Cliente atual</strong>${state.selectedClient?`<span class="chip green">${esc(state.selectedClient.name)}</span><button class="ghost-btn full" style="margin-top:8px" data-action="clear-client">Trocar cliente</button>`:`<button class="primary-btn full" data-route="clientes">Selecionar cliente</button>`}</div>
    <div class="filter-section"><strong>Categorias</strong><label><input type="radio" name="cat" value="" ${!state.filters.category?"checked":""}> Todas</label>${categories.map(c=>`<label><input type="radio" name="cat" value="${esc(c.id)}" ${state.filters.category===c.id?"checked":""}> ${esc(c.name)}</label>`).join("")}</div>
    <div class="filter-section"><strong>Estoque</strong><label><input type="radio" name="stock" value="all" ${state.filters.stock==="all"?"checked":""}> Todos</label><label><input type="radio" name="stock" value="available" ${state.filters.stock==="available"?"checked":""}> Em estoque</label><label><input type="radio" name="stock" value="critical" ${state.filters.stock==="critical"?"checked":""}> Crítico</label></div>
    <div class="filter-section"><strong>Venda rápida</strong><button class="ghost-btn full" data-action="scan">▥ Ler código</button></div>
  </aside><div>
    <div class="toolbar"><select id="catalogSource" aria-label="Origem dos produtos"><option value="all">Oficiais e referências</option><option value="official">Produtos oficiais</option><option value="references">Referências de catálogo</option></select><input class="grow" id="catalogSearch" value="${esc(state.filters.q)}" placeholder="Sofá cinza 2,30, SKU, código..."><select id="catalogSort"><option value="relevance">Mais relevantes</option><option value="name">Nome A–Z</option><option value="priceAsc">Menor preço</option><option value="priceDesc">Maior preço</option></select></div>
    ${loading?'<p class="modern-home-load-status" role="status">Carregando produtos e fotos das referências…</p>':''}
    ${state.filters.source!=='official'&&pvShowcase.error?'<div class="modern-home-load-status error" role="status"><span>Não foi possível carregar as referências.</span><button class="secondary-btn" data-action="retry-catalog-references">Tentar novamente</button></div>':''}
    ${pvShowcase.ready?`<div class="pv-showcase-banner"><div><strong>Catálogo Porto Velho integrado: ${pvShowcaseRows().length} referências com fotos</strong><span>Referências visuais para consulta. O filtro Produtos oficiais mostra apenas o cadastro do ERP; referências não podem gerar pedido.</span></div><button class="secondary-btn" data-route="catalog-manager">Gerenciar no ERP</button></div>`:""}
    <div class="result-meta">Mostrando ${rows.length?start+1:0}–${start+rows.length} de ${all.length} opção(ões) • ${state.products.length} produto(s) cadastrado(s) no ERP</div>
    <div class="catalog-grid">${rows.map(productCard).join("")||`<div class="empty-state">${loading?"Carregando produtos…":"Nenhum produto encontrado para estes filtros."}<button class="secondary-btn" data-action="clear-catalog-filters">Mostrar todos os produtos</button></div>`}</div>
    <div class="pagination">${Array.from({length:pages},(_,i)=>i+1).slice(Math.max(0,state.filters.page-3),Math.max(5,state.filters.page+2)).map(p=>`<button class="${p===state.filters.page?"active":""}" data-action="page" data-page="${p}">${p}</button>`).join("")}</div>
  </div></div>`;$("#catalogSort").value=state.filters.sort;$("#catalogSource").value=state.filters.source;
  if(state.filters.source!=='official'&&!pvShowcase.ready&&!pvShowcase.loading&&!pvShowcase.error&&!state.demo){void loadPvReference();void loadPvShowcase()}
}
function crmStage(client){ensureCatalog();return state.catalog.crm[client.id]?.stage||"Novo contato"}
function renderClientes(){
  const q=norm(state.filters.q),rows=state.clients.filter(c=>!q||norm([c.name,c.document,c.email,c.phone].join(" ")).includes(q));
  const stages=["Novo contato","Orçamento","Negociação","Cliente","Perdido"];
  $("#appContent").innerHTML=pageHead("CLIENTES & CRM","Relacionamento comercial 360º","Tabela de preço, histórico, limite, orçamentos e etapa comercial no mesmo lugar.",`<button class="primary-btn" data-action="new-client">＋ Novo cliente</button>`)+`
    <div class="toolbar"><input id="clientSearch" class="grow" value="${esc(state.filters.q)}" placeholder="Buscar nome, CPF/CNPJ, telefone..."><button class="secondary-btn" data-action="client-list-mode">Cartões</button></div>
    <div class="client-grid">${rows.map(c=>{const crm=state.catalog.crm[c.id]||{};return `<div class="client-card"><div class="client-card-head"><div class="client-avatar">${initials(c.name)}</div><div><strong>${esc(c.name)}</strong><small>${esc(c.document||"Sem documento")}</small></div></div><small>${esc(c.phone||"")} · ${esc(c.email||"")}</small><small>Limite: ${fmtBRL(c.credit_limit)}</small><div class="product-meta" style="margin-top:8px"><span class="chip blue">${esc(crm.stage||"Novo contato")}</span>${state.selectedClient?.id===c.id?`<span class="chip green">Cliente atual</span>`:""}</div><div class="actions"><button class="primary-btn" data-action="select-client" data-id="${esc(c.id)}">Usar no pedido</button><button class="secondary-btn" data-action="client-360" data-id="${esc(c.id)}">Abrir 360º</button><button class="text-btn" data-action="customer-statement" data-id="${esc(c.id)}">Extrato oficial</button></div></div>`}).join("")||`<div class="empty-state">Nenhum cliente.</div>`}</div>
    <div class="panel" style="margin-top:14px"><div class="panel-head"><div><h3>Pipeline comercial</h3><small>Arraste mentalmente o processo; use os botões para avançar a etapa.</small></div></div><div class="pipeline">${stages.map(stage=>`<div class="pipeline-col"><div class="pipeline-head"><span>${stage}</span><b>${state.clients.filter(c=>crmStage(c)===stage).length}</b></div>${state.clients.filter(c=>crmStage(c)===stage).map(c=>`<div class="crm-card"><strong>${esc(c.name)}</strong><small>${esc(state.catalog.crm[c.id]?.notes||"Sem observações")}</small><div class="actions"><button class="secondary-btn" data-action="advance-crm" data-id="${esc(c.id)}">Avançar</button></div></div>`).join("")}</div>`).join("")}</div></div>`;
}
function renderOrcamentos(){
  const f=modern.documentFilter,all=[...modern.documents.filter(d=>['quote','draft'].includes(d.kind)),...state.quotes.filter(q=>!q.commercial_document),...(state.catalog.quoteMeta.preliminary||[])];
  const docs=all.filter(d=>(!f.q||norm([d.code,d.client_name,d.owner_id].join(' ')).includes(norm(f.q)))&&(!f.status||d.status===f.status)&&(!f.kind||d.kind===f.kind)&&(!f.start||String(d.created_at||'').slice(0,10)>=f.start)&&(!f.end||String(d.created_at||'').slice(0,10)<=f.end));
  $('#appContent').innerHTML=pageHead('ATENDIMENTOS','Rascunhos e propostas','Retome documentos salvos, confira versões e preserve as condições da negociação.',`<button class="primary-btn" data-action="new-commercial-cart">＋ Novo atendimento</button>`)+`<div class="modern-filters"><label>Buscar<input id="documentSearch" placeholder="Código, cliente ou responsável" value="${esc(f.q)}"></label><label>Tipo<select id="documentKind"><option value="">Todos</option><option value="draft" ${f.kind==='draft'?'selected':''}>Rascunhos</option><option value="quote" ${f.kind==='quote'?'selected':''}>Propostas</option></select></label><label>Etapa<select id="documentStatus"><option value="">Todas</option>${['Rascunho','Pré-orçamento','Enviado','Negociação','Aprovado','Convertido','Perdido'].map(s=>`<option ${f.status===s?'selected':''}>${s}</option>`).join('')}</select></label><label>De<input id="documentStart" type="date" value="${esc(f.start)}"></label><label>Até<input id="documentEnd" type="date" value="${esc(f.end)}"></label></div>${modern.documentsError?`<p class="quote-notice">${esc(modern.documentsError)} <button class="text-btn" data-action="commercial-reload">Tentar novamente</button></p>`:''}<div class="table-wrap"><table><thead><tr><th>Documento</th><th>Cliente</th><th>Etapa</th><th>Validade</th><th>Total</th><th>Ações</th></tr></thead><tbody>${docs.map(d=>`<tr><td><strong>${esc(d.code||d.id)}</strong><small class="modern-block">${d.kind==='draft'?'Rascunho':d.commercial_document?'Proposta':'Registro anterior'} · ${d.revision?'versão '+d.revision:''}</small></td><td>${esc(d.client_name||'A definir')}</td><td><span class="chip ${d.status==='Convertido'?'green':'blue'}">${esc(d.status)}</span></td><td>${esc(d.valid_until||'A combinar')}</td><td><strong>${fmtBRL(d.total)}</strong></td><td><div class="actions"><button class="secondary-btn" data-action="${d.converted_order_id?'duplicate-commercial-document':'open-commercial-document'}" data-id="${esc(d.id)}">${d.converted_order_id?'Nova negociação':'Reabrir'}</button><button class="text-btn" data-action="duplicate-commercial-document" data-id="${esc(d.id)}">Duplicar</button><button class="text-btn" data-action="print-quote" data-id="${esc(d.id)}">PDF</button>${d.commercial_document?`<button class="text-btn" data-action="document-history" data-id="${esc(d.id)}">Versões</button>${d.kind==='quote'?`<button class="text-btn" data-action="share-document" data-id="${esc(d.id)}">Link / QR</button><button class="text-btn" data-action="revoke-document-shares" data-id="${esc(d.id)}">Revogar links</button>`:''}`:''}${d.kind!=='draft'&&!d.converted_order_id?`<button class="success-btn" data-action="quote-to-order" data-id="${esc(d.id)}">Criar pedido</button>${d.commercial_document?`<button class="text-btn" data-action="document-status" data-id="${esc(d.id)}">Etapa</button>`:''}`:''}</div></td></tr>`).join('')||'<tr><td colspan="6"><div class="empty-state">Nenhum documento para estes filtros.</div></td></tr>'}</tbody></table></div><section class="panel modern-recent"><h3>Solicitações de devolução</h3><p class="help">Solicitações comerciais; sem crédito, estorno ou movimentação automática de estoque.</p>${modern.documents.filter(d=>d.kind==='return_request').map(d=>`<div class="modern-recent-row"><strong>${esc(d.code)}</strong><span>${esc(d.order_code)}</span><span>${esc(d.status)}</span><span>${esc(d.reason)}</span></div>`).join('')||'<p class="help">Nenhuma solicitação registrada.</p>'}</section>`;
}
function renderPedidos(){
  $('#appContent').innerHTML=pageHead('PEDIDOS','Acompanhe cada etapa','Criar rascunho é diferente de confirmar venda. A integração exige condições completas.',`<button class="primary-btn" data-action="new-commercial-cart">＋ Novo atendimento</button>`)+`<div class="table-wrap"><table><thead><tr><th>Pedido e origem</th><th>Cliente</th><th>Etapa</th><th>Condição</th><th>Total</th><th>Ações</th></tr></thead><tbody>${state.orders.map(o=>`<tr><td><strong>${esc(o.code||o.id)}</strong><small class="modern-block">${esc(o.source_document_code||'Sem proposta de origem')}</small></td><td>${esc(o.client_name)}</td><td><span class="chip blue">${esc(o.status)}</span></td><td>${esc(o.payment_method||'A combinar')}</td><td>${fmtBRL(o.total)}</td><td><div class="actions"><button class="secondary-btn" data-action="order-detail" data-id="${esc(o.id)}">Detalhes</button>${o.status==='Aguardando aprovação'&&hasPermission('settings.write')?`<button class="secondary-btn" data-action="approve-order" data-id="${esc(o.id)}">Revisar aprovação</button>`:''}${o.status==='Rascunho'?`<button class="secondary-btn" data-action="confirm-order" data-id="${esc(o.id)}">Confirmar no ERP</button>`:''}${['Confirmado','Entregue','Em rota'].includes(o.status)?`<button class="text-btn" data-action="return-request" data-id="${esc(o.id)}">Solicitar devolução</button>`:''}</div></td></tr>`).join('')||'<tr><td colspan="6"><div class="empty-state">Nenhum pedido. Comece por uma proposta.</div></td></tr>'}</tbody></table></div>`;
}
function renderCatalogManager(){
  if(!canManageCatalog()){go("catalogo");return}
  const all=state.products.filter(p=>p.active!==false),stats={
    noPhoto:all.filter(p=>catalogReadiness(p).status==="no-photo").length,
    incomplete:all.filter(p=>catalogReadiness(p).status==="incomplete").length,
    ready:all.filter(p=>catalogReadiness(p).status==="ready").length,
    published:all.filter(p=>catalogReadiness(p).status==="published").length
  };
  const rows=catalogManagerRows();
  $("#appContent").innerHTML=pageHead("GESTÃO DE CATÁLOGO","Fotos e publicação dos produtos","Área operacional para quem cuida do catálogo. Não exibe custo, financeiro, RH ou fornecedores.",
    `${hasPermission("settings.write")?`<button class="secondary-btn" data-action="import-products">⇧ Importar Excel/CSV</button>`:""}<button class="secondary-btn" data-action="bulk-upload">⇧ Fotos em lote</button><button class="secondary-btn" data-action="pv-auto-link">Vincular fotos Porto Velho</button><button class="secondary-btn" data-route="studio">Fotos & Studio</button><button class="primary-btn" data-action="open-product-form">＋ Cadastrar móvel</button><input id="productImportFile" type="file" accept=".csv,.xlsx,.xls" class="hidden">`)+`
    <div class="catalog-role-banner">Este painel trabalha sobre os mesmos produtos do ERP. Fotos e apresentação comercial são complementares ao cadastro técnico; estoque, cliente e pedidos continuam no banco principal.</div>
    <div class="catalog-manager-summary">
      <div class="summary-box"><small>Total de produtos</small><strong>${all.length}</strong></div>
      <div class="summary-box"><small>Sem foto</small><strong>${stats.noPhoto}</strong></div>
      <div class="summary-box"><small>Incompletos</small><strong>${stats.incomplete}</strong></div>
      <div class="summary-box"><small>Prontos</small><strong>${stats.ready}</strong></div>
      <div class="summary-box"><small>Publicados</small><strong>${stats.published}</strong></div>
    </div>
    <div class="catalog-manager-toolbar">
      <input id="catalogManagerSearch" value="${esc(state.catalogManagerQuery)}" placeholder="Buscar código, produto, categoria, cor...">
      <div class="status-tabs">
        ${[["all","Todos"],["no-photo","Sem foto"],["incomplete","Incompletos"],["ready","Prontos"],["published","Publicados"]].map(([v,l])=>`<button class="status-tab ${state.catalogManagerFilter===v?"active":""}" data-action="catalog-filter" data-filter="${v}">${l}</button>`).join("")}
      </div>
      <input id="bulkCatalogInput" type="file" accept="image/*" multiple hidden>
    </div>
    <div class="catalog-product-list">${rows.map(p=>{const r=catalogReadiness(p),src=mediaFor(p.id)[0]||pvAutoPhoto(p);return `
      <div class="catalog-product-row">
        <div class="catalog-manager-thumb">${src?`<img src="${safePhotoUrl(src)}" alt="${esc(p.name)}">`:`<div class="catalog-manager-empty-photo">SEM<br>FOTO</div>`}</div>
        <div><strong>${esc(p.name)}</strong><small>${esc(p.code)} • ${esc(categoryName(p))}</small><div class="completeness"><span style="width:${r.score}%"></span></div><small>${r.score}% completo</small></div>
        <div class="optional-col"><strong>${r.photos}</strong><small>foto(s)</small></div>
        <div class="optional-col"><span class="chip ${r.status==="published"?"green":r.status==="no-photo"?"red":r.status==="ready"?"blue":"orange"}">${catalogStatusLabel(r.status)}</span></div>
        <div class="optional-col"><strong>${available(p)}</strong><small>estoque disponível</small></div>
        <div class="actions row-actions"><button class="secondary-btn" data-action="catalog-edit" data-id="${esc(p.id)}">Editar</button>${canPublishCatalog()&&r.status==="ready"?`<button class="success-btn" data-action="catalog-publish" data-id="${esc(p.id)}">Publicar</button>`:""}${canPublishCatalog()&&r.published?`<button class="secondary-btn" data-action="catalog-unpublish" data-id="${esc(p.id)}">Ocultar</button>`:""}</div>
      </div>`}).join("")||`<div class="empty-state">Nenhum produto neste filtro.</div>`}</div>`;
}
function renderStudio(){
  if(!canManageCatalog()){go("catalogo");return}
  const selected=state.studioProductId||state.products[0]?.id||"";state.studioProductId=selected;const p=state.products.find(x=>x.id===selected),pres=p?presentationFor(p.id):{},photos=p?mediaFor(p.id):[],vars=p?state.variants.filter(v=>v.product_id===p.id):[];
  $("#appContent").innerHTML=pageHead("STUDIO DE PRODUTOS","Conteúdo comercial e mídia","Produto técnico continua no ERP; aqui você controla como ele aparece para o vendedor.",`${hasPermission("settings.write")?`<button class="secondary-btn" data-action="new-product">＋ Produto no ERP</button>`:""}<button class="primary-btn" data-action="save-studio">Salvar catálogo</button>`)+`
  <div class="catalog-role-banner">Selecione um produto do ERP, envie fotos, defina a capa (primeira foto), preencha a descrição e clique em <strong>Salvar catálogo</strong>. Para divulgar no site, marque <strong>Publicado</strong>. Até 12 fotos por produto.</div><div class="studio-layout"><div class="panel"><div class="toolbar"><select id="studioProductSelect" class="grow">${state.products.map(x=>`<option value="${esc(x.id)}" ${x.id===selected?"selected":""}>${esc(x.code)} — ${esc(x.name)}</option>`).join("")}</select></div>${p?`
    <div class="form-grid">
      <div class="field full"><label>Nome comercial</label><input id="studioTitle" value="${esc(pres.title||p.name)}"></div>
      <div class="field full"><label>Subtítulo</label><input id="studioSubtitle" value="${esc(pres.subtitle||[p.color,p.size].filter(Boolean).join(" • "))}"></div>
      <div class="field"><label>Status comercial</label><select id="studioStatus">${["Ativo","Novo","Mais vendido","Oferta","Últimas unidades","Lançamento","Exclusivo","Sob encomenda"].map(x=>`<option ${x===(pres.status||"Ativo")?"selected":""}>${x}</option>`).join("")}</select></div>
      <div class="field"><label>Destaque na home</label><select id="studioFeatured"><option value="false">Não</option><option value="true">Sim</option></select></div>
      <div class="field"><label>Publicação</label>${canPublishCatalog()?`<select id="studioPublished"><option value="true">Publicado</option><option value="false">Rascunho / oculto</option></select>`:`<input value="${pres.published===true?"Publicado":"Rascunho"}" disabled><input id="studioPublished" type="hidden" value="${String(pres.published===true)}">`}</div>
      <div class="field"><label>Garantia</label><input id="studioWarranty" value="${esc(pres.warranty||"12 meses")}"></div>
      <div class="field full"><label>Descrição comercial</label><textarea id="studioDescription">${esc(pres.description||p.description||"")}</textarea></div>
      <div class="field full"><label>Destaques / benefícios</label><input id="studioHighlights" value="${esc((pres.highlights||[]).join(", "))}" placeholder="estrutura reforçada, fácil abertura, tecido premium"></div>
      <div class="field full"><label>Tags</label><input id="studioTags" value="${esc((pres.tags||[]).join(", "))}"></div>
    </div>
    <div style="margin-top:18px"><div class="panel-head"><div><h3>Galeria principal</h3><small>Até ${CFG.MAX_PHOTOS_PER_PRODUCT} imagens • arraste para reorganizar</small></div></div><div class="dropzone"><strong>Adicionar fotos reais</strong><p class="help">Escolha várias imagens ou, no celular, use a câmera. A primeira imagem é a capa.</p><div class="actions" style="justify-content:center"><label class="primary-btn" style="cursor:pointer">Escolher fotos<input id="studioPhotoInput" type="file" accept="image/*" multiple hidden></label><label class="secondary-btn" style="cursor:pointer">Tirar foto<input id="studioCameraInput" type="file" accept="image/*" capture="environment" hidden></label></div></div><div class="media-grid">${photos.map((src,i)=>`<div class="media-item" draggable="true" data-media-index="${i}"><img src="${safePhotoUrl(src)}">${i===0?`<span class="cover-tag">CAPA</span>`:""}<div class="media-tools"><label class="media-replace-btn" title="Trocar esta foto">Trocar<input type="file" accept="image/jpeg,image/png,image/webp" data-replace-photo="${i}" hidden></label><button data-action="photo-cover" data-index="${i}" title="Definir como capa">★</button><button data-action="photo-left" data-index="${i}" title="Mover para esquerda">‹</button><button data-action="photo-right" data-index="${i}" title="Mover para direita">›</button><button class="media-delete-btn" data-action="remove-photo" data-index="${i}" title="Excluir esta foto do produto" aria-label="Excluir foto ${i+1}">Excluir foto</button></div></div>`).join("")||`<div class="empty-state">Sem fotos.</div>`}</div></div>
    ${pvStudioControls(p)}
     <div style="margin-top:18px"><div class="panel-head"><div><h3>Variações</h3><small>Cor / tamanho / SKU / estoque</small></div></div><div class="table-wrap"><table><thead><tr><th>SKU</th><th>Cor</th><th>Tamanho</th><th>Estoque</th><th>Preço</th><th>Mídia</th></tr></thead><tbody>${vars.map(v=>`<tr><td>${esc(v.sku)}</td><td>${esc(v.color||"—")}</td><td>${esc(v.size||"—")}</td><td>${available(p,v.id)}</td><td>${fmtBRL(v.price||p.price)}</td><td><button class="secondary-btn" data-action="variant-media" data-id="${esc(v.id)}">${mediaForVariant(p.id,v.id).length} foto(s)</button></td></tr>`).join("")||`<tr><td colspan="6">Sem variações.</td></tr>`}</tbody></table></div></div>
    `:`<div class="empty-state">Cadastre produtos no ERP.</div>`}</div>
    <aside class="panel studio-side">${p?`<div class="panel-head"><div><h3>Prévia</h3><small>Como aparece no catálogo</small></div></div>${productCard(p)}<div class="health-grid" style="grid-template-columns:1fr;margin-top:12px"><div class="health-card ok"><span>Estoque</span><strong>${available(p)} disponível</strong></div><div class="health-card"><span>Preço</span><strong>${fmtBRL(promoPrice(p))}</strong></div>${canSeeCost()?`<div class="health-card"><span>Margem estimada</span><strong>${p.price?(((Number(p.price)-Number(p.cost||0))/Number(p.price))*100).toFixed(1):0}%</strong></div>`:""}</div>`:""}</aside>
  </div>`;if(p){$("#studioFeatured").value=String(!!pres.featured);$("#studioPublished").value=String(pres.published!==false)}
}
function renderPromocoes(){
  ensureCatalog();$("#appContent").innerHTML=pageHead("PROMOÇÕES","Campanhas e preços promocionais","Defina desconto, período e produtos. O catálogo ativa e encerra automaticamente.",`<button class="primary-btn" data-action="new-promo">＋ Nova promoção</button>`)+`
  <div class="promo-grid">${state.catalog.promotions.map(p=>`<div class="promo-card"><div class="product-meta"><span class="chip ${p.active?"green":"red"}">${p.active?"Ativa":"Inativa"}</span><span class="chip">${p.productIds?.length||0} produto(s)</span></div><h4>${esc(p.name)}</h4><small>${esc(p.start||"—")} → ${esc(p.end||"—")}</small><div class="promo-value">${p.type==="fixed"?`-${fmtBRL(p.value)}`:`-${Number(p.value||0)}%`}</div><div class="actions"><button class="secondary-btn" data-action="toggle-promo" data-id="${esc(p.id)}">${p.active?"Pausar":"Ativar"}</button><button class="danger-btn" data-action="delete-promo" data-id="${esc(p.id)}">Excluir</button></div></div>`).join("")||`<div class="empty-state">Nenhuma promoção.</div>`}</div>`;
}
function topProducts(){
  const map={};[...state.quotes,...state.orders].forEach(doc=>(doc.items||[]).forEach(i=>{const id=i.product_id||i.productId||i.product_name;map[id]=(map[id]||0)+Number(i.quantity||1)}));
  return Object.entries(map).map(([id,qty])=>({id,qty,p:state.products.find(p=>p.id===id)})).sort((a,b)=>b.qty-a.qty).slice(0,8)
}
async function renderRelatorios(){
  const f=modern.reportFilter;
  $('#appContent').innerHTML=pageHead('RESULTADOS COMERCIAIS','Valores por etapa da negociação','Proposta, rascunho, pedido confirmado e recebimento têm significados diferentes.',`<button class="secondary-btn" data-action="export-report">Exportar CSV</button>`)+`<div class="modern-filters"><label>De<input id="reportStart" type="date" value="${esc(f.start)}"></label><label>Até<input id="reportEnd" type="date" value="${esc(f.end)}"></label><label>Cliente<select id="reportClient"><option value="">Todos</option>${state.clients.map(c=>`<option value="${esc(c.id)}" ${f.client_id===c.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><label>Etapa<select id="reportStatus"><option value="">Todas</option>${['Rascunho','Aguardando aprovação','Confirmado','Entregue'].map(s=>`<option ${f.status===s?'selected':''}>${s}</option>`).join('')}</select></label><label>Responsável<input id="reportSeller" value="${esc(f.seller)}"></label><button class="primary-btn" data-action="reload-commercial-reports">Aplicar filtros</button></div><div id="commercialReportResults" role="status">Consultando resultados…</div>`;
  try{const r=state.demo?{quoted:0,draft_orders:0,confirmed:0,delivered:0,quotes:0,converted:0,rows:[]}:await API.request('/commercial/reports?'+new URLSearchParams(f));modern.report=r;if(state.route!=='relatorios')return;
    $('#commercialReportResults').innerHTML=`<div class="grid modern-home-stats">${[['Valor proposto',r.quoted],['Pedidos em rascunho',r.draft_orders],['Pedidos confirmados',r.confirmed],['Entregues',r.delivered]].map(([label,n])=>`<div class="stat-card"><small>${label}</small><strong>${fmtBRL(n)}</strong></div>`).join('')}</div><p class="help">Conversão por proposta de origem: ${r.quotes?(r.converted/r.quotes*100).toFixed(1):'0'}%. Estes valores não representam pagamentos recebidos.</p><div class="table-wrap"><table><thead><tr><th>Pedido / origem</th><th>Data</th><th>Cliente</th><th>Responsável</th><th>Status</th><th>Valor</th>${canSeeCost()?'<th>Custo histórico</th><th>Resultado nos produtos</th><th>Comissão estimada</th>':''}</tr></thead><tbody>${r.rows.map(x=>`<tr><td>${esc(x.code)}<small class="modern-block">${esc(x.source)}</small></td><td>${esc(x.date)}</td><td>${esc(x.client_name)}</td><td>${esc(x.seller)}</td><td>${esc(x.status)}</td><td>${fmtBRL(x.total)}</td>${canSeeCost()?`<td>${x.cost!=null?fmtBRL(x.cost):'Não disponível'}</td><td>${x.gross_profit!=null?fmtBRL(x.gross_profit):'Não disponível'}</td><td>${x.commission_estimate!=null?fmtBRL(x.commission_estimate):'Regra não definida'}</td>`:''}</tr>`).join('')||'<tr><td colspan="8">Nenhum pedido para os filtros.</td></tr>'}</tbody></table></div>`;
  }catch(e){if($('#commercialReportResults'))$('#commercialReportResults').textContent='Não foi possível consultar: '+e.message}
}
function exportReportCsv(){
  const rows=modern.report?.rows;if(!rows)throw Error('Consulte um relatório antes de exportar.');
  const columns=['code','date','client_name','seller','status','total','source',...(canSeeCost()?['cost','gross_profit','commission_estimate']:[])];
  const safe=v=>{let t=String(v??'');if(/^[=+\-@\t\r]/.test(t))t="'"+t;return '"'+t.replace(/"/g,'""')+'"'};
  const lines=[columns,...rows.map(r=>columns.map(k=>r[k]))].map(r=>r.map(safe).join(';'));
  const blob=new Blob(['\uFEFF'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}),link=document.createElement('a'),url=URL.createObjectURL(blob);link.href=url;link.download=`comercial-${today()}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function renderConfiguracoes(){
  ensureCatalog();const s=state.catalog.settings;
  $("#appContent").innerHTML=pageHead("CONFIGURAÇÕES","Identidade e regras comerciais","Personalize a experiência sem alterar o código.",`<button class="primary-btn" data-action="save-settings">Salvar configurações</button>`)+`
  <div class="grid home-grid"><div class="panel"><div class="panel-head"><div><h3>Empresa</h3><small>Identidade comercial</small></div></div><div class="form-grid"><div class="field full"><label>Nome da empresa / catálogo</label><input id="cfgCompany" value="${esc(s.companyName)}"></div><div class="field"><label>WhatsApp</label><input id="cfgWhatsapp" value="${esc(s.whatsapp||"")}" placeholder="5511999999999"></div><div class="field"><label>Margem mínima (%)</label><input id="cfgMinMargin" type="number" value="${Number(s.minimumMargin??20)}"></div><div class="field"><label>Garantia padrão (meses)</label><input id="cfgWarranty" type="number" min="0" value="${Number(s.defaultWarrantyMonths||12)}"></div></div></div>
  <div class="panel"><div class="panel-head"><div><h3>Condições comerciais</h3><small>Cálculo rápido ao vender</small></div></div><div class="form-grid"><div class="field"><label>Desconto PIX (%)</label><input id="cfgPix" type="number" value="${Number(s.pixDiscount||0)}"></div><div class="field"><label>Parcelas sugeridas</label><input id="cfgInstallments" type="number" value="${Number(s.installments||3)}"></div><div class="field"><label>Acréscimo parcelado (%)</label><input id="cfgFee" type="number" value="${Number(s.installmentFee||0)}"></div></div></div><div class="panel" style="margin-top:14px"><div class="panel-head"><div><h3>Automações do pedido</h3><small>Integração operacional</small></div></div><div class="form-grid"><label class="checkbox-row"><input id="cfgAutoProduction" type="checkbox" ${s.autoCreateProduction?"checked":""}> Criar produção quando faltar estoque</label><label class="checkbox-row"><input id="cfgAutoReceivable" type="checkbox" ${s.autoCreateReceivable?"checked":""}> Criar conta a receber ao confirmar pedido</label><label class="checkbox-row"><input id="cfgAutoDelivery" type="checkbox" ${s.autoCreateDelivery?"checked":""}> Criar entrega ao confirmar pedido</label></div></div></div>
  <div class="panel" style="margin-top:14px"><div class="panel-head"><div><h3>Histórico de alterações</h3><small>Últimos eventos do catálogo</small></div></div><div class="table-wrap"><table><thead><tr><th>Data</th><th>Usuário</th><th>Ação</th><th>Entidade</th><th>Detalhes</th></tr></thead><tbody>${state.catalog.history.slice(0,30).map(h=>`<tr><td>${new Date(h.at).toLocaleString("pt-BR")}</td><td>${esc(h.user)}</td><td>${esc(h.action)}</td><td>${esc(h.entity)}</td><td>${esc(h.details)}</td></tr>`).join("")||`<tr><td colspan="5">Sem histórico.</td></tr>`}</tbody></table></div></div><div class="danger-zone"><strong>Base de demonstração</strong><p style="font-size:9px;color:var(--muted);margin:5px 0 10px">Apaga os dados locais e volta para uma base totalmente zerada.</p><button class="danger-btn" data-action="reset-blank-demo">Zerar demonstração</button></div>`;
}
function renderIntegracao(){
  const ok=!state.demo&&((state.health?.erp==="connected"&&state.health?.catalog_database==="connected")||state.health?.database==="connected"),st=CFG.STORAGE;
  $("#appContent").innerHTML=pageHead("INTEGRAÇÃO ERP","Conectividade e armazenamento","Diagnóstico da API, banco, cache offline e mídia.",`<button class="secondary-btn" data-action="reload">↻ Sincronizar</button>`)+`
  <div class="grid stats-grid"><div class="health-card ${state.demo?"warn":ok?"ok":"bad"}"><span>ERP</span><strong>${state.demo?"Demonstração":ok?"Conectado":"Verificar"}</strong></div><div class="health-card ${navigator.onLine?"ok":"warn"}"><span>Internet</span><strong>${navigator.onLine?"Online":"Offline"}</strong></div><div class="health-card"><span>Produtos</span><strong>${state.products.length}</strong></div><div class="health-card"><span>Revisão catálogo</span><strong>${state.catalogRevision||"—"}</strong></div></div>
  <div class="grid home-grid"><div class="panel"><div class="panel-head"><div><h3>API do ERP</h3><small>Mesma autenticação e banco</small></div></div><div class="field"><label>URL base</label><input id="integrationApiBase" value="${esc(API.base())}" placeholder="https://seu-erp.onrender.com/api/v1"></div><div class="actions" style="margin-top:10px"><button class="primary-btn" data-action="save-api">Salvar</button><button class="secondary-btn" data-action="test-api">Testar</button>${hasPermission("settings.write")?`<button class="secondary-btn" data-action="bootstrap-catalog-profiles">Criar perfis Comercial/Catálogo</button>`:""}</div>
  <div class="health-grid" style="grid-template-columns:1fr;margin-top:14px"><div class="health-card ok"><span>Pedidos</span><strong>/sales-orders disponível</strong></div><div class="health-card ok"><span>Gestão de catálogo</span><strong>/catalog-management protegido por permissões</strong></div><div class="health-card ok"><span>Site / catálogo público</span><strong>/public/catalog publica produtos e fotos aprovados</strong></div><div class="health-card ok"><span>Integração entre sistemas</span><strong>/integration/snapshot centraliza os mesmos dados</strong></div><div class="health-card ok"><span>Estoque</span><strong>/inventory/balances disponível</strong></div></div></div>
  <div class="panel"><div class="panel-head"><div><h3>Fotos dos produtos</h3><small>As imagens ficam compartilhadas entre ERP, comercial e site</small></div></div><div class="form-grid"><div class="field full"><label>Armazenamento</label><select id="storageProvider"><option value="erp_api">Banco/API do Fácil Pedido (recomendado)</option><option value="erp_state">Estado do ERP (somente testes pequenos)</option><option value="supabase">Supabase Storage</option></select></div><div class="field full"><label>Supabase URL</label><input id="supabaseUrl" value="${esc(st.supabaseUrl||"")}"></div><div class="field full"><label>Anon Key</label><input id="supabaseAnon" type="password" value="${esc(st.supabaseAnonKey||"")}"></div><div class="field full"><label>Bucket</label><input id="supabaseBucket" value="${esc(st.bucket||"product-media")}"></div></div><div class="actions" style="margin-top:10px"><button class="primary-btn" data-action="save-storage">Salvar mídia</button></div><p class="help">Com Banco/API, a pessoa do RH/Catálogo envia a foto e ela fica disponível para todos os usuários. O site pode consumir o catálogo publicado em <b>/api/v1/public/catalog</b>.</p></div></div>`;
  $("#storageProvider").value=localStorage.getItem("fp_storage_provider")||CFG.STORAGE.provider;
}

function opData(){ensureCatalog();return state.catalog.operations}
async function persistOps(label="Operação atualizada"){logHistory("ATUALIZAR","Operação",label);await saveCatalogState()}
function nextCode(prefix,list){return `${prefix}-${String(list.length+1).padStart(4,"0")}`}
function sumStatus(list,status){return list.filter(x=>x.status===status).reduce((a,x)=>a+Number(x.amount||0),0)}

function productVariantsText(productId){return state.variants.filter(v=>v.product_id===productId).map(v=>[v.sku||"",v.color||"",v.size||"",Number(v.price||0).toFixed(2),Number(v.stock||0)].join(";")).join("\n")}
function marginPct(price,cost){price=Number(price)||0;cost=Number(cost)||0;return price>0?((price-cost)/price*100):0}
function updateProductMarginPreview(){const price=Number($("#pfPrice")?.value)||0,cost=Number($("#pfCost")?.value)||0,m=marginPct(price,cost),profit=Math.max(0,price-cost);if($("#pfMarginValue"))$("#pfMarginValue").textContent=`${m.toFixed(1)}%`;if($("#pfProfitValue"))$("#pfProfitValue").textContent=fmtBRL(profit);if($("#pfMinMarginValue"))$("#pfMinMarginValue").textContent=`${Number(state.catalog.settings.minimumMargin||20)}%`}
function openProductForm(id=""){
  if(!state.demo&&!hasPermission("settings.write"))return toast("Cadastro técnico disponível ao administrador/gerente. O RH gerencia imagens em Fotos & Studio.","error");
  const p=state.products.find(x=>x.id===id)||{price:0,cost:0,stock:0,reserved_stock:0,min_stock:0,active:true,manufacturing_enabled:false,unit:"UN"};
  const cat=categoryName(p)==="Sem categoria"?"":categoryName(p);
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card wide"><div class="modal-head"><div><h3>${id?"Editar móvel / produto":"Cadastrar móvel / produto"}</h3><p>Cadastro comercial, estoque, características e variações do móvel.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body">
  <div class="v5-section"><div class="v5-title"><div><h3>Identificação</h3><small>Dados usados em busca, etiqueta e catálogo.</small></div></div><div class="form-grid three">
    <div class="field"><label>Código / SKU *</label><input id="pfCode" value="${esc(p.code||"")}" placeholder="SOF-001"></div>
    <div class="field"><label>Código de barras</label><input id="pfBarcode" value="${esc(p.barcode||"")}" inputmode="numeric" placeholder="789..."></div>
    <div class="field"><label>Unidade</label><select id="pfUnit"><option>UN</option><option>CJ</option><option>PC</option><option>M</option><option>M²</option></select></div>
    <div class="field full"><label>Nome do produto *</label><input id="pfName" value="${esc(p.name||"")}" placeholder="Sofá Retrátil 2,30m"></div>
    <div class="field"><label>Categoria</label><input id="pfCategory" value="${esc(cat)}" list="categoryList"><datalist id="categoryList">${state.categories.map(c=>`<option value="${esc(c.name)}">`).join("")}</datalist></div>
    <div class="field"><label>Marca / coleção</label><input id="pfBrand" value="${esc(p.brand||"")}"></div>
    <div class="field"><label>Fornecedor</label><input id="pfSupplier" value="${esc(p.supplier||"")}"></div>
  </div></div>
  <div class="v5-section"><div class="v5-title"><div><h3>Preço e estoque</h3><small>Os valores começam em zero e são definidos pela empresa.</small></div></div><div class="form-grid four">
    <div class="field"><label>Preço de venda (R$) *</label><input id="pfPrice" type="number" min="0" step="0.01" value="${Number(p.price||0).toFixed(2)}"></div>
    ${canSeeCost()?`<div class="field"><label>Custo (R$)</label><input id="pfCost" type="number" min="0" step="0.01" value="${Number(p.cost||0).toFixed(2)}"></div>`:""}
    <div class="field"><label>Estoque inicial</label><input id="pfStock" type="number" min="0" step="1" value="${Number(p.stock||0)}"></div>
    <div class="field"><label>Estoque mínimo</label><input id="pfMinStock" type="number" min="0" step="1" value="${Number(p.min_stock||0)}"></div>
    <div class="field full"><label>Local principal</label><select id="pfLocation"><option value="">Não definido</option>${state.locations.map(l=>`<option value="${esc(l.id)}" ${p.location_id===l.id?"selected":""}>${esc(l.name)}</option>`).join("")}</select></div>
  </div>${canSeeCost()?`<div class="margin-preview"><div><small>Margem atual</small><strong id="pfMarginValue">0,0%</strong></div><div><small>Lucro unitário</small><strong id="pfProfitValue">R$ 0,00</strong></div><div><small>Margem mínima</small><strong id="pfMinMarginValue">${Number(state.catalog.settings.minimumMargin||20)}%</strong></div></div>`:""}</div>
  <div class="v5-section"><div class="v5-title"><div><h3>Características</h3><small>Informações técnicas e comerciais.</small></div></div><div class="form-grid three">
    <div class="field"><label>Cor</label><input id="pfColor" value="${esc(p.color||"")}"></div><div class="field"><label>Tamanho / medida</label><input id="pfSize" value="${esc(p.size||"")}"></div><div class="field"><label>Material</label><input id="pfMaterial" value="${esc(p.material||"")}"></div>
    <div class="field"><label>Largura (cm)</label><input id="pfWidth" type="number" min="0" step="0.1" value="${Number(p.width_cm||0)||""}"></div><div class="field"><label>Altura (cm)</label><input id="pfHeight" type="number" min="0" step="0.1" value="${Number(p.height_cm||0)||""}"></div><div class="field"><label>Profundidade (cm)</label><input id="pfDepth" type="number" min="0" step="0.1" value="${Number(p.depth_cm||0)||""}"></div>
    <div class="field"><label>Garantia (meses)</label><input id="pfWarranty" type="number" min="0" value="${Number(p.warranty_months??state.catalog.settings.defaultWarrantyMonths??12)}"></div>
    <div class="field full"><label>Descrição</label><textarea id="pfDescription">${esc(p.description||"")}</textarea></div>
    <div class="field full"><label class="checkbox-row"><input id="pfManufacturing" type="checkbox" ${p.manufacturing_enabled?"checked":""}> Produto pode ser fabricado quando faltar estoque</label></div>
  </div></div>
  <div class="v5-section"><div class="v5-title"><div><h3>Variações</h3><small>Cor, tamanho, preço e estoque próprios.</small></div></div><div class="variant-help">Uma variação por linha no formato <code>SKU;Cor;Tamanho;Preço;Estoque</code>. Exemplo: <code>SOF-001-BG;Bege;2,30m;2499.90;3</code></div><div class="field" style="margin-top:8px"><textarea id="pfVariants" rows="5" placeholder="SKU;Cor;Tamanho;Preço;Estoque">${esc(productVariantsText(id))}</textarea></div></div>
  <div class="actions" style="margin-top:14px"><button class="secondary-btn" data-close-modal>Cancelar</button><button class="primary-btn" data-action="save-product-form" data-id="${esc(id)}">Salvar produto</button></div>
  </div></div></div>`;$("#modalRoot").classList.add("show");$("#pfUnit").value=p.unit||"UN";updateProductMarginPreview();
}
async function saveProductForm(id=""){
  if(!state.demo&&!hasPermission("settings.write"))throw new Error("Somente administrador ou gerente pode editar o cadastro técnico.");
  const code=$("#pfCode").value.trim(),name=$("#pfName").value.trim();if(!code||!name)return toast("Informe código e nome do produto.","error");
  if(state.products.some(p=>p.id!==id&&norm(p.code)===norm(code)))return toast("Já existe um produto com este código/SKU.","error");
  const categoryNameValue=$("#pfCategory").value.trim();let category=state.categories.find(c=>norm(c.name)===norm(categoryNameValue));if(categoryNameValue&&!category){if(state.demo){category={id:`CAT-${Date.now()}`,name:categoryNameValue};state.categories.push(category)}else{category=await API.request("/categories",{method:"POST",body:JSON.stringify({name:categoryNameValue,item_type:"Produto acabado",active:true})});state.categories.push(category)}}
  const currentProduct=state.products.find(x=>x.id===id),originalStock=Number(currentProduct?.stock||0),price=Number($("#pfPrice").value)||0,cost=canSeeCost()?Number($("#pfCost")?.value)||0:Number(currentProduct?.cost||0);
  const payload={code,name,barcode:$("#pfBarcode").value.trim(),brand:$("#pfBrand").value.trim(),supplier:$("#pfSupplier").value.trim(),category_id:category?.id||null,category_name:categoryNameValue||"",price,cost,technical_cost:cost,stock:Number($("#pfStock").value)||0,reserved_stock:Number(currentProduct?.reserved_stock||0),min_stock:Number($("#pfMinStock").value)||0,color:$("#pfColor").value.trim(),size:$("#pfSize").value.trim(),material:$("#pfMaterial").value.trim(),width_cm:Number($("#pfWidth").value)||0,height_cm:Number($("#pfHeight").value)||0,depth_cm:Number($("#pfDepth").value)||0,warranty_months:Number($("#pfWarranty").value)||0,location_id:$("#pfLocation").value||null,description:$("#pfDescription").value.trim(),manufacturing_enabled:$("#pfManufacturing").checked,active:true,item_type:"Produto acabado",unit:$("#pfUnit").value||"UN"};
  let product=currentProduct;
  if(state.demo){if(product)Object.assign(product,payload);else{product={id:`PRD-${Date.now()}`,...payload};state.products.unshift(product)}}
  else{product=product?await API.request(`/products/${encodeURIComponent(id)}`,{method:"PUT",body:JSON.stringify(payload)}):await API.request("/products",{method:"POST",body:JSON.stringify(payload)});const ix=state.products.findIndex(x=>x.id===id);if(ix>=0)state.products[ix]=product;else state.products.unshift(product)}
  let bal=state.balances.find(b=>b.product_id===product.id&&b.location_id===payload.location_id&&!b.variant_id);if(bal)Object.assign(bal,{quantity:payload.stock,reserved_quantity:Number(bal.reserved_quantity||0),available_quantity:Math.max(0,payload.stock-Number(bal.reserved_quantity||0))});else if(payload.location_id)state.balances.push({product_id:product.id,location_id:payload.location_id,quantity:payload.stock,reserved_quantity:0,available_quantity:payload.stock});
  const existingVariants=state.variants.filter(v=>v.product_id===product.id),variantsChanged=$("#pfVariants").value.trim()!==productVariantsText(product.id).trim(),lines=$("#pfVariants").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean),parsed=[];for(const line of lines){const [sku,color,size,priceV,stockV]=line.split(";").map(x=>x?.trim()||"");if(!sku)continue;parsed.push({id:state.variants.find(v=>v.product_id===product.id&&v.sku===sku)?.id||`VAR-${Date.now()}-${parsed.length}`,product_id:product.id,sku,color,size,price:Number(String(priceV).replace(",","."))||0,stock:Number(stockV)||0,reserved_stock:0})}if(variantsChanged)state.variants=state.variants.filter(v=>v.product_id!==product.id).concat(parsed);
  state.catalog.productExtras[product.id]={barcode:payload.barcode,brand:payload.brand,supplier:payload.supplier,material:payload.material,width_cm:payload.width_cm,height_cm:payload.height_cm,depth_cm:payload.depth_cm,warranty_months:payload.warranty_months};
  Object.assign(product,state.catalog.productExtras[product.id]);
  state.catalog.presentation[product.id]={...(state.catalog.presentation[product.id]||{}),published:state.catalog.presentation[product.id]?.published??false,title:name,description:payload.description,subtitle:[payload.color,payload.size,payload.material].filter(Boolean).join(" • ")};state.catalog.media[product.id]||={photos:[],variantPhotos:{}};
  if(!state.demo){
    // A categoria já foi validada e cadastrada antes da gravação do produto.
    if(payload.location_id && (!currentProduct || originalStock!==payload.stock)){
      const current=state.balances.find(b=>b.product_id===product.id&&b.location_id===payload.location_id&&!b.variant_id);
      if(current)try{await API.request("/inventory/balances",{method:"POST",body:JSON.stringify(current)})}catch{}
    }
    // Editar só preço/descrição não pode regravar centenas de variações.
    if(variantsChanged){const persisted=[];for(const v of parsed){const existing=existingVariants.find(x=>x.sku===v.sku);const payload={product_id:product.id,sku:v.sku,color:v.color,size:v.size,price:v.price,stock:v.stock,barcode:v.barcode||""};persisted.push(await API.request(existing?`/product-variants/${encodeURIComponent(existing.id)}`:"/product-variants",{method:existing?"PUT":"POST",body:JSON.stringify(payload)}))}state.variants=state.variants.filter(v=>v.product_id!==product.id).concat(persisted);}
  }
  logHistory(id?"EDITAR":"CRIAR","Produto",`${code} • ${name} • ${fmtBRL(price)} • margem ${marginPct(price,cost).toFixed(1)}%`);await saveCatalogState();closeModal();toast(id?"Produto atualizado":"Produto cadastrado");go("catalog-manager");
}
function formatDoc(v){v=String(v||"").replace(/\D/g,"").slice(0,14);if(v.length<=11)return v.replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d{1,2})$/,"$1-$2");return v.replace(/(\d{2})(\d)/,"$1.$2").replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d)/,"$1/$2").replace(/(\d{4})(\d{1,2})$/,"$1-$2")}
function formatPhone(v){v=String(v||"").replace(/\D/g,"").slice(0,11);return v.length>10?v.replace(/(\d{2})(\d{5})(\d{4})/,"($1) $2-$3"):v.replace(/(\d{2})(\d{4})(\d{0,4})/,"($1) $2-$3")}
function formatCep(v){v=String(v||"").replace(/\D/g,"").slice(0,8);return v.replace(/(\d{5})(\d{0,3})/,"$1-$2")}
function openClientForm(){
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card wide"><div class="modal-head"><div><h3>Novo cliente</h3><p>Cadastro comercial, contato, endereço e condição de venda.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="v5-section"><div class="form-grid three"><div class="field full"><label>Nome / Razão social *</label><input id="cfName"></div><div class="field"><label>CPF / CNPJ</label><input id="cfDocument" inputmode="numeric"></div><div class="field"><label>Telefone / WhatsApp</label><input id="cfPhone" inputmode="tel"></div><div class="field"><label>E-mail</label><input id="cfEmail" type="email"></div><div class="field"><label>Limite de crédito (R$)</label><input id="cfLimit" type="number" min="0" step="0.01" value="0.00"></div><div class="field"><label>Tabela / perfil de preço</label><select id="cfPriceProfile"><option>Varejo</option><option>Atacado</option><option>Revenda</option><option>Especial</option></select></div><div class="field"><label>Pagamento preferido</label><select id="cfPayment"><option>PIX</option><option>Cartão</option><option>Boleto</option><option>30 dias</option><option>Dinheiro</option></select></div></div></div><div class="v5-section"><div class="v5-title"><div><h3>Endereço</h3><small>Usado em pedido, entrega e montagem.</small></div></div><div class="client-address-grid"><div class="field"><label>CEP</label><input id="cfCep" inputmode="numeric"></div><div class="field wide"><label>Rua / avenida</label><input id="cfStreet"></div><div class="field"><label>Número</label><input id="cfNumber"></div><div class="field"><label>Bairro</label><input id="cfDistrict"></div><div class="field"><label>Cidade</label><input id="cfCity"></div><div class="field"><label>UF</label><input id="cfState" maxlength="2"></div><div class="field full"><label>Complemento</label><input id="cfComplement"></div></div></div><div class="field" style="margin-top:10px"><label>Observações comerciais</label><textarea id="cfNotes"></textarea></div><div class="actions" style="margin-top:12px"><button class="secondary-btn" data-close-modal>Cancelar</button><button class="primary-btn" data-action="save-client-form">Salvar cliente</button></div></div></div></div>`;$("#modalRoot").classList.add("show")
}
async function saveClientForm(){
  const name=$("#cfName").value.trim();if(!name)return toast("Informe o nome do cliente.","error");const email=$("#cfEmail").value.trim();if(email&&!/^\S+@\S+\.\S+$/.test(email))return toast("E-mail inválido.","error");
  const address=[[$("#cfStreet").value.trim(),$("#cfNumber").value.trim()].filter(Boolean).join(", "),$("#cfDistrict").value.trim(),[$("#cfCity").value.trim(),$("#cfState").value.trim().toUpperCase()].filter(Boolean).join("/"),$("#cfCep").value.trim(),$("#cfComplement").value.trim()].filter(Boolean).join(" • ");
  const payload={name,document:$("#cfDocument").value.trim(),phone:$("#cfPhone").value.trim(),email,credit_limit:Number($("#cfLimit").value)||0,address,cep:$("#cfCep").value.trim(),street:$("#cfStreet").value.trim(),number:$("#cfNumber").value.trim(),district:$("#cfDistrict").value.trim(),city:$("#cfCity").value.trim(),state:$("#cfState").value.trim().toUpperCase(),complement:$("#cfComplement").value.trim(),price_profile:$("#cfPriceProfile").value,preferred_payment:$("#cfPayment").value,notes:$("#cfNotes").value.trim(),status:"Ativo"};
  let c;if(state.demo){c={id:`CLI-${Date.now()}`,...payload}}
  else{c=await API.request("/clients",{method:"POST",body:JSON.stringify({name:payload.name,document:payload.document,phone:payload.phone,email:payload.email,notes:payload.notes,active:true})})}
  state.clients.unshift({...payload,...c});state.catalog.crm[c.id]={stage:"Novo contato",lastContact:today(),notes:payload.notes,nextAction:addDays(new Date(),2),extra:{address,price_profile:payload.price_profile,preferred_payment:payload.preferred_payment}};
  logHistory("CRIAR","Cliente",c.name);await saveCatalogState();closeModal();toast("Cliente cadastrado");renderClientes()
}

function renderEstoque(){
  const ops=opData(),total=state.products.reduce((a,p)=>a+available(p),0),reserved=state.balances.reduce((a,b)=>a+Number(b.reserved_quantity||0),0),critical=state.products.filter(p=>available(p)<=Number(p.min_stock||0)).length;
  $("#appContent").innerHTML=pageHead("ESTOQUE","Estoque, reservas e movimentações","Controle por produto e unidade, com histórico completo de entrada, saída e ajuste.",`<button class="secondary-btn" data-action="import-products">⇧ Importar Excel/CSV</button><button class="secondary-btn" data-action="new-stock-movement">＋ Movimentar estoque</button><button class="primary-btn" data-action="open-product-form">＋ Cadastrar móvel</button>`)+`
  <input id="productImportFile" type="file" accept=".csv,.xlsx,.xls" class="hidden">
  <div class="ops-dashboard"><div class="ops-kpi"><small>Produtos</small><strong>${state.products.length}</strong></div><div class="ops-kpi"><small>Disponível</small><strong>${total}</strong></div><div class="ops-kpi"><small>Reservado</small><strong>${reserved}</strong></div><div class="ops-kpi"><small>Estoque crítico</small><strong>${critical}</strong></div><div class="ops-kpi"><small>Valor em venda</small><strong>${fmtBRL(state.products.reduce((a,p)=>a+available(p)*Number(p.price||0),0))}</strong></div><div class="ops-kpi"><small>Valor de custo</small><strong>${fmtBRL(state.products.reduce((a,p)=>a+available(p)*Number(p.cost||0),0))}</strong></div></div>
  <div class="table-wrap"><table><thead><tr><th>Código</th><th>Produto</th><th>Local</th><th>Preço</th><th>Estoque</th><th>Mínimo</th><th>Status</th><th>Ações</th></tr></thead><tbody>${state.products.map(p=>`<tr><td>${esc(p.code)}</td><td><strong>${esc(p.name)}</strong><small style="display:block">${esc(categoryName(p))}${p.barcode?` • ${esc(p.barcode)}`:""}</small></td><td>${esc(locationName(p.location_id))}</td><td>${fmtBRL(p.price)}</td><td><span class="stock-qty">${available(p)}</span></td><td>${Number(p.min_stock||0)}</td><td><span class="chip ${available(p)<=Number(p.min_stock||0)?"orange":"green"}">${available(p)<=Number(p.min_stock||0)?"Atenção":"OK"}</span></td><td><div class="actions"><button class="secondary-btn" data-action="new-stock-movement" data-id="${esc(p.id)}">Movimentar</button><button class="secondary-btn" data-action="open-product-form" data-id="${esc(p.id)}">Editar</button></div></td></tr>`).join("")||`<tr><td colspan="8"><div class="ops-empty"><strong>Nenhum produto cadastrado</strong>Cadastre ou importe os móveis e informe preço e estoque.</div></td></tr>`}</tbody></table></div>
  <div class="v5-section" style="margin-top:14px"><div class="v5-title"><div><h3>Últimas movimentações</h3><small>Auditoria operacional do estoque.</small></div></div><div class="table-wrap"><table><thead><tr><th>Data</th><th>Produto</th><th>Tipo</th><th>Qtd.</th><th>Local</th><th>Motivo</th></tr></thead><tbody>${ops.stockMovements.slice(0,30).map(m=>`<tr><td>${new Date(m.at).toLocaleString("pt-BR")}</td><td>${esc(m.product_name||m.product_id)}</td><td>${esc(m.type)}</td><td class="${m.type==="Entrada"?"stock-movement-positive":m.type==="Saída"?"stock-movement-negative":"stock-movement-adjust"}">${m.type==="Entrada"?"+":m.type==="Saída"?"−":""}${Number(m.quantity||0)}</td><td>${esc(locationName(m.location_id))}</td><td>${esc(m.reason||"—")}</td></tr>`).join("")||`<tr><td colspan="6">Sem movimentações.</td></tr>`}</tbody></table></div></div>`;
}
function openStockMovement(productId=""){if(!state.products.length)return toast("Cadastre um produto primeiro.","error");$("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>Movimentar estoque</h3><p>Entrada, saída ou ajuste manual com histórico.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="form-grid"><div class="field full"><label>Produto</label><select id="smProduct">${state.products.map(p=>`<option value="${esc(p.id)}" ${p.id===productId?"selected":""}>${esc(p.code)} — ${esc(p.name)}</option>`).join("")}</select></div><div class="field"><label>Tipo</label><select id="smType"><option>Entrada</option><option>Saída</option><option>Ajuste</option></select></div><div class="field"><label>Quantidade</label><input id="smQty" type="number" min="0" step="1" value="1"></div><div class="field full"><label>Local</label><select id="smLocation"><option value="">Local principal do produto</option>${state.locations.map(l=>`<option value="${esc(l.id)}">${esc(l.name)}</option>`).join("")}</select></div><div class="field full"><label>Motivo / referência</label><input id="smReason" placeholder="Compra, devolução, avaria, inventário..."></div></div><div class="actions" style="margin-top:12px"><button class="primary-btn" data-action="save-stock-movement">Salvar movimentação</button></div></div></div></div>`;$("#modalRoot").classList.add("show")}
async function saveStockMovement(){
 const pid=$("#smProduct").value,product=state.products.find(p=>p.id===pid);if(!product)return;
 const type=$("#smType").value,qty=Number($("#smQty").value)||0,location=$("#smLocation").value||product.location_id||null;
 if(qty<0||((type!=="Ajuste")&&qty===0))return toast("Informe uma quantidade válida.","error");
 const current=Number(product.stock)||0,availableQty=available(product);
 if(type==="Saída"&&qty>availableQty)return toast("Estoque disponível insuficiente.","error");
 const next=type==="Entrada"?current+qty:type==="Saída"?current-qty:qty;
 const reason=$("#smReason").value.trim()||`Movimentação comercial: ${type}`;
 if(!state.demo){
   await API.request("/inventory/balances",{method:"POST",body:JSON.stringify({product_id:pid,location_id:location,quantity:next,reason})});
   await loadAll();
 }else{
   product.stock=next;const bal=state.balances.find(b=>b.product_id===pid&&!b.variant_id);
   if(bal){bal.quantity=next;bal.available_quantity=next-Number(bal.reserved_quantity||0)}
   opData().stockMovements.unshift({id:`MOV-${Date.now()}`,at:new Date().toISOString(),product_id:pid,product_name:product.name,type,quantity:qty,location_id:location,reason,user:state.user?.full_name||"Usuário"});
 }
 logHistory("ESTOQUE",product.name,`${type} ${qty} • ${reason}`);
 if(state.demo)await saveCatalogState();closeModal();toast("Movimentação registrada no estoque.");renderEstoque();
}
async function loadXlsxLib(){if(window.XLSX)return;await new Promise((resolve,reject)=>{const s=document.createElement("script");s.src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js";s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}
function csvRows(text){const lines=text.replace(/^\uFEFF/,"").split(/\r?\n/).filter(Boolean),sep=(lines[0].match(/;/g)||[]).length>(lines[0].match(/,/g)||[]).length?";":",";const parse=l=>{const out=[];let cur="",q=false;for(let i=0;i<l.length;i++){const c=l[i];if(c==='"'){if(q&&l[i+1]==='"'){cur+='"';i++}else q=!q}else if(c===sep&&!q){out.push(cur);cur=""}else cur+=c}out.push(cur);return out};const head=parse(lines.shift()).map(norm);return lines.map(l=>{const vals=parse(l),o={};head.forEach((h,i)=>o[h]=vals[i]??"");return o})}
async function importProductFile(file){
  if(!state.demo&&!hasPermission("settings.write"))throw new Error("Sem permissão para importar produtos");
  let rows=[];
  if(/\.csv$/i.test(file.name))rows=csvRows(await file.text());
  else{try{await loadXlsxLib();const wb=XLSX.read(await file.arrayBuffer(),{type:"array"});rows=XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]],{defval:""}).map(r=>Object.fromEntries(Object.entries(r).map(([k,v])=>[norm(k),v])))}catch{throw new Error("Falha na leitura do Excel. Salve a planilha como CSV ou confira sua conexão.")}}
  if(rows.length>500)throw new Error("Limite de 500 linhas por importação. Separe em mais planilhas.");
  let added=0,updated=0;const errors=[];
  for(let i=0;i<rows.length;i++){
    const r=rows[i],get=(...ks)=>{for(const k of ks)if(r[norm(k)]!==undefined)return r[norm(k)];return ""};
    const code=String(get("codigo","código","sku")).trim(),name=String(get("nome","produto","movel","móvel")).trim();
    if(!code||!name){errors.push(`Linha ${i+2}: código e nome são obrigatórios`);continue}
    try{
      const original=state.products.find(p=>norm(p.code)===norm(code));
      const catName=String(get("categoria")).trim();let cat=state.categories.find(c=>norm(c.name)===norm(catName));
      if(catName&&!cat){cat=state.demo?{id:`CAT-${Date.now()}-${i}`,name:catName}:await API.request("/categories",{method:"POST",body:JSON.stringify({name:catName,item_type:"Produto acabado",active:true})});state.categories.push(cat)}
      const parseMoney=v=>{const n=String(v??0).replace(/\s|R\$/g,"").replace(/\.(?=\d{3}(?:\D|$))/g,"").replace(",",".");return Number(n)||0};
      const targetStock=Math.max(0,parseMoney(get("estoque","estoque inicial")));
      const payload={code,name,category_id:cat?.id||null,price:parseMoney(get("preco","preço","preco de venda","preço de venda")),cost:parseMoney(get("custo")),color:String(get("cor")).trim(),size:String(get("tamanho","medida")).trim(),min_stock:Math.max(0,parseMoney(get("estoque minimo","estoque mínimo","minimo","mínimo"))),active:true,unit:String(get("unidade")).trim()||"UN",item_type:"Produto acabado",stock:targetStock,description:String(get("descricao","descrição")).trim(),manufacturing_enabled:/^(sim|yes|1|true)$/i.test(String(get("fabricavel","fabricável","fabricacao","fabricação")))};
      let product;
      if(state.demo){product=original?Object.assign(original,payload):{id:`PRD-IMP-${Date.now()}-${i}`,...payload};}
      else product=await API.request(original?`/products/${encodeURIComponent(original.id)}`:"/products",{method:original?"PUT":"POST",body:JSON.stringify(payload)});
      if(original){const index=state.products.findIndex(x=>x.id===original.id);state.products[index]=product;updated++}else{state.products.unshift(product);added++}
      state.catalog.productExtras[product.id]={barcode:String(get("codigo de barras","barcode")).trim(),brand:String(get("marca")).trim(),material:String(get("material")).trim(),supplier:String(get("fornecedor")).trim()};
      state.catalog.media[product.id]||={photos:[],variantPhotos:{}};
      state.catalog.presentation[product.id]||={published:false,title:product.name,description:product.description||""};
    }catch(e){errors.push(`Linha ${i+2} (${code}): ${e.message||"falha na API"}`)}
  }
  logHistory("IMPORTAR","Produtos",`${added} novo(s), ${updated} atualizado(s), ${errors.length} falha(s)`);
  if(added||updated)await saveCatalogState();
  if(!state.demo)await loadAll();
  toast(`${added} cadastrado(s), ${updated} atualizado(s), ${errors.length} erro(s)`,errors.length?"error":"ok");
  if(errors.length){console.warn("Erros de importação:",errors);alert("Linhas não importadas:\n"+errors.slice(0,20).join("\n"))}
  renderEstoque();
}
async function renderProducao(){return renderOfficialOperations('production')}
function openProductionForm(){if(!state.products.length)return toast("Cadastre um produto antes de criar uma ordem de produção.","error");$("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>Nova ordem de produção</h3><p>Planejamento de fabricação.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="form-grid"><div class="field full"><label>Produto</label><select id="prodProduct">${state.products.map(p=>`<option value="${esc(p.id)}">${esc(p.code)} — ${esc(p.name)}</option>`).join("")}</select></div><div class="field"><label>Quantidade</label><input id="prodQty" type="number" min="1" value="1"></div><div class="field"><label>Prazo</label><input id="prodDue" type="date" value="${addDays(new Date(),7)}"></div><div class="field full"><label>Observações</label><textarea id="prodNotes"></textarea></div></div><div class="actions" style="margin-top:12px"><button class="primary-btn" data-action="save-production">Criar ordem</button></div></div></div></div>`;$("#modalRoot").classList.add("show")}
async function saveProduction(){const ops=opData(),pid=$("#prodProduct").value,p=state.products.find(x=>x.id===pid);const x={id:`OP-${Date.now()}`,code:nextCode("OP",ops.production),product_id:pid,product_name:p?.name||"",quantity:Number($("#prodQty").value)||1,due_date:$("#prodDue").value,status:"Aguardando",notes:$("#prodNotes").value.trim(),created_at:new Date().toISOString()};ops.production.unshift(x);await persistOps(`Ordem ${x.code}`);closeModal();renderProducao()}
async function advanceProduction(id){const stages=["Aguardando","Em produção","Acabamento","Conferência","Finalizado"],x=opData().production.find(x=>x.id===id);if(!x)return;const i=stages.indexOf(x.status);x.status=stages[Math.min(stages.length-1,i+1)];if(x.status==="Finalizado"){const p=state.products.find(p=>p.id===x.product_id);if(p){p.stock=Number(p.stock||0)+Number(x.quantity||0);let b=state.balances.find(b=>b.product_id===p.id&&b.location_id===p.location_id);if(b){b.quantity=Number(b.quantity||0)+Number(x.quantity||0);b.available_quantity=Number(b.available_quantity||0)+Number(x.quantity||0)}}}await persistOps(`${x.code}: ${x.status}`);renderProducao()}

async function renderEntregas(){return renderOfficialOperations('deliveries')}
function openDeliveryForm(){const opts=state.orders.map(o=>`<option value="${esc(o.id)}">${esc(o.code||o.id)} — ${esc(o.client_name||"")}</option>`).join("");$("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>Nova entrega</h3><p>Frete, rota e montagem.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="form-grid"><div class="field full"><label>Pedido</label><select id="delOrder"><option value="">Entrega avulsa</option>${opts}</select></div><div class="field"><label>Data</label><input id="delDate" type="date" value="${today()}"></div><div class="field"><label>Frete (R$)</label><input id="delFreight" type="number" min="0" step="0.01" value="0.00"></div><div class="field full"><label>Endereço</label><input id="delAddress"></div><div class="field"><label>Motorista</label><input id="delDriver"></div><div class="field"><label>Montador</label><input id="delAssembler"></div></div><div class="actions" style="margin-top:12px"><button class="primary-btn" data-action="save-delivery">Agendar entrega</button></div></div></div></div>`;$("#modalRoot").classList.add("show")}
async function saveDelivery(){const ops=opData(),oid=$("#delOrder").value,o=state.orders.find(x=>x.id===oid);const x={id:`DEL-${Date.now()}`,code:nextCode("ENT",ops.deliveries),order_id:oid,order_code:o?.code||"",client_name:o?.client_name||"",date:$("#delDate").value,address:$("#delAddress").value.trim()||o?.delivery_address||"",driver:$("#delDriver").value.trim(),assembler:$("#delAssembler").value.trim(),freight:Number($("#delFreight").value)||0,status:"Agendada"};ops.deliveries.unshift(x);await persistOps(`Entrega ${x.code}`);closeModal();renderEntregas()}
async function advanceDelivery(id){const stages=["Agendada","Em separação","Em rota","Montagem","Concluída"],x=opData().deliveries.find(x=>x.id===id);if(!x)return;const i=stages.indexOf(x.status);x.status=stages[Math.min(stages.length-1,i+1)];await persistOps(`${x.code}: ${x.status}`);renderEntregas()}

async function renderFinanceiro(){return renderOfficialOperations('finance')}
function openFinanceForm(kind){const label=kind==="payable"?"Conta a pagar":"Conta a receber";$("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>${label}</h3><p>Novo lançamento financeiro.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="form-grid"><div class="field full"><label>Descrição</label><input id="finDesc"></div><div class="field"><label>Valor (R$)</label><input id="finAmount" type="number" min="0" step="0.01" value="0.00"></div><div class="field"><label>Vencimento</label><input id="finDue" type="date" value="${today()}"></div></div><div class="actions" style="margin-top:12px"><button class="primary-btn" data-action="save-finance" data-kind="${kind}">Salvar lançamento</button></div></div></div></div>`;$("#modalRoot").classList.add("show")}
async function saveFinance(kind){const ops=opData(),arr=kind==="payable"?ops.payables:ops.receivables,x={id:`FIN-${Date.now()}`,description:$("#finDesc").value.trim()||"Lançamento",amount:Number($("#finAmount").value)||0,due_date:$("#finDue").value,status:"Aberto",created_at:new Date().toISOString()};arr.unshift(x);await persistOps(`${kind}: ${x.description}`);closeModal();renderFinanceiro()}
async function settleFinance(kind,id){const arr=kind==="payable"?opData().payables:opData().receivables,x=arr.find(x=>x.id===id);if(!x)return;x.status="Pago";x.paid_at=new Date().toISOString();await persistOps(`Baixa financeira: ${x.description}`);renderFinanceiro()}

function renderEquipe(){const ops=opData(),users=state.demo?ops.users:state.systemUsers;$("#appContent").innerHTML=pageHead("EQUIPE & PERMISSÕES","Acessos por função","Separe vendas, catálogo/RH, estoque, produção, financeiro, logística e administração.",`<button class="primary-btn" data-action="new-user">＋ Novo usuário</button>`)+`<div class="ops-grid">${users.map(u=>`<div class="ops-card"><div class="client-card-head"><div class="client-avatar">${initials(u.name||u.full_name)}</div><div><strong>${esc(u.name||u.full_name)}</strong><small>${esc(u.email||"")}</small></div></div><div class="product-meta"><span class="chip blue">${esc(u.role)}</span><span class="chip ${u.active!==false?"green":"red"}">${u.active!==false?"Ativo":"Inativo"}</span></div><div class="perm-grid" style="margin-top:8px">${(u.permissions||[]).map(p=>`<div class="perm-chip">✓ ${esc(p)}</div>`).join("")||`<div class="perm-chip">Permissões pelo perfil</div>`}</div></div>`).join("")||`<div class="ops-empty" style="grid-column:1/-1"><strong>Nenhum usuário adicional cadastrado</strong>Crie o acesso do RH/Catálogo, vendedores e demais setores.</div>`}</div>`}
function openUserForm(){$("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>Novo usuário</h3><p>Crie o acesso real e defina exatamente o perfil de trabalho.</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="form-grid"><div class="field"><label>Nome</label><input id="usrName"></div><div class="field"><label>E-mail</label><input id="usrEmail" type="email"></div><div class="field"><label>Senha inicial</label><input id="usrPassword" type="password" placeholder="Mínimo 8 caracteres"></div><div class="field"><label>Função</label><select id="usrRole"><option>Vendedor</option><option>Gerente</option><option>RH / Catálogo</option><option>Estoque</option><option>Produção</option><option>Financeiro</option><option>Logística</option><option>Administrador</option></select></div></div><p class="help" style="margin-top:8px">RH / Catálogo pode cadastrar fotos, organizar a vitrine e publicar produtos, sem acesso a custos e financeiro.</p><div class="actions" style="margin-top:12px"><button class="primary-btn" data-action="save-user">Salvar usuário</button></div></div></div></div>`;$("#modalRoot").classList.add("show")}
async function saveUser(){
  const name=$("#usrName").value.trim(),email=$("#usrEmail").value.trim(),password=$("#usrPassword").value,role=$("#usrRole").value;
  if(!name)return toast("Informe o nome.","error");if(!email||!/^\S+@\S+\.\S+$/.test(email))return toast("Informe um e-mail válido.","error");if(password.length<8)return toast("A senha precisa ter pelo menos 8 caracteres.","error");
  if(state.demo){const map={Vendedor:["Catálogo","Clientes","Orçamentos","Pedidos"],Gerente:["Vendas","Descontos","Relatórios","Aprovações"],"RH / Catálogo":["Catálogo","Fotos","Publicação"],Estoque:["Produtos","Estoque"],Produção:["PCP","Produção"],Financeiro:["Financeiro","Relatórios"],Logística:["Entregas","Montagem"],Administrador:["Acesso total"]};opData().users.unshift({id:`USR-${Date.now()}`,name,email,role,permissions:map[role]||[],active:true});await persistOps(`Usuário ${name}`)}
  else{const u=await API.request("/users",{method:"POST",body:JSON.stringify({full_name:name,email,password,role})});state.systemUsers.unshift(u)}
  closeModal();toast("Usuário criado");renderEquipe()
}

function renderAuditoria(){const h=state.catalog.history;$("#appContent").innerHTML=pageHead("AUDITORIA","Histórico de alterações","Rastreie criação, edição, estoque, preços, pedidos e operações.")+`<div class="table-wrap"><table><thead><tr><th>Data</th><th>Usuário</th><th>Ação</th><th>Entidade</th><th>Detalhes</th></tr></thead><tbody>${h.map(x=>`<tr class="audit-row"><td>${new Date(x.at).toLocaleString("pt-BR")}</td><td>${esc(x.user)}</td><td><strong>${esc(x.action)}</strong></td><td>${esc(x.entity)}</td><td>${esc(x.details)}</td></tr>`).join("")||`<tr><td colspan="5"><div class="ops-empty"><strong>Sem alterações registradas</strong>O histórico aparecerá conforme o sistema for usado.</div></td></tr>`}</tbody></table></div>`}

async function approveOrder(id){const reason=prompt('Motivo da aprovação comercial:');if(!reason?.trim())return;const o=await API.request(`/commercial/orders/${encodeURIComponent(id)}/approve`,{method:'POST',body:JSON.stringify({reason})});state.orders=state.orders.map(x=>x.id===id?o:x);toast('Aprovação registrada no servidor');renderPedidos()}
async function printQuote(id,internal=false){
  let q=modern.documents.find(q=>q.id===id)||state.quotes.find(q=>q.id===id)||(state.catalog.quoteMeta.preliminary||[]).find(q=>q.id===id);if(!q)throw Error('Proposta não encontrada.');
  const win=window.open('','_blank');if(!win)throw Error('Permita abrir a aba de impressão.');
  try{if(q.commercial_document&&!state.demo)q=await API.request(`/commercial/documents/${encodeURIComponent(id)}${internal?'/internal':''}`);
    const old=state.catalog.quoteMeta[id]||{},m={...old,freight:q.freight??old.freight,assembly:q.assembly??old.assembly,orderDiscount:q.discount_spec?.value??old.orderDiscount??q.discount??0,discountType:q.discount_spec?.type||'amount',payments:q.payments||old.payments||[],payment:q.payment_method,validUntil:q.valid_until,deliveryDate:q.delivery_date,notes:q.notes||old.notes};
    const html=quoteDocumentHtml(q.items||[],m,{internal,costSnapshot:q.cost_snapshot,code:q.code,client:q.client_name,address:q.delivery_address||old.deliveryAddress,reference:(q.items||[]).some(i=>i.reference),revision:q.revision,share:modern.shares[id]});win.document.open();win.document.write(html);win.document.close();
  }catch(e){win.close();throw e}
}
async function resetBlankDemo(){if(!confirm("Zerar produtos, clientes, pedidos, estoque, produção, entregas e financeiro desta demonstração?"))return;localStorage.removeItem("fp_commercial_v5_demo_state");demoData();await saveCatalogState();toast("Base zerada");go("inicio")}
function render(){updateTop();switch(state.route){case"catalog-manager":renderCatalogManager();break;case"catalogo":renderCatalogo();break;case"clientes":renderClientes();break;case"orcamentos":renderOrcamentos();break;case"pedidos":renderPedidos();break;case"estoque":renderEstoque();break;case"producao":renderProducao();break;case"entregas":renderEntregas();break;case"financeiro":renderFinanceiro();break;case"equipe":renderEquipe();break;case"auditoria":renderAuditoria();break;case"studio":renderStudio();break;case"promocoes":renderPromocoes();break;case"relatorios":renderRelatorios();break;case"configuracoes":renderConfiguracoes();renderFreightRules();break;case"integracao":renderIntegracao();break;default:renderInicio()}}
function openCart(){const drawer=$("#cartDrawer");drawer.classList.add("open");if(window.innerWidth>=840)drawer.classList.add("quote-expanded");$("#drawerBackdrop").classList.add("show");renderCart()}
function closeCart(){const drawer=$("#cartDrawer");drawer.classList.remove("open","quote-expanded");$("#drawerBackdrop").classList.remove("show")}
function lineMargin(i){const price=Number(i.unitPrice??promoPrice(i.product)),cost=Number(i.product.cost||0);return price?((price*(1-(Number(i.discount)||0)/100)-cost)/price)*100:0}
function quoteGrossTotal(){try{return cartCalculation().gross}catch{return 0}}
function quoteLineTotal(i){try{return window.FPCommercialMoney.calculate({items:[{quantity:i.qty,unit_price:i.unitPrice,discount_spec:{type:i.discountType||'percent',value:i.discount||0}}]}).total}catch{return 0}}
function quoteCostText(i){const cost=(i.variantId?state.variants.find(v=>v.id===i.variantId)?.cost:null)??i.product.cost;return !i.product._pvReference&&cost!=null?fmtBRL(cost):"Não cadastrado"}
function renderCart(){
  const m=cartMeta(),doc=modern.cartDocument;let calc,error='';
  try{calc=cartCalculation();if(calc.payment_error)error=calc.payment_error}catch(e){error=e.message;calc={gross:0,item_discount:0,subtotal:0,discount:0,total:0,remaining:0,planned_total:0,items:[]}}
  const valid=state.cart.length>0&&!error&&!modern.busy;
  $('#cartDrawer .drawer-head').innerHTML=`<div><small>FÁCIL PEDIDO · COMERCIAL V5</small><h3>${esc(doc?.code||'Novo atendimento')}</h3><p id="commercialCartStatus" class="help ${error?'error':''}" role="status">${esc(error||`${doc?'Versão '+doc.revision+' • ':''}${modern.dirty?'Alterações ainda não salvas':'Monte uma proposta sem movimentar estoque'}`)}</p></div><div class="actions"><button class="secondary-btn" data-action="save-commercial-draft" ${valid?'':'disabled'}>Salvar rascunho</button><button class="primary-btn" data-action="create-quote" ${valid?'':'disabled'}>Salvar proposta</button><button class="icon-btn" data-close-drawer aria-label="Fechar carrinho">×</button></div>`;
  $('#cartDrawerBody').innerHTML=`<section class="quote-panel"><div class="modern-cart-context"><div class="field"><label for="cartClient">Cliente do atendimento</label><select id="cartClient"><option value="">Selecione um cliente</option>${state.clients.map(c=>`<option value="${esc(c.id)}" ${state.selectedClient?.id===c.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></div><div class="field"><label for="cartValidUntil">Validade da proposta</label><input id="cartValidUntil" type="date" value="${esc(m.validUntil)}"></div><button class="secondary-btn" data-action="commercial-documents">Retomar rascunho</button></div><div class="modern-cart-list">${state.cart.map((i,n)=>`<article class="modern-cart-item" data-cart-line="${n}"><img src="${esc(cartPhoto(i.product,i.variantId))}" loading="lazy" alt="${esc(i.product.name)}"><div class="modern-item-name"><strong>${esc(i.product.name)}</strong><small>${esc(i.product.code||'Sem código')} · ${i.product._pvReference?'Referência — proposta preliminar':'Produto oficial'}</small><small>${i.variantId?'Variação: '+esc(state.variants.find(v=>v.id===i.variantId)?.sku||i.variantId):''}</small><button class="text-btn" data-action="quote-open-product" data-index="${n}">Ver detalhes e condições</button>${canSeeCost()?`<small class="internal-cost">Custo unitário (interno): ${quoteCostText(i)}</small>`:''}</div><div class="field"><label for="cartQty${n}">Quantidade</label><div class="modern-qty"><button data-action="cart-dec" data-index="${n}" aria-label="Diminuir quantidade de ${esc(i.product.name)}">−</button><input id="cartQty${n}" aria-label="Quantidade de ${esc(i.product.name)}" data-modern-qty="${n}" type="number" min="0.001" max="100000" step="0.001" value="${Number(i.qty)}"><button data-action="cart-inc" data-index="${n}" aria-label="Aumentar quantidade de ${esc(i.product.name)}">+</button></div></div><div class="field"><label for="cartUnit${n}">Unitário (R$)</label><input id="cartUnit${n}" data-modern-unit="${n}" type="number" min="0" step="0.01" value="${Number(i.unitPrice||0)}"><small>${i.priceSource==='client_price_table'?'Tabela do cliente':'Preço do produto / negociado'}</small></div><div class="field"><label for="cartDisc${n}">Desconto do item</label><div class="modern-discount"><input id="cartDisc${n}" data-modern-discount="${n}" type="number" min="0" step="0.01" value="${Number(i.discount||0)}"><select aria-label="Unidade do desconto de ${esc(i.product.name)}" data-modern-discount-type="${n}"><option value="percent" ${i.discountType!=='amount'?'selected':''}>%</option><option value="amount" ${i.discountType==='amount'?'selected':''}>R$ no item</option></select></div></div><div class="modern-item-total"><small>Total do item</small><strong data-modern-line-total="${n}">${fmtBRL(calc.items[n]?.total||0)}</strong><button class="text-btn danger" data-action="cart-remove" data-index="${n}" aria-label="Remover ${esc(i.product.name)}">Remover</button></div></article>`).join('')||'<div class="empty-state">Adicione produtos oficiais ou consulte o catálogo de referências.</div>'}</div><div class="actions modern-cart-actions"><button class="secondary-btn" data-action="add-more-product">＋ Adicionar produto</button>${modern.undo?'<button class="secondary-btn" data-action="undo-cart-remove">Desfazer remoção</button>':''}<button class="text-btn" data-action="new-commercial-cart">Novo atendimento</button></div>${cartHasReference()?'<p class="quote-notice">Esta proposta contém referências de catálogo. Para gerar pedido, primeiro vincule os itens ao cadastro oficial.</p>':''}</section>`;
  $('#cartDrawerFoot').innerHTML=`<div class="modern-cart-bottom"><div class="modern-cart-forms"><section class="quote-panel"><h4>Entrega e montagem</h4><div class="form-grid"><div class="field"><label for="cartCep">CEP</label><input id="cartCep" inputmode="numeric" maxlength="9" placeholder="00000-000" value="${esc(m.cep)}"></div><div class="field"><label for="cartNumber">Número</label><input id="cartNumber" placeholder="Número ou S/N" value="${esc(m.number)}"></div><div class="field full"><button class="secondary-btn" data-action="lookup-cart-cep">Buscar endereço pelo CEP</button><small id="cartCepStatus">Você também pode preencher o endereço manualmente.</small></div><div class="field full"><label for="cartStreet">Endereço / rua</label><input id="cartStreet" value="${esc(m.street)}"></div><div class="field"><label for="cartDistrict">Bairro</label><input id="cartDistrict" value="${esc(m.district)}"></div><div class="field"><label for="cartCity">Cidade</label><input id="cartCity" value="${esc(m.city)}"></div><div class="field"><label for="cartUf">UF</label><input id="cartUf" maxlength="2" value="${esc(m.uf)}"></div><div class="field"><label for="cartComplement">Complemento</label><input id="cartComplement" value="${esc(m.complement)}"></div><div class="field"><label for="cartDeliveryDate">Data de entrega combinada</label><input id="cartDeliveryDate" type="date" value="${esc(m.deliveryDate)}"></div><div class="field"><label for="cartFreight">Frete (R$)</label><input id="cartFreight" type="number" min="0" step="0.01" value="${Number(m.freight||0)}"><small>${esc(m.freightLabel||'Valor combinado manualmente')}</small></div><div class="field"><label for="cartAssembly">Montagem (R$)</label><input id="cartAssembly" type="number" min="0" step="0.01" value="${Number(m.assembly||0)}"></div><div class="field"><label for="cartDistance">Distância informada (km, opcional)</label><input id="cartDistance" type="number" min="0" step="0.1" value="${esc(m.distance||'')}"></div><button class="secondary-btn" data-action="quote-freight">Consultar regra de frete</button></div></section><section class="quote-panel"><h4>Plano de pagamentos</h4><p class="help">Valores previstos; não representam cobrança ou recebimento.</p><div class="field"><label for="cartPayment">Condição comercial</label><select id="cartPayment">${['PIX','À vista','Dinheiro','Cartão','Boleto','Transferência','A combinar'].map(t=>`<option ${m.payment===t?'selected':''}>${t}</option>`).join('')}</select></div><div class="modern-payments">${m.payments.map((p,n)=>`<div class="modern-payment"><div class="field"><label>Forma<select data-pay-method="${n}">${['PIX','Dinheiro','Cartão','Boleto','Transferência'].map(t=>`<option ${p.method===t?'selected':''}>${t}</option>`).join('')}</select></label></div><div class="field"><label>Valor (R$)<input data-modern-pay-value="${n}" type="number" min="0" step="0.01" value="${Number(p.amount||0)}"></label></div><div class="field"><label>Data prevista<input data-pay-date="${n}" type="date" value="${esc(p.date||'')}"></label></div><button class="icon-btn danger" data-action="remove-payment" data-index="${n}" aria-label="Remover parcela ${n+1}">×</button></div>`).join('')}</div><button class="secondary-btn" data-action="add-payment">＋ Adicionar pagamento</button><details class="modern-installments"><summary>Dividir o saldo em parcelas</summary><div class="form-grid"><div class="field"><label for="cartInstallments">Número de parcelas</label><input id="cartInstallments" type="number" min="1" max="120" value="${Number(m.installments||pricePolicy().installments||1)}"></div><div class="field"><label for="cartFirstPayment">Primeiro vencimento</label><input id="cartFirstPayment" type="date" value="${esc(m.firstPaymentDate||'')}"></div><button class="secondary-btn" data-action="generate-installments">Distribuir saldo</button></div></details><div class="field"><label for="cartNotes">Observações e condições</label><textarea id="cartNotes" rows="3">${esc(m.notes)}</textarea></div></section></div><aside class="quote-panel modern-cart-summary"><h4>Resumo da proposta</h4><div id="modernTotals">${modernTotalsHtml(calc)}</div><div class="field"><label for="cartOrderDiscount">Desconto geral</label><div class="modern-discount"><input id="cartOrderDiscount" type="number" min="0" step="0.01" value="${Number(m.orderDiscount||0)}"><select id="cartDiscountType" aria-label="Unidade do desconto geral"><option value="amount" ${m.discountType!=='percent'?'selected':''}>R$</option><option value="percent" ${m.discountType==='percent'?'selected':''}>%</option></select></div></div><p class="help">${pricePolicy().source==='client_policy'?'Condição do cliente':'Condição padrão da empresa'} · À vista: ${fmtBRL(calc.subtotal*(1-Number(pricePolicy().pixDiscount||0)/100))} nos produtos (${Number(pricePolicy().pixDiscount||0)}%). Simulação; o desconto só altera o total quando aplicado.</p><button class="text-btn" data-action="apply-cash-discount" ${valid?'':'disabled'}>Aplicar condição à vista</button><div class="quote-actions-stack"><button class="primary-btn" data-action="create-quote" ${valid?'':'disabled'}>Salvar proposta</button><button class="secondary-btn" data-action="create-order" ${valid&&!cartHasReference()?'':'disabled'} title="Cria rascunho; confirmação é uma etapa separada">Criar rascunho de pedido</button><button class="secondary-btn" data-action="print-cart" ${valid?'':'disabled'}>PDF do cliente</button>${canSeeCost()?`<button class="secondary-btn" data-action="print-cart-internal" ${valid?'':'disabled'}>PDF interno com custo</button>`:''}<button class="secondary-btn" data-action="share-cart" ${valid?'':'disabled'}>Link e QR da proposta</button></div></aside></div>`;
  scheduleCartQuote();
}
async function addToCart(id,variantId=null){
  if(modern.busy)throw Error('Aguarde a conferência dos preços do cliente.');
  const p=state.products.find(p=>p.id===id)||pvShowcase.rows.find(p=>p.id===id);if(!p)return;
  if(!canUseSales()&&!state.demo)throw Error('Sem permissão para orçamentos.');
  if(modern.cartDocument?.converted_order_id)modern.cartDocument=null;
  const v=variantId?state.variants.find(v=>v.id===variantId):null;
  const base=p._pvReference?(p.review_needed?0:Number(p.price||0)):await clientPrice(p);
  const source=modern.priceSources[`${state.selectedClient?.id||''}:${p.id}`]||'product_default';
  const price=v?.price!=null&&source==='product_default'?Number(v.price):base;
  const item=state.cart.find(i=>i.product.id===id&&(i.variantId||'')===(variantId||''));
  if(item)item.qty++;else state.cart.push({product:p,variantId,qty:1,discount:0,discountType:'percent',unitPrice:price,priceSource:state.selectedClient?(modern.priceSources[`${state.selectedClient.id}:${p.id}`]||'product_default'):'product_default'});
  markCartDirty();updateTop();closeModal();openCart();
}
async function openProduct(id,variantId=null){
  const p=state.products.find(x=>x.id===id);if(!p)return;state.recent=[id,...state.recent.filter(x=>x!==id)].slice(0,12);
  const vars=state.variants.filter(v=>v.product_id===id),chosen=variantId?vars.find(v=>v.id===variantId):null,pres=presentationFor(id),photos=chosen?mediaForVariant(id,chosen.id):mediaFor(id),gallery=photos.length?photos:[photoFor(p,chosen?.id)],balances=stockRows().filter(b=>b.product_id===id&&(chosen?b.variant_id===chosen.id:true)),basePrice=await clientPrice(p),price=chosen?.price!=null&&(modern.priceSources[`${state.selectedClient?.id||''}:${p.id}`]||'product_default')==='product_default'?Number(chosen.price):basePrice;
  const suggestion=bestStockLocation(p,1);
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>${esc(pres.title||p.name)}</h3><p>${esc(p.code)} ${chosen?`• ${esc(chosen.sku)}`:""}</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="product-detail">
  <div><div class="gallery-main" id="galleryMain"><img src="${safePhotoUrl(gallery[0])}"></div><div class="gallery-thumbs">${gallery.map((src,i)=>`<button class="gallery-thumb" data-gallery-src="${safePhotoUrl(src)}"><img src="${safePhotoUrl(src)}"></button>`).join("")}</div></div>
  <div class="detail-info"><div class="product-meta"><span class="chip">${esc(categoryName(p))}</span><span class="chip ${stockClass(p)}">${chosen?available(p,chosen.id):available(p)} disponível</span>${pres.status&&pres.status!=="Ativo"?`<span class="chip violet">${esc(pres.status)}</span>`:""}</div><h2>${esc(pres.title||p.name)}</h2><p class="product-sub">${esc(pres.subtitle||[p.color,p.size].filter(Boolean).join(" • "))}</p>
  <div class="detail-price">${fmtBRL(price)}</div><button class="secondary-btn" data-action="product-price-eye" data-id="${esc(p.id)}" aria-label="Ver preço normal, à vista e valor custo">👁 Ver condições e V.C.</button><div class="quote-price-info hidden" id="productPriceInfo"><strong>Valor normal:</strong> ${fmtBRL(price)}<br><strong>À vista (PIX):</strong> ${fmtBRL(price*(1-Number(pricePolicy().pixDiscount||0)/100))}<br>${canSeeCost()?`<strong>V.C. (custo):</strong> ${(chosen?.cost??p.cost)!=null?fmtBRL(chosen?.cost??p.cost):"Não cadastrado"}`:"V.C. disponível apenas para perfil autorizado"}</div>${state.selectedClient?`<span class="chip green">Preço para ${esc(state.selectedClient.name)}</span>`:""}
  <div class="market-condition-box"><strong>Condições comerciais</strong><div class="green">PIX: ${fmtBRL(price*(1-Number(pricePolicy().pixDiscount||0)/100))}</div><div>${Number(pricePolicy().installments||1)}x de ${fmtBRL((price*(1+Number(pricePolicy().installmentFee||0)/100))/(Number(pricePolicy().installments||1)||1))}</div><div style="margin-top:6px">${suggestion?`Retirada sugerida: <b>${esc(locationName(suggestion.location_id))}</b>`:"Consulte disponibilidade por unidade."}</div></div>
  ${vars.length?`<div style="margin-top:12px"><strong style="font-size:9px">Variações</strong><div class="variant-grid">${vars.map(v=>`<button class="variant-btn ${chosen?.id===v.id?"active":""}" data-action="choose-variant" data-product="${esc(p.id)}" data-id="${esc(v.id)}">${esc(v.color||"Sem cor")} • ${esc(v.size||"Padrão")} • ${available(p,v.id)} un.</button>`).join("")}</div></div>`:""}
  <p style="font-size:10px;color:var(--muted);line-height:1.6">${esc(pres.description||p.description||"Sem descrição.")}</p>${(pres.highlights||[]).length?`<div class="product-meta">${pres.highlights.map(x=>`<span class="chip blue">✓ ${esc(x)}</span>`).join("")}</div>`:""}
  <div class="stock-box"><strong style="font-size:9px">Estoque por local</strong>${balances.length?balances.map(b=>`<div class="stock-row"><span>${esc(locationName(b.location_id))}</span><strong>${Number(b.available_quantity??(Number(b.quantity||0)-Number(b.reserved_quantity||0))).toLocaleString("pt-BR")}</strong></div>`).join(""):`<div class="stock-row"><span>${esc(locationName(p.location_id))}</span><strong>${available(p)}</strong></div>`}${suggestion?`<div class="stock-row"><span>Sugestão de retirada</span><strong>${esc(locationName(suggestion.location_id))}</strong></div>`:""}</div>
  <div class="detail-actions"><button class="secondary-btn" data-action="share-product" data-id="${esc(p.id)}">WhatsApp</button><button class="secondary-btn" data-action="copy-product-link" data-id="${esc(p.id)}">Copiar link</button><button class="secondary-btn" data-action="favorite" data-id="${esc(p.id)}">${state.favorites.has(p.id)?"♥":"♡"}</button><button class="secondary-btn" data-action="presentation-add" data-id="${esc(p.id)}">＋ Apresentação</button><button class="primary-btn" data-action="add" data-id="${esc(p.id)}" data-variant="${esc(chosen?.id||"")}">Adicionar</button></div>
  <div style="margin-top:18px"><strong style="font-size:9px">Combine com</strong><div class="product-meta" style="margin-top:8px">${state.products.filter(x=>x.id!==p.id&&(x.category_id===p.category_id||categoryName(x)===categoryName(p))).slice(0,3).map(x=>`<button class="variant-btn" data-action="detail" data-id="${esc(x.id)}">${esc(x.name)} • ${fmtBRL(promoPrice(x))}</button>`).join("")||`<span class="help">Sem relacionados cadastrados.</span>`}</div></div>
  </div></div></div></div></div>`;$("#modalRoot").classList.add("show");
}
function closeModal(){$("#modalRoot").classList.remove("show");$("#modalRoot").innerHTML=""}
async function uploadSupabase(file,productId){
  const url=localStorage.getItem("fp_supabase_url"),key=localStorage.getItem("fp_supabase_anon"),bucket=localStorage.getItem("fp_supabase_bucket")||"product-media";
  if(!url||!key)throw new Error("Supabase Storage não configurado.");
  const ext=(file.name.split(".").pop()||"jpg").toLowerCase(),path=`products/${productId}/${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;
  const res=await fetch(`${url.replace(/\/+$/,"")}/storage/v1/object/${encodeURIComponent(bucket)}/${path}`,{method:"POST",headers:{Authorization:`Bearer ${key}`,apikey:key,"Content-Type":file.type||"image/jpeg","x-upsert":"false"},body:file});
  if(!res.ok)throw new Error(`Falha no Storage (${res.status}). Verifique bucket/policies.`);
  return `${url.replace(/\/+$/,"")}/storage/v1/object/public/${encodeURIComponent(bucket)}/${path}`;
}
async function fileToDataUrl(file){
  return new Promise((resolve,reject)=>{const r=new FileReader();r.onerror=reject;r.onload=()=>{const img=new Image();img.onload=()=>{const max=CFG.MAX_PHOTO_SIDE,scale=Math.min(1,max/Math.max(img.width,img.height)),c=document.createElement("canvas");c.width=Math.round(img.width*scale);c.height=Math.round(img.height*scale);c.getContext("2d").drawImage(img,0,0,c.width,c.height);resolve(c.toDataURL("image/jpeg",CFG.JPEG_QUALITY))};img.onerror=reject;img.src=r.result};r.readAsDataURL(file)});
}
async function uploadErpMedia(file,productId){
  const dataUrl=await fileToDataUrl(file);
  const result=await API.request("/media",{method:"POST",body:JSON.stringify({product_id:productId,filename:file.name||"foto.jpg",data_url:dataUrl})});
  if(Number.isInteger(result.revision))state.catalogRevision=result.revision;return result.url || `${API.base()}${result.path.startsWith("/api/v1/")?result.path.slice(7):result.path}`;
}
async function deleteErpMedia(src){
  if(state.demo||!src||!API.base())return false;
  // Existing uploads may reference the original Render service; delete only via current authenticated API.
  const match=String(src).match(/\/api\/v1\/media\/([a-f0-9-]{36})(?:[?#]|$)/i);
  if(!match)return false;
  await API.request(`/media/${encodeURIComponent(match[1])}`,{method:"DELETE"});
  await loadCatalogState();
  return true;
}
async function storePhoto(file,productId){
  // On real systems, all accounts share the PostgreSQL-backed media, never browser-local Supabase settings.
  if(state.demo)return fileToDataUrl(file);
  return uploadErpMedia(file,productId);
}
async function replaceStudioPhoto(file,index){
  if(!file)return;
  const p=state.products.find(x=>x.id===state.studioProductId);
  if(!p||!canManageCatalog())throw new Error("Sem permissão para trocar foto");
  if(!["image/jpeg","image/png","image/webp"].includes(file.type))throw new Error("Use JPG, PNG ou WebP");
  if(!mediaFor(p.id)[index])throw new Error("Foto não encontrada; atualize a galeria");
  const draft={};for(const id of ["studioTitle","studioSubtitle","studioStatus","studioFeatured","studioPublished","studioWarranty","studioDescription","studioHighlights","studioTags"]){const el=document.getElementById(id);if(el)draft[id]=el.value;}
  if(state.demo){
    mediaFor(p.id)[index]=await fileToDataUrl(file);
    await saveCatalogState();
  }else{
    const dataUrl=await fileToDataUrl(file);
    // Atomic replacement: image content and gallery entry are updated together in Postgres.
    await API.request("/media/replace",{method:"POST",body:JSON.stringify({product_id:p.id,index,filename:file.name||"foto.jpg",data_url:dataUrl})});
    await loadCatalogState();
  }
  renderStudio();
  for(const [id,value] of Object.entries(draft)){const el=document.getElementById(id);if(el)el.value=value;}
  toast("Foto substituída e salva no catálogo compartilhado");
}
async function saveStudio(){
  const p=state.products.find(x=>x.id===state.studioProductId);if(!p)return;
  if(!canManageCatalog())throw new Error("Sem permissão para editar o catálogo.");
  if($("#studioPublished")?.value==="true"&&!mediaFor(p.id).length)throw new Error("Adicione ao menos uma foto antes de publicar o produto.");
  state.catalog.presentation[p.id]={...(presentationFor(p.id)),title:$("#studioTitle").value.trim(),subtitle:$("#studioSubtitle").value.trim(),status:$("#studioStatus").value,featured:$("#studioFeatured").value==="true",published:canPublishCatalog()?$("#studioPublished").value==="true":presentationFor(p.id).published===true,warranty:$("#studioWarranty").value.trim(),description:$("#studioDescription").value.trim(),highlights:$("#studioHighlights").value.split(",").map(x=>x.trim()).filter(Boolean),tags:$("#studioTags").value.split(",").map(x=>x.trim()).filter(Boolean)};
  logHistory("SALVAR","Produto",p.name);await saveCatalogState();toast("Catálogo salvo");renderStudio();
}
async function createQuote(){return saveCommercialDocument('quote')}
async function createOrderFromCart(){
  if(modern.saving||modern.busy)throw Error('Aguarde a conferência do carrinho.');
  if(cartHasReference())throw Error('Produtos de referência precisam de cadastro oficial para gerar pedido.');
  const doc=await saveCommercialDocument('quote',false);
  await quoteToOrder(doc.id);
}
async function quoteToOrder(id){
  if(window._fpConvertingQuote)throw Error('Conversão em andamento.');
  window._fpConvertingQuote=true;
  try{
  let d=modern.documents.find(q=>q.id===id)||state.quotes.find(q=>q.id===id);
  if(!d?.commercial_document){await openCommercialDocument(id,true);d=await saveCommercialDocument('quote',false)}
  if(!d)throw Error('Proposta não encontrada.');
  let order;
  if(state.demo){order={...d,id:`DEMO-ORDER-${d.id}`,code:`PED-${d.code}`,status:'Rascunho',source_document_id:d.id};}
  else order=await API.request(`/commercial/documents/${encodeURIComponent(d.id)}/convert`,{method:'POST',body:JSON.stringify({base_revision:d.revision})});
  state.orders=[order,...state.orders.filter(o=>o.id!==order.id)];
  await loadCommercialDocuments();modern.dirty=false;modern.cartDocument=null;state.cart=[];state.cartMeta=null;updateTop();closeCart();go('pedidos');toast('Rascunho de pedido criado. Nenhuma venda, reserva ou cobrança foi concluída.');
  }finally{window._fpConvertingQuote=false}
}
async function confirmOrder(id){
  const o=state.orders.find(x=>x.id===id);if(!o)return;if(o.status==="Aguardando aprovação")return toast("Aprove o pedido antes de confirmar.","error");
  if(state.demo){
    const ops=opData();
    for(const item of o.items||[]){const p=state.products.find(p=>p.id===item.product_id);if(!p)continue;const need=Number(item.quantity||0),avail=available(p),reserve=Math.min(avail,need);let b=state.balances.find(b=>b.product_id===p.id&&(!p.location_id||b.location_id===p.location_id));if(b){b.reserved_quantity=Number(b.reserved_quantity||0)+reserve;b.available_quantity=Math.max(0,Number(b.quantity||0)-Number(b.reserved_quantity||0))}p.reserved_stock=Number(p.reserved_stock||0)+reserve;const shortage=Math.max(0,need-avail);if(shortage&&p.manufacturing_enabled&&state.catalog.settings.autoCreateProduction){ops.production.unshift({id:`OP-${Date.now()}-${p.id}`,code:nextCode("OP",ops.production),product_id:p.id,product_name:p.name,quantity:shortage,due_date:addDays(new Date(),7),status:"Aguardando",notes:`Gerada pelo pedido ${o.code}`,order_id:o.id,created_at:new Date().toISOString()})}}
    if(state.catalog.settings.autoCreateReceivable&&!ops.receivables.some(x=>x.order_id===o.id))ops.receivables.unshift({id:`REC-${Date.now()}`,description:`Pedido ${o.code} — ${o.client_name}`,amount:Number(o.total||0),due_date:today(),status:"Aberto",order_id:o.id,created_at:new Date().toISOString()});
    if(state.catalog.settings.autoCreateDelivery&&!ops.deliveries.some(x=>x.order_id===o.id))ops.deliveries.unshift({id:`DEL-${Date.now()}`,code:nextCode("ENT",ops.deliveries),order_id:o.id,order_code:o.code,client_name:o.client_name,date:addDays(new Date(),1),address:o.delivery_address||"",driver:"",assembler:"",freight:Number(o.freight||0),status:"Agendada"});
    o.status="Confirmado";logHistory("CONFIRMAR","Pedido",`${o.code} • estoque/financeiro/logística`);await saveCatalogState();toast("Pedido confirmado e módulos integrados atualizados");renderPedidos();return;
  }
  const result=await API.request(`/sales-orders/${encodeURIComponent(id)}/confirm`,{method:"POST",body:JSON.stringify({auto_create_production:state.catalog.settings.autoCreateProduction!==false,create_receivable:state.catalog.settings.autoCreateReceivable!==false})});const idx=state.orders.findIndex(x=>x.id===id);if(idx>=0)state.orders[idx]=result.order;toast(result.integration_warnings?.length?"Pedido com integração parcial. Confira o ERP e os avisos de sincronização.":result.production_orders_created?.length?`Confirmado e ${result.production_orders_created.length} OP(s) criada(s)`:"Pedido confirmado e estoque reservado");await loadAll();renderPedidos();
}
function shareTextProduct(p){const s=state.catalog.settings,pr=priceDisplay(p);return `${s.companyName}\n${presentationFor(p.id).title||p.name}\n${presentationFor(p.id).subtitle||""}\nPreço: ${fmtBRL(pr.final)}\nEstoque: ${available(p)}\n${presentationFor(p.id).description||""}`.trim()}
function openWhatsApp(text){window.open(`https://wa.me/?text=${encodeURIComponent(text)}`,"_blank","noopener")}
async function shareCart(){const d=await saveCommercialDocument('quote',false);await shareCommercialDocument(d.id)}
function quoteDocumentHtml(items,meta,opts={}){
  const internal=!!opts.internal&&canSeeCost(),payload={items:items.map(i=>({product_id:i.product?.id||i.product_id,product_name:[i.product?.name||i.product_name||i.description,i.variant_label||(i.variantId?state.variants.find(v=>v.id===i.variantId)?.sku:'')].filter(Boolean).join(' — '),product_ref:i.product?.code||i.product_ref||'',quantity:i.qty??i.quantity,unit_price:i.unitPrice??i.unit_price,discount_spec:i.discount_spec||{type:i.discountType||'percent',value:i.discount??i.discount_percent??0}})),discount_spec:{type:meta.discountType||'amount',value:meta.orderDiscount||0},freight:meta.freight||0,assembly:meta.assembly||0,payments:meta.payments||[]};
  const c=window.FPCommercialMoney.calculate(payload),qr=opts.share?.qr_url||`${API.base()}/public/catalog-qr`,company=state.catalog.settings.companyName||'Fácil Pedido';
  const costs=opts.costSnapshot;
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(opts.code||'Proposta Fácil Pedido')}</title><style>body{font:14px Arial,sans-serif;color:#172554;padding:28px;margin:0}main{max-width:960px;margin:auto}header{display:flex;justify-content:space-between;border-bottom:5px solid #ffe600;padding-bottom:16px;gap:20px}h1{font-size:25px;margin:0}small{color:#64748b;display:block}table{width:100%;border-collapse:collapse;margin:24px 0}th,td{padding:10px;text-align:left;border-bottom:1px solid #e2e8f0;font-size:12px}th{background:#f8fafc}thead{display:table-header-group}tr{break-inside:avoid}.modern-totals{max-width:400px;margin-left:auto}.modern-totals div{display:flex;justify-content:space-between;padding:7px}.modern-totals dd{font-weight:bold}.total{font-size:20px;border-top:2px solid #172554}button{padding:12px;background:#ffe600;border:0;border-radius:10px;font-weight:bold}.notice{padding:12px;background:#fff7d6}.notes{white-space:pre-wrap}img{width:105px;height:105px}@media print{button{display:none}body{padding:0}@page{size:A4;margin:14mm}}@media(max-width:600px){body{padding:12px}td,th{padding:6px;font-size:11px}}</style></head><body><main><button onclick="window.print()">Imprimir / Salvar PDF</button><header><div><h1>${esc(company)}</h1><p>${internal?'DOCUMENTO INTERNO COM CUSTO':'PROPOSTA COMERCIAL'} · ${esc(opts.code||'Prévia não salva')}</p><small>Validade: ${esc(meta.validUntil||'A combinar')} ${opts.revision?'· Versão '+opts.revision:''}</small></div><div><img src="${esc(qr)}" alt="QR ${opts.share?'da proposta':'do catálogo'}"><small>QR ${opts.share?'da proposta':'do catálogo'}</small></div></header><p><strong>Cliente:</strong> ${esc(opts.client||state.selectedClient?.name||'A definir')}<br><strong>Entrega:</strong> ${esc(opts.address||cartShippingAddress()||'A combinar')}<br><strong>Data de entrega:</strong> ${esc(meta.deliveryDate||'A combinar')}<br><strong>Condição:</strong> ${esc(meta.payment||'A combinar')}</p>${opts.reference?'<p class="notice">Pré-orçamento com referências: cadastro e preços sujeitos a validação. Sem pedido ou reserva.</p>':''}<table><thead><tr><th>Produto / código</th><th>Qtd.</th><th>Unitário</th><th>Desconto</th>${internal?'<th>Custo unit.</th>':''}<th>Total</th></tr></thead><tbody>${c.items.map((i,n)=>`<tr><td><strong>${esc(i.product_name)}</strong><small>${esc(i.product_ref)}</small></td><td>${i.quantity}</td><td>${fmtBRL(i.unit_price)}</td><td>${fmtBRL(i.discount_spec.amount)}</td>${internal?`<td>${costs?(costs[n]?.unit_cost!=null?fmtBRL(costs[n].unit_cost):'Não cadastrado'):(Number(items[n]?.product?.cost)>0?fmtBRL(items[n].product.cost):'Não cadastrado')}</td>`:''}<td>${fmtBRL(i.total)}</td></tr>`).join('')}</tbody></table>${modernTotalsHtml(c)}<h3>Pagamentos previstos</h3><table><thead><tr><th>Forma</th><th>Valor</th><th>Data prevista</th><th>Situação</th></tr></thead><tbody>${(meta.payments||[]).map(p=>`<tr><td>${esc(p.method)}</td><td>${fmtBRL(p.amount)}</td><td>${esc(p.date||'A definir')}</td><td>Planejado</td></tr>`).join('')||'<tr><td colspan="4">A combinar.</td></tr>'}</tbody></table><h3>Observações e condições</h3><p class="notes">${esc(meta.notes||'—')}</p><footer><small>${internal?'USO INTERNO • Custo histórico quando disponível; não compartilhar com cliente.':'Este documento não realiza cobrança nem comprova recebimento.'}</small></footer></main></body></html>`;
}
function printDraft(items,meta,opts={}){const tab=window.open("","_blank");if(!tab){toast("Permita pop-ups para abrir o PDF.","error");return}tab.document.open();tab.document.write(quoteDocumentHtml(items,meta,opts));tab.document.close();tab.focus()}
async function printCart(internal=false){
  if(!state.cart.length||!cartAllPriced())throw Error('Adicione itens e defina seus valores.');
  if(modern.cartDocument&&!modern.dirty)return printQuote(modern.cartDocument.id,internal);
  const tab=window.open('','_blank');if(!tab)throw Error('Permita abrir a aba de impressão.');
  try{
    if(!state.demo)await API.request('/commercial/calculate',{method:'POST',body:JSON.stringify(cartPayload())});
    const costs=internal?state.cart.map(i=>({unit_cost:(i.variantId?state.variants.find(v=>v.id===i.variantId)?.cost:null)??i.product.cost})):undefined;
    const html=quoteDocumentHtml(state.cart,clone(cartMeta()),{internal,reference:cartHasReference(),costSnapshot:costs});
    tab.document.open();tab.document.write(html);tab.document.close();tab.focus();
  }catch(e){tab.close();throw e}
}

function printPreQuote(id){const q=(state.catalog.quoteMeta.preliminary||[]).find(x=>x.id===id);if(!q)return;printDraft(q.items,{...state.catalog.quoteMeta[id],payment:q.payment_method},{reference:true,client:q.client_name,code:q.code,address:state.catalog.quoteMeta[id]?.deliveryAddress});}
function productLink(p){const url=new URL(location.origin+"/comercial/");if(p?._pvReference)url.searchParams.set("pv_product",p.id);else url.searchParams.set("product",p.id);return url.toString()}
async function copyProductLink(p){if(!p)throw Error('Produto não encontrado');const url=productLink(p);try{await navigator.clipboard.writeText(url);toast('Link copiado. O destinatário pode precisar fazer login.')}catch{prompt('Copie o link (pode exigir login):',url)}}
async function lookupCartCep(){const m=cartMeta(),raw=String($("#cartCep")?.value||m.cep||"").replace(/\D/g,"");if(raw.length!==8){toast("Digite um CEP com 8 números.","error");return}const status=$("#cartCepStatus");if(status)status.textContent="Consultando CEP…";try{let data;try{const r=await fetch(`https://viacep.com.br/ws/${raw}/json/`);if(!r.ok)throw Error("CEP indisponível");data=await r.json();if(data.erro)throw Error("CEP não encontrado") }catch{const r=await fetch(`https://brasilapi.com.br/api/cep/v1/${raw}`);if(!r.ok)throw Error("CEP não encontrado");const b=await r.json();data={logradouro:b.street,bairro:b.neighborhood,localidade:b.city,uf:b.state}}m.cep=raw.slice(0,5)+"-"+raw.slice(5);m.street=String(data.logradouro||"");m.district=String(data.bairro||"");m.city=String(data.localidade||"");m.uf=String(data.uf||"");renderCart();toast("Endereço localizado. Informe o número e confirme o frete.")}catch(err){if(status)status.textContent="Não foi possível consultar. Preencha o endereço manualmente.";toast(String(err.message||err),"error")}}

function startPresentation(ids=null){
  modern.presentationMode=true;
  const list=(ids?.length?ids:state.presentationIds.length?state.presentationIds:filteredProducts().slice(0,12).map(p=>p.id));state.presentationIds=list;
  $("#presentationRoot").innerHTML=`<div class="presentation-toolbar"><div><strong>${esc(state.catalog.settings.companyName)}</strong> <small>• modo apresentação • ${list.length} produto(s)</small></div><div class="actions"><button class="secondary-btn" data-action="presentation-share">Compartilhar seleção</button><button class="secondary-btn" data-action="presentation-print">Imprimir / PDF</button><button class="primary-btn" data-action="close-presentation">Sair</button></div></div><div class="presentation-products">${list.map(id=>state.products.find(p=>p.id===id)).filter(Boolean).map(productCard).join("")}</div>`;$("#presentationRoot").classList.remove("hidden")
}
function closePresentation(){modern.presentationMode=false;$("#presentationRoot").classList.add("hidden");$("#presentationRoot").innerHTML=""}
function openClient360(id){
  const c=state.clients.find(x=>x.id===id);if(!c)return;const q=state.quotes.filter(x=>x.client_id===id),o=state.orders.filter(x=>x.client_id===id),crm=state.catalog.crm[id]||{},cs=state.clientStates.find(x=>(x.server?.id||x.id)===id),prices=cs?.price_table||[];
  $("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card"><div class="modal-head"><div><h3>${esc(c.name)}</h3><p>${esc(c.document||"")}</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="grid stats-grid"><div class="stat-card"><small>Limite</small><strong>${fmtBRL(c.credit_limit)}</strong></div><div class="stat-card"><small>Orçamentos</small><strong>${q.length}</strong></div><div class="stat-card"><small>Pedidos</small><strong>${o.length}</strong></div><div class="stat-card"><small>Comprado</small><strong>${fmtBRL(o.reduce((s,x)=>s+Number(x.total||0),0))}</strong></div></div><div class="grid home-grid"><div class="panel"><h3>CRM</h3><div class="field"><label>Etapa</label><select id="clientCrmStage">${["Novo contato","Orçamento","Negociação","Cliente","Perdido"].map(x=>`<option ${x===(crm.stage||"Novo contato")?"selected":""}>${x}</option>`).join("")}</select></div><div class="field" style="margin-top:8px"><label>Observações</label><textarea id="clientCrmNotes">${esc(crm.notes||"")}</textarea></div><button class="primary-btn" style="margin-top:8px" data-action="save-client-crm" data-id="${esc(id)}">Salvar CRM</button></div><div class="panel"><h3>Tabela específica</h3>${prices.map(x=>`<div class="stock-row"><span>${esc(x.product_name||x.product_ref)}</span><strong>${fmtBRL(x.price)}</strong></div>`).join("")||`<div class="empty-state">Sem preços exclusivos.</div>`}</div></div></div></div></div>`;$("#modalRoot").classList.add("show");
}
async function scanBarcode(){
  if("BarcodeDetector" in window && navigator.mediaDevices?.getUserMedia){
    toast("Leitor por câmera disponível. Use HTTPS no celular para liberar a câmera.");const code=prompt("Nesta versão desktop, digite/cole o código lido:");
    if(code){state.filters.q=code;go("catalogo")}
  }else{const code=prompt("Digite ou escaneie o código de barras/SKU:");if(code){state.filters.q=code;go("catalogo")}}
}
async function newProduct(){openProductForm()}
async function newClient(){openClientForm()}
function newPromo(){
  const name=prompt("Nome da promoção:");if(!name)return;const value=Number(prompt("Desconto em %:","10")||0),ids=prompt("Códigos/IDs dos produtos separados por vírgula (vazio = produto atual do Studio):","")||"";
  const productIds=ids.split(",").map(x=>x.trim()).filter(Boolean).map(ref=>state.products.find(p=>[p.id,p.code,p.name].includes(ref))?.id||ref);if(!productIds.length&&state.studioProductId)productIds.push(state.studioProductId);
  state.catalog.promotions.unshift({id:`PROMO-${Date.now()}`,name,productIds,type:"percent",value,start:today(),end:addDays(new Date(),7),active:true});logHistory("CRIAR","Promoção",name);saveCatalogState().then(()=>renderPromocoes());
}
function orderDetail(id){
  const o=state.orders.find(o=>o.id===id);if(!o)return;
  modernModal(o.code||'Pedido',`<p><strong>${esc(o.client_name)}</strong> · ${esc(o.status)}</p><p>Origem: ${esc(o.source_document_code||'Atendimento direto')} ${o.source_document_revision?'· versão '+o.source_document_revision:''}</p><p>Entrega: ${esc(o.delivery_address||'A combinar')}<br>Data: ${esc(o.delivery_date||'A combinar')}</p><div class="table-wrap"><table><thead><tr><th>Produto</th><th>Qtd.</th><th>Total</th></tr></thead><tbody>${(o.items||[]).map(i=>`<tr><td>${esc(i.product_name||i.description)}</td><td>${Number(i.quantity)}</td><td>${fmtBRL(i.total)}</td></tr>`).join('')}</tbody></table></div>${modernTotalsHtml(o)}<h4>Pagamentos planejados</h4>${(o.payments||[]).map(p=>`<p>${esc(p.method)} · ${fmtBRL(p.amount)} · ${esc(p.date)} · Planejado</p>`).join('')||'<p>Nenhum plano registrado.</p>'}<p>${esc(o.notes||'')}</p><p class="help">${esc((o.integration_log||[]).join(' • '))}</p>`);
}
function showNotifications(){
  const n=notifications();$("#notificationPopover").innerHTML=`<div class="panel-head"><div><h3>Notificações</h3><small>${n.length} alerta(s)</small></div></div>${n.map(x=>`<div class="notification-item"><strong>${esc(x.title)}</strong><small>${esc(x.text)}</small></div>`).join("")||`<div class="empty-state">Tudo em ordem.</div>`}`;$("#notificationPopover").classList.toggle("hidden")
}
async function saveSettings(){
  Object.assign(state.catalog.settings,{companyName:$("#cfgCompany").value.trim()||"Fácil Pedido",whatsapp:$("#cfgWhatsapp").value.trim(),minimumMargin:Number($("#cfgMinMargin").value),pixDiscount:Number($("#cfgPix").value)||0,installments:Number($("#cfgInstallments").value)||1,installmentFee:Number($("#cfgFee").value)||0,autoCreateProduction:$("#cfgAutoProduction")?.checked!==false,autoCreateReceivable:$("#cfgAutoReceivable")?.checked!==false,autoCreateDelivery:$("#cfgAutoDelivery")?.checked!==false,defaultWarrantyMonths:Number($("#cfgWarranty")?.value)||12,requireDiscountApproval:true});logHistory("SALVAR","Configurações","Regras comerciais e automações");await saveCatalogState();updateTop();toast("Configurações salvas")
}

function openGlobalSearch(query){const q=norm(query);if(!q)return;const products=state.products.filter(p=>norm([p.code,p.barcode,p.name,p.color,p.size,p.material,p.brand].join(" ")).includes(q)).slice(0,8),clients=state.clients.filter(c=>norm([c.name,c.document,c.phone,c.email].join(" ")).includes(q)).slice(0,8),orders=state.orders.filter(o=>norm([o.code,o.client_name,o.status].join(" ")).includes(q)).slice(0,8),quotes=state.quotes.filter(o=>norm([o.code,o.client_name,o.status].join(" ")).includes(q)).slice(0,8);const group=(title,items,render)=>items.length?`<div class="search-group"><h4>${title}</h4>${items.map(render).join("")}</div>`:"";$("#modalRoot").innerHTML=`<div class="modal-overlay"><div class="modal-card wide"><div class="modal-head"><div><h3>Busca global</h3><p>Resultados para “${esc(query)}”</p></div><button class="icon-btn" data-close-modal>×</button></div><div class="modal-body"><div class="search-results">${group("Produtos",products,p=>`<div class="search-hit"><div><strong>${esc(p.name)}</strong><small>${esc(p.code)} ${p.barcode?`• ${esc(p.barcode)}`:""} • ${fmtBRL(p.price)}</small></div><button class="secondary-btn" data-action="detail" data-id="${esc(p.id)}">Abrir</button></div>`)}${group("Clientes",clients,c=>`<div class="search-hit"><div><strong>${esc(c.name)}</strong><small>${esc(c.document||"")} • ${esc(c.phone||"")}</small></div><button class="secondary-btn" data-action="client-360" data-id="${esc(c.id)}">360°</button></div>`)}${group("Pedidos",orders,o=>`<div class="search-hit"><div><strong>${esc(o.code||o.id)}</strong><small>${esc(o.client_name||"")} • ${esc(o.status||"")} • ${fmtBRL(o.total)}</small></div><button class="secondary-btn" data-action="order-detail" data-id="${esc(o.id)}">Abrir</button></div>`)}${group("Orçamentos",quotes,o=>`<div class="search-hit"><div><strong>${esc(o.code||o.id)}</strong><small>${esc(o.client_name||"")} • ${esc(o.status||"")} • ${fmtBRL(o.total)}</small></div><button class="secondary-btn" data-action="print-quote" data-id="${esc(o.id)}">PDF</button></div>`)}${!products.length&&!clients.length&&!orders.length&&!quotes.length?`<div class="ops-empty"><strong>Nenhum resultado</strong>Tente nome, código, CPF/CNPJ, telefone ou número do pedido.</div>`:""}</div></div></div></div>`;$("#modalRoot").classList.add("show")}
function roleDashboardHtml(){const role=String(state.user?.role||"Administrador"),r=norm(role);let icon="📊",text="Visão completa da operação.";if(r.includes("vendedor")||r.includes("comercial")){icon="🛒";text="Prioridade: clientes, orçamentos, pedidos e follow-ups."}else if(r.includes("estoque")){icon="📦";text="Prioridade: disponibilidade, reservas e estoque crítico."}else if(r.includes("produ")){icon="⚒";text="Prioridade: ordens de produção, prazos e gargalos."}else if(r.includes("finan")){icon="R$";text="Prioridade: recebimentos, pagamentos e vencimentos."}else if(r.includes("log")){icon="🚚";text="Prioridade: entregas, rotas e montagens."}return `<div class="role-dashboard"><div class="role-icon">${icon}</div><div><strong>Painel de ${esc(role)}</strong><small>${text}</small></div></div>`}
async function handleProductImportInput(file){if(!file)return;await importProductFile(file)}
function cartPayload(){
  const m=cartMeta();
  return {client_id:state.selectedClient?.id||'',client_name:state.selectedClient?.name||'',
    items:state.cart.map(i=>({product_id:i.product._pvReference?null:i.product.id,product_ref:i.product.code||'',product_name:i.product.name,description:i.product.name,reference:!!i.product._pvReference,variant_id:i.variantId||null,location_id:i.locationId||null,quantity:i.qty,unit_price:i.unitPrice,discount_spec:{type:i.discountType||'percent',value:i.discount||0},notes:i.notes||'',price_source:i.priceSource||'product_default'})),
    discount_spec:{type:m.discountType||'amount',value:m.orderDiscount||0},freight:m.freight||0,assembly:m.assembly||0,
    payment_method:m.payment,payments:m.payments,notes:m.notes,valid_until:m.validUntil,delivery_date:m.deliveryDate||'',
    shipping_address:Object.fromEntries(['cep','street','number','complement','district','city','uf'].map(k=>[k,m[k]||''])),delivery_address:cartShippingAddress(),freight_source:m.freightSource||'manual'};
}

function cartCalculation(){
  if(!state.cart.length)return {gross:0,item_discount:0,subtotal:0,discount:0,freight:0,assembly:0,total:0,planned_total:0,remaining:0,items:[]};
  const payload=cartPayload();
  try{return window.FPCommercialMoney.calculate(payload)}catch(e){
    if(!String(e.message).includes('pagamentos planejados'))throw e;
    const c=window.FPCommercialMoney.calculate({...payload,payments:[]}),planned=Number((payload.payments||[]).reduce((n,p)=>n+window.FPCommercialMoney.scaled(p.amount),0n))/100;
    return {...c,planned_total:planned,remaining:Math.round((c.total-planned)*100)/100,payment_error:e.message};
  }
}

function pricePolicy(){return modern.policy||state.catalog.settings}

async function setCommercialClient(id){
  const selected=state.clients.find(c=>c.id===id)||null,seq=++modern.clientSeq;
  const official=state.cart.filter(i=>!i.product._pvReference),ids=[...new Set(official.map(i=>i.product.id))];
  modern.busy=true;setCartStatus('Conferindo preços do cliente…');
  try{
    let prices=[],policy=state.catalog.settings;
    if(!state.demo){
      const [p,r]=await Promise.all([API.request('/commercial/prices',{method:'POST',body:JSON.stringify({client_id:selected?.id||'',product_ids:ids})}),API.request(`/commercial/policy?client_id=${encodeURIComponent(selected?.id||'')}`)]);
      prices=p.prices;policy=r;
    }else prices=official.map(i=>({product_id:i.product.id,price:promoPrice(i.product),source:'product_default'}));
    if(seq!==modern.clientSeq)return;
    // Valida a tabela completa antes de atualizar qualquer item do carrinho.
    if(!Array.isArray(prices))throw Error('Tabela de preços indisponível. Cliente anterior mantido.');
    const prepared=official.map(i=>{const p=prices.find(x=>String(x.product_id)===String(i.product.id));if(!p||!Number.isFinite(Number(p.price))||Number(p.price)<0||p.source==='not_found')throw Error('Preço indisponível para '+i.product.name+'. Cliente anterior mantido.');const v=i.variantId?state.variants.find(v=>v.id===i.variantId):null;const unitPrice=(p.source==='product_default'&&v?.price!=null)?Number(v.price):Number(p.price);if(!Number.isFinite(unitPrice)||unitPrice<0)throw Error('Preço inválido para '+i.product.name);return {i,p,unitPrice}});
    if(seq!==modern.clientSeq)return;
    state.selectedClient=selected;state.clientPriceCache={};modern.policy=policy;
    for(const {i,p,unitPrice} of prepared){i.unitPrice=unitPrice;i.priceSource=p.source;state.clientPriceCache[`${selected?.id||''}:${i.product.id}`]=Number(p.price)}
    markCartDirty();updateTop();if($('#cartDrawer').classList.contains('open'))renderCart();else render();
    toast('Cliente e preços atualizados. Confira as novas condições.');
  }catch(e){if($('#cartClient'))$('#cartClient').value=state.selectedClient?.id||'';toast(e.message,'error')}
  finally{if(seq===modern.clientSeq){modern.busy=false;scheduleCartQuote()}}
}

function setCartStatus(text,error=false){const e=$('#commercialCartStatus');if(e){e.textContent=text;e.classList.toggle('error',error)}}

function markCartDirty(){modern.dirty=true;modern.mutation++;modern.lastQuote=null;scheduleCartQuote()}

function scheduleCartQuote(){clearTimeout(modern.timer);modern.timer=setTimeout(syncCartQuote,240)}

async function syncCartQuote(){
  if(!state.cart.length||state.demo)return;
  const seq=++modern.quoteSeq,signature=JSON.stringify(cartPayload());
  try{const data=await API.request('/commercial/calculate',{method:'POST',body:signature});if(seq!==modern.quoteSeq||signature!==JSON.stringify(cartPayload()))return;modern.lastQuote=data;setCartStatus('Totais conferidos pelo servidor • '+(modern.dirty?'alterações ainda não salvas':'documento salvo'))}
  catch(e){if(seq===modern.quoteSeq)setCartStatus(e.message,true)}
}

async function loadCommercialDocuments(){
  if(state.demo)return;
  try{modern.documents=await API.request('/commercial/documents');modern.documentsLoaded=true;
    state.quotes=[...modern.documents.filter(d=>d.kind==='quote'),...state.quotes.filter(q=>!q.commercial_document)];
    if(state.route==='orcamentos')renderOrcamentos();
  }catch(e){modern.documentsError=e.message;toast('Rascunhos e propostas: '+e.message,'error')}
}

async function saveCommercialDocument(kind='quote',notify=true){
  if(modern.saving||modern.busy)throw Error('Aguarde a operação atual.');
  if(!state.cart.length)throw Error('Adicione produtos antes de salvar.');
  if(kind==='quote'&&!state.selectedClient)throw Error('Selecione um cliente.');
  if(kind==='quote'&&!cartAllPriced())throw Error('Defina o valor de todos os produtos.');
  const check=cartCalculation();if(check.payment_error)throw Error(check.payment_error);modern.saving=true;
  const mutation=modern.mutation;
  try{
    const current=modern.cartDocument,payload={...cartPayload(),kind:current?.kind==='quote'?'quote':kind,base_revision:current?.revision};
    let doc;
    if(state.demo){doc={...window.FPCommercialMoney.calculate(payload),id:current?.id||`DEMO-${Date.now()}`,code:current?.code||`ORC-DEMO-${Date.now()}`,revision:(current?.revision||0)+1,kind,commercial_document:true,status:cartHasReference()?'Pré-orçamento':'Rascunho',created_at:new Date().toISOString()};modern.documents=[doc,...modern.documents.filter(d=>d.id!==doc.id)]}
    else doc=await API.request(current&&!current.converted_order_id?`/commercial/documents/${encodeURIComponent(current.id)}`:'/commercial/documents',{method:current&&!current.converted_order_id?'PUT':'POST',body:JSON.stringify(payload)});
    modern.cartDocument=doc;modern.documents=[doc,...modern.documents.filter(d=>d.id!==doc.id)];modern.dirty=mutation!==modern.mutation;
    state.quotes=[...modern.documents.filter(d=>d.kind==='quote'),...state.quotes.filter(q=>!q.commercial_document)];
    if(notify)toast(`${kind==='draft'?'Rascunho':'Proposta'} ${doc.code} salvo • versão ${doc.revision}`);
    if($('#cartDrawer').classList.contains('open'))renderCart();return doc;
  }finally{modern.saving=false}
}

function resetCommercialCart(){
  if(modern.dirty&&state.cart.length&&!confirm('Há alterações não salvas. Iniciar outro atendimento?'))return;
  state.cart=[];state.cartMeta=null;modern.cartDocument=null;modern.dirty=false;modern.policy=null;modern.mutation++;modern.lastQuote=null;updateTop();openCart();
}

async function openCommercialDocument(id,duplicate=false){
  if(modern.dirty&&state.cart.length&&!confirm('Substituir as alterações não salvas pelo documento selecionado?'))return;
  let d=modern.documents.find(d=>d.id===id)||state.quotes.find(q=>q.id===id)||(state.catalog.quoteMeta.preliminary||[]).find(q=>q.id===id);
  if(!d)throw Error('Documento não encontrado.');
  if(d.commercial_document&&!state.demo)d=await API.request(`/commercial/documents/${encodeURIComponent(id)}`);
  const legacy=state.catalog.quoteMeta[id]||{},m=d.shipping_address||{};
  state.selectedClient=state.clients.find(c=>c.id===d.client_id)||null;
  state.cart=(d.items||[]).map(i=>{const p=state.products.find(p=>p.id===i.product_id)||pvShowcase.rows.find(p=>p.id===i.product_ref)||{id:i.product_id||i.product_ref||'reference',name:i.product_name||i.description,code:i.product_ref||'',price:i.unit_price,_pvReference:!!i.reference};return {product:p,variantId:i.variant_id,locationId:i.location_id,qty:i.quantity,unitPrice:i.unit_price,discount:i.discount_spec?.value??i.discount_percent??i.discount??0,discountType:i.discount_spec?.type||'percent',priceSource:i.price_source,notes:i.notes||''}});
  state.cartMeta={...cartMeta(),...m,freight:d.freight??legacy.freight??0,assembly:d.assembly??legacy.assembly??0,orderDiscount:d.discount_spec?.value??legacy.orderDiscount??d.discount??0,discountType:d.discount_spec?.type||'amount',payment:d.payment_method||'A combinar',payments:clone(d.payments||legacy.payments||[]),notes:d.notes||legacy.notes||'',deliveryAddress:d.delivery_address||legacy.deliveryAddress||'',deliveryDate:d.delivery_date||'',validUntil:duplicate?addDays(new Date(),7):d.valid_until||addDays(new Date(),7),freightSource:d.freight_source||'manual'};
  modern.cartDocument=!duplicate&&d.commercial_document&&!d.converted_order_id?d:null;modern.dirty=duplicate||!d.commercial_document;modern.policy=d.commercial_policy||state.catalog.settings;modern.mutation++;updateTop();openCart();scheduleCartQuote();
}

function modernTotalsHtml(c){return `<dl class="modern-totals"><div><dt>Produtos brutos</dt><dd>${fmtBRL(c.gross)}</dd></div><div><dt>Descontos nos itens</dt><dd>− ${fmtBRL(c.item_discount)}</dd></div><div><dt>Produtos líquidos</dt><dd>${fmtBRL(c.subtotal)}</dd></div><div><dt>Desconto geral</dt><dd>− ${fmtBRL(c.discount)}</dd></div><div><dt>Frete</dt><dd>${fmtBRL(c.freight)}</dd></div><div><dt>Montagem</dt><dd>${fmtBRL(c.assembly)}</dd></div><div class="total"><dt>Total final</dt><dd>${fmtBRL(c.total)}</dd></div><div><dt>Pagamentos previstos</dt><dd>${fmtBRL(c.planned_total)}</dd></div><div><dt>${c.remaining<0?'Pagamentos em excesso':'Saldo a planejar'}</dt><dd>${fmtBRL(Math.abs(c.remaining||0))}</dd></div></dl>`}

function refreshCartNumbers(){
  try{const c=cartCalculation();if($('#modernTotals'))$('#modernTotals').innerHTML=modernTotalsHtml(c);c.items.forEach((i,n)=>{const e=$(`[data-modern-line-total="${n}"]`);if(e)e.textContent=fmtBRL(i.total)});setCartStatus(c.payment_error||'Alterações ainda não salvas',!!c.payment_error);}
  catch(e){setCartStatus(e.message,true)}updateTop();markCartDirty();
}

function modernModal(title,body){$('#modalRoot').innerHTML=`<div class="modal-overlay"><section class="modal-card wide" role="dialog" aria-modal="true" aria-label="${esc(title)}"><div class="modal-head"><h3>${esc(title)}</h3><button class="icon-btn" data-close-modal aria-label="Fechar">×</button></div><div class="modal-body">${body}</div></section></div>`;$('#modalRoot').classList.add('show')}

async function shareCommercialDocument(id){
  let doc=modern.documents.find(d=>d.id===id);if(!doc)throw Error('Salve uma proposta para compartilhar.');
  if(doc.kind!=='quote')throw Error('Salve como proposta antes de compartilhar.');
  if(state.demo)throw Error('O compartilhamento persistente exige conexão com o servidor.');
  const share=await API.request(`/commercial/documents/${encodeURIComponent(id)}/share`,{method:'POST'});modern.shares[id]=share;
  modernModal('Compartilhar proposta',`<p>Este link mostra a versão ${doc.revision}, sem custo interno. Expira em ${esc(new Date(share.expires_at).toLocaleDateString('pt-BR'))}. Novas edições não alteram esta versão compartilhada.</p><img class="modern-share-qr" src="${esc(share.qr_url)}" alt="QR da proposta"><div class="field"><label for="proposalShareUrl">Link da proposta</label><input id="proposalShareUrl" readonly value="${esc(share.url)}"></div><div class="actions"><button class="primary-btn" data-action="copy-proposal-url">Copiar link</button><a class="secondary-btn" href="${esc(share.url)}" target="_blank" rel="noopener noreferrer">Abrir proposta</a><button class="secondary-btn" data-action="whatsapp-proposal" data-id="${esc(id)}">Abrir no WhatsApp</button></div><p class="help">Você confirma o envio no aplicativo de mensagens. Para cancelar o acesso, use “Revogar links”.</p>`);
}

async function customerStatement(id){
  modernModal('Posição comercial do cliente','<p>Consultando o extrato oficial…</p>');
  try{const r=await API.request(`/commercial/customer/${encodeURIComponent(id)}/statement`);modernModal('Extrato oficial do cliente',`<p>Limite cadastrado: ${fmtBRL(r.credit_limit)}</p><div class="table-wrap"><table><thead><tr><th>Descrição</th><th>Vencimento</th><th>Valor</th><th>Status</th></tr></thead><tbody>${r.entries.map(x=>`<tr><td>${esc(x.description)}</td><td>${esc(x.due_date)}</td><td>${fmtBRL(x.amount)}</td><td>${esc(x.status)}</td></tr>`).join('')||'<tr><td colspan="4">Nenhum lançamento disponível.</td></tr>'}</tbody></table></div><p class="help">Consulta ao financeiro oficial. Nenhuma baixa ou cobrança é realizada aqui.</p>`)}catch(e){modernModal('Extrato indisponível',`<p>${esc(e.message)}</p><p>Esta consulta respeita a permissão financeira do seu usuário.</p>`)}
}

async function documentHistory(id){const rows=await API.request(`/commercial/documents/${encodeURIComponent(id)}/versions`);modernModal('Histórico de versões',rows.map(r=>`<section class="panel"><h4>Versão ${r.revision}</h4><p>${esc(new Date(r.created_at).toLocaleString('pt-BR'))} · ${esc(r.document.client_name)} · ${fmtBRL(r.document.total)}</p><p>${esc(r.document.delivery_address)} · ${esc(r.document.payment_method)}</p></section>`).join(''))}

async function setDocumentStatus(id){
  const d=modern.documents.find(q=>q.id===id);if(!d)return;
  modernModal('Etapa da proposta',`<div class="field"><label for="newDocumentStatus">Etapa</label><select id="newDocumentStatus">${['Rascunho','Enviado','Negociação','Aprovado','Perdido'].map(s=>`<option ${d.status===s?'selected':''}>${s}</option>`).join('')}</select></div><div class="field"><label for="documentStatusReason">Motivo (obrigatório para perdido)</label><textarea id="documentStatusReason"></textarea></div><button class="primary-btn" data-action="save-document-status" data-id="${esc(id)}">Salvar etapa</button>`);
}

function openReturnRequest(id){const o=state.orders.find(o=>o.id===id);if(!o)return;modernModal('Solicitar devolução',`<p>${esc(o.code)} · ${esc(o.client_name)}</p>${o.items.map((i,n)=>`<div class="field"><label>${esc(i.product_name||i.description)} — quantidade solicitada<input type="number" data-return-index="${n}" min="0" max="${Number(i.quantity)}" step="0.001" value="0"></label></div>`).join('')}<div class="field"><label for="returnReason">Motivo</label><textarea id="returnReason"></textarea></div><p class="quote-notice">Esta ação registra a solicitação. Estoque, crédito e estorno dependem de análise no ERP.</p><button class="primary-btn" data-action="save-return-request" data-id="${esc(id)}">Registrar solicitação</button>`)}

async function modernAction(a,id,btn){
  if(a==='save-freight-rules'){await saveFreightRules();return true}
  if(a==='save-commercial-draft'){await saveCommercialDocument('draft');return true}
  if(a==='new-commercial-cart'){resetCommercialCart();return true}
  if(a==='commercial-documents'){closeCart();go('orcamentos');return true}
  if(a==='open-commercial-document'||a==='duplicate-commercial-document'){await openCommercialDocument(id,a.startsWith('duplicate'));return true}
  if(a==='commercial-reload'){await loadCommercialDocuments();render();return true}
  if(a==='undo-cart-remove'){if(modern.undo){state.cart.splice(modern.undo.index,0,modern.undo.item);modern.undo=null;markCartDirty();updateTop();renderCart()}return true}
  if(a==='document-history'){await documentHistory(id);return true}
  if(a==='document-status'){await setDocumentStatus(id);return true}
  if(a==='save-document-status'){const d=modern.documents.find(d=>d.id===id);await API.request(`/commercial/documents/${encodeURIComponent(id)}/status`,{method:'POST',body:JSON.stringify({base_revision:d.revision,status:$('#newDocumentStatus').value,reason:$('#documentStatusReason').value})});closeModal();await loadCommercialDocuments();return true}
  if(a==='share-document'){await shareCommercialDocument(id);return true}
  if(a==='revoke-document-shares'){await API.request(`/commercial/documents/${encodeURIComponent(id)}/shares`,{method:'DELETE'});delete modern.shares[id];toast('Links desta proposta revogados');return true}
  if(a==='copy-proposal-url'){await navigator.clipboard.writeText($('#proposalShareUrl').value);toast('Link copiado');return true}
  if(a==='whatsapp-proposal'){const d=modern.documents.find(d=>d.id===id);openWhatsApp(`Proposta ${d.code}\n${modern.shares[id].url}`);return true}
  if(a==='home-page'){
    const page=Number(btn.dataset.page);if(Number.isInteger(page)&&page>0){modern.homePage=page;renderHomeProducts();$('#homeProducts')?.scrollIntoView?.({block:'start',behavior:'smooth'})}return true;
  }
  if(a==='home-open-catalog'){
    Object.assign(state.filters,{source:'all',q:'',category:'',stock:'all',favorites:false,page:1});go('catalogo');if(!pvShowcase.ready)await loadPvShowcase();return true;
  }
  if(a==='show-official-products'){Object.assign(state.filters,{source:'official',q:'',category:'',stock:'all',favorites:false,page:1});go('catalogo');return true}
  if(a==='clear-catalog-filters'){Object.assign(state.filters,{source:'all',q:'',category:'',stock:'all',favorites:false,page:1});renderCatalogo();return true}
  if(a==='home-retry-products'||a==='retry-catalog-references'){
    pvShowcase.error='';const pending=loadPvShowcase();void loadPvReference();renderHomeProducts();if(state.route==='catalogo')refreshCatalogPreservingFocus();await pending;return true;
  }
  if(a==='show-references'){Object.assign(state.filters,{source:'references',q:'',category:'',stock:'all',favorites:false,page:1});await loadPvReference();await loadPvShowcase();go('catalogo');return true}
  if(a==='apply-cash-discount'){cartMeta().discountType='percent';cartMeta().orderDiscount=Number(pricePolicy().pixDiscount||0);markCartDirty();renderCart();updateTop();return true}
  if(a==='quote-freight'){const m=cartMeta(),r=await API.request('/commercial/freight',{method:'POST',body:JSON.stringify({cep:m.cep,distance_km:m.distance===''||m.distance==null?null:Number(m.distance)})});if(r.amount!=null)m.freight=r.amount;m.freightSource=r.source;m.freightLabel=r.label;markCartDirty();renderCart();updateTop();toast(r.label);return true}
  if(a==='generate-installments'){const m=cartMeta(),n=Number($('#cartInstallments').value),due=$('#cartFirstPayment').value;if(!Number.isInteger(n)||n<1||n>120||!due)throw Error('Informe de 1 a 120 parcelas e o primeiro vencimento.');const cents=Math.round(cartCalculation().remaining*100);if(cents<=0)throw Error('Não há saldo a planejar.');const base=Math.floor(cents/n);for(let k=0;k<n;k++)m.payments.push({method:['PIX','Dinheiro','Cartão','Boleto','Transferência'].includes(m.payment)?m.payment:'PIX',amount:(base+(k===n-1?cents-base*n:0))/100,date:(()=>{const d=new Date(due+'T12:00:00');const day=d.getDate();d.setDate(1);d.setMonth(d.getMonth()+k);const last=new Date(d.getFullYear(),d.getMonth()+1,0).getDate();d.setDate(Math.min(day,last));return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`})()});m.installments=n;m.firstPaymentDate=due;markCartDirty();renderCart();return true}
  if(a==='reload-commercial-reports'){modern.reportFilter=Object.fromEntries([['start','reportStart'],['end','reportEnd'],['client_id','reportClient'],['status','reportStatus'],['seller','reportSeller']].map(([k,id])=>[k,$('#'+id).value]));await renderRelatorios();return true}
  if(a==='customer-statement'){await customerStatement(id);return true}
  if(a==='return-request'){openReturnRequest(id);return true}
  if(a==='save-return-request'){const items=$$('[data-return-index]').filter(e=>Number(e.value)>0).map(e=>({index:Number(e.dataset.returnIndex),quantity:Number(e.value)}));if(!items.length)throw Error('Selecione ao menos um produto.');if(!$('#returnReason').value.trim())throw Error('Informe o motivo.');await API.request(`/commercial/orders/${encodeURIComponent(id)}/return-requests`,{method:'POST',body:JSON.stringify({items,reason:$('#returnReason').value})});closeModal();await loadCommercialDocuments();toast('Solicitação registrada, sem estorno ou movimentação de estoque');return true}
  return false;
}

async function renderOfficialOperations(kind){
  const config={finance:{title:'Recebimentos e posição comercial',description:'Consulta aos lançamentos de receita do ERP oficial. Pagamentos previstos da proposta continuam no seu documento.',columns:[['description','Descrição'],['due_date','Vencimento'],['amount','Valor'],['status','Situação']]},deliveries:{title:'Entregas dos pedidos',description:'Datas e situações consultadas na logística oficial.',columns:[['code','Entrega'],['order_ref','Pedido'],['recipient_name','Destinatário'],['scheduled_date','Data'],['address','Endereço'],['status','Situação']]},production:{title:'Produção dos pedidos',description:'Acompanhe as ordens oficiais relacionadas aos pedidos.',columns:[['code','Ordem'],['order_ref','Pedido'],['product_name','Produto'],['quantity','Quantidade'],['forecast_date','Previsão'],['status','Situação']]}}[kind];
  $('#appContent').innerHTML=pageHead('ACOMPANHAMENTO COMERCIAL',config.title,config.description)+`<p class="quote-notice">Esta tela é de consulta. Alterações operacionais e baixas são realizadas pelos responsáveis no ERP.</p><div id="officialOperationsResult" role="status">Consultando dados oficiais…</div>`;
  const route=state.route;
  try{const data=await API.request('/commercial/operations/'+kind);if(state.route!==route)return;const rows=data.rows;
    $('#officialOperationsResult').innerHTML=`<div class="table-wrap"><table><thead><tr>${config.columns.map(([k,label])=>`<th>${label}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${config.columns.map(([key])=>`<td>${key==='amount'?fmtBRL(r[key]):esc(r[key]??'—')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${config.columns.length}">Nenhum registro disponível para este acesso.</td></tr>`}</tbody></table></div>`;
  }catch(e){if(state.route===route&&$('#officialOperationsResult'))$('#officialOperationsResult').innerHTML=`<div class="empty-state">${esc(e.message)}<p>Confira as permissões do usuário e a disponibilidade da API do ERP.</p></div>`}
}
function renderFreightRules(){
  if(!hasPermission('settings.write'))return;
  const s=state.catalog.settings;
  $('#appContent').insertAdjacentHTML('beforeend',`<section class="panel modern-recent"><h3>Regras comerciais de frete e comissão</h3><p class="help">Use valores aprovados pela empresa. A distância é informada pelo atendente; não é calculada a partir do CEP.</p><div class="form-grid"><div class="field"><label for="cfgFreightKm">Valor por km (R$)</label><input id="cfgFreightKm" type="number" min="0" step="0.01" value="${Number(s.freightPerKm||0)}"></div><div class="field"><label for="cfgFreightMin">Frete mínimo (R$)</label><input id="cfgFreightMin" type="number" min="0" step="0.01" value="${Number(s.freightMinimum||0)}"></div><div class="field"><label for="cfgCommission">Comissão estimada nos produtos (%)</label><input id="cfgCommission" type="number" min="0" max="100" step="0.01" value="${Number(s.commissionPercent||0)}"></div><div class="field full"><label for="cfgFreightZones">Faixas de CEP — uma por linha: prefixo; valor; nome</label><textarea id="cfgFreightZones" rows="5" placeholder="Exemplo de formato: 09; 50; Região de entrega">${esc((s.freightZones||[]).map(z=>`${z.prefix}; ${z.amount}; ${z.label||''}`).join('\n'))}</textarea></div></div><p class="help">A faixa mais específica prevalece. Comissão fica registrada no novo pedido como estimativa; nenhum pagamento é gerado.</p><button class="primary-btn" data-action="save-freight-rules">Salvar regras comerciais</button></section>`);
}
async function saveFreightRules(){
  const rate=Number($('#cfgFreightKm').value),minimum=Number($('#cfgFreightMin').value),commission=Number($('#cfgCommission').value);
  if(!Number.isFinite(rate)||!Number.isFinite(minimum)||rate<0||minimum<0||commission<0||commission>100)throw Error('Confira os valores das regras.');
  const zones=$('#cfgFreightZones').value.split('\n').map(x=>x.trim()).filter(Boolean).map(line=>{const [prefix,value,...label]=line.split(';').map(x=>x.trim());const amount=Number(String(value).replace(',','.'));if(!/^\d{1,8}$/.test(prefix)||!Number.isFinite(amount)||amount<0)throw Error('Faixa inválida: use prefixo; valor; nome.');return {prefix,amount,label:label.join('; ')}});
  Object.assign(state.catalog.settings,{freightPerKm:rate,freightMinimum:minimum,freightZones:zones,commissionPercent:commission});await saveCatalogState();toast('Regras comerciais salvas');
}
function modernInput(e){
  const t=e.target,m=cartMeta();let changed=false;
  if(t.matches('[data-modern-qty]')){state.cart[Number(t.dataset.modernQty)].qty=t.value;changed=true}
  if(t.matches('[data-modern-unit]')){const i=state.cart[Number(t.dataset.modernUnit)];i.unitPrice=t.value;i.priceSource='negotiated';changed=true}
  if(t.matches('[data-modern-discount]')){state.cart[Number(t.dataset.modernDiscount)].discount=t.value;changed=true}
  if(t.matches('[data-modern-discount-type]')){state.cart[Number(t.dataset.modernDiscountType)].discountType=t.value;changed=true}
  if(t.matches('[data-modern-pay-value]')){m.payments[Number(t.dataset.modernPayValue)].amount=t.value;changed=true}
  const fields={cartFreight:'freight',cartAssembly:'assembly',cartOrderDiscount:'orderDiscount',cartDiscountType:'discountType',cartDeliveryDate:'deliveryDate',cartValidUntil:'validUntil',cartDistance:'distance',cartFirstPayment:'firstPaymentDate',cartInstallments:'installments'};
  if(fields[t.id]){m[fields[t.id]]=t.value;if(t.id==='cartFreight'){m.freightSource='manual';m.freightLabel='Valor combinado manualmente'}changed=true}
  if(t.id?.startsWith('cart')||t.matches('[data-pay-date],[data-pay-method]')){if(!['cartClient','cartButton'].includes(t.id))modern.dirty=true}
  if(changed)refreshCartNumbers();
  if(['documentKind','documentStatus','documentStart','documentEnd'].includes(t.id)){modern.documentFilter[{documentKind:'kind',documentStatus:'status',documentStart:'start',documentEnd:'end'}[t.id]]=t.value;renderOrcamentos()}
  if(t.id==='documentSearch'){modern.documentFilter.q=t.value;clearTimeout(modern.searchTimer);const cursor=t.selectionStart;modern.searchTimer=setTimeout(()=>{renderOrcamentos();const x=$('#documentSearch');x?.focus();x?.setSelectionRange(cursor,cursor)},180)}
}

function bind(){
  document.addEventListener("click",async e=>{
    const route=e.target.closest("[data-route]");if(route){if(route.dataset.route==='catalogo')Object.assign(state.filters,{source:'all',q:'',category:'',stock:'all',favorites:false,page:1});go(route.dataset.route);return}
    if(e.target.closest("[data-close-modal]")){closeModal();return}if(e.target.closest("[data-close-drawer]")){closeCart();return}
    const gallery=e.target.closest("[data-gallery-src]");if(gallery){$("#galleryMain img").src=gallery.dataset.gallerySrc;return}
    const cat=e.target.closest("[data-category]");if(cat){state.filters.source="all";state.filters.category=cat.dataset.category;state.filters.page=1;go("catalogo");return}
    const btn=e.target.closest("[data-action]");if(!btn)return;const a=btn.dataset.action,id=btn.dataset.id;
    try{
      if(await modernAction(a,id,btn))return;
      if(["cart-inc","cart-dec","cart-remove","clear-quote-cart","add-payment","remove-payment"].includes(a)){
        if(a==="cart-remove")modern.undo={item:state.cart[Number(btn.dataset.index)],index:Number(btn.dataset.index)};
        markCartDirty();
      }
      if(a==="detail")await openProduct(id);
      else if(a==="pv-reference-detail")pvReferenceDetail(id);
      else if(a==="pv-add")await addToCart(id);
      else if(a==="pv-share")await copyProductLink(pvShowcase.rows.find(p=>p.id===id));
      else if(a==="copy-product-link")await copyProductLink(state.products.find(p=>p.id===id));
      else if(a==="product-price-eye")$("#productPriceInfo")?.classList.toggle("hidden");
      else if(a==="reference-price-eye")$("#pvPriceInfo")?.classList.toggle("hidden");
      else if(a==="pv-hide-photo")await pvHidePhoto(id,btn.dataset.photo||"");
      else if(a==="pv-restore-photos")await pvRestorePhotos(id);
      else if(a==="pv-go-manager"){closeModal();go("catalog-manager")}
      else if(a==="choose-variant")await openProduct(btn.dataset.product,id);
      else if(a==="add")await addToCart(id,btn.dataset.variant||null);
      else if(a==="favorite"){state.favorites.has(id)?state.favorites.delete(id):state.favorites.add(id);persistFavorites();render()}
      else if(a==="toggle-favorites"){state.filters.favorites=!state.filters.favorites;state.filters.page=1;renderCatalogo()}
      else if(a==="clear-client"){await setCommercialClient("");renderCatalogo()}
      else if(a==="page"){state.filters.page=Number(btn.dataset.page);renderCatalogo();window.scrollTo({top:0,behavior:"smooth"})}
      else if(a==="select-client"){await setCommercialClient(id);renderClientes()}
      else if(a==="client-360")openClient360(id);
      else if(a==="save-client-crm"){state.catalog.crm[id]={...(state.catalog.crm[id]||{}),stage:$("#clientCrmStage").value,notes:$("#clientCrmNotes").value,lastContact:today()};logHistory("CRM","Cliente",state.clients.find(c=>c.id===id)?.name||id);await saveCatalogState();closeModal();renderClientes()}
      else if(a==="advance-crm"){const stages=["Novo contato","Orçamento","Negociação","Cliente","Perdido"],cur=crmStage(state.clients.find(c=>c.id===id)),next=stages[Math.min(stages.length-1,stages.indexOf(cur)+1)];state.catalog.crm[id]={...(state.catalog.crm[id]||{}),stage:next,lastContact:today()};await saveCatalogState();renderClientes()}
      else if(a==="new-client")await newClient();
      else if(a==="new-product"){if(state.demo||hasPermission("settings.write"))await newProduct();else toast("Solicite o cadastro técnico do produto ao administrador.","error")}
      else if(a==="save-studio")await saveStudio();
      else if(a==="catalog-edit"){if(!state.demo&&!hasPermission("settings.write")){state.studioProductId=id;go("studio")}else openProductForm(id)}
      else if(a==="catalog-filter"){state.catalogManagerFilter=btn.dataset.filter||"all";renderCatalogManager()}
      else if(a==="bulk-upload"){document.getElementById("bulkCatalogInput")?.click()}
      else if(a==="pv-auto-link")await pvBulkLink();
      else if(a==="pv-gallery")pvGallery();
      else if(a==="pv-gallery-search")pvGallery(1,$("#pvGallerySearchInput")?.value||"");
      else if(a==="pv-gallery-page")pvGallery(Number(btn.dataset.page),$("#pvGallerySearchInput")?.value||"");
      else if(a==="pv-picker")pvPicker(Number(btn.dataset.page)||1);
      else if(a==="pv-picker-page")pvPicker(Number(btn.dataset.page),$("#pvSearchInput")?.value||"");
      else if(a==="pv-search")pvPicker(1,$("#pvSearchInput")?.value||"");
      else if(a==="pv-attach")await pvAttachPhoto(btn.dataset.page,btn.dataset.kind);
      else if(a==="pv-disable"){state.catalog.media[state.studioProductId]||={photos:[],variantPhotos:{}};state.catalog.media[state.studioProductId].disableReference=true;await saveCatalogState();renderStudio()}
      else if(a==="pv-enable"){state.catalog.media[state.studioProductId]||={photos:[],variantPhotos:{}};state.catalog.media[state.studioProductId].disableReference=false;await saveCatalogState();renderStudio()}

      else if(a==="catalog-publish"){await setCatalogPublished(id,true);toast("Produto publicado");renderCatalogManager()}
      else if(a==="catalog-unpublish"){await setCatalogPublished(id,false);toast("Produto ocultado");renderCatalogManager()}
      else if(a==="photo-cover"){const arr=mediaFor(state.studioProductId),i=Number(btn.dataset.index);if(i>0){arr.unshift(arr.splice(i,1)[0]);logHistory("CAPA","Produto",state.products.find(p=>p.id===state.studioProductId)?.name||"");await saveCatalogState();renderStudio()}}
      else if(a==="photo-left"){const arr=mediaFor(state.studioProductId),i=Number(btn.dataset.index);if(i>0){[arr[i-1],arr[i]]=[arr[i],arr[i-1]];await saveCatalogState();renderStudio()}}
      else if(a==="photo-right"){const arr=mediaFor(state.studioProductId),i=Number(btn.dataset.index);if(i<arr.length-1){[arr[i+1],arr[i]]=[arr[i],arr[i+1]];await saveCatalogState();renderStudio()}}
      else if(a==="remove-photo"){
        if(!canManageCatalog())throw new Error("Sem permissão para excluir fotos.");
        const productId=state.studioProductId,arr=mediaFor(productId),i=Number(btn.dataset.index),src=arr[i];
        if(!src)throw new Error("Imagem inexistente. Atualize o Studio.");
        if(arr.length===1 && presentationFor(productId).published===true)throw new Error("Despublique o produto antes de excluir a última foto.");
        if(!confirm(`Excluir esta foto do produto?${i===0?"\\nA próxima imagem passará a ser a capa.":""}\\n\\nO produto, seu preço e seu estoque serão preservados.`))return;
        const draft={};for(const field of ["studioTitle","studioSubtitle","studioStatus","studioFeatured","studioPublished","studioWarranty","studioDescription","studioHighlights","studioTags"]){const el=document.getElementById(field);if(el)draft[field]=el.value}
        const uploadedId=String(src).match(/\/api\/v1\/media\/([a-f0-9-]{36})(?:[?#]|$)/i);
        if(!state.demo&&uploadedId){
          // Backend removes the media row and its catalog link in one transaction.
          await deleteErpMedia(src);
        }else{
          // Static PDF reference/external photo: only detach, never delete shared assets.
          const media=state.catalog.media[productId]||={photos:[],variantPhotos:{}},wasDisabled=!!media.disableReference;
          arr.splice(i,1);
          if(!arr.length)media.disableReference=true;
          try{await saveCatalogState()}catch(e){arr.splice(i,0,src);media.disableReference=wasDisabled;throw e}
        }
        renderStudio();for(const [field,value] of Object.entries(draft)){const el=document.getElementById(field);if(el)el.value=value}
        toast("Foto excluída do produto. Nome, preço e estoque preservados.");
      }
      else if(a==="variant-media"){toast("Selecione a variação no detalhe do produto para usar a mídia específica.")}
      else if(a==="new-promo")newPromo();
      else if(a==="toggle-promo"){const p=state.catalog.promotions.find(x=>x.id===id);if(p)p.active=!p.active;await saveCatalogState();renderPromocoes()}
      else if(a==="delete-promo"){state.catalog.promotions=state.catalog.promotions.filter(x=>x.id!==id);await saveCatalogState();renderPromocoes()}
      else if(a==="quote-to-order")await quoteToOrder(id);
      else if(a==="quote-followup"){const q=state.quotes.find(x=>x.id===id);openWhatsApp(`Olá! Estamos acompanhando o orçamento ${q?.code||""} no valor de ${fmtBRL(q?.total)}. Posso te ajudar com alguma dúvida?`)}
      else if(a==="quote-lost"){await setDocumentStatus(id)}
      else if(a==="confirm-order")await confirmOrder(id);
      else if(a==="order-detail")orderDetail(id);
      else if(a==="cart-inc"){state.cart[Number(btn.dataset.index)].qty=Number(state.cart[Number(btn.dataset.index)].qty)+1;updateTop();renderCart()}
      else if(a==="cart-dec"){state.cart[Number(btn.dataset.index)].qty=Math.max(0.001,Number(state.cart[Number(btn.dataset.index)].qty)-1);updateTop();renderCart()}
      else if(a==="cart-remove"){state.cart.splice(Number(btn.dataset.index),1);updateTop();renderCart()}
      else if(a==="cart-eye")$("#cartEyeRow"+Number(btn.dataset.index))?.classList.toggle("hidden");
      else if(a==="quote-edit-discount")$("[data-cart-discount='"+Number(btn.dataset.index)+"']")?.focus();
      else if(a==="quote-open-product"){const i=state.cart[Number(btn.dataset.index)];if(i)(i.product._pvReference?pvReferenceDetail(i.product.id):await openProduct(i.product.id,i.variantId));}
      else if(a==="quote-copy-product"){const i=state.cart[Number(btn.dataset.index)];if(i)await copyProductLink(i.product);}
      else if(a==="add-more-product"){closeCart();go("catalogo");}
      else if(a==="clear-quote-cart"){if(confirm("Remover todos os produtos do carrinho?")){state.cart=[];updateTop();renderCart();}}
      else if(a==="toggle-quote-expand")$("#cartDrawer").classList.toggle("quote-expanded");
      else if(a==="lookup-cart-cep")await lookupCartCep();
      else if(a==="add-payment"){cartMeta().payments.push({method:"PIX",amount:0});renderCart()}
      else if(a==="remove-payment"){cartMeta().payments.splice(Number(btn.dataset.index),1);renderCart()}
      else if(a==="print-pre-quote")printPreQuote(id);
      else if(a==="create-quote")await createQuote();
      else if(a==="create-order")await createOrderFromCart();
      else if(a==="open-cart")openCart();
      else if(a==="logout")logout();
      else if(a==="share-product")openWhatsApp(shareTextProduct(state.products.find(p=>p.id===id)));
      else if(a==="share-cart")await shareCart();
      else if(a==="print-cart")await printCart();
      else if(a==="print-cart-internal"){if(!canSeeCost())throw Error("Sem permissão para consultar valores de custo.");await printCart(true)}
      else if(a==="scan")await scanBarcode();
      else if(a==="start-presentation"){modern.presentationMode=true;startPresentation();}
      else if(a==="presentation-add"){if(!state.presentationIds.includes(id))state.presentationIds.push(id);toast("Produto adicionado à apresentação");}
      else if(a==="close-presentation"){modern.presentationMode=false;closePresentation();}
      else if(a==="presentation-share"){const url=new URL(location.href);url.searchParams.set("catalog",state.presentationIds.join(","));navigator.clipboard?.writeText(url.toString()).then(()=>toast("Link da seleção copiado")).catch(()=>prompt("Copie o link:",url.toString()));}
      else if(a==="presentation-print")window.print();
      else if(a==="reload")await reloadAll();
      else if(a==="save-api"){API.setBase($("#integrationApiBase").value);toast("URL salva.")}
      else if(a==="test-api"){const h=await API.request("/health");toast(h.database==="connected"?"API e banco conectados":"API respondeu, banco não conectado",h.database==="connected"?"ok":"error")}
      else if(a==="save-storage"){localStorage.setItem("fp_storage_provider",$("#storageProvider").value);localStorage.setItem("fp_supabase_url",$("#supabaseUrl").value.trim());localStorage.setItem("fp_supabase_anon",$("#supabaseAnon").value.trim());localStorage.setItem("fp_supabase_bucket",$("#supabaseBucket").value.trim()||"product-media");toast("Configuração de mídia salva")}
      else if(a==="bootstrap-catalog-profiles"){const r=await API.request("/catalog-management/bootstrap-profiles",{method:"POST"});toast(`Perfis configurados: ${r.profiles?.join(", ")||"ok"}`)}
      else if(a==="open-product-form")openProductForm(id||"");
      else if(a==="new-stock-movement")openStockMovement(id||"");
      else if(a==="save-stock-movement")await saveStockMovement();
      else if(a==="import-products"){document.getElementById("productImportFile")?.click()}
      else if(a==="export-report")exportReportCsv();
      else if(a==="save-product-form")await saveProductForm(id||"");
      else if(a==="save-client-form")await saveClientForm();
      else if(a==="new-production")openProductionForm();
      else if(a==="save-production")await saveProduction();
      else if(a==="advance-production")await advanceProduction(id);
      else if(a==="new-delivery")openDeliveryForm();
      else if(a==="save-delivery")await saveDelivery();
      else if(a==="advance-delivery")await advanceDelivery(id);
      else if(a==="new-finance")openFinanceForm(btn.dataset.kind||"receivable");
      else if(a==="save-finance")await saveFinance(btn.dataset.kind||"receivable");
      else if(a==="settle-finance")await settleFinance(btn.dataset.kind||"receivable",id);
      else if(a==="new-user")openUserForm();
      else if(a==="save-user")await saveUser();
      else if(a==="approve-order")await approveOrder(id);
      else if(a==="print-quote")await printQuote(id);
      else if(a==="reset-blank-demo")await resetBlankDemo();
      else if(a==="save-settings")await saveSettings();
    }catch(err){toast(err.message||"Erro","error")}
  });
  document.addEventListener("change",async e=>{
    modernInput(e);
    if(e.target.id==="catalogSource"){state.filters.source=e.target.value;state.filters.page=1;if(e.target.value!=="official"){await loadPvReference();await loadPvShowcase()}renderCatalogo()}

    if(e.target.name==="cat"){state.filters.category=e.target.value;state.filters.page=1;if(e.target.value.startsWith("PV::")&&state.filters.source==="official")state.filters.source="all";renderCatalogo()}
    if(e.target.name==="stock"){state.filters.stock=e.target.value;state.filters.page=1;renderCatalogo()}
    if(e.target.id==="catalogSort"){state.filters.sort=e.target.value;renderCatalogo()}
    if(e.target.id==="studioProductSelect"){state.studioProductId=e.target.value;renderStudio()}
    if(e.target.id==="cartClient"){await setCommercialClient(e.target.value)}
    if(e.target.id==="cartPayment"){cartMeta().payment=e.target.value;markCartDirty()}
    if(e.target.matches("[data-cart-discount]")){state.cart[Number(e.target.dataset.cartDiscount)].discount=clamp(Number(e.target.value)||0,0,100);updateTop();renderCart()}
    if(e.target.matches("[data-cart-unit]")){state.cart[Number(e.target.dataset.cartUnit)].unitPrice=Math.max(0,Number(e.target.value)||0);updateTop();renderCart()}
    if(e.target.matches("[data-pay-value]")){cartMeta().payments[Number(e.target.dataset.payValue)].amount=Math.max(0,Number(e.target.value)||0);renderCart()}
    if(e.target.matches("[data-pay-date]")){cartMeta().payments[Number(e.target.dataset.payDate)].date=e.target.value;markCartDirty()}


    if(e.target.matches("[data-pay-method]")){cartMeta().payments[Number(e.target.dataset.payMethod)].method=e.target.value;markCartDirty()}
    if(e.target.matches?.('input[data-replace-photo]')){
      try{await replaceStudioPhoto(e.target.files?.[0],Number(e.target.dataset.replacePhoto))}
      catch(err){toast(err.message||"Não foi possível trocar a foto","error")}
      return;
    }
    if(e.target.id==="studioPhotoInput"||e.target.id==="studioCameraInput"){
      const p=state.products.find(x=>x.id===state.studioProductId);if(!p)return;
      const capacity=Math.max(0,CFG.MAX_PHOTOS_PER_PRODUCT-mediaFor(p.id).length);
      const files=[...e.target.files].slice(0,capacity);let count=0;
      const draft={};for(const id of ["studioTitle","studioSubtitle","studioStatus","studioFeatured","studioPublished","studioWarranty","studioDescription","studioHighlights","studioTags"]){const el=document.getElementById(id);if(el)draft[id]=el.value;}
      for(const f of files){
        try{
          const src=await storePhoto(f,p.id);count++;
          if(state.demo){state.catalog.media[p.id]||={photos:[],variantPhotos:{}};state.catalog.media[p.id].photos.push(src);}
        }catch(err){toast(err.message||"Falha ao enviar imagem","error");}
      }
      if(state.demo){if(count)await saveCatalogState();}
      else if(count)await loadCatalogState();
      if(count){logHistory("MÍDIA","Produto",`${p.name}: ${count} arquivo(s)`);toast(`${count} foto(s) salvas`);}
      renderStudio();for(const [id,v] of Object.entries(draft)){const el=document.getElementById(id);if(el)el.value=v;}
      e.target.value="";
    }
    if(e.target.id==="productImportFile"){await handleProductImportInput(e.target.files?.[0]);e.target.value=""}
    if(e.target.id==="bulkCatalogInput"){
      const files=[...e.target.files];let matched=0,unmatched=[];
      for(const file of files){
        const fname=norm(file.name);
        const p=state.products.find(p=>fname.includes(norm(p.code))||fname.startsWith(norm(p.code).replace(/[^a-z0-9]/g,"")));
        if(!p){unmatched.push(file.name);continue}
        if(mediaFor(p.id).length>=CFG.MAX_PHOTOS_PER_PRODUCT)continue;
        try{
          const src=await storePhoto(file,p.id);
          if(state.demo){state.catalog.media[p.id]||={photos:[],variantPhotos:{}};state.catalog.media[p.id].photos.push(src);}
          matched++;
        }catch(err){unmatched.push(file.name)}
      }
      if(matched){
        if(state.demo)await saveCatalogState();else await loadCatalogState();
        logHistory("UPLOAD EM LOTE","Catálogo",`${matched} foto(s)`);
      }
      toast(`${matched} foto(s) vinculada(s)${unmatched.length?` • ${unmatched.length} sem vínculo` : ""}`,unmatched.length?"error":"ok");renderCatalogManager();
      e.target.value="";
    }
  });
  document.addEventListener("input",e=>{
    modernInput(e);
    if(e.target.id==="catalogSearch"){
      const q=e.target.value,cursor=e.target.selectionStart;
      state.filters.q=q;state.filters.page=1;
      clearTimeout(window._fpCatalogSearchTimer);
      window._fpCatalogSearchTimer=setTimeout(()=>{
        if(!document.getElementById("catalogSearch"))return;
        renderCatalogo();const input=document.getElementById("catalogSearch");
        if(input){input.focus();try{input.setSelectionRange(cursor,cursor)}catch{}}
      },180);
    }
    if(e.target.id==="clientSearch"){state.filters.q=e.target.value;renderClientes()}
    if(e.target.id==="catalogManagerSearch"){state.catalogManagerQuery=e.target.value;renderCatalogManager()}
    if(e.target.id==="cfDocument")e.target.value=formatDoc(e.target.value);
    if(e.target.id==="cfPhone")e.target.value=formatPhone(e.target.value);
    if(e.target.id==="cfCep")e.target.value=formatCep(e.target.value);
    if(e.target.id==="cfState")e.target.value=e.target.value.toUpperCase().replace(/[^A-Z]/g,"").slice(0,2);
    if(e.target.id==="pfPrice"||e.target.id==="pfCost")updateProductMarginPreview();
    for(const [field,key] of Object.entries({cartCep:"cep",cartNumber:"number",cartComplement:"complement",cartStreet:"street",cartDistrict:"district",cartCity:"city",cartUf:"uf"})){if(e.target.id===field){cartMeta()[key]=e.target.value;markCartDirty()}}
    if(e.target.id==="cartNotes"){cartMeta().notes=e.target.value;markCartDirty()}
  });
  $("#cartButton").onclick=openCart;$("#drawerBackdrop").onclick=closeCart;$("#logoutButton").onclick=logout;$("#menuButton").onclick=()=>$("#sidebar").classList.toggle("open");$("#scanButton").onclick=scanBarcode;$("#notificationButton").onclick=showNotifications;$("#favoriteShortcut").onclick=()=>{state.filters.favorites=true;go("catalogo")};$("#presentationButton").onclick=()=>startPresentation();
  $("#globalSearch").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();openGlobalSearch(e.target.value)}});
  document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("#globalSearch").focus()}if(e.key==="Escape"){closeModal();closeCart();$("#notificationPopover").classList.add("hidden")}})
  let draggedMediaIndex=null;
  document.addEventListener("dragstart",e=>{const item=e.target.closest?.("[data-media-index]");if(!item)return;draggedMediaIndex=Number(item.dataset.mediaIndex);item.classList.add("dragging")});
  document.addEventListener("dragend",e=>{e.target.closest?.("[data-media-index]")?.classList.remove("dragging");$$(".drop-target").forEach(x=>x.classList.remove("drop-target"))});
  document.addEventListener("dragover",e=>{const item=e.target.closest?.("[data-media-index]");if(item){e.preventDefault();item.classList.add("drop-target")}});
  document.addEventListener("dragleave",e=>{e.target.closest?.("[data-media-index]")?.classList.remove("drop-target")});
  document.addEventListener("drop",async e=>{const item=e.target.closest?.("[data-media-index]");if(!item||draggedMediaIndex===null)return;e.preventDefault();const target=Number(item.dataset.mediaIndex),arr=mediaFor(state.studioProductId);if(target!==draggedMediaIndex&&arr[draggedMediaIndex]){const [moved]=arr.splice(draggedMediaIndex,1);arr.splice(target,0,moved);await saveCatalogState();renderStudio()}draggedMediaIndex=null});
  window.addEventListener("online",()=>{state.online=true;updateTop();toast("Conexão restaurada")});window.addEventListener("offline",()=>{state.online=false;updateTop();toast("Você está offline. Aguarde reconexão para consultar dados reais.","error")});
}
async function reloadAll(){try{await loadAll();toast("Sincronizado");render()}catch(e){toast(e.message,"error")}}
let loginInProgress=false;
$("#loginForm").addEventListener("submit",async e=>{
  e.preventDefault();
  if(loginInProgress)return;
  loginInProgress=true;
  const form=e.currentTarget,submit=form.querySelector('button[type="submit"]');
  if(submit)submit.disabled=true;
  const fd=new FormData(form);
  $("#loginStatus").textContent="Conectando...";
  try{
    API.setBase(fd.get("apiBase"));
    const email=String(fd.get("email")||"").trim().toLowerCase();
    // When the ERP accepted authentication but the subsequent catalogue load
    // was rate-limited, reuse the validated session instead of sending the
    // same credentials again on every click.
    const sameSession=Boolean(API.token()&&state.user&&String(state.user.email||"").trim().toLowerCase()===email);
    if(!sameSession){
      API.setToken("");state.user=null;
      await login(email,String(fd.get("password")||""));
    }
    await loadAll();state.demo=false;showApp();toast("ERP sincronizado");
    const requested=new URLSearchParams(location.search).get("product");if(requested&&!window._fpSharedLinkOpened){window._fpSharedLinkOpened=true;setTimeout(()=>openProduct(requested),100)}
  }catch(err){
    const authenticated=Boolean(API.token()&&state.user);
    if([401,403].includes(Number(err.status))){API.setToken("");state.user=null;}
    const explanation=authenticated&&Number(err.status)===429?" Login realizado; falta sincronizar os dados. Aguarde antes de clicar novamente (sem reenviar o login).":"";
    $("#loginStatus").textContent=err.message+explanation;toast(err.message+explanation,"error");
  }finally{
    loginInProgress=false;
    if(submit)submit.disabled=false;
  }
});
if(!(location.protocol==="file:"||["localhost","127.0.0.1"].includes(location.hostname)))$("#demoButton").classList.add("hidden");
$("#demoButton").onclick=async()=>{if(!(location.protocol==="file:"||["localhost","127.0.0.1"].includes(location.hostname)))return;state.demo=true;state.user={id:"demo",full_name:"Admin",role:"administrator"};state.permissions=["*"];await loadAll();showApp()};
if(location.protocol!=="file:")localStorage.removeItem("fp_commercial_v4_snapshot");
const modalRoot=$("#modalRoot");
function syncModalScroll(){
  document.documentElement.classList.toggle("fp-modal-open",modalRoot.classList.contains("show")&&modalRoot.childElementCount>0);
}
const modalObserver=new MutationObserver(syncModalScroll);
modalObserver.observe(modalRoot,{attributes:true,attributeFilter:["class"],childList:true});
syncModalScroll();
$("#apiBaseInput").value=API.base();bind();
window.addEventListener("beforeunload",e=>{if(modern.dirty&&state.cart.length){e.preventDefault();e.returnValue=""}});

if(API.token()&&API.base())(async()=>{try{state.user=await API.request("/auth/me");await loadAll();showApp();const requested=new URLSearchParams(location.search).get("product");if(requested&&!window._fpSharedLinkOpened){window._fpSharedLinkOpened=true;setTimeout(()=>openProduct(requested),100)}}catch{API.setToken("")}})();
})();
