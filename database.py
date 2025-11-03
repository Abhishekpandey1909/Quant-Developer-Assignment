"""
Database module for storing tick data and aggregated OHLC data.
Uses SQLite for lightweight, file-based storage suitable for local development.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd
from sqlalchemy import create_engine, Table, Column, String, Float, DateTime, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()


class TickData(Base):
    """SQLAlchemy model for tick data."""
    __tablename__ = 'ticks'
    
    id = Column(String, primary_key=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    price = Column(Float)
    size = Column(Float)
    
    def __repr__(self):
        return f"<TickData(symbol={self.symbol}, timestamp={self.timestamp}, price={self.price})>"


class OHLCData(Base):
    """SQLAlchemy model for OHLC aggregated data."""
    __tablename__ = 'ohlc'
    
    id = Column(String, primary_key=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    timeframe = Column(String)  # '1s', '1m', '5m'
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    def __repr__(self):
        return f"<OHLCData(symbol={self.symbol}, timeframe={self.timeframe}, close={self.close})>"


class Database:
    """Database manager for tick and OHLC data storage."""
    
    def __init__(self, db_path: str = "data/trades.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def insert_tick(self, symbol: str, timestamp: datetime, price: float, size: float):
        """Insert a single tick."""
        try:
            tick_id = f"{symbol}_{timestamp.isoformat()}_{price}_{size}"
            tick = TickData(
                id=tick_id,
                symbol=symbol,
                timestamp=timestamp,
                price=price,
                size=size
            )
            self.session.merge(tick)  # Use merge to handle duplicates
            self.session.commit()
        except Exception as e:
            logger.error(f"Error inserting tick: {e}")
            self.session.rollback()
    
    def insert_ticks_batch(self, ticks: List[Dict]):
        """Insert multiple ticks in batch."""
        try:
            for tick_data in ticks:
                tick_id = f"{tick_data['symbol']}_{tick_data['timestamp'].isoformat()}_{tick_data['price']}_{tick_data['size']}"
                tick = TickData(
                    id=tick_id,
                    symbol=tick_data['symbol'],
                    timestamp=tick_data['timestamp'],
                    price=tick_data['price'],
                    size=tick_data['size']
                )
                self.session.merge(tick)
            self.session.commit()
        except Exception as e:
            logger.error(f"Error inserting batch: {e}")
            self.session.rollback()
    
    def insert_ohlc(self, symbol: str, timestamp: datetime, timeframe: str,
                   open: float, high: float, low: float, close: float, volume: float):
        """Insert OHLC aggregated data."""
        try:
            ohlc_id = f"{symbol}_{timeframe}_{timestamp.isoformat()}"
            ohlc = OHLCData(
                id=ohlc_id,
                symbol=symbol,
                timestamp=timestamp,
                timeframe=timeframe,
                open=open,
                high=high,
                low=low,
                close=close,
                volume=volume
            )
            self.session.merge(ohlc)
            self.session.commit()
        except Exception as e:
            logger.error(f"Error inserting OHLC: {e}")
            self.session.rollback()
    
    def get_ticks(self, symbol: Optional[str] = None, 
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  limit: Optional[int] = None) -> pd.DataFrame:
        """Retrieve ticks as DataFrame."""
        query = self.session.query(TickData)
        
        if symbol:
            query = query.filter(TickData.symbol == symbol)
        if start_time:
            query = query.filter(TickData.timestamp >= start_time)
        if end_time:
            query = query.filter(TickData.timestamp <= end_time)
        
        query = query.order_by(TickData.timestamp.desc())
        
        if limit:
            query = query.limit(limit)
        
        df = pd.read_sql(query.statement, self.engine)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        return df
    
    def get_ohlc(self, symbol: Optional[str] = None,
                 timeframe: Optional[str] = None,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None) -> pd.DataFrame:
        """Retrieve OHLC data as DataFrame."""
        query = self.session.query(OHLCData)
        
        if symbol:
            query = query.filter(OHLCData.symbol == symbol)
        if timeframe:
            query = query.filter(OHLCData.timeframe == timeframe)
        if start_time:
            query = query.filter(OHLCData.timestamp >= start_time)
        if end_time:
            query = query.filter(OHLCData.timestamp <= end_time)
        
        query = query.order_by(OHLCData.timestamp)
        
        df = pd.read_sql(query.statement, self.engine)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def get_symbols(self) -> List[str]:
        """Get list of all unique symbols."""
        result = self.session.query(TickData.symbol).distinct().all()
        return [r[0] for r in result]
    
    def close(self):
        """Close database connection."""
        self.session.close()
