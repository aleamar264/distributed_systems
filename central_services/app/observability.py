from prometheus_client import CollectorRegistry, Counter, Gauge

# Use a local registry to avoid global re-registration on reload
REGISTRY = CollectorRegistry()

# Counters
inventory_updates_total = Counter(
    "central_inventory_updates_total",
    "Total successful inventory updates",
    registry=REGISTRY,
)
inventory_update_conflicts_total = Counter(
    "central_inventory_update_conflicts_total",
    "Total inventory updates that failed due to optimistic lock conflicts",
    registry=REGISTRY,
)
inventory_update_failures_total = Counter(
    "central_inventory_update_failures_total",
    "Total inventory updates that failed due to errors",
    registry=REGISTRY,
)
bulk_sync_total = Counter(
    "central_bulk_sync_total",
    "Total bulk sync batches processed",
    registry=REGISTRY,
)

# Gauges (set at scrape time)
inventory_count_gauge = Gauge(
    "central_inventory_count", "Number of inventory items in central DB", registry=REGISTRY
)
idempotency_keys_gauge = Gauge(
    "central_idempotency_keys", "Number of idempotency keys stored", registry=REGISTRY
)
