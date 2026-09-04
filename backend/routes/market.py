from fastapi import APIRouter, HTTPException, Depends
from models import StockDetailResponse, MarketStatusResponse, SearchResult
from routes.watchlist import get_watchlist_service, get_market_service
from services.watchlist import WatchlistService
from services.market import MarketService

router = APIRouter()

@router.get("/stock/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(symbol: str, service: WatchlistService = Depends(get_watchlist_service)):
    detail = await service.get_stock_detail(symbol.upper())
    if not detail:
        raise HTTPException(status_code=404, detail="Symbol not found or data unavailable")
    return detail

@router.get("/market/status", response_model=MarketStatusResponse)
async def get_market_status(market: MarketService = Depends(get_market_service)):
    benchmark, meta = await market.get_benchmark()
    
    nifty_price = benchmark.price if benchmark else None
    nifty_change_pct = None
    if benchmark and benchmark.previous_close and benchmark.price:
        nifty_change_pct = round((benchmark.price - benchmark.previous_close) / benchmark.previous_close * 100, 2)
        
    return MarketStatusResponse(
        nifty_price=nifty_price,
        nifty_change_pct=nifty_change_pct,
        market_status=meta.market_status,
        timestamp=meta.timestamp,
        source=meta.source,
        freshness=meta.freshness
    )

@router.get("/search", response_model=list[SearchResult])
async def search_stocks(q: str, market: MarketService = Depends(get_market_service)):
    if not q:
        return []
    results = await market.search(q)
    return [SearchResult(**r) for r in results]
