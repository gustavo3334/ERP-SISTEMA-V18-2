window.FP_COMMERCIAL_CONFIG = {
  VERSION: "5.4.4-inicio-e-categorias",
  API_BASE: location.pathname.startsWith("/comercial") ? `${location.origin}/comercial/api/v1` : (localStorage.getItem("fp_commercial_api_base_v5_amarelo") || (location.protocol==="file:"?"http://127.0.0.1:8010/api/v1":`${location.origin}/api/v1`)),
  STATE_KEY: "facil-pedido-commercial-v5-amarelo",
  PAGE_SIZE: 24,
  MAX_PHOTOS_PER_PRODUCT: 12,
  MAX_PHOTO_SIDE: 1400,
  JPEG_QUALITY: 0.82,
  STORAGE: {
    provider: localStorage.getItem("fp_storage_provider") || "erp_api",
    supabaseUrl: localStorage.getItem("fp_supabase_url") || "",
    supabaseAnonKey: localStorage.getItem("fp_supabase_anon") || "",
    bucket: localStorage.getItem("fp_supabase_bucket") || "product-media"
  }
};
