from typing import List, Dict
from collections import Counter, defaultdict
from statistics import mean, stdev
from .collector import YieldOpportunity

class YieldDataProcessor:
    """Process yield data for analysis without pandas dependency"""
    
    def __init__(self, max_apy_threshold: float = 2.0):  # 200% APY max by default
        self.max_apy_threshold = max_apy_threshold
    
    def remove_outliers(self, opportunities: List[YieldOpportunity]) -> List[YieldOpportunity]:
        """Remove statistical outliers from APY values"""
        if not opportunities:
            return []
            
        apys = [opp.apy for opp in opportunities]
        
        # Calculate mean and standard deviation
        try:
            avg = mean(apys)
            std = stdev(apys)
            
            # Define outlier thresholds (2 standard deviations)
            upper_bound = min(avg + 2 * std, self.max_apy_threshold)
            lower_bound = max(0, avg - 2 * std)
            
            # Filter opportunities
            filtered = [
                opp for opp in opportunities 
                if lower_bound <= opp.apy <= upper_bound
            ]
            
            return filtered
        except Exception:
            # Fallback to simple threshold if statistical calculation fails
            return [opp for opp in opportunities if opp.apy <= self.max_apy_threshold]
    
    def to_dict_list(self, opportunities: List[YieldOpportunity]) -> List[Dict]:
        """Convert opportunities to list of dictionaries"""
        
        # First remove outliers
        filtered_opportunities = self.remove_outliers(opportunities)
        
        data = []
        for opp in filtered_opportunities:
            data.append({
                'protocol': opp.protocol,
                'pair': opp.pair,
                'apy': opp.apy,
                'tvl': opp.tvl,
                'category': opp.category,
                'audit_score': opp.risks.get('audit_score', 0.5),
                'pool_id': opp.pool_id,
                'apy_percent': opp.apy,
                'risk_adjusted_apy': opp.apy * opp.risks.get('audit_score', 0.5)
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