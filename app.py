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
    min_tvl: int = Query(0, ge=0, description="Minimum TVL in USD"),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results")
):
    """Get filtered Solana yield opportunities"""
    try:
        opportunities = await get_cached_yields()
        
        if not opportunities:
            return []
        
        # Apply filters
        filtered_opportunities = opportunities.copy()
        
        # Filter by APY
        if min_apy > 0:
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.apy >= min_apy]
        
        # Filter by TVL
        if min_tvl > 0:
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.tvl >= min_tvl]
        
        # Filter by categories
        if categories:
            category_list = [cat.strip().lower() for cat in categories.split(',')]
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.category.lower() in category_list]
        
        # Sort by APY descending and limit results
        filtered_opportunities.sort(key=lambda x: x.apy, reverse=True)
        filtered_opportunities = filtered_opportunities[:limit]
        
        # Calculate risk scores and convert to response format
        risk_scorer = RiskScorer()
        response_data = []
        errors_count = 0
        
        for opp in filtered_opportunities:
            try:
                risk_data = risk_scorer.calculate_risk_score(opp.protocol, opp.tvl, opp.apy)
                response_data.append(YieldResponse(
                    protocol=opp.protocol,
                    pool_id=opp.pool_id,
                    pair=opp.pair,
                    apy=opp.apy,
                    tvl=opp.tvl,
                    category=opp.category,
                    tokens=opp.tokens,
                    audit_score=opp.risks.get('audit_score', 0.5),
                    risk_level=risk_data['risk_level'],
                    last_updated=opp.last_updated.isoformat()
                ))
            except Exception as e:
                errors_count += 1
                logger.error(f"Error processing opportunity {opp.protocol}: {e}")
                # Don't skip - include with default risk level
                response_data.append(YieldResponse(
                    protocol=opp.protocol,
                    pool_id=opp.pool_id,
                    pair=opp.pair,
                    apy=opp.apy,
                    tvl=opp.tvl,
                    category=opp.category,
                    tokens=opp.tokens,
                    audit_score=opp.risks.get('audit_score', 0.5),
                    risk_level="Medium Risk",  # Default risk level
                    last_updated=opp.last_updated.isoformat()
                ))
        
        logger.info(f"Processed {len(response_data)} opportunities with {errors_count} errors")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error in get_yields: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics():
    """Get market analytics summary"""
    try:
        opportunities = await get_cached_yields()
        
        if not opportunities:
            raise HTTPException(status_code=404, detail="No yield data available")
        
        processor = YieldDataProcessor()
        stats = processor.get_summary_stats(opportunities)
        
        return AnalyticsResponse(
            total_opportunities=stats['total_opportunities'],
            total_protocols=stats['total_protocols'],
            total_tvl=stats['total_tvl'],
            average_apy=stats['average_apy'],
            categories=stats['categories'],
            top_protocols=stats['top_protocols']
        )
        
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