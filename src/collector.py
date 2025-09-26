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
                # Get all pools from DeFiLlama
                response = await client.get(self.base_url)
                response.raise_for_status()
                data = response.json()
                all_pools = data.get('data', [])
            except httpx.RequestError as e:
                logging.error(f"Failed to fetch data from DeFiLlama: {e}")
                return []
            except httpx.HTTPStatusError as e:
                logging.error(f"HTTP error from DeFiLlama: {e}")
                return []
        
        # Filter for Solana
        solana_pools = self._filter_solana_pools(all_pools)
        
        # Convert to YieldOpportunity objects
        opportunities = []
        for pool in solana_pools:
            opp = self._create_opportunity(pool)
            if opp and self._validate_opportunity(opp):
                opportunities.append(opp)
        
        # Remove duplicates and sort
        opportunities = self._deduplicate(opportunities)
        opportunities.sort(key=lambda x: x.apy, reverse=True)
        
        print(f"âœ… Collected {len(opportunities)} Solana yield opportunities")
        return opportunities
    
    def _filter_solana_pools(self, pools: List[Dict]) -> List[Dict]:
        """Filter pools for Solana ecosystem"""
        
        solana_protocols = {
            'raydium', 'orca', 'solend', 'mango', 'port', 'tulip', 'marinade', 
            'lido', 'saber', 'sunny', 'drift', 'zeta', 'friktion', 'quarry',
            'aldrin', 'cropper', 'meteora', 'lifinity', 'apricot', 'jet',
            'francium', 'larix', 'marginfi', 'kamino', 'socean', 'jpool'
        }
        
        solana_pools = []
        for pool in pools:
            chain = pool.get('chain', '').lower()
            project = pool.get('project', '').lower()
            
            if (chain == 'solana' or 
                any(protocol in project for protocol in solana_protocols)):
                solana_pools.append(pool)
        
        return solana_pools
    
    def _create_opportunity(self, pool: Dict) -> Optional[YieldOpportunity]:
        """Convert pool data to YieldOpportunity"""
        
        apy = pool.get('apy', 0)
        tvl = pool.get('tvlUsd', 0)
        
        # Convert percentage to decimal if needed
        if apy > 5:
            apy = apy / 100
            
        if apy <= 0 or tvl <= 0:
            return None
        
        protocol = pool.get('project', 'Unknown')
        category = self._categorize_protocol(protocol, pool.get('symbol', ''))
        
        return YieldOpportunity(
            protocol=protocol,
            pool_id=pool.get('pool', ''),
            pair=pool.get('symbol', ''),
            apy=apy,
            tvl=tvl,
            category=category,
            tokens=pool.get('underlyingTokens', []),
            risks={
                'il_risk': pool.get('ilRisk', 'no'),
                'audit_score': self._get_audit_score(protocol)
            },
            metadata={
                'url': pool.get('url', ''),
                'reward_tokens': pool.get('rewardTokens', [])
            },
            last_updated=datetime.now()
        )
    
    def _categorize_protocol(self, protocol: str, symbol: str) -> str:
        """Categorize protocol type"""
        
        protocol_lower = protocol.lower()
        
        if any(p in protocol_lower for p in ['raydium', 'orca', 'serum', 'aldrin']):
            return 'dex'
        elif any(p in protocol_lower for p in ['solend', 'mango', 'port', 'tulip']):
            return 'lending'
        elif any(p in protocol_lower for p in ['marinade', 'lido', 'socean']):
            return 'liquid_staking'
        elif any(p in protocol_lower for p in ['drift', 'zeta', 'friktion']):
            return 'derivatives'
        elif any(p in protocol_lower for p in ['saber', 'sunny', 'quarry']):
            return 'farm'
        else:
            return 'other'
    
    def _get_audit_score(self, protocol: str) -> float:
        """Estimate audit score"""
        high_audit = {'orca', 'raydium', 'solend', 'marinade'}
        medium_audit = {'mango', 'port', 'drift', 'saber'}
        
        protocol_lower = protocol.lower()
        
        if any(p in protocol_lower for p in high_audit):
            return 0.9
        elif any(p in protocol_lower for p in medium_audit):
            return 0.7
        else:
            return 0.5
    
    def _validate_opportunity(self, opp: YieldOpportunity) -> bool:
        """Validate opportunity"""
        if opp.apy < 0.05 or opp.apy > 1000:  # 0.5% to 1000%
            return False
        if opp.tvl < 1000:  # Minimum $1000 TVL
            return False
        return True
    
    def _deduplicate(self, opportunities: List[YieldOpportunity]) -> List[YieldOpportunity]:
        """Remove duplicates"""
        seen = set()
        unique = []
        
        for opp in opportunities:
            key = f"{opp.protocol}_{opp.pair}"
            if key not in seen:
                seen.add(key)
                unique.append(opp)
        
        return unique

# Simple interface
async def get_all_solana_yields() -> List[YieldOpportunity]:
    collector = ComprehensiveSolanaCollector()
    return await collector.get_all_solana_yields()