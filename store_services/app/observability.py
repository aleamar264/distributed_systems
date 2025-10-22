from prometheus_client import CollectorRegistry, Counter, Gauge

REGISTRY = CollectorRegistry()

sync_attempts_total = Counter(
    "store_sync_attempts_total",
    "Total sync attempts made to central",
    registry=REGISTRY,
)
sync_success_total = Counter(
    "store_sync_success_total",
    "Total successful syncs",
    registry=REGISTRY,
)
sync_conflicts_total = Counter(
    "store_sync_conflicts_total",
    "Total syncs that hit conflicts",
    registry=REGISTRY,
)
sync_failures_total = Counter(
    "store_sync_failures_total",
    "Total syncs that failed",
    registry=REGISTRY,
)

inventory_count = Gauge(
    "store_inventory_count", "Local inventory count", registry=REGISTRY
)
pending_changes_gauge = Gauge(
    "store_pending_changes", "Number of pending changes queued for sync", registry=REGISTRY
)

# Local operations
local_updates_total = Counter(
    "store_local_updates_total", "Total local inventory updates applied", registry=REGISTRY
)
 
# Timing
sync_duration_seconds = Gauge(
    "store_sync_duration_seconds",
    "Duration in seconds of sync attempts (latest)",
    registry=REGISTRY,
)

# Push request timing
push_response_seconds = Gauge(
    "store_push_response_seconds",
    "Time in seconds for push requests to central (latest)",
    registry=REGISTRY,
)
