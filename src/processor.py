from typing import List, Dict
from collections import Counter, defaultdict
from statistics import mean, stdev
from .collector import YieldOpportunity
from datetime import datetime

class YieldDataProcessor:
    """Process yield data for analysis without pandas dependency"""
    
    def __init__(self, max_apy_threshold: float = 50.0):  # 50% APY max by default
        self.max_apy_threshold = max_apy_threshold
        self.min_apy_threshold = 0.1  # 0.1% minimum APY
        self.min_tvl_threshold = 10000  # $10,000 minimum TVL
    
    def remove_outliers(self, opportunities: List[YieldOpportunity]) -> List[YieldOpportunity]:
        """Remove statistical outliers from APY values using multiple criteria"""
        if not opportunities:
            return []
            
        # Convert APY to percentage before filtering
        for opp in opportunities:
            opp.apy = opp.apy * 100 if opp.apy < 1 else opp.apy
            
        # First filter by basic thresholds
        basic_filtered = [
            opp for opp in opportunities 
            if (self.min_apy_threshold <= opp.apy <= self.max_apy_threshold and 
                opp.tvl >= self.min_tvl_threshold)
        ]
        
        if not basic_filtered:
            return []
            
        # Apply statistical filtering
        apys = [opp.apy for opp in basic_filtered]
        
        try:
            avg = mean(apys)
            std = stdev(apys)
            
            upper_bound = min(avg + 1.5 * std, self.max_apy_threshold)
            lower_bound = max(self.min_apy_threshold, avg - 1.5 * std)
            
            filtered = [
                opp for opp in basic_filtered
                if all([
                    lower_bound <= opp.apy <= upper_bound,
                    opp.apy <= self.max_apy_threshold,
                    opp.apy >= self.min_apy_threshold,
                    opp.tvl >= self.min_tvl_threshold
                ])
            ]
            
            return filtered
            
        except Exception as e:
            return basic_filtered

    def to_dict_list(self, opportunities: List[YieldOpportunity]) -> List[Dict]:
        """Convert opportunities to list of dictionaries"""
        filtered_opportunities = self.remove_outliers(opportunities)
        
        data = []
        for opp in filtered_opportunities:
            # APY should already be in percentage form from remove_outliers
            data.append({
                'protocol': opp.protocol,
                'pair': opp.pair,
                'apy': opp.apy,  # Already in percentage
                'tvl': opp.tvl,
                'category': opp.category,
                'audit_score': opp.risks.get('audit_score', 0.5),
                'pool_id': opp.pool_id,
                'tokens': opp.tokens,
                'risk_level': self._get_risk_level(opp),
                'last_updated': datetime.now().isoformat()
            })
        
        return data
    
    def get_summary_stats(self, opportunities: List[YieldOpportunity]) -> Dict:
        """Get summary statistics without pandas"""
        
        if not opportunities:
            return {'error': 'No opportunities'}
        
        # Remove outliers before processing
        filtered_opportunities = self.remove_outliers(opportunities)
        data = self.to_dict_list(filtered_opportunities)
        
        if not data:
            return {'error': 'No valid opportunities after filtering'}
        
        # Basic calculations
        total_opportunities = len(filtered_opportunities)
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
            'top_protocols': top_protocols,
            'filtered_count': len(opportunities) - total_opportunities  # Number of filtered outliers
        }

    def _get_risk_level(self, opportunity: YieldOpportunity) -> str:
        """Determine risk level based on opportunity characteristics"""
        if opportunity.risks.get('audit_score', 0.5) >= 0.9:
            return 'Low'
        elif opportunity.risks.get('audit_score', 0.5) >= 0.7:
            return 'Medium'
        else:
            return 'High'