# Binance Futures Analytics Dashboard

A complete end-to-end analytical application for real-time Binance Futures trade data, featuring data ingestion, storage, quantitative analytics, and interactive visualization.

## 🎯 Project Overview

This application demonstrates a complete workflow from real-time data ingestion to quantitative analytics and visualization:

- **Data Source**: Binance Futures WebSocket streams for live tick data
- **Data Storage**: SQLite database with tick and OHLC data
- **Analytics**: Price statistics, OLS regression, hedge ratios, spread analysis, z-scores, ADF tests, rolling correlations
- **Visualization**: Interactive Streamlit dashboard with real-time updates
- **Features**: Alerting system, data export, OHLC upload

## 🏗️ Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐
│  WebSocket      │
│  (Binance API)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Collector │
│  (async/websocket)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Database     │
│   (SQLite)      │
│  - Ticks        │
│  - OHLC         │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼        ▼
┌────────┐ ┌──────────────┐
│ Data   │ │  Analytics   │
│Processor│ │   Engine     │
└───┬────┘ └──────┬───────┘
    │             │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   Streamlit │
    │  Frontend   │
    └─────────────┘
```

### Components

1. **Data Collector** (`data_collector.py`): Async WebSocket client for Binance streams
2. **Database** (`database.py`): SQLite storage layer with SQLAlchemy ORM
3. **Data Processor** (`data_processor.py`): Background worker for resampling ticks to OHLC
4. **Analytics Engine** (`analytics.py`): Quantitative analytics computations
5. **Frontend** (`app.py`): Streamlit dashboard with interactive visualizations

## 📋 Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## 🚀 Installation

1. Clone or download this repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Usage

### Quick Start

Run the application with a single command:

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Workflow

1. **Start Data Collection**:
   - Enter symbols in the sidebar (e.g., `btcusdt,ethusdt`)
   - Click "▶️ Start" to begin collecting data
   - Data will be stored in SQLite database

2. **View Analytics**:
   - Select symbols and timeframes from the sidebar
   - Navigate through tabs to view different analytics
   - Charts update in near-real-time

3. **Configure Alerts**:
   - Set alert conditions (e.g., Z-Score > 2)
   - Select symbols to monitor
   - Alerts appear automatically when triggered

4. **Export Data**:
   - Go to "Export" tab
   - Choose format (CSV, JSON, Excel)
   - Download processed data

5. **Upload OHLC Data**:
   - Use "Export" tab to upload CSV/JSON files
   - Specify symbol and timeframe
   - Data will be imported to database

## 📊 Analytics Features

### Price Statistics
- Mean, median, std deviation, min, max
- Skewness and kurtosis
- Trade count and volume metrics

### OLS Regression & Hedge Ratio
- Linear regression between two assets
- Hedge ratio calculation
- R-squared and significance tests
- Robust regression option (Huber)

### Spread Analysis
- Price spread calculation
- Hedged spread (using hedge ratio)
- Spread statistics

### Z-Score
- Rolling z-score of spread/price
- Threshold-based alerts
- Mean reversion signals

### ADF Test (Stationarity)
- Augmented Dickey-Fuller test
- Stationarity assessment
- Critical values

### Rolling Correlation
- Dynamic correlation between pairs
- Configurable rolling window
- Time-series visualization

## 🔔 Alerting System

Configure custom alerts for:
- Z-Score thresholds (e.g., > 2 or < -2)
- Spread thresholds
- Price thresholds

Alerts trigger automatically when conditions are met and display prominently in the dashboard.

## 💾 Data Export

Export processed data in multiple formats:
- **CSV**: Standard comma-separated format
- **JSON**: Structured JSON format
- **Excel**: (Future enhancement)

Files include timestamp for easy tracking.

## 📤 OHLC Data Upload

Upload historical OHLC data:
- Supports CSV and JSON formats
- Required columns: timestamp, open, high, low, close, volume
- Automatically imports to database for analysis

## 🗄️ Database Schema

### TickData
- `id`: Unique identifier
- `symbol`: Trading symbol
- `timestamp`: Trade timestamp
- `price`: Trade price
- `size`: Trade size/quantity

### OHLCData
- `id`: Unique identifier
- `symbol`: Trading symbol
- `timestamp`: Bar timestamp
- `timeframe`: Aggregation period (1s, 1m, 5m)
- `open`, `high`, `low`, `close`: OHLC prices
- `volume`: Aggregated volume

## 🔧 Configuration

### Timeframes
- `1s`: 1-second bars
- `1m`: 1-minute bars
- `5m`: 5-minute bars

### Rolling Window
- Configurable window size (5-100)
- Used for z-score and correlation calculations
- Default: 20

## 📈 Methodology

### Data Sampling
Tick data is resampled to OHLC format using pandas resampling:
- **Open**: First price in period
- **High**: Maximum price
- **Low**: Minimum price
- **Close**: Last price
- **Volume**: Sum of trade sizes

### OLS Regression
Standard least squares regression:
- `y = β₀ + β₁x + ε`
- Hedge ratio = β₁
- Spread = y - β₁x

### Z-Score Calculation
- `z = (x - μ) / σ`
- Rolling mean (μ) and std (σ) over window
- Measures deviation from mean

### ADF Test
Tests null hypothesis of unit root (non-stationarity):
- If p-value < 0.05: series is stationary
- Critical values at 1%, 5%, 10% levels

## 🎨 UI/UX Features

- **Wide Layout**: Optimized for analytics dashboards
- **Tabs Organization**: Clear separation of views
- **Interactive Charts**: Plotly with zoom, pan, hover
- **Real-time Updates**: Auto-refresh capability
- **Color-coded Metrics**: Visual indicators for changes
- **Responsive Design**: Adapts to screen size

## 🔍 Design Decisions

### Storage: SQLite
- **Rationale**: File-based, no server required, perfect for local dev
- **Trade-off**: Not ideal for high-frequency/high-volume production
- **Scaling**: Can migrate to PostgreSQL/InfluxDB with minimal code changes

### Frontend: Streamlit
- **Rationale**: Rapid development, Python-native, built-in components
- **Trade-off**: Less customizable than React, but faster to build
- **Scaling**: Can add REST API layer for external frontends

### Processing: Background Threads
- **Rationale**: Non-blocking, allows real-time updates
- **Trade-off**: Thread management complexity
- **Scaling**: Can use Celery/Redis for distributed processing

### Modular Architecture
- **Rationale**: Easy to extend, test, and maintain
- **Trade-off**: More files, but better organization
- **Scaling**: Each module can be containerized independently

## 🚦 Extensibility

The architecture supports easy extension:

1. **New Data Sources**: Implement collector interface
2. **New Analytics**: Add methods to AnalyticsEngine
3. **New Visualizations**: Add tabs to Streamlit app
4. **Different Storage**: Swap database implementation
5. **API Layer**: Add FastAPI/Flask REST endpoints

## 🐛 Troubleshooting

### No Data Appearing
- Ensure collector is started
- Check symbol names are correct (lowercase, e.g., `btcusdt`)
- Verify WebSocket connection (check logs)

### Charts Not Updating
- Enable auto-refresh checkbox
- Check if data processor is running
- Verify timeframe selection matches available data

### Database Errors
- Ensure `data/` directory exists
- Check file permissions
- Restart application

## 📝 Logging

Logs are written to:
- Console output
- File: `collector.log`

Log levels: INFO, WARNING, ERROR, DEBUG

## 🔐 Security Notes

This is a local development application. For production:
- Add authentication/authorization
- Secure database connections
- Validate user inputs
- Rate limiting for API calls
- Environment variable for secrets

## 📚 References

- [Binance WebSocket API](https://binance-docs.github.io/apidocs/futures/en/#websocket-market-data)
- [Statsmodels Documentation](https://www.statsmodels.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## 📄 License

This project is provided for evaluation purposes.

## 👨‍💻 Developer Notes

See `CHATGPT_USAGE.md` for details on AI assistance used in development.

---

**Note**: This application is designed for demonstration and evaluation. For production use, additional considerations around scalability, security, and performance would be required.