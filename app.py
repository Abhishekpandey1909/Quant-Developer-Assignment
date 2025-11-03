#!/usr/bin/env python3
"""
Main Streamlit application for Binance Futures Analytics Dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import asyncio
import threading
import time
import logging
from io import StringIO
import numpy as np

from database import Database
from analytics import AnalyticsEngine
from data_collector import BinanceCollector
from data_processor import DataProcessor

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Binance Futures Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = Database()
if 'collector_running' not in st.session_state:
    st.session_state.collector_running = False
if 'collector_thread' not in st.session_state:
    st.session_state.collector_thread = None
if 'processor_thread' not in st.session_state:
    st.session_state.processor_thread = None
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

# Initialize analytics engine
engine = AnalyticsEngine()

# Title
st.title("📊 Binance Futures Analytics Dashboard")
st.markdown("Real-time trade data analytics and visualization")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Symbol selection
    symbols_input = st.text_input(
        "Symbols (comma-separated)",
        value="btcusdt,ethusdt",
        help="Enter trading symbols separated by commas"
    )
    symbols = [s.strip().lower() for s in symbols_input.split(',') if s.strip()]
    
    # Start/Stop collector
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start", disabled=st.session_state.collector_running):
            if symbols:
                st.session_state.collector_running = True
                st.rerun()
    
    with col2:
        if st.button("⏹️ Stop", disabled=not st.session_state.collector_running):
            st.session_state.collector_running = False
            st.rerun()
    
    st.divider()
    
    # Timeframe selection
    st.subheader("📅 Timeframe")
    timeframe = st.selectbox("Select timeframe", ["1s", "1m", "5m"], index=1)
    
    # Rolling window
    rolling_window = st.slider("Rolling Window", min_value=5, max_value=100, value=20, step=5)
    
    # Available symbols
    available_symbols = st.session_state.db.get_symbols()
    if available_symbols:
        st.subheader("📈 Available Symbols")
        for sym in available_symbols:
            st.text(sym)
    
    st.divider()
    
    # Alert configuration
    st.subheader("🔔 Alerts")
    alert_condition = st.selectbox(
        "Alert Condition",
        ["Z-Score >", "Z-Score <", "Spread >", "Spread <", "Price >", "Price <"]
    )
    alert_threshold = st.number_input("Threshold", value=2.0)
    alert_symbol = st.selectbox("Symbol", available_symbols if available_symbols else [])
    
    if st.button("Add Alert"):
        st.session_state.alerts.append({
            'condition': alert_condition,
            'threshold': alert_threshold,
            'symbol': alert_symbol,
            'active': True
        })
        st.success("Alert added!")
    
    if st.session_state.alerts:
        st.markdown("### Active Alerts")
        for i, alert in enumerate(st.session_state.alerts):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"{alert['condition']} {alert['threshold']} ({alert['symbol']})")
            with col2:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.alerts.pop(i)
                    st.rerun()


# Main content
if not st.session_state.collector_running and not available_symbols:
    st.info("👆 Start the collector from the sidebar to begin collecting data.")
else:
    # Get symbols to display
    display_symbols = symbols if st.session_state.collector_running else available_symbols
    
    if not display_symbols:
        st.warning("No data available. Start the collector with symbols.")
    else:
        # Symbol selector for charts
        selected_symbol = st.selectbox("Select Symbol", display_symbols, key="chart_symbol")
        
        # Get recent data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        # Get ticks
        ticks_df = st.session_state.db.get_ticks(
            symbol=selected_symbol,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Get OHLC for selected timeframe
        ohlc_df = st.session_state.db.get_ohlc(
            symbol=selected_symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time
        )
        
        if not ticks_df.empty or not ohlc_df.empty:
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            if not ticks_df.empty:
                latest_price = ticks_df.iloc[-1]['price']
                price_change = latest_price - ticks_df.iloc[0]['price'] if len(ticks_df) > 1 else 0
                price_change_pct = (price_change / ticks_df.iloc[0]['price'] * 100) if len(ticks_df) > 1 and ticks_df.iloc[0]['price'] > 0 else 0
                total_volume = ticks_df['size'].sum()
                
                with col1:
                    st.metric("Latest Price", f"${latest_price:,.2f}", f"{price_change_pct:+.2f}%")
                with col2:
                    st.metric("Price Change", f"${price_change:+,.2f}")
                with col3:
                    st.metric("Total Volume", f"{total_volume:,.4f}")
                with col4:
                    st.metric("Trade Count", f"{len(ticks_df):,}")
            
            # Tabs for different views
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📈 Price Chart", "📊 OHLC", "📉 Spread & Z-Score", 
                "🔗 Correlation", "📋 Statistics", "💾 Export"
            ])
            
            with tab1:
                st.subheader("Price Chart")
                if not ohlc_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=ohlc_df['timestamp'],
                        y=ohlc_df['close'],
                        mode='lines',
                        name='Close Price',
                        line=dict(color='#1f77b4', width=2)
                    ))
                    fig.update_layout(
                        title=f"{selected_symbol.upper()} Price ({timeframe})",
                        xaxis_title="Time",
                        yaxis_title="Price (USDT)",
                        hovermode='x unified',
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No OHLC data available for selected timeframe. Data is being processed...")
            
            with tab2:
                st.subheader("OHLC Candlestick Chart")
                if not ohlc_df.empty and len(ohlc_df) > 0:
                    fig = go.Figure(data=go.Candlestick(
                        x=ohlc_df['timestamp'],
                        open=ohlc_df['open'],
                        high=ohlc_df['high'],
                        low=ohlc_df['low'],
                        close=ohlc_df['close']
                    ))
                    fig.update_layout(
                        title=f"{selected_symbol.upper()} OHLC ({timeframe})",
                        xaxis_title="Time",
                        yaxis_title="Price (USDT)",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No OHLC data available for selected timeframe.")
            
            with tab3:
                st.subheader("Spread & Z-Score Analysis")
                
                if len(display_symbols) >= 2:
                    symbol2 = st.selectbox(
                        "Select Second Symbol for Spread",
                        [s for s in display_symbols if s != selected_symbol],
                        key="spread_symbol"
                    )
                    
                    # Get data for both symbols
                    ticks2 = st.session_state.db.get_ticks(
                        symbol=symbol2,
                        start_time=start_time,
                        end_time=end_time,
                        limit=10000
                    )
                    
                    # Get OHLC for both
                    ohlc2 = st.session_state.db.get_ohlc(
                        symbol=symbol2,
                        timeframe=timeframe,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if not ohlc_df.empty and not ohlc2.empty:
                        # Compute OLS regression
                        merged = pd.merge_asof(
                            ohlc_df[['timestamp', 'close']].sort_values('timestamp'),
                            ohlc2[['timestamp', 'close']].sort_values('timestamp'),
                            on='timestamp',
                            suffixes=('_1', '_2')
                        )
                        
                        if len(merged) > 10:
                            # OLS Regression
                            ols_result = engine.compute_ols_regression(
                                merged['close_1'], merged['close_2']
                            )
                            
                            if 'hedge_ratio' in ols_result:
                                st.metric("Hedge Ratio", f"{ols_result['hedge_ratio']:.4f}")
                                st.metric("R-squared", f"{ols_result.get('r_squared', 0):.4f}")
                                
                                # Compute spread
                                spread = engine.compute_spread(ohlc_df, ohlc2, hedge_ratio=ols_result['hedge_ratio'])
                                spread_series = pd.Series(spread.values, index=merged['timestamp'])
                                
                                # Z-score
                                zscore = engine.compute_zscore(spread_series, window=rolling_window)
                                
                                # Plot spread
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=merged['timestamp'],
                                    y=spread_series,
                                    mode='lines',
                                    name='Spread',
                                    line=dict(color='blue')
                                ))
                                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                                fig.update_layout(
                                    title="Spread",
                                    xaxis_title="Time",
                                    yaxis_title="Spread",
                                    height=300
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Plot z-score
                                fig2 = go.Figure()
                                fig2.add_trace(go.Scatter(
                                    x=merged['timestamp'],
                                    y=zscore,
                                    mode='lines',
                                    name='Z-Score',
                                    line=dict(color='red')
                                ))
                                fig2.add_hline(y=2, line_dash="dash", line_color="orange", annotation_text="Upper Threshold")
                                fig2.add_hline(y=-2, line_dash="dash", line_color="orange", annotation_text="Lower Threshold")
                                fig2.add_hline(y=0, line_dash="dash", line_color="gray")
                                fig2.update_layout(
                                    title="Z-Score",
                                    xaxis_title="Time",
                                    yaxis_title="Z-Score",
                                    height=300
                                )
                                st.plotly_chart(fig2, use_container_width=True)
                                
                                # Check alerts
                                if not zscore.empty:
                                    latest_zscore = zscore.iloc[-1]
                                    for alert in st.session_state.alerts:
                                        if alert['active'] and alert['symbol'] == selected_symbol:
                                            if alert['condition'] == "Z-Score >" and latest_zscore > alert['threshold']:
                                                st.error(f"🚨 ALERT: Z-Score {latest_zscore:.2f} > {alert['threshold']}")
                                            elif alert['condition'] == "Z-Score <" and latest_zscore < -alert['threshold']:
                                                st.error(f"🚨 ALERT: Z-Score {latest_zscore:.2f} < -{alert['threshold']}")
                    else:
                        st.info("Insufficient data for spread analysis. Need data for both symbols.")
                else:
                    st.info("Need at least 2 symbols for spread analysis.")
            
            with tab4:
                st.subheader("Rolling Correlation")
                
                if len(display_symbols) >= 2:
                    symbol2 = st.selectbox(
                        "Select Second Symbol",
                        [s for s in display_symbols if s != selected_symbol],
                        key="corr_symbol"
                    )
                    
                    ohlc2 = st.session_state.db.get_ohlc(
                        symbol=symbol2,
                        timeframe=timeframe,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if not ohlc_df.empty and not ohlc2.empty:
                        merged = pd.merge_asof(
                            ohlc_df[['timestamp', 'close']].sort_values('timestamp'),
                            ohlc2[['timestamp', 'close']].sort_values('timestamp'),
                            on='timestamp',
                            suffixes=('_1', '_2')
                        )
                        
                        if len(merged) > rolling_window:
                            corr = engine.compute_rolling_correlation(
                                merged['close_1'], merged['close_2'], window=rolling_window
                            )
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=merged['timestamp'],
                                y=corr,
                                mode='lines',
                                name='Correlation',
                                line=dict(color='green')
                            ))
                            fig.add_hline(y=0, line_dash="dash", line_color="gray")
                            fig.update_layout(
                                title=f"Rolling Correlation ({selected_symbol} vs {symbol2})",
                                xaxis_title="Time",
                                yaxis_title="Correlation",
                                height=400
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Need at least 2 symbols for correlation analysis.")
            
            with tab5:
                st.subheader("Statistics")
                
                if not ohlc_df.empty:
                    # Price stats
                    price_stats = engine.compute_price_stats(ohlc_df, price_col='close')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### Price Statistics")
                        for key, value in price_stats.items():
                            st.text(f"{key.capitalize()}: {value}")
                    
                    # ADF Test
                    if len(ohlc_df) > 10:
                        st.markdown("### ADF Test (Stationarity)")
                        adf_result = engine.compute_adf_test(ohlc_df['close'])
                        
                        if 'adf_statistic' in adf_result:
                            st.text(f"ADF Statistic: {adf_result['adf_statistic']:.4f}")
                            st.text(f"P-value: {adf_result['pvalue']:.4f}")
                            st.text(f"Stationary: {'Yes' if adf_result['is_stationary'] else 'No'}")
                            
                            st.markdown("### Critical Values")
                            for level, value in adf_result['critical_values'].items():
                                st.text(f"{level}: {value:.4f}")
            
            with tab6:
                st.subheader("Data Export")
                
                export_format = st.selectbox("Export Format", ["CSV", "JSON", "Excel"])
                
                if st.button("Export OHLC Data"):
                    if not ohlc_df.empty:
                        buffer = StringIO()
                        if export_format == "CSV":
                            csv = ohlc_df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name=f"{selected_symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        elif export_format == "JSON":
                            json_str = ohlc_df.to_json(orient='records', date_format='iso')
                            st.download_button(
                                label="Download JSON",
                                data=json_str,
                                file_name=f"{selected_symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                    else:
                        st.warning("No data to export")
                
                # OHLC Upload
                st.divider()
                st.subheader("Upload OHLC Data")
                uploaded_file = st.file_uploader("Choose a file", type=['csv', 'json'])
                
                if uploaded_file is not None:
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df = pd.read_csv(uploaded_file)
                        else:
                            df = pd.read_json(uploaded_file)
                        
                        if 'timestamp' in df.columns or 'time' in df.columns:
                            time_col = 'timestamp' if 'timestamp' in df.columns else 'time'
                            df[time_col] = pd.to_datetime(df[time_col])
                            
                            # Assume required columns
                            required_cols = ['open', 'high', 'low', 'close']
                            if all(col in df.columns for col in required_cols):
                                symbol_name = st.text_input("Symbol", value="uploaded")
                                tf = st.selectbox("Timeframe", ["1s", "1m", "5m"])
                                
                                if st.button("Import Data"):
                                    for _, row in df.iterrows():
                                        st.session_state.db.insert_ohlc(
                                            symbol=symbol_name,
                                            timestamp=row[time_col],
                                            timeframe=tf,
                                            open=row['open'],
                                            high=row['high'],
                                            low=row['low'],
                                            close=row['close'],
                                            volume=row.get('volume', 0)
                                        )
                                    st.success(f"Imported {len(df)} rows!")
                            else:
                                st.error("Missing required columns: open, high, low, close")
                        else:
                            st.error("Missing timestamp column")
                    except Exception as e:
                        st.error(f"Error uploading file: {e}")

# Background thread for collector (simplified for Streamlit)
def run_collector_async():
    """Run collector in background thread with new event loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        collector = BinanceCollector(symbols, st.session_state.db)
        loop.run_until_complete(collector.run())
    except Exception as e:
        logger.error(f"Collector error: {e}")

def run_processor_async():
    """Run processor in background thread with new event loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        processor = DataProcessor(st.session_state.db)
        loop.run_until_complete(processor.run())
    except Exception as e:
        logger.error(f"Processor error: {e}")

# Start background threads only once
if st.session_state.collector_running:
    if st.session_state.collector_thread is None or not st.session_state.collector_thread.is_alive():
        st.session_state.collector_thread = threading.Thread(target=run_collector_async, daemon=True)
        st.session_state.collector_thread.start()
        logger.info("Collector thread started")
    
    if st.session_state.processor_thread is None or not st.session_state.processor_thread.is_alive():
        st.session_state.processor_thread = threading.Thread(target=run_processor_async, daemon=True)
        st.session_state.processor_thread.start()
        logger.info("Processor thread started")

# Auto-refresh control
auto_refresh = st.checkbox("Auto-refresh (every 5s)", value=True)
if auto_refresh and st.session_state.collector_running:
    time.sleep(5)
    st.rerun()
