const CACHE_NAME = "narnia-v1";

const urlsToCache = [
"/",
"/estoque",
"/compras",
"/static/style.css",
"/static/icon.png"
];

self.addEventListener("install", event => {

event.waitUntil(
caches.open(CACHE_NAME)
.then(cache => cache.addAll(urlsToCache))
);

});

self.addEventListener("fetch", event => {

event.respondWith(

caches.match(event.request)
.then(response => {

return response || fetch(event.request);

})

);

});
