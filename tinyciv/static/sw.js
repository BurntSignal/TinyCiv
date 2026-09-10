const CACHE_NAME = "tinyciv-v0.5.8";
const STATIC_ASSETS = [
  "./",
  "app.css",
  "app.js",
  "manifest.json",
  "icon-192.png",
  "icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.includes("/api/")) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = { notification: { title: "TinyCiv", body: "A new Chronicle event was recorded." } };
  }

  const notification = payload.notification || payload;
  const title = notification.title || "TinyCiv";
  const options = {
    body: notification.body || "A new Chronicle event was recorded.",
    icon: "icon-192.png",
    badge: "icon-192.png",
    tag: `tinyciv-${Date.now()}`,
    renotify: false,
    data: {
      url: notification.navigate || "./",
    },
  };

  const tasks = [self.registration.showNotification(title, options)];
  if (self.navigator?.setAppBadge) {
    const badgeCount = Number(notification.app_badge || 1);
    tasks.push(self.navigator.setAppBadge(Number.isFinite(badgeCount) ? badgeCount : 1));
  }
  event.waitUntil(Promise.all(tasks));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "./", self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      for (const client of windows) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return clients.openWindow ? clients.openWindow(target) : undefined;
    })
  );
});
