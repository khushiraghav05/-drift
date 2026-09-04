from fastapi import APIRouter, HTTPException, Depends
from models import WatchlistResponse, AddStockRequest, AddStockResponse
from services.watchlist import WatchlistService
from services.market import MarketService
from providers.yahoo import YahooFinanceProvider
from providers.demo import DemoProvider
from config import settings

router = APIRouter()

def get_market_service():
    provider = DemoProvider() if settings.MARKET_PROVIDER == "demo" else YahooFinanceProvider()
    return MarketService(provider)

def get_watchlist_service(market_service=Depends(get_market_service)):
    return WatchlistService(market_service)

@router.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(service: WatchlistService = Depends(get_watchlist_service)):
    try:
        items = await service.get_watchlist()
        
        benchmark, meta = await service.market.get_benchmark()
        nifty_price = benchmark.price if benchmark else None
        nifty_change_pct = None
        if benchmark and benchmark.previous_close and benchmark.price:
            nifty_change_pct = round((benchmark.price - benchmark.previous_close) / benchmark.previous_close * 100, 2)
            
        return WatchlistResponse(
            stocks=items,
            market={
                "nifty_price": nifty_price,
                "nifty_change_pct": nifty_change_pct,
                "market_status": meta.market_status.value,
                "timestamp": meta.timestamp
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/watchlist", response_model=AddStockResponse)
async def add_stock(req: AddStockRequest, service: WatchlistService = Depends(get_watchlist_service)):
    try:
        # verify symbol exists
        search_res = await service.market.search(req.symbol)
        display_name = req.symbol
        for res in search_res:
            if res['symbol'].upper() == req.symbol.upper():
                display_name = res['name']
                break
                
        added = await service.add_stock(req.symbol.upper(), display_name)
        return AddStockResponse(symbol=req.symbol.upper(), display_name=display_name, added=added)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/watchlist/{symbol}")
async def remove_stock(symbol: str, service: WatchlistService = Depends(get_watchlist_service)):
    removed = await service.remove_stock(symbol.upper())
    if not removed:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    return {"message": "removed"}
