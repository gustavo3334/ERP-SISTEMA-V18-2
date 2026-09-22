(() => {
  const MARKET_ROUTES = new Set([
    'marketplace','sellerDetalhe','marketplacePedidoDetalhe','sellerPortal','lojaMarketplace',
    'marketplaceProdutoDetalhe','compradorConta','sellerOnboarding','pimProdutoDetalhe',
    'marketplaceChat','multicanalErros','logisticaMarketplace'
  ]);

  function currentRoute(){
    return (location.hash.replace(/^#\/?/,'').split('?')[0].split('/')[0] || 'dashboard').trim();
  }

  function redirectLegacyMarketplace(){
    if(MARKET_ROUTES.has(currentRoute())){
      history.replaceState(null,'',location.pathname + location.search + '#/dashboard');
      try{ window.go?.('dashboard'); }catch(_){ }
    }
  }

  function removeResidualUI(){
    document.querySelectorAll('[data-page="marketplace"], #marketplace, #marketCart').forEach(el=>el.remove());
    document.querySelectorAll('option').forEach(opt=>{ if(opt.textContent.trim()==='Seller') opt.remove(); });
    document.querySelectorAll('button').forEach(btn=>{
      if(btn.textContent.trim()==='Seller' && /demoLogin/.test(btn.getAttribute('onclick')||'')) btn.remove();
    });
  }

  // Mantém compatibilidade com código legado sem voltar a exibir ou operar Marketplace.
  window.renderMarketplace = () => {};
  window.renderMarketplacePro = () => {};
  window.renderMarketCart = () => {};
  window.toggleMarketCart = () => {};
  window.openMarketplaceCheckout = () => false;
  window.openMarketplaceForm = () => { window.toast?.('O módulo Marketplace foi removido deste ERP.'); return false; };

  function boot(){
    removeResidualUI();
    redirectLegacyMarketplace();
    window.addEventListener('hashchange', redirectLegacyMarketplace);
    window.fpFrontVersion = '15.0.0-sem-marketplace';
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();
