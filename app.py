from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

# Import existing modules (adjust paths if necessary)
from src.collector import get_all_solana_yields
from src.processor import YieldDataProcessor
from src.models import RiskScorer, PortfolioOptimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class OptimizeRequest(BaseModel):
    investment_amount: float
    risk_tolerance: str
    time_horizon: str

class YieldResponse(BaseModel):
    protocol: str
    pool_id: str
    pair: str
    apy: float
    tvl: float
    category: str
    tokens: List[str]
    audit_score: float
    risk_level: str
    last_updated: str

class AnalyticsResponse(BaseModel):
    total_opportunities: int
    total_protocols: int
    total_tvl: float
    average_apy: float
    categories: Dict[str, int]
    top_protocols: Dict[str, float]

# Initialize FastAPI app
app = FastAPI(
    title="Solana Yield Farming API",
    description="API for Solana yield farming opportunities and portfolio optimization",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# In-memory cache
cache = {
    "yields_data": None,
    "last_updated": None,
    "cache_ttl": timedelta(minutes=5)
}

async def get_cached_yields():
    """Get yields data with caching"""
    now = datetime.now()
    
    # Check if cache is valid
    if (cache["yields_data"] is not None and 
        cache["last_updated"] is not None and
        now - cache["last_updated"] < cache["cache_ttl"]):
        logger.info("Returning cached yield data")
        return cache["yields_data"]
    
    # Fetch fresh data
    logger.info("Fetching fresh yield data")
    try:
        opportunities = await get_all_solana_yields()
        cache["yields_data"] = opportunities
        cache["last_updated"] = now
        return opportunities
    except Exception as e:
        logger.error(f"Failed to fetch yield data: {e}")
        if cache["yields_data"]:
            logger.info("Returning stale cache data due to fetch error")
            return cache["yields_data"]
        raise HTTPException(status_code=500, detail="Failed to fetch yield data")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Solana Yield Farming API is running!", "status": "healthy"}

@app.get("/api/yields")
async def get_yields(
    min_apy: float = Query(0.0, ge=0.0, description="Minimum APY (as decimal, e.g., 0.05 for 5%)"),
    max_apy: float = Query(10000.0, description="Maximum APY"),
    categories: Optional[str] = Query(None, description="Comma-separated categories to filter")
):
    """Get filtered Solana yield opportunities"""
    try:
        opportunities = await get_cached_yields()
        
        # Apply filters and transform to frontend format
        filtered = [
            {
                "id": o.pool_id,  # Match frontend's id
                "protocol": o.protocol,
                "pool": o.pair,   # Match frontend's pool
                "apy": o.apy,
                "tvl": o.tvl,
                "category": o.category,
                "risk": o.risks.get('risk_level', 'Medium')  # Match frontend's risk
            }
            for o in opportunities
            if min_apy <= o.apy <= max_apy
            and (not categories or o.category in categories.split(','))
        ]
        
        return {"yields": filtered}
    except Exception as e:
        logger.error(f"Error in get_yields: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """Get yield analytics"""
    try:
        opportunities = await get_cached_yields()
        stats = YieldDataProcessor().get_summary_stats(opportunities)
        
        # Transform to match frontend format
        return {
            "marketOverview": {
                "totalMarketCap": stats["total_tvl"] / 1e9,  # In billions
                "totalVolume24h": 156.7,  # Placeholder; add if available
                "activeProtocols": stats["total_protocols"],
                "avgYieldChange": stats["average_apy"],
                "riskIndex": 6.8,  # Placeholder; compute average risk if possible
                "marketSentiment": "Bullish"  # Placeholder
            },
            "categoryDistribution": [
                {"name": cat, "value": count, "color": "#9945FF"}  # Add colors as needed
                for cat, count in stats["categories"].items()
            ]
        }
    except Exception as e:
        logger.error(f"Error in get_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio")  # Match frontend proxy
async def optimize_portfolio(request: OptimizeRequest):
    """Optimize portfolio allocation"""
    try:
        opportunities = await get_cached_yields()
        
        # Prepare opportunity data with risk scores
        opp_data = [
            {
                'protocol': opp.protocol,
                'pair': opp.pair,
                'apy': opp.apy,
                'tvl': opp.tvl,
                'audit_score': opp.risks.get('audit_score', 0.5),
                'risk_level': RiskScorer().calculate_risk_score(opp.protocol, opp.tvl, opp.apy)['risk_level']
            }
            for opp in opportunities
        ]
        
        if not opp_data:
            raise HTTPException(status_code=400, detail="No valid opportunities available for optimization")
        
        # Get optimal allocation
        allocations = PortfolioOptimizer().find_optimal_allocation(
            opp_data, request.investment_amount, request.risk_tolerance
        )
        
        if not allocations:
            raise HTTPException(status_code=400, detail="No optimal allocation found for given parameters")
        
        # Transform to match frontend format
        allocations = [
            {
                "id": f"id-{i}",
                "protocol": a["protocol"],
                "pool": a["pair"],
                "allocation": a["allocation_amount"],
                "percentage": a["allocation_percentage"],
                "expectedApy": a["expected_apy"],
                "risk": a.get("risk_level", "Medium")
            }
            for i, a in enumerate(allocations)
        ]
        
        return {"data": allocations}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in optimize_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        opportunities = await get_cached_yields()
        data_status = 'healthy' if opportunities else 'no_data'
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "data_status": data_status,
            "cached_opportunities": len(opportunities) if opportunities else 0,
            "cache_last_updated": cache["last_updated"].isoformat() if cache["last_updated"] else None
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)