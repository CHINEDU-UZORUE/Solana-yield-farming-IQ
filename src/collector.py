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
        
        # Debug: Print all unique chain values (lowercase)
        unique_chains = set(pool.get('chain', '').lower() for pool in all_pools if pool.get('chain'))
        print(f"All available chains: {sorted(unique_chains)}")
        
        # Filter for Solana chain (convert to lowercase for comparison)
        solana_pools = [pool for pool in all_pools if pool.get('chain', '').lower() == 'solana']
        
        print(f"Found {len(solana_pools)} Solana pools from {len(all_pools)} total pools")
        
        # Convert to opportunities
        opportunities = []
        for pool in solana_pools:
            opp = self._create_opportunity(pool)
            if opp:
                opportunities.append(opp)
        
        # Sort by APY and return
        opportunities.sort(key=lambda x: x.apy, reverse=True)
        print(f"✅ Returning {len(opportunities)} Solana yield opportunities")
        return opportunities
    
    def _create_opportunity(self, pool: Dict) -> Optional[YieldOpportunity]:
        """Convert pool data to YieldOpportunity"""
        
        apy = pool.get('apy', 0)
        tvl = pool.get('tvlUsd', 0)
        
        # Basic validation
        if not apy or not tvl or apy <= 0 or tvl < 1000:
            return None
        
        # Convert percentage APY to decimal if needed
        if apy > 5:
            apy = apy / 100
        
        return YieldOpportunity(
            protocol=pool.get('project', 'Unknown'),
            pool_id=pool.get('pool', ''),
            pair=pool.get('symbol', ''),
            apy=apy,
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
        elif any(x in project for x in ['marinade', 'lido']):
            return 'liquid_staking'
        elif any(x in project for x in ['drift', 'zeta']):
            return 'derivatives'
        else:
            return 'other'
    
    def _get_audit_score(self, project: str) -> float:
        """Simple audit scoring"""
        project = project.lower()
        
        if any(x in project for x in ['orca', 'raydium', 'solend', 'marinade']):
            return 0.9
        elif any(x in project for x in ['mango', 'port', 'drift']):
            return 0.7
        else:
            return 0.5

async def get_all_solana_yields() -> List[YieldOpportunity]:
    collector = ComprehensiveSolanaCollector()
    return await collector.get_all_solana_yields()