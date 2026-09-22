(() => {
  'use strict';

  const VERSION = '18.2.0';
  const DEFAULTS = [
    {name:'Estoque Principal',warehouse:'Principal',aisle:'',rack:'',shelf:'',address_code:'EST-PRINCIPAL',description:'Local padrão para produtos acabados e saldo geral.',active:true},
    {name:'Matéria-prima',warehouse:'Principal',aisle:'',rack:'',shelf:'',address_code:'MAT-PRIMA',description:'Local padrão para matérias-primas e insumos.',active:true},
    {name:'Expedição',warehouse:'Principal',aisle:'',rack:'',shelf:'',address_code:'EXPEDICAO',description:'Produtos separados e aguardando saída/entrega.',active:true},
    {name:'Quarentena / Avarias',warehouse:'Principal',aisle:'',rack:'',shelf:'',address_code:'QUARENTENA',description:'Itens bloqueados, avariados ou aguardando conferência.',active:true}
  ];

  let cachedLocations = [];
  let loadingPromise = null;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const valid = row => row && row.active !== false && String(row.id || '').trim() && (String(row.name || '').trim() || String(row.address_code || '').trim());

  async function request(url, options={}) {
    const response = await fetch(url, {
      cache: 'no-store',
      credentials: 'same-origin',
      ...options,
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
        ...(options.body ? {'Content-Type':'application/json'} : {}),
        ...(options.headers || {})
      }
    });
    if (!response.ok) {
      const text = await response.text().catch(()=>'');
      throw new Error(`HTTP ${response.status}${text ? ` - ${text.slice(0,180)}` : ''}`);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async function fetchLocations({ensureDefaults=true}={}) {
    if (loadingPromise) return loadingPromise;
    loadingPromise = (async () => {
      let rows = await request('/api/v1/stock-locations');
      rows = Array.isArray(rows) ? rows.filter(valid) : [];

      if (ensureDefaults) {
        const codes = new Set(rows.map(x => String(x.address_code || '').trim().toUpperCase()));
        for (const item of DEFAULTS) {
          const code = item.address_code.toUpperCase();
          if (codes.has(code)) continue;
          try {
            const created = await request('/api/v1/stock-locations', {method:'POST', body:JSON.stringify(item)});
            if (created && valid(created)) rows.push(created);
            codes.add(code);
          } catch (error) {
            console.warn('[v18.2.0] Falha ao criar local padrão', code, error);
          }
        }
        rows = await request('/api/v1/stock-locations');
        rows = Array.isArray(rows) ? rows.filter(valid) : [];
      }

      cachedLocations = rows;
      try {
        if (typeof engineeringData !== 'undefined') {
          engineeringData.locations = rows;
          engineeringData.summary = {...(engineeringData.summary || {}), locations: rows.length};
        }
      } catch (_) {}
      return rows;
    })().finally(() => { loadingPromise = null; });
    return loadingPromise;
  }

  function labelFor(loc) {
    const main = [loc.name, loc.address_code].filter(Boolean).join(' · ');
    const detail = [loc.warehouse, loc.aisle ? `Corredor ${loc.aisle}` : '', loc.rack ? `Rack ${loc.rack}` : '', loc.shelf ? `Prat. ${loc.shelf}` : ''].filter(Boolean).join(' / ');
    return detail ? `${main} — ${detail}` : main;
  }

  function setSelectState(select, rows, preferredValue='') {
    if (!select) return;
    const current = preferredValue || select.value || select.dataset.preferredValue || '';
    if (!rows.length) {
      select.innerHTML = '<option value="">Nenhum local disponível</option>';
      select.value = '';
      select.classList.add('validation-error');
      select.title = 'Nenhum local de estoque foi retornado pelo backend.';
      return;
    }
    select.innerHTML = rows.map(loc => `<option value="${esc(loc.id)}">${esc(labelFor(loc) || loc.id)}</option>`).join('');
    select.value = rows.some(x => String(x.id) === String(current)) ? current : String(rows[0].id);
    select.classList.remove('validation-error');
    select.title = '';
  }

  function ensureHelper(select) {
    const field = select?.closest('.field');
    if (!field) return;
    let help = field.querySelector('.fp-stock-location-runtime-help');
    if (!help) {
      help = document.createElement('small');
      help.className = 'form-help fp-stock-location-runtime-help';
      help.style.display = 'block';
      help.style.marginTop = '6px';
      field.appendChild(help);
    }
    help.innerHTML = `Locais carregados do banco · <strong>v${VERSION}</strong> · <button type="button" class="fp-stock-location-refresh" style="border:0;background:transparent;color:var(--primary);font-weight:800;cursor:pointer;padding:0">recarregar</button>`;
    const btn = help.querySelector('.fp-stock-location-refresh');
    if (btn) btn.onclick = async () => {
      btn.disabled = true;
      btn.textContent = 'carregando...';
      try {
        const rows = await fetchLocations({ensureDefaults:true});
        setSelectState(select, rows, select.value);
        window.toast?.(`${rows.length} locais de estoque carregados`);
      } catch (error) {
        console.error('[v18.2.0] Recarregar locais:', error);
        select.innerHTML = '<option value="">Erro ao carregar locais</option>';
        window.toast?.('Erro ao carregar locais de estoque');
      } finally {
        btn.disabled = false;
        btn.textContent = 'recarregar';
      }
    };
  }

  async function populateProductLocationSelect() {
    const select = document.querySelector('#enterpriseForm select[name="locationId"]');
    if (!select || select.dataset.fpLocationLoading === '1') return false;
    select.dataset.fpLocationLoading = '1';
    select.dataset.preferredValue = select.value || '';
    select.innerHTML = '<option value="">Carregando locais...</option>';
    select.disabled = true;
    ensureHelper(select);
    try {
      const rows = await fetchLocations({ensureDefaults:true});
      setSelectState(select, rows, select.dataset.preferredValue);
      return true;
    } catch (error) {
      console.error('[v18.2.0] Falha ao popular Local de estoque:', error);
      select.innerHTML = '<option value="">Erro ao carregar — clique em recarregar</option>';
      select.value = '';
      select.classList.add('validation-error');
      select.title = String(error.message || error);
      return false;
    } finally {
      select.disabled = false;
      select.dataset.fpLocationLoading = '0';
      ensureHelper(select);
    }
  }

  async function prefetch() {
    try { await fetchLocations({ensureDefaults:true}); }
    catch (error) { console.warn('[v18.2.0] Prefetch de locais falhou:', error); }
  }

  const originalOpenEnterpriseForm = window.openEnterpriseForm;
  if (typeof originalOpenEnterpriseForm === 'function') {
    window.openEnterpriseForm = async function(type, id=null) {
      if (type === 'products') {
        try { await fetchLocations({ensureDefaults:true}); }
        catch (error) { console.warn('[v18.2.0] Pré-carga antes do modal falhou:', error); }
      }
      const result = await originalOpenEnterpriseForm.apply(this, arguments);
      if (type === 'products') setTimeout(populateProductLocationSelect, 0);
      return result;
    };
  }

  const observer = new MutationObserver(() => {
    const select = document.querySelector('#enterpriseForm select[name="locationId"]');
    if (select && select.dataset.fpLocationObserved !== '1') {
      select.dataset.fpLocationObserved = '1';
      setTimeout(populateProductLocationSelect, 0);
    }
  });

  function start() {
    observer.observe(document.documentElement, {childList:true, subtree:true});
    prefetch();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();

  window.fpReloadStockLocations = async () => {
    cachedLocations = [];
    const rows = await fetchLocations({ensureDefaults:true});
    await populateProductLocationSelect();
    return rows;
  };
})();
