#!/usr/bin/env python3
"""
Blockchain Oracle Service - Simple Version
Real-time price data with basic API key authentication
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp

app = FastAPI(
    title="Blockchain Oracle Service",
    description="Simple real-time price oracle for DeFi applications",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Valid API keys (add more as you get customers)
VALID_API_KEYS = {
    "ee68782e71900105ab4eb44256ca50016bfff7568341bf7696af9aceb2322c09": "admin"
}

# Price cache with TTL
price_cache: Dict[str, dict] = {}
cache_ttl = 30

class PriceResponse(BaseModel):
    symbol: str
    price: float
    timestamp: str
    source: str
    accuracy: float

async def fetch_price_from_okx(symbol: str) -> Optional[float]:
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0' and data.get('data'):
                        return float(data['data'][0]['last'])
    except Exception as e:
        print(f"Error fetching {symbol} from OKX: {e}")
    return None

async def get_aggregated_price(symbol: str) -> Optional[PriceResponse]:
    if symbol in price_cache:
        cached = price_cache[symbol]
        if datetime.fromisoformat(cached['timestamp']) > datetime.utcnow() - timedelta(seconds=cache_ttl):
            return PriceResponse(**cached)
    
    price = await fetch_price_from_okx(symbol)
    if not price:
        return None
    
    response = PriceResponse(
        symbol=symbol,
        price=price,
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source='OKX',
        accuracy=0.1
    )
    
    price_cache[symbol] = response.dict()
    return response

@app.get("/api/v1/price/{symbol}")
async def get_price(symbol: str, api_key: str = Query(...)):
    valid_symbols = ['BTC', 'ETH', 'LINK', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE']
    if symbol.upper() not in valid_symbols:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    price_data = await get_aggregated_price(symbol.upper())
    if price_data is None:
        raise HTTPException(status_code=503, detail="Price data unavailable")
    
    return price_data

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + 'Z'}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
