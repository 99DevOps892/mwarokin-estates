**IndexedDB Investigation for Larger Storage**  
*(Context: Mwarokin Estates offline-first PWA + the Python `offline.py` engine)*

### 1. Current Storage Quotas (2025–2026)

| Browser              | Typical Limit per Origin                          | Notes |
|----------------------|---------------------------------------------------|-------|
| **Chrome / Edge / Chromium** | Up to **60% of total disk** (often hundreds of GB) | Shared pool. Can reach 100+ GB on modern devices. |
| **Firefox**          | Up to **50% of free disk**, hard group limit ~2 GB | Older versions prompted at 50 MB. |
| **Safari (Desktop)** | ~1 GB (prompts user to increase in 200 MB steps) | More restrictive. |
| **Safari (iOS)**     | ~50 MB – 1 GB (highly variable)                   | Data can be purged after 7 days of non-use if not installed as PWA. |
| **Private / Incognito** | Severely reduced (~5% or less)                 | Almost never reliable for offline data. |

**Key takeaway**: IndexedDB is **designed for large datasets**. Unlike `localStorage` (hard ~5 MB), it can realistically hold **hundreds of megabytes to multiple gigabytes** on desktop Chrome/Firefox.

### 2. How Much Can You Actually Store?

- There is **no fixed hard limit** in the spec.
- The real limit is the **origin quota** managed by the browser’s Storage Manager.
- You can (and should) query it at runtime:

```js
const { usage, quota } = await navigator.storage.estimate();
console.log(`Using ${(usage/1024/1024).toFixed(1)} MB of ${(quota/1024/1024/1024).toFixed(1)} GB`);
```

- Chrome may report quotas of **300+ GB** on a large drive.
- Practical recommendation for a real-estate app (units, payments, maintenance, documents, images):
  - Aim to stay under **500 MB – 2 GB** for excellent cross-browser reliability.
  - Beyond that, use progressive loading + server-side pagination.

### 3. Persistence vs Eviction

By default storage is **“best-effort”** (browser can delete it when disk is low).

Request **persistent storage** (highly recommended for offline-first):

```js
if (navigator.storage && navigator.storage.persist) {
  const granted = await navigator.storage.persist();
  console.log(granted ? "Persistent storage granted" : "User denied or not available");
}
```

- Once granted, the browser only clears the data if the **user** explicitly deletes site data.
- Installed PWAs (Add to Home Screen) are much more likely to receive persistent storage automatically.

### 4. IndexedDB vs Alternatives for Large Data

| Technology              | Best For                          | Capacity          | Query Power      | DX / Speed                  | Recommendation for Mwarokin |
|-------------------------|-----------------------------------|-------------------|------------------|-----------------------------|-----------------------------|
| **IndexedDB**           | Structured domain data + offline queue | Very high (GBs)  | Indexes + cursors | Verbose (use Dexie/idb)    | **Primary choice** for browser |
| **OPFS + SQLite WASM**  | Complex relational queries, large analytics | Very high        | Full SQL         | Excellent (wa-sqlite)      | Best long-term upgrade     |
| **Cache API**           | Static assets / HTTP responses    | High             | URL matching only| Simple                      | Use for images/documents   |
| **localStorage**        | Tiny preferences only             | ~5 MB            | None             | Synchronous (blocks UI)    | Avoid                      |

**Current best practice (2026)**:
- Start with **IndexedDB** (via Dexie.js or idb) for the action queue, entities, and activity log.
- For heavy analytics / complex reporting later → move to **SQLite compiled to WASM + Origin Private File System (OPFS)**.

### 5. Best Practices for Large Storage in Mwarokin Estates

1. **Always request persistent storage** early in the app lifecycle.
2. Monitor quota and warn the user before large imports:
   ```js
   const { usage, quota } = await navigator.storage.estimate();
   if (usage / quota > 0.8) showStorageWarning();
   ```
3. Store binary data (receipts, photos, PDFs) as **Blobs** — IndexedDB handles them efficiently.
4. Use **indexes** only on fields you actually query (status, unit_id, created_at, role…).
5. Keep the offline action queue in its own object store so it can be cleared independently after successful sync.
6. Combine with **Service Worker + Background Sync** so the Python `offline.py` engine (or a JS mirror) can flush the queue when connectivity returns.
7. For very large datasets, implement **lazy loading / pagination** and never load the entire estate history into memory at once.

### 6. Relationship to the Python `offline.py` Engine

- The Python engine uses **SQLite + WAL** on the server / desktop / Electron side — excellent for large data and concurrent access.
- On the pure browser / PWA side you mirror the same concepts with **IndexedDB**:
  - Same action queue structure
  - Same agentic decision rules (can be ported to JS)
  - Same optimistic local writes + background sync

A clean architecture is:

```
PWA (IndexedDB)  ←→  Service Worker  ←→  FastAPI / offline bridge  ←→  offline.py (SQLite WAL)
```

### Summary Recommendation

**Yes — IndexedDB is the right choice for larger offline storage** in the Mwarokin Estates PWA.

- It supports far more data than localStorage.
- With `navigator.storage.persist()` + proper quota monitoring it is reliable for multi-hundred-MB datasets.
- For the absolute highest performance and full SQL later, plan a migration path to **OPFS-backed SQLite WASM**.

Would you like me to also generate a production-ready **Dexie.js / IndexedDB schema + sync layer** that mirrors the Python `offline.py` action queue and agentic rules?