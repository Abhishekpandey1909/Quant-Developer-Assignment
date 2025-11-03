# System Architecture

## Architecture Diagram

The architecture diagram should be created in draw.io with the following structure:

### Components and Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      EXTERNAL SYSTEM                         │
│                  Binance Futures WebSocket                   │
│              (wss://fstream.binance.com/ws)                   │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     │ Real-time Trade Stream
                     │ (tick data: symbol, price, size, timestamp)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │      Data Collector (data_collector.py)                │ │
│  │  - Async WebSocket client                              │ │
│  │  - Auto-reconnect with exponential backoff             │ │
│  │  - Data normalization                                   │ │
│  │  - Buffer management                                    │ │
│  └────────────┬─────────────────────────────────────────────┘ │
│               │                                               │
│               │ Normalized Tick Data                          │
│               ▼                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Database Layer (database.py)                   │ │
│  │  - SQLite storage                                       │ │
│  │  - SQLAlchemy ORM                                       │ │
│  │  - TickData table                                       │ │
│  │  - OHLCData table                                       │ │
│  └────────────┬─────────────────────────────────────────────┘ │
└───────────────┼─────────────────────────────────────────────────┘
                │
                │ Stored Data
                ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATA PROCESSING LAYER                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Data Processor (data_processor.py)                   │ │
│  │  - Background worker                                   │ │
│  │  - Resample ticks to OHLC (1s, 1m, 5m)                 │ │
│  │  - Continuous aggregation                              │ │
│  └────────────┬─────────────────────────────────────────────┘ │
│               │                                               │
│               │ Aggregated OHLC Data                          │
│               ▼                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │      Analytics Engine (analytics.py)                   │ │
│  │  - Price statistics                                    │ │
│  │  - OLS regression & hedge ratio                        │ │
│  │  - Spread calculation                                 │ │
│  │  - Z-score computation                                 │ │
│  │  - ADF test (stationarity)                             │ │
│  │  - Rolling correlation                                 │ │
│  └────────────┬─────────────────────────────────────────────┘ │
└───────────────┼─────────────────────────────────────────────────┘
                │
                │ Analytics Results
                ▼
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │      Streamlit Frontend (app.py)                       │ │
│  │  - Interactive dashboard                               │ │
│  │  - Real-time visualizations (Plotly)                   │ │
│  │  - Alert system                                        │ │
│  │  - Data export                                         │ │
│  │  - OHLC upload                                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Ingestion**: WebSocket → Data Collector → Database
2. **Processing**: Database → Data Processor → OHLC Database
3. **Analytics**: Database → Analytics Engine → Results
4. **Visualization**: Database + Analytics → Frontend → User

## Component Details

### Data Collector
- **Technology**: Python asyncio, websockets library
- **Responsibilities**: 
  - WebSocket connection management
  - Data normalization
  - Batch insertion to database
- **Scaling**: Can run multiple collectors for different symbols

### Database
- **Technology**: SQLite, SQLAlchemy ORM
- **Schema**: 
  - TickData: Raw tick records
  - OHLCData: Aggregated bar data
- **Scaling**: Can migrate to PostgreSQL/InfluxDB

### Data Processor
- **Technology**: Python asyncio, pandas
- **Responsibilities**:
  - Resample ticks to OHLC
  - Multiple timeframe support
  - Background processing
- **Scaling**: Can use Celery for distributed processing

### Analytics Engine
- **Technology**: pandas, numpy, statsmodels, scipy
- **Responsibilities**:
  - Statistical computations
  - Regression analysis
  - Time series analysis
- **Scaling**: Stateless, can run in parallel

### Frontend
- **Technology**: Streamlit, Plotly
- **Responsibilities**:
  - User interface
  - Real-time updates
  - Visualization
  - Alert management
- **Scaling**: Can add REST API layer

## Alert Flow

```
User Configures Alert (Frontend)
         │
         ▼
Alert Condition Stored (Session State)
         │
         ▼
Analytics Engine Computes Metric (e.g., Z-Score)
         │
         ▼
Frontend Checks Alert Condition
         │
         ▼
If Triggered → Display Alert to User
```

## Extension Points

1. **New Data Sources**: Implement collector interface
2. **New Storage**: Swap database implementation
3. **New Analytics**: Add methods to AnalyticsEngine
4. **New Visualizations**: Add tabs to frontend
5. **API Layer**: Add REST endpoints

## Scaling Considerations

- **Database**: SQLite → PostgreSQL for production
- **Processing**: Threads → Celery workers
- **Frontend**: Streamlit → React + FastAPI
- **Ingestion**: Single collector → Multiple collectors per symbol

## Instructions for Draw.io

1. Create new diagram in draw.io
2. Use rectangles for components
3. Use arrows for data flow
4. Color code layers:
   - Blue: External/Ingestion
   - Green: Storage
   - Orange: Processing
   - Purple: Presentation
5. Add labels on arrows describing data format
6. Export as PNG/SVG

A sample draw.io XML structure is provided below (save as `.drawio` file).
