from fastapi import APIRouter, HTTPException, Depends
from models import ReviewRequest
from routes.watchlist import get_watchlist_service
from services.watchlist import WatchlistService

router = APIRouter()

@router.post("/review")
async def review_stocks(req: ReviewRequest, service: WatchlistService = Depends(get_watchlist_service)):
    try:
        count = await service.review_stocks([s.upper() for s in req.symbols])
        return {"reviewed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
