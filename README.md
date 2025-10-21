# Solana Yield Farming API

A FastAPI-based service that aggregates and analyzes yield farming opportunities across the Solana ecosystem.

## Features

- **Real-time Yield Data**: Fetches and processes yield opportunities from DeFiLlama
- **Risk Analysis**: Includes risk scoring and portfolio optimization
- **Outlier Detection**: Implements statistical filtering for unrealistic APY values
- **Caching System**: Implements efficient caching to reduce API calls
- **Portfolio Optimization**: Suggests optimal yield farming allocations based on risk tolerance

## API Endpoints

### GET /api/yields
Get filtered yield opportunities with customizable parameters:
- `min_apy`: Minimum APY (decimal)
- `min_tvl`: Minimum Total Value Locked (USD)
- `categories`: Filter by categories (comma-separated)
- `limit`: Maximum number of results
- `max_apy`: Maximum APY threshold

### GET /api/analytics
Get market overview and statistics:
- Total opportunities
- Protocol statistics
- TVL distribution
- Category breakdown

### POST /api/optimize
Generate optimized portfolio allocation:
```json
{
    "investment_amount": 1000,
    "risk_tolerance": "Conservative|Moderate|Aggressive",
    "time_horizon": "short|medium|long"
}
```

### GET /api/health
Service health check endpoint

## Technology Stack

- Python 3.11.9
- FastAPI
- HTTPX for async HTTP requests
- Pydantic for data validation
- Uvicorn ASGI server

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Environment Variables

The application uses CORS configuration through environment variables:
- Default configuration allows all origins for development

## Project Structure

```
├── src/
│   ├── collector.py    # Data collection from DeFiLlama
│   ├── processor.py    # Data processing and analysis
│   └── models.py       # Risk scoring and optimization
├── app.py             # FastAPI application
├── requirements.txt   # Dependencies
├── runtime.txt       # Python version specification
└── README.md
```

## Data Processing

- Implements outlier detection for APY values
- Calculates risk scores based on:
  - Protocol reputation
  - TVL (Total Value Locked)
  - APY sustainability
  - Audit status

## Risk Scoring

Risk levels are calculated based on:
- Protocol reputation
- TVL size
- APY reasonability
- Historical performance
- Audit status

## Portfolio Optimization

Optimization considers:
- Risk tolerance level
- Investment amount
- Protocol diversification
- Risk-adjusted returns

## API Response Examples

### Yield Opportunity
```json
{
    "protocol": "raydium",
    "pool_id": "example_pool",
    "pair": "SOL-USDC",
    "apy": 0.15,
    "tvl": 1000000,
    "category": "dex",
    "audit_score": 0.9,
    "risk_level": "Low Risk"
}
```

## Error Handling

- Implements comprehensive error handling
- Returns appropriate HTTP status codes
- Includes detailed error messages
- Fallback mechanisms for data fetching failures

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details