# models.py
from typing import Dict, List

class RiskScorer:
    """Calculate risk scores for yield opportunities"""
    
    def calculate_risk_score(self, protocol: str, tvl: float, apy: float, apy_mean_30d: Optional[float] = None) -> Dict:
        """Calculate comprehensive risk score using APY and optional 30-day mean"""
        
        # Input validation
        if tvl < 0 or apy < 0:
            raise ValueError("TVL and APY must be non-negative")
        
        # TVL score (higher TVL = lower risk)
        tvl_score = min(1.0, tvl / 10_000_000)
        
        # Protocol score
        protocol_score = self._get_protocol_score(protocol)
        
        # APY risk (very high APY = higher risk) - adjusted for percentage APY (e.g., 0.5 = 0.5%, 5 = 5%)
        effective_apy = apy_mean_30d if apy_mean_30d is not None else apy  # Use 30d mean if available
        if effective_apy < 0.5:  # Less than 0.5% APY
            apy_risk = 1.0
        elif effective_apy < 5:  # 0.5-5% APY
            apy_risk = 0.9
        elif effective_apy < 50:  # 5-50% APY
            apy_risk = 0.7
        elif effective_apy < 200:  # 50-200% APY
            apy_risk = 0.5
        elif effective_apy < 500:  # 200-500% APY
            apy_risk = 0.3
        elif effective_apy < 2000:  # 500-2000% APY
            apy_risk = 0.2
        else:  # Very high APY (>2000%)
            apy_risk = 0.1
        
        # Overall score
        weights = {'tvl': 0.3, 'protocol': 0.4, 'apy': 0.3}
        overall_score = (
            tvl_score * weights['tvl'] +
            protocol_score * weights['protocol'] +
            apy_risk * weights['apy']
        )
        
        return {
            'overall': overall_score,
            'risk_level': self._get_risk_level(overall_score),
            'breakdown': {
                'tvl_score': tvl_score,
                'protocol_score': protocol_score,
                'apy_risk': apy_risk
            }
        }
    
    def _get_protocol_score(self, protocol: str) -> float:
        """Score protocol based on reputation"""
        scores = {
            'raydium': 0.95, 'orca': 0.95, 'solend': 0.9,
            'marinade': 0.9, 'jito-liquid-staking': 0.9, 'mango': 0.8,
            'port': 0.8, 'drift': 0.75, 'saber': 0.75, 'sunny': 0.7,
            'kamino': 0.8, 'marginfi': 0.75
        }
        protocol_lower = protocol.lower()
        
        # Check if any known protocol name is in the protocol string
        for known_protocol, score in scores.items():
            if known_protocol in protocol_lower:
                return score
                
        return 0.5  # Default for unknown protocols
    
    def _get_risk_level(self, score: float) -> str:
        """Convert score to risk level"""
        if score >= 0.8:
            return "Low Risk"
        elif score >= 0.6:
            return "Medium Risk"
        elif score >= 0.4:
            return "High Risk"
        else:
            return "Very High Risk"

class PortfolioOptimizer:
    def find_optimal_allocation(self, opportunities: List[Dict], 
                              investment: float, risk_tolerance: str) -> List[Dict]:
        """Find optimal allocation"""
        risk_filters = {
            "Conservative": ["Low Risk"],
            "Moderate": ["Low Risk", "Medium Risk"],
            "Aggressive": ["Low Risk", "Medium Risk", "High Risk"]
        }
        
        allowed_risks = risk_filters.get(risk_tolerance, ["Low Risk", "Medium Risk"])
        filtered_opps = [o for o in opportunities if o.get('risk_level') in allowed_risks]
        
        if not filtered_opps:
            return []
        
        # Calculate weighted score and handle zero case
        scores = [o['apy'] * o.get('audit_score', 0.5) for o in filtered_opps]
        total_score = sum(scores) or 1.0  # Avoid division by zero
        
        allocations = []
        for i, opp in enumerate(filtered_opps[:5]):  # Top 5 opportunities
            weight = (opp['apy'] * opp.get('audit_score', 0.5)) / total_score
            allocation_amount = investment * weight
            if allocation_amount > 0:  # Only include if allocation is meaningful
                allocations.append({
                    'protocol': opp['protocol'],
                    'pair': opp['pair'],
                    'allocation_percentage': weight * 100,
                    'allocation_amount': allocation_amount,
                    'expected_apy': opp['apy'],
                    'risk_level': opp.get('risk_level', 'Medium Risk')
                })
        
        # Normalize to ensure total allocation matches investment
        if allocations:
            total_allocated = sum(a['allocation_amount'] for a in allocations)
            if total_allocated > 0:
                for a in allocations:
                    a['allocation_percentage'] = (a['allocation_amount'] / total_allocated) * 100
                    a['allocation_amount'] = (a['allocation_amount'] / total_allocated) * investment
        
        return allocations