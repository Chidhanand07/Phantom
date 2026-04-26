from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.portfolio.models import TradeMemory

router = APIRouter(prefix="/memories", tags=["memory"])


@router.get("")
def get_memories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(TradeMemory).order_by(TradeMemory.timestamp.desc())
    ).scalars().all()
    return [
        {
            "id": str(m.id),
            "stock": m.stock,
            "action": m.action,
            "price": float(m.price),
            "quantity": m.quantity,
            "timestamp": m.timestamp.isoformat(),
            "thesis": m.thesis,
            "signals_at_entry": m.signals_at_entry,
            "target_price": float(m.target_price) if m.target_price else None,
            "stop_loss": float(m.stop_loss) if m.stop_loss else None,
            "thesis_status": m.thesis_status,
        }
        for m in rows
    ]
