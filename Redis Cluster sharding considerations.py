**Redis Cluster Sharding Considerations**  
(for the Mwarokin Stays caching layer)

Redis Cluster partitions data across multiple nodes using **16384 hash slots**. Every key is assigned to a slot via:

```text
slot = CRC16(key) mod 16384
```

Understanding how this interacts with your cache design is critical once you move beyond a single Redis instance.

### 1. Key Design Rules in a Cluster

| Rule | Why it matters | Impact on Mwarokin Stays |
|------|----------------|--------------------------|
| **Prefer single-key operations** | Multi-key commands (`MGET`, `DEL` of many keys, `SCAN` across slots) require all keys to live in the same slot or the command fails / is partially executed | Your current `delete_pattern("properties*")` becomes expensive or unreliable |
| **Use hash tags `{...}`** for related keys | Keys containing `{tag}` are forced into the **same slot** | Essential for version counters + list keys, or for tag-based invalidation |
| **Avoid huge key spaces with wildcards** | `SCAN` + `DEL` across many slots is slow and can block | Prefer versioned keys over broad pattern deletes |
| **Keep values reasonably sized** | Large values increase network and memory pressure on individual shards | Property objects are fine; avoid caching giant result sets |

**Good key examples for Cluster**
```text
mwarokin:property:{42}                  # single property
mwarokin:properties:v{17}:{hash}        # versioned list (hash tag on version)
mwarokin:metrics
mwarokin:locations
mwarokin:tag:property:{42}              # reverse index for tags
```

**Bad patterns**
```text
mwarokin:properties:*                   # forces cross-slot SCAN
mwarokin:property:42 + mwarokin:property:43 in one multi-key command without tags
```

### 2. How Sharding Affects Your Current Invalidation Strategies

#### A. TTL-only
Works perfectly. No multi-key issues.

#### B. Explicit single-key delete
```python
cache.delete("property", property_id)   # still fine
```
Safe and recommended.

#### C. Pattern / wildcard delete (`SCAN` + `DEL`)
```python
cache.delete_pattern("properties")      # becomes costly
```
- Must iterate every node
- Higher latency and CPU
- Risk of partial failure

**Recommendation**: Replace broad patterns with **versioned keys**.

#### D. Versioned keys (highly recommended in Cluster)
```python
# Global version forced into one slot via hash tag
version_key = "mwarokin:properties:version{props}"

# List keys also use the same tag so they can be managed together if needed
list_key = f"mwarokin:properties:v{{{version}}}:{query_hash}"
```
Bumping the version instantly “invalidates” all list caches without touching thousands of keys.

#### E. Tag-based invalidation
Requires reverse indexes. Force related tags into the same slot:

```text
mwarokin:tag:property:{42}
mwarokin:tag:location:{Westlands}
```

Then store the set of cache keys under that tag. All operations on a tag stay single-slot.

### 3. Multi-Key Command Limitations

Commands that operate on multiple keys (**MGET, MSET, DEL of several keys, SDIFF, ZUNION, etc.**) only succeed if **every key maps to the same hash slot**.

Your current code is mostly safe because you almost always operate on one key at a time. Watch out for:

- Future “get multiple properties by IDs”
- Any bulk favorite or metrics aggregation that touches many keys

**Solutions**
1. Use hash tags so related keys share a slot.
2. Issue multiple single-key commands (or use pipelines carefully).
3. Move the aggregation logic to the application layer.

### 4. Client Library Considerations

| Client | Cluster support | Notes |
|--------|-----------------|-------|
| `redis-py` | Yes (`RedisCluster`) | Use `RedisCluster` instead of `Redis` |
| `aioredis` / `redis.asyncio` | Yes | Preferred for FastAPI |
| Connection pooling | Per-node pools | Automatic slot mapping |

Example migration:

```python
from redis.cluster import RedisCluster

self._client = RedisCluster.from_url(
    "redis://redis-node-1:6379",
    decode_responses=True,
    skip_full_coverage_check=True,   # useful in some cloud setups
)
```

### 5. Data Distribution for Mwarokin Stays

| Data type | Cardinality | Recommended approach |
|-----------|-------------|----------------------|
| Individual properties | Low–medium (hundreds) | One key per property. Natural even distribution. |
| Filtered list results | High (many filter combinations) | Versioned keys + short TTL. Avoid storing every possible filter forever. |
| Locations / Amenities | Very low | Single keys – fine. |
| Metrics | Single key | Fine. |
| Session favorites | Medium–high | Key per session or per user. Consider short TTL. |
| Tag reverse indexes | Medium | Use hash tags. |

Because property IDs and query hashes are well distributed, you will rarely see hot shards **unless** you put a very popular global counter or lock on a fixed key without a hash tag.

### 6. Operational Considerations

- **Resharding** – moving slots between nodes is online but increases latency temporarily. Prefer adding capacity before you are under heavy load.
- **Cross-slot transactions / Lua** – not supported. Keep Lua scripts single-key.
- **Memory imbalance** – monitor per-node memory. Large cached lists can create hot nodes.
- **Network hop** – every multi-node operation adds latency. Keep read paths to a single key when possible.
- **Failover** – Cluster handles replica promotion; your client must support `MOVED` / `ASK` redirections (all modern clients do).

### 7. Practical Recommendations for Your Backend

1. **Switch to versioned list keys** (best ROI)
   ```python
   version = cache.client.get("mwarokin:properties:version{props}") or "0"
   cache_key = f"v{version}:{make_cache_key(...)}"
   ```

2. **Use hash tags** for any keys that must stay together (version + related lists, tag indexes).

3. **Replace `delete_pattern`** with version bump + selective single-key deletes.

4. **Keep single-property and metrics keys** as they are — they shard naturally.

5. **When you adopt Redis Cluster**, change only the client initialization; the rest of the `RedisCache` class can stay almost identical if you already avoid multi-key commands.

6. **Monitor**
   - Slot distribution
   - Hot keys
   - `MOVED` redirections rate
   - Per-node memory & CPU

### Summary Table

| Strategy              | Cluster Friendliness | Recommended for Mwarokin? |
|-----------------------|----------------------|---------------------------|
| TTL only              | Excellent            | Yes (secondary safety)    |
| Single-key delete     | Excellent            | Yes                       |
| Versioned keys        | Excellent            | **Strongly yes**          |
| Pattern delete (SCAN) | Poor                 | Avoid / minimize          |
| Tag-based with hash tags | Good              | Yes for advanced needs    |
| Multi-key MGET/DEL    | Risky                | Avoid without hash tags   |
| Pub/Sub invalidation  | Good                 | Yes at multi-instance scale |

Would you like me to produce an updated version of the `RedisCache` class that is **Cluster-ready** (versioned keys + hash tags + safe invalidation)?