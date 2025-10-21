from common.schemas import (
	GenericResponse,
	TxnAbortRequest,
	TxnCommitRequest,
	TxnCommitResponse,
	TxnPrepareResponse,
	TxnPrepareRquest,
)
from fastapi import APIRouter, Header

router = APIRouter(prefix="/central", tags=["central"])

@router.post("/txn/prepare", response_model=TxnPrepareResponse)
async def prepare_transaction(
	payload: TxnPrepareRquest,
	idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
	"""
	Central validates availability for proposed lines across global view.
	- Acquire short-lived locks on affected SKUs (in-memory or DB-level).
	- Check global available quantity >= sum(reservations).
	- If ok: record txn as PREPARED (durable), return prepared.
	- Otherwise: return abort with reason.
	"""
	raise NotImplementedError


@router.post("/txn/commit", response_model=TxnCommitResponse)
async def txn_commit(
	payload: TxnCommitRequest,
	idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
	"""
	Commit the transaction in the central DB. Mark txn committed and update global inventory.
	On success, instruct store to commit local via store's /txn/commit-local.
	"""
	raise NotImplementedError


@router.post("/txn/abort", response_model=GenericResponse)
async def txn_abort(
	payload: TxnAbortRequest,
	idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
	"""
	Mark transaction aborted in central and instruct any prepared stores to rollback.
	"""
	raise NotImplementedError


@router.get("/inventory/{sku}")
async def get_global_inventory(sku: str):
	"""
	Return authoritative global inventory for SKU.
	"""
	raise NotImplementedError


@router.post("/sync/reconcile", response_model=GenericResponse)
async def reconcile_trigger():
	"""
	Trigger reconciliation job (compare store snapshots vs central).
	"""
	raise NotImplementedError
