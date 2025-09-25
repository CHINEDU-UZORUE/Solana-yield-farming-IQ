import pandas as pd
from typing import List, Dict
from .collector import YieldOpportunity

class YieldDataProcessor:
    """Process yield data for analysis"""
    
    def to_dataframe(self, opportunities: List[YieldOpportunity]) -> pd.DataFrame:
        """Convert opportunities to DataFrame"""
        
        data = []
        for opp in opportunities:
            data.append({
                'protocol': opp.protocol,
                'pair': opp.pair,
                'apy': opp.apy,
                'tvl': opp.tvl,
                'category': opp.category,
                'audit_score': opp.risks.get('audit_score', 0.5),
                'pool_id': opp.pool_id
            })
        
        df = pd.DataFrame(data)
        df['apy_percent'] = df['apy'] * 100
        df['risk_adjusted_apy'] = df['apy'] * df['audit_score']
        
        return df
    
    def get_summary_stats(self, opportunities: List[YieldOpportunity]) -> Dict:
        """Get summary statistics"""
        
        if not opportunities:
            return {'error': 'No opportunities'}
        
        df = self.to_dataframe(opportunities)
        
        return {
            'total_opportunities': len(opportunities),
            'total_protocols': df['protocol'].nunique(),
            'total_tvl': df['tvl'].sum(),
            'average_apy': df['apy'].mean(),
            'categories': df['category'].value_counts().to_dict(),
            'top_protocols': df.groupby('protocol')['tvl'].sum().sort_values(ascending=False).head(5).to_dict()
        }