from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging
from collections import Counter, defaultdict

# Import existing modules
from src.collector import get_all_solana_yields, YieldOpportunity
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

import os

# CORS configuration using environment variables
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
    min_apy: float = Query(0.1, ge=0.1, description="Minimum APY (in percentage)"),
    min_tvl: int = Query(10000, ge=0, description="Minimum TVL in USD"),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    max_apy: float = Query(50.0, ge=0.0, le=200.0, description="Maximum APY (in percentage)")
):
    """Get Solana yield opportunities with filters"""
    try:
        opportunities = await get_cached_yields()
        if not opportunities:
            return []
            
        processor = YieldDataProcessor(max_apy_threshold=max_apy)
        processed_data = processor.to_dict_list(opportunities)
        
        # Count protocols before filtering
        all_protocols = set(opp['protocol'] for opp in processed_data)
        logger.info(f"Total protocols before filtering: {len(all_protocols)}")
        
        # Apply filters
        if categories:
            category_list = [c.strip() for c in categories.split(',')]
            processed_data = [opp for opp in processed_data if opp['category'] in category_list]
        
        filtered_data = [
            opp for opp in processed_data
            if opp['apy'] >= min_apy and opp['tvl'] >= min_tvl
        ]
        
        # Count protocols after filtering
        filtered_protocols = set(opp['protocol'] for opp in filtered_data)
        logger.info(f"Total protocols after filtering: {len(filtered_protocols)}")
        
        sorted_data = sorted(filtered_data, key=lambda x: x['apy'], reverse=True)[:limit]
        return sorted_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics():
    """Get market analytics summary"""
    try:
        opportunities = await get_cached_yields()
        if not opportunities:
            return {"error": "No data available"}
            
        processor = YieldDataProcessor()
        # Use the same filtering logic as /api/yields
        processed_data = processor.to_dict_list(opportunities)
        
        # Calculate analytics using processed data
        total_opportunities = len(processed_data)
        protocols = set(opp['protocol'] for opp in processed_data)
        total_protocols = len(protocols)
        
        total_tvl = sum(opp['tvl'] for opp in processed_data)
        average_apy = sum(opp['apy'] for opp in processed_data) / total_opportunities if total_opportunities > 0 else 0
        
        categories = Counter(opp['category'] for opp in processed_data)
        
        # Calculate TVL by protocol
        protocol_tvl = defaultdict(float)
        for opp in processed_data:
            protocol_tvl[opp['protocol']] += opp['tvl']
        
        top_protocols = dict(sorted(protocol_tvl.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return {
            "total_opportunities": total_opportunities,
            "total_protocols": total_protocols,
            "total_tvl": total_tvl,
            "average_apy": average_apy,
            "categories": dict(categories),
            "top_protocols": top_protocols
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize")
async def optimize_portfolio(request: OptimizeRequest):
    """Generate optimal portfolio allocation"""
    try:
        # Validate input
        if request.investment_amount <= 0:
            raise HTTPException(status_code=400, detail="Investment amount must be positive")
        
        if request.risk_tolerance not in ["Conservative", "Moderate", "Aggressive"]:
            raise HTTPException(status_code=400, detail="Invalid risk tolerance")
        
        opportunities = await get_cached_yields()
        
        if not opportunities:
            raise HTTPException(status_code=404, detail="No yield data available for optimization")
        
        # Calculate risk scores and prepare data
        risk_scorer = RiskScorer()
        optimizer = PortfolioOptimizer()
        
        opp_data = []
        for opp in opportunities:
            try:
                risk_data = risk_scorer.calculate_risk_score(opp.protocol, opp.tvl, opp.apy)
                opp_data.append({
                    'protocol': opp.protocol,
                    'pair': opp.pair,
                    'apy': opp.apy,
                    'tvl': opp.tvl,
                    'audit_score': opp.risks.get('audit_score', 0.5),
                    'risk_level': risk_data['risk_level']
                })
            except Exception as e:
                logger.warning(f"Error processing opportunity for optimization {opp.protocol}: {e}")
                continue
        
        if not opp_data:
            raise HTTPException(status_code=400, detail="No valid opportunities available for optimization")
        
        # Get optimal allocation
        allocations = optimizer.find_optimal_allocation(
            opp_data, request.investment_amount, request.risk_tolerance
        )
        
        if not allocations:
            raise HTTPException(status_code=400, detail="No optimal allocation found for given parameters")
        
        # Calculate summary metrics
        total_apy = sum(a['allocation_amount'] * a['expected_apy'] for a in allocations) / request.investment_amount
        
        return {
            "strategy": {
                "expected_apy": total_apy,
                "annual_yield": request.investment_amount * total_apy,
                "total_positions": len(allocations),
                "risk_tolerance": request.risk_tolerance,
                "time_horizon": request.time_horizon
            },
            "allocations": allocations,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in optimize_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test data fetching
        opportunities = await get_cached_yields()
        data_status = "healthy" if opportunities else "no_data"
        
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