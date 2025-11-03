#!/usr/bin/env python3
"""
Enhanced Binance Futures Trade Data Collector with database storage.
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import List
import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI

from database import Database

logger = logging.getLogger(__name__)


class BinanceCollector:
    """Collects trade data from Binance Futures WebSocket streams."""
    
    BASE_WS_URL = "wss://fstream.binance.com/ws"
    MAX_RECONNECT_DELAY = 60
    INITIAL_RECONNECT_DELAY = 1
    
    def __init__(self, symbols: List[str], db: Database):
        """
        Initialize the collector.
        
        Args:
            symbols: List of trading symbols (e.g., ['btcusdt', 'ethusdt'])
            db: Database instance for storage
        """
        self.symbols = [s.lower().strip() for s in symbols if s.strip()]
        if not self.symbols:
            raise ValueError("At least one symbol must be provided")
        
        self.db = db
        self.running = False
        self.buffer = []
        self.reconnect_delays = {symbol: self.INITIAL_RECONNECT_DELAY for symbol in self.symbols}
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def normalize(self, data: dict) -> dict:
        """Normalize Binance trade data to a consistent format."""
        timestamp = data.get('T') or data.get('E') or data.get('t')
        if timestamp:
            ts = datetime.fromtimestamp(timestamp / 1000)
        else:
            ts = datetime.utcnow()
            
        return {
            'symbol': data.get('s', '').lower(),
            'timestamp': ts,
            'price': float(data.get('p', 0)),
            'size': float(data.get('q', 0))
        }
    
    async def handle_trade(self, symbol: str, message: str):
        """Handle incoming trade message."""
        try:
            data = json.loads(message)
            
            if data.get('e') == 'trade':
                normalized = self.normalize(data)
                self.buffer.append(normalized)
                logger.debug(f"Received trade for {symbol}: {normalized}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {symbol}: {e}")
        except Exception as e:
            logger.error(f"Error handling trade for {symbol}: {e}")
    
    async def connect_symbol(self, symbol: str):
        """Connect to WebSocket stream for a symbol with auto-reconnect."""
        url = f"{self.BASE_WS_URL}/{symbol}@trade"
        
        while self.running:
            try:
                logger.info(f"Connecting to {symbol} stream...")
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to {symbol} stream")
                    self.reconnect_delays[symbol] = self.INITIAL_RECONNECT_DELAY
                    
                    async for message in ws:
                        if not self.running:
                            break
                        await self.handle_trade(symbol, message)
                        
            except ConnectionClosed:
                logger.warning(f"Connection closed for {symbol}, reconnecting...")
            except InvalidURI as e:
                logger.error(f"Invalid URI for {symbol}: {e}")
                break
            except Exception as e:
                logger.error(f"Error in connection for {symbol}: {e}")
            
            if self.running:
                delay = self.reconnect_delays[symbol]
                logger.info(f"Reconnecting {symbol} in {delay} seconds...")
                await asyncio.sleep(delay)
                self.reconnect_delays[symbol] = min(
                    delay * 2, 
                    self.MAX_RECONNECT_DELAY
                )
    
    async def save_buffer(self):
        """Periodically save buffered data to database."""
        while self.running:
            await asyncio.sleep(2)  # Save every 2 seconds
            
            if not self.buffer:
                continue
            
            try:
                # Save to database
                self.db.insert_ticks_batch(self.buffer)
                logger.debug(f"Saved {len(self.buffer)} trades to database")
                self.buffer.clear()
                
            except Exception as e:
                logger.error(f"Error saving buffer: {e}")
    
    async def run(self):
        """Run the collector."""
        self.running = True
        logger.info(f"Starting collector for symbols: {', '.join(self.symbols)}")
        
        tasks = [
            asyncio.create_task(self.connect_symbol(symbol))
            for symbol in self.symbols
        ]
        
        save_task = asyncio.create_task(self.save_buffer())
        
        try:
            await asyncio.gather(*tasks, save_task)
        except Exception as e:
            logger.error(f"Error in collector: {e}")
        finally:
            # Final save
            if self.buffer:
                self.db.insert_ticks_batch(self.buffer)
                logger.info(f"Final save: {len(self.buffer)} trades")
            
            logger.info("Collector stopped")
