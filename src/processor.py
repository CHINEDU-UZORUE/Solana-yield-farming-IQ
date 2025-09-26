from typing import List, Dict
from collections import Counter, defaultdict
from .collector import YieldOpportunity

class YieldDataProcessor:
    """Process yield data for analysis without pandas dependency"""
    
    def to_dict_list(self, opportunities: List[YieldOpportunity]) -> List[Dict]:
        """Convert opportunities to list of dictionaries"""
        
        data = []
        for opp in opportunities:
            data.append({
                'protocol': opp.protocol,
                'pair': opp.pair,
                'apy': opp.apy,
                'tvl': opp.tvl,
                'category': opp.category,
                'audit_score': opp.risks.get('audit_score', 0.5),
                'pool_id': opp.pool_id,
                'apy_percent': opp.apy * 100,
                'risk_adjusted_apy': opp.apy * opp.risks.get('audit_score', 0.5)
            })
        
        return data
    
    def get_summary_stats(self, opportunities: List[YieldOpportunity]) -> Dict:
        """Get summary statistics without pandas"""
        
        if not opportunities:
            return {'error': 'No opportunities'}
        
        data = self.to_dict_list(opportunities)
        
        # Basic calculations
        total_opportunities = len(opportunities)
        protocols = set(opp['protocol'] for opp in data)
        total_protocols = len(protocols)
        
        # TVL and APY calculations
        total_tvl = sum(opp['tvl'] for opp in data)
        average_apy = sum(opp['apy'] for opp in data) / len(data) if data else 0
        
        # Category distribution
        categories = Counter(opp['category'] for opp in data)
        
        # Top protocols by TVL
        protocol_tvl = defaultdict(float)
        for opp in data:
            protocol_tvl[opp['protocol']] += opp['tvl']
        
        top_protocols = dict(
            sorted(protocol_tvl.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        return {
            'total_opportunities': total_opportunities,
            'total_protocols': total_protocols,
            'total_tvl': total_tvl,
            'average_apy': average_apy,
            'categories': dict(categories),
            'top_protocols': top_protocols
        }