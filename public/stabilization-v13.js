(() => {
  const V = "13.0.0";
  let currentModalKind = "";

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));

  const money = value => new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(value||0));
  const isoDay = d => new Date(d).toISOString().slice(0,10);

  async function json(path, options={}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        "Accept":"application/json",
        ...(options.body instanceof FormData ? {} : {"Content-Type":"application/json"}),
        ...(options.headers||{})
      }
    });
    let body=null;
    if(response.status!==204)body=await response.json().catch(()=>null);
    if(!response.ok){
      const detail=body?.detail;
      const message=typeof detail==="string"?detail:(detail?.message||body?.message||`Erro HTTP ${response.status}`);
      const error=new Error(message); error.status=response.status; error.body=body; throw error;
    }
    return body;
  }

  function setCard(label, value, trend="Dados atualizados pelo sistema") {
    const cards=[...document.querySelectorAll("#dashboard .kpi")];
    const card=cards.find(c=>c.querySelector("small")?.textContent.trim()===label);
    if(!card)return;
    const strong=card.querySelector("strong");
    const trendEl=card.querySelector(".trend");
    if(strong)strong.textContent=value;
    if(trendEl){trendEl.textContent=trend;trendEl.className="trend";}
  }

  async function refreshDashboardReal(){
    try{
      const [summary,orders,production,products,balances,financial,deliveries]=await Promise.all([
        json("/api/v1/dashboard/summary"),
        json("/api/v1/sales-orders").catch(()=>[]),
        json("/api/v1/production-orders").catch(()=>[]),
        json("/api/v1/products").catch(()=>[]),
        json("/api/v1/inventory/balances").catch(()=>[]),
        json("/api/v1/financial-entries").catch(()=>[]),
        json("/api/v1/deliveries").catch(()=>[])
      ]);

      const today=isoDay(new Date());
      const now=new Date(),year=now.getFullYear(),month=now.getMonth();
      const inMonth = value => {
        if(!value)return false;
        const d=new Date(`${String(value).slice(0,10)}T12:00:00`);
        return d.getFullYear()===year && d.getMonth()===month;
      };
      const activeOrder=o=>!["Expedido","Cancelado","Concluído","Concluída"].includes(String(o.status||""));
      const validSale=o=>!["Rascunho","Cancelado"].includes(String(o.status||""));
      const todaySales=(orders||[]).filter(o=>String(o.issue_date||"").slice(0,10)===today&&validSale(o)).reduce((s,o)=>s+Number(o.total||0),0);
      const monthSales=(orders||[]).filter(o=>inMonth(o.issue_date)&&validSale(o)).reduce((s,o)=>s+Number(o.total||0),0);

      const monthIncome=(financial||[]).filter(x=>x.kind==="Receita"&&inMonth(x.due_date||x.created_at)).reduce((s,x)=>s+Number(x.amount||0),0);
      const monthExpense=(financial||[]).filter(x=>x.kind==="Despesa"&&inMonth(x.due_date||x.created_at)).reduce((s,x)=>s+Number(x.amount||0),0);

      const productMap=new Map((products||[]).map(p=>[String(p.id),p]));
      const balanceByProduct=new Map();
      (balances||[]).forEach(b=>balanceByProduct.set(String(b.product_id),(balanceByProduct.get(String(b.product_id))||0)+Number(b.available_quantity||0)));
      const critical=(products||[]).filter(p=>{
        const min=Number(p.min_stock||0);
        if(min<=0)return false;
        const available=balanceByProduct.has(String(p.id))?balanceByProduct.get(String(p.id)):Number(p.stock||0)-Number(p.reserved_stock||0);
        return available<=min;
      }).length;

      const overdue=(financial||[]).filter(x=>{
        const status=String(x.status||"").toLowerCase();
        return x.due_date && String(x.due_date)<today && !status.includes("pago") && !status.includes("receb");
      }).reduce((s,x)=>s+Number(x.amount||0),0);

      const deliveryToday=(deliveries||[]).filter(x=>String(x.scheduled_date||"").slice(0,10)===today && !["Entregue","Cancelada","Cancelado"].includes(String(x.status||""))).length;

      setCard("Faturamento hoje",money(todaySales),todaySales?"Pedidos confirmados de hoje":"Sem faturamento confirmado hoje");
      setCard("Faturamento do mês",money(monthSales),monthSales?"Pedidos confirmados no mês":"Sem faturamento confirmado no mês");
      setCard("Pedidos ativos",String((orders||[]).filter(activeOrder).length),"Pedidos ainda não finalizados");
      setCard("Lucro estimado",money(monthIncome-monthExpense),"Receitas menos despesas do mês");
      setCard("Produção em andamento",String((production||[]).filter(x=>x.status!=="Concluída").length),"Ordens ainda não concluídas");
      setCard("Estoque crítico",String(critical),critical?"Itens no mínimo ou abaixo":"Nenhum item crítico");
      setCard("Contas vencidas",money(overdue),overdue?"Títulos vencidos pendentes":"Nenhuma conta vencida");
      setCard("Entregas hoje",String(deliveryToday),deliveryToday?"Entregas programadas para hoje":"Nenhuma entrega hoje");

      renderMonthlySales(orders||[]);
      window.fpDashboardLastRefresh=new Date().toISOString();
      return true;
    }catch(error){
      console.warn("Dashboard real aguardando backend:",error);
      return false;
    }
  }

  function renderMonthlySales(orders){
    const target=document.getElementById("salesBars");
    if(!target)return;
    const year=new Date().getFullYear();
    const values=Array.from({length:12},()=>0);
    orders.forEach(o=>{
      if(!o.issue_date||["Rascunho","Cancelado"].includes(String(o.status||"")))return;
      const d=new Date(`${String(o.issue_date).slice(0,10)}T12:00:00`);
      if(d.getFullYear()===year)values[d.getMonth()]+=Number(o.total||0);
    });
    const max=Math.max(1,...values);
    const months=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
    target.innerHTML=values.map((v,i)=>`<div class="bar-wrap" title="${money(v)}"><div class="bar" style="height:${Math.max(5,(v/max)*100)}%"></div><span>${months[i]}</span></div>`).join("");
  }

  async function hydrateCommercial(){
    try{
      const [orders,quotes]=await Promise.all([
        json("/api/v1/sales-orders").catch(()=>[]),
        json("/api/v1/quotes").catch(()=>[])
      ]);
      data.orders=(orders||[]).map(o=>{
        const item=(o.items||[])[0]||{};
        const product=(o.items||[]).length>1?`${item.description||"Produto"} +${o.items.length-1}`:(item.description||"—");
        return[o.code||o.id,o.client_name||"—",product,money(o.total),o.payment_method||"—",o.issue_date||"—",o.status||"—",o.id];
      });
      data.quotes=(quotes||[]).map(q=>[
        q.code||q.id,q.client_name||"—",money(q.total),q.valid_until||"—",`${Number(q.probability||0)}%`,"—",q.status||"Rascunho",q.id
      ]);
      try{render();}catch(_){}
      return true;
    }catch(error){
      console.warn("Comercial:",error);
      return false;
    }
  }

  async function loginReal(){
    const username=document.getElementById("loginUser")?.value.trim()||"";
    const password=document.getElementById("loginPassword")?.value||"";
    const message=document.getElementById("loginAccessMessage");
    if(!username||!password){
      if(message){message.textContent="Informe usuário/e-mail e senha.";message.classList.add("show");}
      return false;
    }
    try{
      const result=await json("/api/v1/auth/login",{method:"POST",body:JSON.stringify({username,password})});
      localStorage.setItem("access_token",result.token);
      localStorage.setItem("fp_logged","1");
      localStorage.setItem("fp_role",result.user?.role==="administrator"?"Administrador":(result.user?.role||"Administrador"));
      if(message)message.classList.remove("show");
      document.getElementById("login")?.classList.add("hidden");
      document.getElementById("erp")?.classList.remove("hidden");
      await refreshDashboardReal();
      setTimeout(()=>window.fpReloadEverythingFromBackend?.(),100);
      return true;
    }catch(error){
      if(message){message.textContent=`Acesso negado: ${error.message}`;message.classList.add("show");}
      return false;
    }
  }

  function installAuthMode(){
    const originalEnter=window.enterApp;
    window.enterApp=function(bypass=false){
      const required=Boolean(window.FP_AUTH_REQUIRED)||localStorage.getItem("fp_auth_mode")==="required";
      if(required&&!bypass)return loginReal();
      return originalEnter ? originalEnter(bypass) : true;
    };
    const originalDemo=window.demoLogin;
    window.demoLogin=function(role){
      if(Boolean(window.FP_AUTH_REQUIRED)||localStorage.getItem("fp_auth_mode")==="required"){
        toast("Modo demonstração desativado neste ambiente.");
        return false;
      }
      return originalDemo ? originalDemo(role) : false;
    };
  }

  function buildQuotePayload(asOrder=false){
    const clientSelect=document.getElementById("fpQuoteClient");
    const productSelect=document.getElementById("fpQuoteProduct");
    const localClient=(enterpriseData.clients||[]).find(c=>String(c.id)===String(clientSelect?.selectedOptions[0]?.dataset.clientId||""));
    const localProduct=(enterpriseData.products||[]).find(p=>String(p.id)===String(productSelect?.selectedOptions[0]?.dataset.productId||""));
    const qty=Math.max(1,Number(document.getElementById("fpQuoteQty")?.value)||1);
    const unit=Number(document.getElementById("fpQuoteUnitPrice")?.value)||0;
    const percent=Math.min(100,Math.max(0,Number(document.getElementById("fpQuoteDiscount")?.value)||0));
    const freight=Math.max(0,Number(document.getElementById("fpQuoteFreight")?.value)||0);
    const payment=document.getElementById("fpQuotePayment")?.value||"";
    const textarea=document.querySelector("#modalBody textarea");
    const notes=textarea?.value||"";
    const dateInput=document.querySelector('#modalBody input[type="date"]');
    if(!localClient)throw new Error("Selecione um cliente.");
    if(!localProduct)throw new Error("Selecione um produto.");
    if(!localProduct._serverId)throw new Error("O produto ainda não foi sincronizado com o backend.");
    if(asOrder){
      return{
        client_id:localClient._serverId||null,
        client_name:localClient.name||"",
        payment_method:payment,
        delivery_address:localClient.address||"",
        notes,
        discount:0,
        freight,
        items:[{
          product_id:localProduct._serverId,
          description:localProduct.name||"",
          quantity:qty,
          unit_price:unit,
          discount_percent:percent
        }]
      };
    }
    return{
      client_id:localClient._serverId||null,
      client_name:localClient.name||"",
      valid_until:dateInput?.value||null,
      probability:0,
      payment_method:payment,
      status:"Rascunho",
      notes,
      items:[{
        product_id:localProduct._serverId,
        product_name:localProduct.name||"",
        quantity:qty,
        unit_price:unit,
        discount:(qty*unit)*(percent/100)
      }]
    };
  }

  async function saveCommercialModal(){
    const asOrder=currentModalKind==="sales-order";
    try{
      const payload=buildQuotePayload(asOrder);
      const result=await json(asOrder?"/api/v1/sales-orders":"/api/v1/quotes",{method:"POST",body:JSON.stringify(payload)});
      clearDirty?.();
      closeModal?.();
      toast(asOrder?`Pedido ${result.code||""} salvo no backend`:`Orçamento ${result.code||""} salvo no backend`);
      await Promise.allSettled([refreshDashboardReal(),hydrateCommercial()]);
      return true;
    }catch(error){
      toast(error.message);
      return false;
    }
  }

  function installCommercialModal(){
    const originalOpen=window.openModal;
    window.openModal=function(title,type="generic"){
      currentModalKind=(type==="quote" && /pedido/i.test(String(title)))?"sales-order":type;
      return originalOpen(title,type);
    };
    const originalSave=window.saveModal;
    window.saveModal=function(){
      if((currentModalKind==="quote"||currentModalKind==="sales-order") && document.getElementById("fpQuoteClient")){
        return saveCommercialModal();
      }
      return originalSave();
    };
  }

  async function syncEnterpriseRecord(type,record,isNew){
    if(type==="products"){
      const categoryRecord=(engineeringData?.categories||[]).find(c=>String(c.id||"")===String(record.categoryId||"")||String(c.name||"").toLowerCase()===String(record.category||"").toLowerCase());
      const supplierRecord=(enterpriseData?.suppliers||[]).find(x=>String(x._serverId||"")===String(record.supplierId||"")||String(x.id||"")===String(record.supplierId||"")||String(x.legalName||x.tradeName||"").toLowerCase()===String(record.supplier||"").toLowerCase());
      const locationRecord=(engineeringData?.locations||[]).find(l=>String(l.id||"")===String(record.locationId||""));
      const payload={
        code:record.code||record.id,
        name:record.name||"",
        description:record.description||"",
        item_type:record.itemType||"Produto acabado",
        category_id:categoryRecord?.id||null,
        supplier_id:supplierRecord?._serverId||supplierRecord?.id||null,
        location_id:locationRecord?.id||null,
        color:record.color||"",
        size:record.size||"",
        unit:record.unit||"UN",
        cost:Number(record.cost||0),
        technical_cost:Number(record.technicalCost||0),
        price:Number(record.price||0),
        stock:Number(record.stock||0),
        reserved_stock:Number(record.reservedStock||0),
        min_stock:Number(record.minStock||0),
        base_stock:Number(record.baseStock||0),
        manufacturing_enabled:!!record.manufacturingEnabled,
        active:record.status!=="Inativo"
      };
      const result=await json(record._serverId?`/api/v1/products/${record._serverId}`:"/api/v1/products",{method:record._serverId?"PUT":"POST",body:JSON.stringify(payload)});
      record._serverId=result.id;
      record.id=record.id||result.id;
      return result;
    }
    if(type==="suppliers"){
      const payload={
        legal_name:record.legalName||record.tradeName||"",
        trade_name:record.tradeName||"",
        document:record.document||"",
        email:record.email||"",
        phone:record.phone||"",
        notes:record.notes||"",
        active:record.status!=="Inativo"
      };
      const result=await json(record._serverId?`/api/v1/suppliers/${record._serverId}`:"/api/v1/suppliers",{method:record._serverId?"PUT":"POST",body:JSON.stringify(payload)});
      record._serverId=result.id;
      return result;
    }
  }

  function installEnterpriseSync(){
    const originalSave=window.saveEnterpriseForm;
    window.saveEnterpriseForm=function(){
      const state=enterpriseFormState?{...enterpriseFormState}:null;
      const ok=originalSave();
      if(ok && state && ["products","suppliers"].includes(state.type)){
        const list=enterpriseData[state.type]||[];
        const record=state.id?list.find(x=>x.id===state.id):list[0];
        if(record){
          syncEnterpriseRecord(state.type,record,!state.id).then(()=>{
            window.fpSaveEverything?.({syncServer:true,force:true});
            toast("Cadastro salvo e sincronizado com o backend");
          }).catch(error=>{
            record._syncError=error.message;
            toast(`Salvo localmente, mas o backend recusou: ${error.message}`);
          });
        }
      }
      if(ok && state?.type==="accessUsers"){
        const list=enterpriseData.accessUsers||[];
        const record=state.id?list.find(x=>x.id===state.id):list[0];
        if(record)delete record.password;
        toast("Senha não é armazenada no front. Use o usuário do backend para acesso real.");
      }
      return ok;
    };
  }

  function installInventoryActions(){
    window.openInventoryModal=function(){
      openFrontActionModal(
        "Movimentação de estoque",
        "Toda alteração será registrada no ledger do backend.",
        `<form class="grid form-grid">
          <div class="field"><label>Produto</label><select name="product_id" required>${(engineeringData.products||[]).map(p=>`<option value="${esc(p._serverId||p.id)}">${esc(p.code)} · ${esc(p.name)}</option>`).join("")}</select></div>
          <div class="field"><label>Local</label><select name="location_id">${(engineeringData.locations||[]).map(l=>`<option value="${esc(l.id)}">${esc(l.address_code||l.name)}</option>`).join("")}</select></div>
          <div class="field"><label>Tipo</label><select name="movement_type"><option value="AJUSTE_ENTRADA">Entrada / ajuste positivo</option><option value="AJUSTE_SAIDA">Saída / ajuste negativo</option></select></div>
          <div class="field"><label>Quantidade</label><input name="quantity" type="number" min="0.0001" step="0.0001" required></div>
          <div class="field"><label>Custo unitário</label><input name="unit_cost" type="number" min="0" step="0.01"></div>
          <div class="field" style="grid-column:1/-1"><label>Motivo / observações</label><textarea name="notes" required></textarea></div>
        </form>`,
        async values=>{
          try{
            const qty=Math.abs(Number(values.quantity||0));
            if(!qty)throw new Error("Informe uma quantidade maior que zero.");
            const signed=values.movement_type==="AJUSTE_SAIDA"?-qty:qty;
            await json("/api/v1/inventory/movements",{method:"POST",body:JSON.stringify({
              product_id:values.product_id,
              location_id:values.location_id||null,
              movement_type:values.movement_type,
              quantity:signed,
              unit_cost:Number(values.unit_cost||0),
              reference_type:"manual_adjustment",
              reference_id:"",
              notes:values.notes||""
            })});
            toast("Movimentação registrada no backend");
            await Promise.allSettled([hydrateEngineering(),refreshDashboardReal()]);
          }catch(error){toast(error.message);}
        }
      );
    };

    window.openTransferModal=function(){
      openFrontActionModal(
        "Transferência de estoque",
        "Bloqueada nesta versão até o backend possuir transferência atômica entre locais.",
        `<div class="notice"><strong>Proteção contra divergência</strong><br><br>
        A transferência não será simulada nem executada como duas operações independentes. Isso evita uma saída ser registrada sem a entrada correspondente. Enquanto o endpoint transacional não estiver disponível no backend, use movimentações manuais controladas.</div>`
      );
    };
  }

  function installCentralEmptyState(){
    window.renderCentral=function(){
      const approvals=document.getElementById("approvalsList");
      if(approvals)approvals.innerHTML='<div class="empty">Nenhuma aprovação real pendente.</div>';
      const agenda=document.getElementById("agendaToday");
      if(agenda)agenda.innerHTML='<div class="empty">Nenhum compromisso cadastrado.</div>';
      const task=document.getElementById("taskBoard");
      if(task)task.innerHTML='<div class="empty">Nenhuma tarefa cadastrada.</div>';
      try{renderCalendar("unifiedCalendar",[])}catch(_){}
    };
    renderCentral();
  }

  function installProductionDnD(){
    window.setupDragAndDrop=function(){
      document.querySelectorAll("#productionBoard .kan-card").forEach(card=>{
        card.draggable=true;
        card.addEventListener("dragstart",()=>card.classList.add("dragging"));
        card.addEventListener("dragend",()=>card.classList.remove("dragging"));
      });
      document.querySelectorAll("#productionBoard .kan-col").forEach(col=>{
        col.addEventListener("dragover",e=>{e.preventDefault();col.classList.add("drag-target")});
        col.addEventListener("dragleave",()=>col.classList.remove("drag-target"));
        col.addEventListener("drop",async e=>{
          e.preventDefault();col.classList.remove("drag-target");
          const card=document.querySelector("#productionBoard .kan-card.dragging");
          if(!card)return;
          const id=card.dataset.orderId||card.getAttribute("data-id");
          const stage=col.querySelector(".kan-head")?.childNodes[0]?.textContent?.trim()||"";
          if(!id){toast("Esta OP não possui ID do backend; movimento cancelado.");return;}
          try{
            await json(`/api/v1/production-orders/${encodeURIComponent(id)}/workflow-stage?stage=${encodeURIComponent(stage)}`,{method:"PATCH"});
            toast("Etapa atualizada no backend");
            await hydrateEngineering();
          }catch(error){toast(error.message);}
        });
      });

      document.querySelectorAll("#crmBoard .kan-card").forEach(card=>card.draggable=false);
    };
  }

  function installServiceWorker(){
    if("serviceWorker" in navigator && location.protocol==="https:"){
      navigator.serviceWorker.register("./sw.js").catch(err=>console.warn("Service worker:",err));
    }
  }

  function cleanDemoWords(){
    document.querySelectorAll(".workspace small").forEach(el=>{
      if(/ambiente de produção/i.test(el.textContent||""))el.textContent="Ambiente de homologação";
    });
    document.querySelectorAll("button").forEach(btn=>{
      if(btn.textContent.trim()==="Comparar")btn.title="Disponível após dados reais";
    });
  }

  function wireRefreshButton(){
    const buttons=[...document.querySelectorAll("#dashboard button")].filter(b=>/atualizar/i.test(b.textContent||""));
    buttons.forEach(btn=>{
      btn.onclick=async()=>{
        btn.disabled=true;
        const old=btn.textContent;
        btn.textContent="Atualizando...";
        await Promise.allSettled([refreshDashboardReal(),hydrateEnterprise(),hydrateEngineering()]);
        btn.textContent=old;btn.disabled=false;
        toast("Dados atualizados");
      };
    });
  }

  async function boot(){
    installAuthMode();
    installCommercialModal();
    installEnterpriseSync();
    installInventoryActions();
    installCentralEmptyState();
    installProductionDnD();
    installServiceWorker();
    cleanDemoWords();
    wireRefreshButton();
    window.getMockIP=()=> "IP indisponível";

    setTimeout(()=>refreshDashboardReal(),700);
    setTimeout(()=>hydrateCommercial(),800);
    setTimeout(()=>hydrateEnterprise(),900);
    setTimeout(()=>hydrateEngineering(),1100);
    setInterval(()=>refreshDashboardReal(),60000);

    window.fpRefreshDashboardReal=refreshDashboardReal;
    window.fpHydrateCommercial=hydrateCommercial;
    window.fpLoginReal=loginReal;
    window.fpFrontVersion=V;
  }

  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});
  else boot();
})();