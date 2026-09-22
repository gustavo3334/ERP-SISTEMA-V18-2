(() => {
  const VERSION = window.FP_FRONT_VERSION || "12.0.0-preprod";
  const BACKUP_VERSION = 1;
  const RECOVERY_KEY = "fp_recovery_snapshot_v1";
  let connectionState = "checking";
  let lastBackendCheck = null;

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));

  function getTopActions(){
    return document.querySelector(".top-actions");
  }

  function currentApiLabel(){
    const base = window.fpGetApiBase?.() || "";
    if (base) return base;
    if (location.protocol === "file:") return "Não configurado";
    return `${location.origin}/api/v1`;
  }

  function setPill(state, text){
    connectionState = state;
    const pill = document.getElementById("fpOpsPill");
    if (!pill) return;
    pill.dataset.state = state;
    pill.querySelector(".fp-label").textContent = text;
  }

  async function testBackend(){
    setPill("checking","Verificando...");
    try{
      const response = await fetch("/api/v1/system/environment", {
        headers: {"Accept":"application/json","Cache-Control":"no-cache"}
      });
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = await response.json().catch(()=>({}));
      lastBackendCheck = {ok:true, status:response.status, body, at:new Date().toISOString()};
      setPill("online","Backend conectado");
      refreshOpsModal();
      return lastBackendCheck;
    }catch(error){
      lastBackendCheck = {ok:false, error:String(error.message||error), at:new Date().toISOString()};
      const localOnly = location.protocol === "file:" && !window.fpGetApiBase?.();
      setPill(localOnly ? "local" : "offline", localOnly ? "Modo local" : "Backend offline");
      refreshOpsModal();
      return lastBackendCheck;
    }
  }

  function storageSize(){
    let chars=0;
    for(let i=0;i<localStorage.length;i++){
      const key=localStorage.key(i) || "";
      const value=localStorage.getItem(key) || "";
      chars += key.length + value.length;
    }
    return Math.round((chars*2)/1024);
  }

  function operationalCounts(){
    let clients=0, products=0, employees=0, production=0, orders=0;
    try{clients = Array.isArray(enterpriseData?.clients) ? enterpriseData.clients.length : 0}catch(_){}
    try{products = Array.isArray(enterpriseData?.products) ? enterpriseData.products.length : 0}catch(_){}
    try{
      const eng = Array.isArray(engineeringData?.products) ? engineeringData.products.length : 0;
      products = Math.max(products, eng);
    }catch(_){}
    try{employees = Array.isArray(rhEmployees) ? rhEmployees.length : 0}catch(_){}
    try{production = Array.isArray(data?.production) ? data.production.length : 0}catch(_){}
    try{orders = Array.isArray(data?.orders) ? data.orders.length : 0}catch(_){}
    return {clients,products,employees,production,orders};
  }

  function exportBackup(){
    const local = {};
    for(let i=0;i<localStorage.length;i++){
      const key=localStorage.key(i);
      if(key && (key.startsWith("fp_") || key === "access_token")){
        local[key] = localStorage.getItem(key);
      }
    }
    let completeState = null;
    try{ completeState = window.fpGetCompleteState?.() || null; }catch(_){}
    const payload = {
      app:"Facil Pedido ERP",
      version:VERSION,
      backupVersion:BACKUP_VERSION,
      createdAt:new Date().toISOString(),
      apiBase:window.fpGetApiBase?.() || "",
      localStorage:local,
      completeState
    };
    const blob = new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});
    const a=document.createElement("a");
    a.href=URL.createObjectURL(blob);
    a.download=`facil-pedido-backup-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    setTimeout(()=>URL.revokeObjectURL(a.href),1000);
    window.toast?.("Backup exportado");
  }

  function createRecoverySnapshot(reason="auto"){
    try{
      const payload={
        reason,createdAt:new Date().toISOString(),version:VERSION,
        completeState:window.fpGetCompleteState?.() || null
      };
      localStorage.setItem(RECOVERY_KEY,JSON.stringify(payload));
      return true;
    }catch(_){ return false; }
  }

  function importBackupFile(file){
    if(!file) return;
    const reader=new FileReader();
    reader.onload=()=>{
      try{
        const payload=JSON.parse(String(reader.result||"{}"));
        if(!payload || payload.app!=="Facil Pedido ERP") throw new Error("Arquivo de backup inválido.");
        createRecoverySnapshot("antes-da-importacao");
        const phrase=prompt("A restauração substituirá os dados locais atuais. Digite RESTAURAR para continuar:");
        if(phrase!=="RESTAURAR") return;
        Object.entries(payload.localStorage||{}).forEach(([k,v])=>{
          if(v===null||v===undefined) localStorage.removeItem(k);
          else localStorage.setItem(k,String(v));
        });
        if(payload.completeState && window.fpRestoreEverything){
          window.fpRestoreEverything(payload.completeState);
          window.fpSaveEverything?.({syncServer:true,force:true});
        }
        alert("Backup restaurado. A página será recarregada.");
        location.reload();
      }catch(error){
        alert(error.message||"Não foi possível restaurar o backup.");
      }
    };
    reader.readAsText(file);
  }

  function restoreRecovery(){
    try{
      const raw=localStorage.getItem(RECOVERY_KEY);
      if(!raw) return alert("Nenhum ponto de recuperação disponível.");
      const payload=JSON.parse(raw);
      if(!payload.completeState) return alert("O ponto de recuperação não contém um estado restaurável.");
      const phrase=prompt("Digite RECUPERAR para voltar ao último ponto de recuperação:");
      if(phrase!=="RECUPERAR") return;
      window.fpRestoreEverything?.(payload.completeState);
      window.fpSaveEverything?.({syncServer:true,force:true});
      location.reload();
    }catch(error){ alert("Não foi possível recuperar os dados."); }
  }

  async function runDiagnostics(){
    const results=[];
    results.push(["HTML principal",!!document.querySelector("#dashboard"),"Dashboard encontrado"]);
    results.push(["Navegação",document.querySelectorAll(".nav-btn[data-page]").length>5,`${document.querySelectorAll(".nav-btn[data-page]").length} módulos`]);

    let localOk=false;
    try{
      const key="__fp_diag__";
      localStorage.setItem(key,"ok");
      localOk=localStorage.getItem(key)==="ok";
      localStorage.removeItem(key);
    }catch(_){}
    results.push(["Persistência local",localOk,localOk?"Leitura e escrita OK":"Falha no armazenamento local"]);

    const persistence=window.fpPersistenceStatus?.();
    results.push(["Persistência universal",!!window.fpSaveEverything,window.fpSaveEverything?"Rotina ativa":"Rotina não carregada"]);

    const backend=await testBackend();
    results.push(["Backend FastAPI",!!backend.ok,backend.ok?`HTTP ${backend.status}`:(backend.error||"Sem conexão")]);

    const counts=operationalCounts();
    results.push(["Dados carregados",true,`${counts.clients} clientes · ${counts.products} produtos · ${counts.employees} colaboradores`]);

    const fakeQuote = [...document.querySelectorAll("#quoteItems input")].some(i=>/BAU 79 Suede Preto/i.test(i.value||""));
    results.push(["Sem item demonstrativo automático",!fakeQuote,fakeQuote?"Item demonstrativo encontrado":"OK"]);

    renderTestResults(results);
    return results;
  }

  function renderTestResults(results){
    const target=document.getElementById("fpTestResults");
    if(!target) return;
    target.innerHTML=results.map(([name,ok,detail])=>`
      <div class="fp-test-row">
        <div><strong>${esc(name)}</strong><small style="display:block;color:var(--muted);margin-top:3px">${esc(detail)}</small></div>
        <span class="${ok?"fp-ok":"fp-bad"}">${ok?"OK":"ATENÇÃO"}</span>
      </div>`).join("");
  }

  function modalHtml(){
    const counts=operationalCounts();
    const status=window.fpPersistenceStatus?.() || {};
    return `
      <div class="fp-ops-dialog">
        <div class="fp-ops-head">
          <div><h3>Central de diagnóstico</h3><p>Conexão, persistência, backup e checklist antes de publicar.</p></div>
          <button class="icon-btn" id="fpOpsClose" aria-label="Fechar">✕</button>
        </div>
        <div class="fp-ops-body">
          <div class="fp-ops-grid">
            <div class="fp-ops-card"><strong>Versão do front</strong><div class="fp-ops-value">${esc(VERSION)}</div><small>Build de pré-produção para testes.</small></div>
            <div class="fp-ops-card"><strong>Backend</strong><div class="fp-ops-value">${lastBackendCheck?.ok?"Conectado":"Não confirmado"}</div><small>${esc(currentApiLabel())}</small></div>
            <div class="fp-ops-card"><strong>Persistência</strong><div class="fp-ops-value">${status.initialized?"Ativa":"Inicializando"}</div><small>Revisão do servidor: ${esc(status.serverRevision ?? "—")}</small></div>
            <div class="fp-ops-card"><strong>Cache local</strong><div class="fp-ops-value">${storageSize()} KB</div><small>${counts.clients} clientes · ${counts.products} produtos · ${counts.employees} colaboradores</small></div>
          </div>

          <div class="fp-ops-field">
            <label>URL pública do backend FastAPI</label>
            <input id="fpBackendUrl" value="${esc(window.fpGetApiBase?.()||"")}" placeholder="https://seu-backend.exemplo.com">
            <small style="display:block;color:var(--muted);margin-top:6px">Deixe vazio quando front e API estiverem no mesmo domínio. Na Vercel, informe a URL pública do backend.</small>
          </div>

          <div class="fp-ops-actions">
            <button class="primary" id="fpSaveBackend">Salvar backend</button>
            <button id="fpTestBackend">Testar conexão</button>
            <button id="fpForceSave">Salvar tudo agora</button>
            <button id="fpExportBackup">Exportar backup</button>
            <button id="fpImportBackup">Restaurar backup</button>
            <button id="fpRecovery">Ponto de recuperação</button>
            <button id="fpRunDiag">Executar diagnóstico</button>
          </div>
          <input id="fpBackupFile" type="file" accept=".json,application/json" hidden>
          <div class="fp-test-list" id="fpTestResults"></div>
        </div>
      </div>`;
  }

  function ensureModal(){
    let modal=document.getElementById("fpOpsModal");
    if(!modal){
      modal=document.createElement("div");
      modal.id="fpOpsModal";
      modal.className="fp-ops-modal";
      modal.innerHTML=modalHtml();
      document.body.appendChild(modal);
      wireModal(modal);
    }
    return modal;
  }

  function refreshOpsModal(){
    const old=document.getElementById("fpOpsModal");
    if(!old || !old.classList.contains("show")) return;
    old.innerHTML=modalHtml();
    wireModal(old);
  }

  function wireModal(modal){
    modal.querySelector("#fpOpsClose")?.addEventListener("click",()=>modal.classList.remove("show"));
    modal.addEventListener("click",e=>{if(e.target===modal)modal.classList.remove("show")},{once:true});
    modal.querySelector("#fpSaveBackend")?.addEventListener("click",()=>{
      const value=modal.querySelector("#fpBackendUrl").value.trim();
      if(value && !/^https?:\/\//i.test(value)) return alert("Use uma URL iniciando com https:// ou http://.");
      window.fpSetApiBase?.(value);
      alert("Configuração salva. A página será recarregada para todas as integrações usarem o novo backend.");
      location.reload();
    });
    modal.querySelector("#fpTestBackend")?.addEventListener("click",testBackend);
    modal.querySelector("#fpForceSave")?.addEventListener("click",async()=>{
      createRecoverySnapshot("salvamento-manual");
      window.fpSaveEverything?.({syncServer:true,force:true});
      window.fpSyncRhRelational?.({force:true});
      window.fpSyncClientRelational?.({force:true});
      window.toast?.("Salvamento solicitado");
      setTimeout(testBackend,500);
    });
    modal.querySelector("#fpExportBackup")?.addEventListener("click",exportBackup);
    modal.querySelector("#fpImportBackup")?.addEventListener("click",()=>modal.querySelector("#fpBackupFile").click());
    modal.querySelector("#fpBackupFile")?.addEventListener("change",e=>importBackupFile(e.target.files?.[0]));
    modal.querySelector("#fpRecovery")?.addEventListener("click",restoreRecovery);
    modal.querySelector("#fpRunDiag")?.addEventListener("click",runDiagnostics);
  }

  function openOps(){
    const modal=ensureModal();
    refreshOpsModal();
    modal.classList.add("show");
  }

  function addPill(){
    if(document.getElementById("fpOpsPill")) return;
    const actions=getTopActions();
    if(!actions) return;
    const pill=document.createElement("button");
    pill.id="fpOpsPill";
    pill.type="button";
    pill.dataset.state="checking";
    pill.title="Abrir diagnóstico de conexão e persistência";
    pill.innerHTML='<span class="fp-dot"></span><span class="fp-label">Verificando...</span>';
    pill.addEventListener("click",openOps);
    const profile=actions.querySelector(".profile");
    actions.insertBefore(pill,profile||null);
  }

  function dynamicSearch(q){
    const query=String(q||"").trim().toLowerCase();
    const results=[];
    const add=(kind,title,subtitle,page,icon)=>{
      if(!title) return;
      const hay=`${kind} ${title} ${subtitle||""}`.toLowerCase();
      if(query && !hay.includes(query)) return;
      results.push({kind,title,subtitle,page,icon});
    };

    try{
      (enterpriseData.clients||[]).forEach(c=>add("Cliente",c.name,c.document||c.phone||"", "cadastros","👤"));
      (enterpriseData.products||[]).forEach(p=>add("Produto",p.name,p.code||p.category||"", "estoque","📦"));
      (enterpriseData.suppliers||[]).forEach(s=>add("Fornecedor",s.name||s.tradeName,s.document||"", "cadastros","🏭"));
    }catch(_){}
    try{
      (engineeringData.products||[]).forEach(p=>add("Produto",p.name,p.code||p.itemType||"", "estoque","📦"));
    }catch(_){}
    try{
      (rhEmployees||[]).forEach(e=>add("Colaborador",e.name||e.fullName,e.position||e.sector||"", "rhFolha","🧑‍💼"));
    }catch(_){}
    try{
      (data.production||[]).forEach(row=>add("Produção",row?.[0],row?.[2]||"", "producao","🏭"));
      (data.orders||[]).forEach(row=>add("Pedido",row?.[0],row?.[1]||"", "vendas","🧾"));
      (data.quotes||[]).forEach(row=>add("Orçamento",row?.[0],row?.[1]||"", "vendas","📄"));
    }catch(_){}

    const unique=[];
    const seen=new Set();
    results.forEach(r=>{
      const key=`${r.kind}|${r.title}|${r.subtitle}`;
      if(!seen.has(key)){seen.add(key);unique.push(r);}
    });
    return unique.slice(0,30);
  }

  function installDynamicSearch(){
    window.globalSearch=function(q){
      const box=document.getElementById("searchResults");
      if(!box) return;
      if(document.activeElement?.id!=="globalSearch"){box.classList.remove("show");return}
      const rows=dynamicSearch(q);
      if(!rows.length){
        box.innerHTML='<div class="fp-empty-search">Nenhum registro real encontrado.</div>';
        box.classList.add("show");
        return;
      }
      box.innerHTML=rows.map((r,i)=>`
        <button class="search-item fp-search-result" type="button" data-index="${i}" style="width:100%;border:0;background:transparent;color:inherit;text-align:left">
          <span>${r.icon}</span>
          <div><strong style="font-size:12px">${esc(r.title)}</strong><small style="display:block;color:var(--muted)">${esc(r.subtitle||"")}</small></div>
          <span class="status blue fp-search-kind">${esc(r.kind)}</span>
        </button>`).join("");
      box.querySelectorAll(".fp-search-result").forEach(btn=>btn.addEventListener("click",()=>{
        const r=rows[Number(btn.dataset.index)];
        box.classList.remove("show");
        if(r?.page){
          location.hash=`#/${r.page}`;
          window.activatePage?.(r.page);
        }
      }));
      box.classList.add("show");
    };
  }

  function installRealAssistant(){
    window.askAI=function(){
      const input=document.getElementById("aiInput");
      const q=String(input?.value||"").trim();
      if(!q) return;
      const messages=document.getElementById("aiMessages");
      if(!messages) return;
      messages.insertAdjacentHTML("beforeend",`<div class="list-item"><div><strong>Você</strong><small style="display:block;margin-top:4px">${esc(q)}</small></div></div>`);

      const c=operationalCounts();
      let answer="";
      const total=c.clients+c.products+c.employees+c.production+c.orders;
      if(!total){
        answer="Ainda não há dados operacionais suficientes para uma análise. Cadastre ou sincronize clientes, produtos, pedidos, produção e colaboradores para eu gerar um resumo baseado no sistema.";
      }else if(/estoque|compr/i.test(q)){
        let critical=0;
        try{
          critical=(engineeringData.products||[]).filter(p=>{
            const stock=Number(p.stock||0), min=Number(p.minimum_stock||p.minimumStock||p.minStock||0);
            return min>0 && stock<=min;
          }).length;
        }catch(_){}
        answer=`Com os dados atualmente carregados, há ${c.products} produto(s) cadastrado(s) e ${critical} item(ns) identificado(s) no limite ou abaixo do estoque mínimo. Abra Estoque & Compras para revisar antes de gerar pedidos de compra.`;
      }else if(/produ|atras|ordem/i.test(q)){
        answer=`A visão atual possui ${c.production} ordem(ns) de produção carregada(s). Use o módulo Produção para conferir prazo, etapa e responsável de cada OP; o resumo não inventa atrasos quando a data real não está cadastrada.`;
      }else{
        answer=`Resumo dos dados carregados: ${c.clients} cliente(s), ${c.products} produto(s), ${c.orders} pedido(s), ${c.production} ordem(ns) de produção e ${c.employees} colaborador(es). Os números são derivados apenas do estado atual do sistema.`;
      }
      setTimeout(()=>messages.insertAdjacentHTML("beforeend",`<div class="list-item"><div><strong>Assistente</strong><small style="display:block;margin-top:4px">${esc(answer)}</small></div></div>`),180);
      input.value="";
    };
  }

  function sanitizeDemoReports(){
    try{
      if(typeof reportDefinitions==="undefined") return;
      Object.values(reportDefinitions).forEach(r=>{
        if(!r) return;
        r.kpis=(r.kpis||[]).map(k=>[k[0], /^R\$/i.test(String(k[1]||"")) ? "R$ 0,00" : /%/.test(String(k[1]||"")) ? "0%" : "0", "Sem dados reais", k[3]||"•", "good"]);
        r.values=(r.values||[]).map(()=>0);
        r.trend="Sem dados reais";
        r.distribution=[];
        r.ranking=[];
        r.insights=[["ℹ️","Aguardando dados reais","Este relatório será preenchido somente com informações cadastradas ou retornadas pelo backend."]];
        r.rows=[];
      });
    }catch(_){}
  }

  function safeClear(){
    const original=window.fpResetToCompletelyBlank;
    if(typeof original!=="function" || original.__fpSafeWrapped) return;
    const wrapped=function(){
      createRecoverySnapshot("antes-de-limpar");
      const phrase=prompt("Esta ação remove os dados locais do sistema. Um ponto de recuperação será criado. Digite LIMPAR para confirmar:");
      if(phrase!=="LIMPAR") return;
      return original();
    };
    wrapped.__fpSafeWrapped=true;
    window.fpResetToCompletelyBlank=wrapped;
  }

  function dailyRecovery(){
    const today=new Date().toISOString().slice(0,10);
    const key="fp_recovery_last_day";
    if(localStorage.getItem(key)===today) return;
    if(createRecoverySnapshot("backup-diario")) localStorage.setItem(key,today);
  }

  function keyboard(){
    document.addEventListener("keydown",e=>{
      if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==="s"){
        e.preventDefault();
        createRecoverySnapshot("atalho-salvar");
        window.fpSaveEverything?.({syncServer:true,force:true});
        window.toast?.("Salvamento solicitado");
      }
      if((e.ctrlKey||e.metaKey) && e.shiftKey && e.key.toLowerCase()==="b"){
        e.preventDefault(); exportBackup();
      }
    });
  }

  function installGlobalErrorCapture(){
    window.addEventListener("error",event=>{
      try{
        const logs=JSON.parse(localStorage.getItem("fp_front_error_log")||"[]");
        logs.unshift({at:new Date().toISOString(),message:event.message||"Erro",source:event.filename||"",line:event.lineno||0});
        localStorage.setItem("fp_front_error_log",JSON.stringify(logs.slice(0,50)));
      }catch(_){}
    });
    window.addEventListener("unhandledrejection",event=>{
      try{
        const logs=JSON.parse(localStorage.getItem("fp_front_error_log")||"[]");
        logs.unshift({at:new Date().toISOString(),message:String(event.reason?.message||event.reason||"Promise rejeitada")});
        localStorage.setItem("fp_front_error_log",JSON.stringify(logs.slice(0,50)));
      }catch(_){}
    });
  }

  function boot(){
    addPill();
    installDynamicSearch();
    installRealAssistant();
    sanitizeDemoReports();
    safeClear();
    keyboard();
    installGlobalErrorCapture();
    setTimeout(dailyRecovery,1800);
    setTimeout(testBackend,650);
    setInterval(testBackend,30000);
    window.fpOpenDiagnostics=openOps;
    window.fpExportBackup=exportBackup;
    window.fpRunDiagnostics=runDiagnostics;
  }

  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot,{once:true});
  else boot();
})();
