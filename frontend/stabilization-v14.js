(() => {
  const V="14.0.0";
  let modalKindV14="";
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
  const money=v=>new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(v||0));
  async function req(path,options={}){
    const response=await fetch(path,{...options,headers:{Accept:"application/json",...(options.body instanceof FormData?{}:{"Content-Type":"application/json"}),...(options.headers||{})}});
    let body=null;if(response.status!==204)body=await response.json().catch(()=>null);
    if(!response.ok){const d=body?.detail;throw new Error(typeof d==="string"?d:(d?.message||body?.message||`Erro HTTP ${response.status}`));}
    return body;
  }

  async function hydratePurchasing(){
    try{
      const orders=await req("/api/v1/purchase-orders");
      const suppliers=enterpriseData?.suppliers||[];
      data.purchases=(orders||[]).map(o=>{
        const supplier=suppliers.find(s=>String(s._serverId||s.id)===String(o.supplier_id));
        return[o.code,supplier?.tradeName||supplier?.legalName||"Fornecedor",money(o.total),o.expected_date||"—","—",o.status,o.id];
      });
      /* A listagem detalhada de compras também passa a vir do backend real.
         Isso elimina linhas demonstrativas e garante que prazo/fornecedor/status
         reapareçam após fechar e abrir o sistema. */
      try{
        if(typeof purchaseFollowupData!=="undefined"&&Array.isArray(purchaseFollowupData)){
          const products=enterpriseData?.products||engineeringData?.products||[];
          const detailed=[];
          (orders||[]).forEach(o=>{
            const supplier=suppliers.find(s=>String(s._serverId||s.id)===String(o.supplier_id));
            (o.items||[]).forEach(item=>{
              const product=products.find(p=>String(p._serverId||p.id)===String(item.product_id));
              detailed.push({
                code:o.code||"",date:String(o.issue_date||"").slice(0,10),delivery:String(o.expected_date||"").slice(0,10),
                client:"",type:"Ordem de compra",product:item.description||product?.name||"",qty:String(item.quantity??""),
                supplier:supplier?.tradeName||supplier?.legalName||"",_supplierId:supplier?._serverId||supplier?.id||o.supplier_id||"",purchaseStatus:o.status||"Aberta",
                expectedDelivery:String(o.expected_date||"").slice(0,10),observation:o.notes||"",freight:Number(o.freight||0)?money(o.freight):"",freightValue:Number(o.freight||0),
                category:product?.category||"",subcategory:product?.subcategory||"",color:product?.color||"",size:product?.size||"",
                productType:product?.itemType||product?.item_type||"",quoteStatus:o.status||"Aberta",_serverOrderId:o.id||"",_serverItemId:item.id||""
              });
            });
          });
          purchaseFollowupData.splice(0,purchaseFollowupData.length,...detailed);
          renderPurchaseFollowupTable?.();
        }
      }catch(error){console.warn("Detalhamento de compras:",error);}
      const tbody=document.getElementById("purchasesTable");
      if(tbody)tbody.innerHTML=(orders||[]).length?(orders||[]).map(o=>{
        const supplier=suppliers.find(s=>String(s._serverId||s.id)===String(o.supplier_id));
        const canReceive=!['Cancelada','Recebida'].includes(o.status);
        const canCancel=!['Cancelada','Recebida','Parcialmente recebida'].includes(o.status);
        return `<tr><td><strong>${esc(o.code)}</strong></td><td>${esc(supplier?.tradeName||supplier?.legalName||'Fornecedor')}</td><td>${money(o.total)}</td><td>${esc(o.expected_date||'—')}</td><td>—</td><td>${badge(o.status)}</td><td><div class="actions">${canReceive?`<button class="btn sm success" onclick="fpReceivePurchase('${o.id}')">Receber</button>`:''}${canCancel?`<button class="btn sm danger" onclick="fpCancelPurchase('${o.id}')">Cancelar</button>`:''}</div></td></tr>`;
      }).join(""):`<tr><td colspan="7"><div class="empty">Nenhuma compra cadastrada.</div></td></tr>`;
    }catch(e){console.warn("Compras:",e);}
  }

  function purchaseForm(){
    const suppliers=(enterpriseData?.suppliers||[]).filter(x=>x._serverId);
    const products=(enterpriseData?.products||engineeringData?.products||[]).filter(x=>x._serverId);
    return `<form id="fpPurchaseForm" class="grid form-grid">
      <div class="field"><label>Fornecedor</label><select name="supplier_id" required><option value="">Selecione</option>${suppliers.map(s=>`<option value="${esc(s._serverId)}">${esc(s.tradeName||s.legalName||s.name)}</option>`).join('')}</select></div>
      <div class="field"><label>Previsão</label><input name="expected_date" type="date"></div>
      <div class="field"><label>Condição de pagamento</label><input name="payment_terms" placeholder="Ex.: 28 dias"></div>
      <div class="field"><label>Produto</label><select name="product_id" required><option value="">Selecione</option>${products.map(p=>`<option value="${esc(p._serverId)}">${esc(p.code||'')} · ${esc(p.name)}</option>`).join('')}</select></div>
      <div class="field"><label>Quantidade</label><input name="quantity" type="number" min="0.001" step="0.001" value="1" required></div>
      <div class="field"><label>Custo unitário</label><input name="unit_cost" type="number" min="0" step="0.01" value="0" required></div>
      <div class="field"><label>Frete</label><input name="freight" type="number" min="0" step="0.01" value="0"></div>
      <div class="field"><label>Desconto</label><input name="discount" type="number" min="0" step="0.01" value="0"></div>
      <div class="field" style="grid-column:1/-1"><label>Observações</label><textarea name="notes"></textarea></div>
    </form>`;
  }

  async function savePurchase(){
    const form=document.getElementById("fpPurchaseForm");if(!form)return false;
    const f=new FormData(form);
    const product=(enterpriseData?.products||engineeringData?.products||[]).find(p=>String(p._serverId)===String(f.get('product_id')));
    const payload={supplier_id:f.get('supplier_id')||null,expected_date:f.get('expected_date')||null,payment_terms:String(f.get('payment_terms')||''),notes:String(f.get('notes')||''),discount:Number(f.get('discount')||0),freight:Number(f.get('freight')||0),items:[{product_id:String(f.get('product_id')),description:product?.name||'',quantity:Number(f.get('quantity')||0),unit_cost:Number(f.get('unit_cost')||0),location_id:product?.locationId||product?.location_id||null}]};
    try{const out=await req("/api/v1/purchase-orders",{method:"POST",body:JSON.stringify(payload)});closeModal?.();toast(`Compra ${out.code} criada`);await hydratePurchasing();return true;}catch(e){toast(e.message);return false;}
  }

  window.fpReceivePurchase=async id=>{
    try{
      const order=await req(`/api/v1/purchase-orders/${id}`);
      const remaining=(order.items||[]).filter(i=>Number(i.quantity)>Number(i.received_quantity)).map(i=>({item_id:i.id,quantity:Number(i.quantity)-Number(i.received_quantity)}));
      if(!remaining.length)return toast("Compra já recebida.");
      if(!confirm(`Receber o saldo restante de ${order.code} e atualizar o estoque?`))return;
      await req(`/api/v1/purchase-orders/${id}/receive`,{method:"POST",body:JSON.stringify({items:remaining,create_payable:true})});
      toast("Recebimento registrado no estoque e financeiro");await Promise.allSettled([hydratePurchasing(),window.fpRefreshDashboardReal?.(),hydrateEngineering?.()]);
    }catch(e){toast(e.message);}
  };
  window.fpCancelPurchase=async id=>{try{if(!confirm("Cancelar esta ordem de compra?"))return;await req(`/api/v1/purchase-orders/${id}/cancel`,{method:"POST"});toast("Compra cancelada");await hydratePurchasing();}catch(e){toast(e.message);}};
  window.fpPatchPurchaseFollowup=async(index,patch)=>{
    const row=(typeof purchaseFollowupData!=="undefined"&&purchaseFollowupData[index])||null;
    if(!row?._serverOrderId)return toast("A compra ainda não possui vínculo com o backend.");
    try{
      await req(`/api/v1/purchase-orders/${row._serverOrderId}`,{method:"PUT",body:JSON.stringify(patch||{})});
      toast("Compra atualizada e salva no sistema");
      await hydratePurchasing();
      window.fpSaveEverything?.({syncServer:true,force:true});
      return true;
    }catch(error){toast(error.message);return false;}
  };

  async function hydrateFinance(){
    try{
      const rows=await req("/api/v1/financial-entries?limit=500");
      const rec=(rows||[]).filter(x=>x.kind==="Receita"),pay=(rows||[]).filter(x=>x.kind==="Despesa");
      const rt=document.getElementById("receivablesTable"),pt=document.getElementById("payablesTable");
      if(rt)rt.innerHTML=rec.length?rec.map(x=>`<tr><td><strong>${esc(x.description)}</strong></td><td>${esc(x.category||'—')}</td><td>${esc(x.due_date||'—')}</td><td>—</td><td>${money(x.amount)}</td><td>${/recebid|pago/i.test(x.status)?money(x.amount):money(0)}</td><td>${badge(x.status)}</td><td><button class="btn sm ${/recebid|pago/i.test(x.status)?'secondary':'success'}" onclick="fpToggleFinancial('${x.id}','${esc(x.kind)}','${esc(x.status)}')">${/recebid|pago/i.test(x.status)?'Reabrir':'Receber'}</button></td></tr>`).join(''):`<tr><td colspan="8"><div class="empty">Nenhuma conta a receber.</div></td></tr>`;
      if(pt)pt.innerHTML=pay.length?pay.map(x=>`<tr><td><strong>${esc(x.description)}</strong></td><td>${esc(x.category||'—')}</td><td>${esc(x.category||'—')}</td><td>${esc(x.due_date||'—')}</td><td>${money(x.amount)}</td><td>${badge(x.status)} <button class="btn sm ${/pago/i.test(x.status)?'secondary':'success'}" onclick="fpToggleFinancial('${x.id}','${esc(x.kind)}','${esc(x.status)}')">${/pago/i.test(x.status)?'Reabrir':'Pagar'}</button></td></tr>`).join(''):`<tr><td colspan="6"><div class="empty">Nenhuma conta a pagar.</div></td></tr>`;
    }catch(e){console.warn("Financeiro:",e);}
  }
  window.fpToggleFinancial=async(id,kind,status)=>{try{const paid=/recebid|pago/i.test(status);const next=paid?(kind==='Receita'?'A receber':'A pagar'):(kind==='Receita'?'Recebido':'Pago');await req(`/api/v1/financial-entries/${id}`,{method:"PUT",body:JSON.stringify({status:next})});toast(`Status alterado para ${next}`);await Promise.allSettled([hydrateFinance(),window.fpRefreshDashboardReal?.()]);}catch(e){toast(e.message);}};

  function financeForm(){return `<form id="fpFinanceForm" class="grid form-grid"><div class="field"><label>Tipo</label><select name="kind"><option>Receita</option><option>Despesa</option></select></div><div class="field"><label>Descrição</label><input name="description" required></div><div class="field"><label>Categoria</label><input name="category"></div><div class="field"><label>Vencimento</label><input name="due_date" type="date"></div><div class="field"><label>Valor</label><input name="amount" type="number" min="0" step="0.01" required></div><div class="field"><label>Status</label><select name="status"><option>A receber</option><option>A pagar</option><option>Recebido</option><option>Pago</option></select></div><div class="field" style="grid-column:1/-1"><label>Observações</label><textarea name="notes"></textarea></div></form>`;}
  async function saveFinance(){const form=document.getElementById('fpFinanceForm');if(!form)return false;const f=new FormData(form);const kind=String(f.get('kind'));let status=String(f.get('status')||'');if(kind==='Receita'&&status==='A pagar')status='A receber';if(kind==='Despesa'&&status==='A receber')status='A pagar';try{await req('/api/v1/financial-entries',{method:'POST',body:JSON.stringify({kind,description:String(f.get('description')||''),category:String(f.get('category')||''),due_date:f.get('due_date')||null,amount:Number(f.get('amount')||0),status,notes:String(f.get('notes')||'')})});closeModal?.();toast('Lançamento financeiro salvo');await Promise.allSettled([hydrateFinance(),window.fpRefreshDashboardReal?.()]);return true;}catch(e){toast(e.message);return false;}}

  function transferForm(){
    const products=(engineeringData?.products||enterpriseData?.products||[]).filter(p=>p._serverId);
    const locs=engineeringData?.locations||[];
    return `<form id="fpTransferForm" class="grid form-grid"><div class="field"><label>Produto</label><select name="product_id" required>${products.map(p=>`<option value="${esc(p._serverId)}">${esc(p.code)} · ${esc(p.name)}</option>`).join('')}</select></div><div class="field"><label>Quantidade</label><input name="quantity" type="number" min="0.001" step="0.001" required></div><div class="field"><label>Origem</label><select name="source_location_id" required><option value="">Selecione</option>${locs.map(l=>`<option value="${esc(l.id)}">${esc(l.address_code||l.name)}</option>`).join('')}</select></div><div class="field"><label>Destino</label><select name="destination_location_id" required><option value="">Selecione</option>${locs.map(l=>`<option value="${esc(l.id)}">${esc(l.address_code||l.name)}</option>`).join('')}</select></div><div class="field" style="grid-column:1/-1"><label>Motivo</label><textarea name="notes"></textarea></div></form>`;
  }
  async function saveTransfer(){const f=new FormData(document.getElementById('fpTransferForm'));try{await req('/api/v1/inventory/transfer',{method:'POST',body:JSON.stringify({product_id:String(f.get('product_id')),quantity:Number(f.get('quantity')||0),source_location_id:String(f.get('source_location_id')),destination_location_id:String(f.get('destination_location_id')),notes:String(f.get('notes')||'')})});closeModal?.();toast('Transferência concluída em uma única transação');await Promise.allSettled([hydrateEngineering?.(),window.fpRefreshDashboardReal?.()]);return true;}catch(e){toast(e.message);return false;}}

  function installModals(){
    const originalOpen=window.openModal,originalSave=window.saveModal;
    window.openModal=function(title,type='generic'){
      if(type==='purchase'){modalKindV14='purchase';document.getElementById('modalTitle').textContent=title;document.getElementById('modalBody').innerHTML=purchaseForm();document.getElementById('modalOverlay').classList.add('show');markDirty?.();return;}
      if(type==='finance'){modalKindV14='finance-v14';document.getElementById('modalTitle').textContent=title;document.getElementById('modalBody').innerHTML=financeForm();document.getElementById('modalOverlay').classList.add('show');markDirty?.();return;}
      modalKindV14='';
      return originalOpen(title,type);
    };
    window.saveModal=function(){if(modalKindV14==='purchase')return savePurchase();if(modalKindV14==='finance-v14')return saveFinance();if(modalKindV14==='transfer-v14')return saveTransfer();return originalSave();};
    window.openTransferModal=function(){modalKindV14='transfer-v14';document.getElementById('modalTitle').textContent='Transferência de estoque';document.getElementById('modalBody').innerHTML=transferForm();document.getElementById('modalOverlay').classList.add('show');markDirty?.();};
  }

  function marketplaceSafeMode(){
    try{Object.keys(marketplaceData||{}).forEach(k=>{if(Array.isArray(marketplaceData[k]))marketplaceData[k].length=0;});}catch(_){}
    const page=document.getElementById('marketplace');if(page){
      page.querySelectorAll('.kpi strong').forEach(x=>x.textContent='0');
      const p=page.querySelector('.page-head p');if(p)p.textContent='Módulo em implantação. Nenhuma operação de marketplace é executada nesta versão de homologação.';
      page.querySelectorAll('button').forEach(b=>{if(!/voltar|tema/i.test(b.textContent||'')){b.disabled=true;b.title='Disponível após integração real do marketplace';}});
    }
  }


  let accessProfilesV14=[];
  async function hydrateAccessControl(){
    try{
      const [profiles,users]=await Promise.all([req('/api/v1/access-control/profiles'),req('/api/v1/access-control/users')]);
      accessProfilesV14=profiles||[];
      enterpriseData.accessUsers=(users||[]).map(u=>{
        const profile=accessProfilesV14.find(p=>String(p.id)===String(u.profile_id));
        return{id:u.id,_serverId:u.id,employeeId:'',employee:u.full_name||u.email,username:u.email,profile:u.role==='administrator'?'Administrador':(profile?.name||'Usuário'),days:[1,2,3,4,5],start:'00:00',end:'23:59',lastAccess:'Servidor',status:u.active?'Ativo':'Bloqueado',autoBlock:false};
      });
      renderEnterpriseAccessUsers?.();
      renderAccessSimulator?.();
      return true;
    }catch(e){console.warn('Acessos:',e);return false;}
  }

  function installAccessControl(){
    const previous=window.saveEnterpriseForm;
    window.saveEnterpriseForm=function(){
      if(enterpriseFormState?.type!=='accessUsers')return previous();
      const form=document.getElementById('enterpriseForm');if(!form)return false;
      if(!validateEnterpriseForm(form))return false;
      const f=new FormData(form),email=String(f.get('username')||'').trim().toLowerCase(),password=String(f.get('password')||''),profileName=String(f.get('profile')||'Vendedor'),active=String(f.get('status')||'Ativo')==='Ativo';
      if(!email.includes('@')){toast('Para acesso real, informe um e-mail válido.');return false;}
      const profile=accessProfilesV14.find(p=>p.name===profileName);
      const employeeValue=String(f.get('employeeId')||'');
      const fullName=employeeValue.split(' | ').slice(1).join(' | ')||email;
      const existing=enterpriseFormState.id?enterpriseData.accessUsers.find(x=>x.id===enterpriseFormState.id):null;
      (async()=>{
        try{
          if(existing?._serverId){
            await req(`/api/v1/access-control/users/${existing._serverId}`,{method:'PUT',body:JSON.stringify({full_name:fullName,role:profileName==='Administrador'?'administrator':'user',active,profile_id:profile?.id||null})});
            if(password)await req(`/api/v1/access-control/users/${existing._serverId}/password`,{method:'POST',body:JSON.stringify({password})});
          }else{
            if(password.length<8)throw new Error('A senha inicial precisa ter pelo menos 8 caracteres.');
            await req('/api/v1/access-control/users',{method:'POST',body:JSON.stringify({email,full_name:fullName,password,role:profileName==='Administrador'?'administrator':'user',profile_id:profile?.id||null,active})});
          }
          enterpriseFormState=null;closeModal?.();toast('Usuário salvo no backend');await hydrateAccessControl();
        }catch(e){toast(e.message);}
      })();
      return true;
    };
    window.simulateCustomAccess=function(){toast('Simulação de horário desativada. O acesso real é validado pelo FastAPI e pelas permissões do perfil.');};
  }

  function installProductionAuthGuard(){
    window.fpEnableProductionAuth=()=>{localStorage.setItem('fp_auth_mode','required');toast('Autenticação obrigatória ativada neste navegador. Saia e entre novamente.');};
    window.fpDisableProductionAuth=()=>{if(window.FP_AUTH_REQUIRED){toast('A autenticação é obrigatória neste ambiente.');return false;}localStorage.removeItem('fp_auth_mode');toast('Modo de homologação local ativado.');};
  }

  async function fullHydrate(){await Promise.allSettled([hydratePurchasing(),hydrateFinance(),hydrateAccessControl(),window.fpRefreshDashboardReal?.(),hydrateEnterprise?.(),hydrateEngineering?.()]);}

  function boot(){installModals();installAccessControl();window.renderMarketplace=marketplaceSafeMode;window.renderMarketplacePro=marketplaceSafeMode;marketplaceSafeMode();installProductionAuthGuard();setTimeout(fullHydrate,1400);setInterval(()=>Promise.allSettled([hydratePurchasing(),hydrateFinance()]),90000);window.fpHydratePurchasing=hydratePurchasing;window.fpHydrateFinance=hydrateFinance;window.fpHydrateAccessControl=hydrateAccessControl;window.fpFrontVersion=V;}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
