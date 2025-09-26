# collector.py
import asyncio
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class YieldOpportunity:
    protocol: str
    pool_id: str
    pair: str
    apy: float
    apy_base: Optional[float] = None  # Optional from sample
    apy_mean_30d: Optional[float] = None  # Optional from sample
    tvl: float
    category: str
    tokens: List[str]
    risks: Dict
    metadata: Dict
    last_updated: datetime

class ComprehensiveSolanaCollector:
    """Single collector for ALL Solana yield opportunities"""
    
    def __init__(self):
        self.base_url = 'https://yields.llama.fi/pools'
        self.timeout = 30.0
        
    async def get_all_solana_yields(self) -> List[YieldOpportunity]:
        """Get ALL Solana yield opportunities"""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.base_url)
                response.raise_for_status()
                data = response.json()
                all_pools = data.get('data', [])
            except Exception as e:
                logging.error(f"Failed to fetch data: {e}")
                return []
        
        # Filter for Solana chain (convert to lowercase for comparison)
        solana_pools = [pool for pool in all_pools if pool.get('chain', '').lower() == 'solana']
        
        print(f"Found {len(solana_pools)} Solana pools from {len(all_pools)} total pools")
        
        # Convert to opportunities with validation
        opportunities = []
        for pool in solana_pools:
            opp = self._create_opportunity(pool)
            if opp and self._validate_opportunity(opp):
                opportunities.append(opp)
        
        # Sort by APY and return
        opportunities.sort(key=lambda x: x.apy, reverse=True)
        print(f"✅ Returning {len(opportunities)} Solana yield opportunities")
        return opportunities
    
    def _create_opportunity(self, pool: Dict) -> Optional[YieldOpportunity]:
        """Convert pool data to YieldOpportunity"""
        
        apy = pool.get('apy', 0)
        apy_base = pool.get('apyBase')
        apy_mean_30d = pool.get('apyMean30d')
        tvl = pool.get('tvlUsd', 0)
        
        # Basic validation
        if apy <= 0 or tvl < 100:  # Lowered TVL threshold
            return None
        
        return YieldOpportunity(
            protocol=pool.get('project', 'Unknown'),
            pool_id=pool.get('pool', ''),
            pair=pool.get('symbol', ''),
            apy=apy,
            apy_base=apy_base,
            apy_mean_30d=apy_mean_30d,
            tvl=tvl,
            category=self._get_category(pool.get('project', '')),
            tokens=pool.get('underlyingTokens', []),
            risks={'audit_score': self._get_audit_score(pool.get('project', ''))},
            metadata={
                'url': pool.get('url', ''),
                'reward_tokens': pool.get('rewardTokens', [])
            },
            last_updated=datetime.now()
        )
    
    def _get_category(self, project: str) -> str:
        """Simple categorization"""
        project = project.lower()
        
        if any(x in project for x in ['raydium', 'orca', 'serum']):
            return 'dex'
        elif any(x in project for x in ['solend', 'mango', 'port']):
            return 'lending'
        elif any(x in project for x in ['marinade', 'lido', 'jito-liquid-staking']):
            return 'liquid_staking'
        elif any(x in project for x in ['drift', 'zeta']):
            return 'derivatives'
        else:
            return 'other'
    
    def _get_audit_score(self, project: str) -> float:
        """Simple audit scoring"""
        project = project.lower()
        
        if any(x in project for x in ['orca', 'raydium', 'solend', 'marinade', 'jito-liquid-staking']):
            return 0.9
        elif any(x in project for x in ['mango', 'port', 'drift']):
            return 0.7
        else:
            return 0.5

    def _validate_opportunity(self, opp: YieldOpportunity) -> bool:
        """Validate opportunity and filter outliers"""
        
        # Filter extreme APY outliers while keeping high-yield DeFi (in percentage, 0.1 to 2000%)
        if opp.apy < 0.1 or opp.apy > 2000:  
            return False
            
        # Minimum TVL threshold
        if opp.tvl < 100:
            return False
            
        # Must have valid protocol and pair names
        if not opp.protocol or not opp.pair:
            return False
            
        return True
    
async def get_all_solana_yields() -> List[YieldOpportunity]:
    collector = ComprehensiveSolanaCollector()
    return await collector.get_all_solana_yields()