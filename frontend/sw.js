const CACHE="facil-pedido-front-v18-2-1-sync-session-fix";
const APP=["./","./index.html","./config.js","./api-bridge.js","./preproduction.css","./preproduction.js","./stabilization-v13.js","./stabilization-v14.js","./stabilization-v15.js","./manifest.webmanifest","./icon-192.png","./icon-512.png"];
self.addEventListener("install",event=>{self.skipWaiting();event.waitUntil(caches.open(CACHE).then(c=>c.addAll(APP)).catch(()=>{}))});
self.addEventListener("activate",event=>event.waitUntil(Promise.all([self.clients.claim(),caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))])));
self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);
  if(url.pathname.startsWith("/api/")||event.request.method!=="GET")return;
  if(url.origin!==self.location.origin)return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response&&response.ok){const copy=response.clone();caches.open(CACHE).then(c=>c.put(event.request,copy)).catch(()=>{})}
    return response;
  }).catch(()=>caches.match(event.request).then(cached=>cached||caches.match("./index.html"))));
});
