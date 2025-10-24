"""Script to populate the inventory table with test data."""
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.db import session
from app.models.models import Inventory


async def populate_inventory():
    """Populate inventory with test data."""
    items = [
        Inventory(
            sku="ELEC-LAPTOP-001",
            name="ThinkPad X1 Carbon",
            quantity=50,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-PHONE-002",
            name="iPhone 15 Pro",
            quantity=100,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-TABLET-003",
            name="iPad Air 5",
            quantity=75,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-WATCH-004",
            name="Apple Watch Series 8",
            quantity=150,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-HEAD-005",
            name="Sony WH-1000XM5",
            quantity=200,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-CAM-006",
            name="Canon EOS R6",
            quantity=25,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-GAME-007",
            name="PlayStation 5",
            quantity=30,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-TV-008",
            name="LG OLED C2 65\"",
            quantity=15,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-SPEAK-009",
            name="Sonos Five",
            quantity=45,
            version=1,
            updated_at=datetime.now(UTC)
        ),
        Inventory(
            sku="ELEC-MON-010",
            name="Dell Ultrasharp U2723QE",
            quantity=60,
            version=1,
            updated_at=datetime.now(UTC)
        ),
    ]

    async with session() as db:
        # Check if items already exist
        for item in items:
            existing = await db.execute(
                select(Inventory).where(Inventory.sku == item.sku)
            )
            if not existing.scalar_one_or_none():
                db.add(item)

        await db.commit()

if __name__ == "__main__":
    asyncio.run(populate_inventory())
