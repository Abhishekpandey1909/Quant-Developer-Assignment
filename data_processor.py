"""
Data processor for resampling tick data to OHLC and computing aggregations.
Runs in background to continuously process incoming data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
import pandas as pd

from database import Database
from analytics import AnalyticsEngine

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes tick data into OHLC aggregations."""
    
    def __init__(self, db: Database, timeframes: List[str] = ['1s', '1m', '5m']):
        """
        Initialize data processor.
        
        Args:
            db: Database instance
            timeframes: List of timeframes to aggregate ('1s', '1m', '5m')
        """
        self.db = db
        self.timeframes = timeframes
        self.engine = AnalyticsEngine()
        self.running = False
        
    async def process_timeframe(self, timeframe: str):
        """Process a specific timeframe."""
        while self.running:
            try:
                # Get symbols
                symbols = self.db.get_symbols()
                
                for symbol in symbols:
                    # Get recent ticks not yet aggregated for this timeframe
                    # Simple approach: get last hour of data and resample
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=1)
                    
                    ticks = self.db.get_ticks(symbol=symbol, start_time=start_time, end_time=end_time)
                    
                    if ticks.empty:
                        continue
                    
                    # Resample to OHLC
                    ohlc_df = self.engine.resample_data(ticks, timeframe)
                    
                    # Save OHLC data
                    for _, row in ohlc_df.iterrows():
                        self.db.insert_ohlc(
                            symbol=symbol,
                            timestamp=row['timestamp'],
                            timeframe=timeframe,
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row.get('volume', 0)
                        )
                    
                    logger.debug(f"Processed {len(ohlc_df)} {timeframe} bars for {symbol}")
                
                # Wait based on timeframe before next processing
                wait_seconds = {
                    '1s': 1,
                    '1m': 60,
                    '5m': 300
                }.get(timeframe, 60)
                
                await asyncio.sleep(wait_seconds)
                
            except Exception as e:
                logger.error(f"Error processing {timeframe}: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Run the processor."""
        self.running = True
        logger.info(f"Starting data processor for timeframes: {', '.join(self.timeframes)}")
        
        tasks = [
            asyncio.create_task(self.process_timeframe(tf))
            for tf in self.timeframes
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in processor: {e}")
        finally:
            logger.info("Data processor stopped")
