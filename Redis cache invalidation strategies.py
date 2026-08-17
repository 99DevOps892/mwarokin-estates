**Redis Cache Invalidation Strategies**  
(for the Mwarokin Stays backend and general production use)

Below is a practical exploration of the main strategies, ranked from simplest to most sophisticated, with concrete recommendations for your property-listing + booking system.

### 1. TTL-Only (Time-Based Expiration)

**How it works**  
Every key is set with an expiry (`SETEX` / `SET ... EX`). After the TTL the key simply disappears. No explicit delete is needed.

**In your current code**
```python
cache.set(data, CACHE_TTL_SHORT, "properties", cache_key)   # 60 s
cache.set(data, CACHE_TTL_MEDIUM, "property", property_id)  # 5 min
```

**Pros**  
- Extremely simple  
- Automatically cleans stale data  
- Zero coordination between writers and readers  

**Cons**  
- Stale data window (up to the full TTL)  
- Cache stampedes possible when many keys expire at the same moment  
- Hard to guarantee “fresh after a booking”  

**When to use**  
Low-write, high-read data where slight staleness is acceptable (locations, amenities, metrics).

---

### 2. Explicit Invalidation on Write (Cache-Aside + Delete)

**How it works**  
On every mutation you actively delete the affected keys (or key patterns).

**In your current code**
```python
def invalidate_property(self, property_id: int):
    self.delete("property", property_id)
    self.delete_pattern("properties")   # all filtered lists
    self.delete("metrics")
```

**Pros**  
- Immediate consistency after writes  
- Easy to reason about  
- Works well with the cache-aside pattern you already use  

**Cons**  
- Must remember every key that depends on the changed entity  
- Pattern deletes (`SCAN` + `DEL`) can be expensive at scale  
- Race conditions possible (read happens between write and delete)  

**Best practice enhancement**
```python
# Prefer exact keys over broad patterns when possible
cache.delete("property", property_id)
cache.delete("properties", "rating")          # known popular sorts
cache.delete("properties", "price-low")
# Only fall back to pattern for the long tail
cache.delete_pattern("properties")
```

---

### 3. Versioned / Namespace Keys (Lazy Invalidation)

**How it works**  
Instead of deleting keys you bump a version counter. All readers include the current version in the key.

```python
# On write
version = cache.client.incr("mwarokin:properties:version")

# On read
version = cache.get("properties:version") or 0
key = f"properties:v{version}:{hash_of_filters}"
```

**Pros**  
- Instant “invalidation” of the entire set without scanning  
- No race between delete and concurrent reads  
- Old keys just expire via TTL  

**Cons**  
- Slightly more complex key construction  
- Old version keys linger until TTL  

**Excellent for**  
Your heavily filtered `/properties` endpoint.

---

### 4. Tag-Based Invalidation

**How it works**  
Each cache entry is associated with one or more tags. When data changes you invalidate by tag.

```python
# When caching a property list that includes Westlands + Pool
cache.set(..., tags=["location:Westlands", "amenity:Pool", "property:3"])

# On update of property 3
cache.invalidate_tags(["property:3"])
```

Redis itself does not have native tags, so you maintain reverse indexes:

```
tag:property:3 → set of cache keys
tag:location:Westlands → set of cache keys
```

**Pros**  
- Precise, multi-dimensional invalidation  
- Scales better than pure pattern matching  

**Cons**  
- Extra write overhead (maintaining the reverse sets)  
- More code complexity  

**Good fit** when a single property appears in many different filter combinations.

---

### 5. Event-Driven / Pub-Sub Invalidation

**How it works**  
Writers publish an event; every application instance (or a dedicated cache worker) listens and invalidates locally or in Redis.

```python
# After booking confirmation
redis.publish("cache:invalidate", json.dumps({
    "type": "property",
    "id": property_id
}))
```

**Pros**  
- Works across multiple API instances  
- Decouples business logic from cache logic  
- Can be extended to other services (search index, analytics, etc.)  

**Cons**  
- Requires a reliable pub/sub or message bus  
- At-least-once delivery semantics must be handled  

**Recommended** once you move beyond a single FastAPI process.

---

### 6. Write-Through / Write-Behind

| Strategy       | Behaviour                                      | Use case                          |
|----------------|------------------------------------------------|-----------------------------------|
| Write-through  | Update DB **and** cache in the same request    | Strong consistency, hot keys      |
| Write-behind   | Update cache first, async flush to DB          | Extremely high write throughput   |
| Write-around   | Update DB only; next read will repopulate cache| Rarely changing data              |

For Mwarokin Stays the pure **cache-aside + explicit invalidation** (what you have) is usually the best default. Write-through becomes attractive only for a few very hot keys (e.g. a single featured property).

---

### 7. Soft Invalidation + Background Refresh

Mark a key as “stale” instead of deleting it, then refresh it asynchronously:

```python
cache.set(data, ttl=..., soft_expire_at=now+30)
# Reader sees soft-expired key → returns stale data + triggers background refresh
```

Protects against cache stampedes and keeps latency low.

---

### Recommended Strategy Mix for Mwarokin Stays

| Data                         | Primary Strategy              | Secondary / Safety Net      | TTL   |
|------------------------------|-------------------------------|-----------------------------|-------|
| Individual property          | Explicit delete on update     | Versioned key               | 5 min |
| Filtered property lists      | Versioned keys + pattern delete | Tag-based (location/amenity) | 60 s |
| Locations / Amenities        | Explicit delete on property change | Long TTL                  | 15 min |
| Metrics                      | Explicit delete on booking    | Short TTL                   | 2 min |
| Favorites (per session)      | Usually no cache or very short TTL | —                        | —     |

### Concrete Upgrade Path (minimal code change)

1. **Add a global properties version**
```python
def get_properties_version(self) -> int:
    return int(self.get("properties:version") or 0)

def bump_properties_version(self):
    if self.available:
        self._client.incr(self._key("properties:version"))
```

2. **Include version in every list cache key**
```python
version = cache.get_properties_version()
cache_key = f"v{version}:{make_cache_key(...)}"
```

3. **On any property mutation or booking confirmation**
```python
cache.bump_properties_version()
cache.invalidate_property(property_id)   # still delete the single-item key
cache.invalidate_metrics()
```

This gives you near-instant list invalidation without expensive `SCAN` on every write, while keeping the rest of your existing code intact.

### Anti-Patterns to Avoid

- Deleting with `KEYS *` (blocks Redis) → always use `SCAN`
- Caching user-specific data with long TTLs without proper isolation
- Forgetting to invalidate on **all** write paths (admin update, booking confirm, occupancy changes, etc.)
- Setting the same TTL for every key type

Would you like me to produce the next version of the backend that implements **versioned keys + tag-based invalidation** (or any other combination) on top of the current code?