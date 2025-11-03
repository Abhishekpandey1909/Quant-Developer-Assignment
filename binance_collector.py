#!/usr/bin/env python3
"""
Binance Futures Trade Data Collector
Collects real-time trade data from Binance Futures WebSocket streams
and saves it as NDJSON (newline-delimited JSON) format.
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import List
import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI


class BinanceCollector:
    """Collects trade data from Binance Futures WebSocket streams."""
    
    BASE_WS_URL = "wss://fstream.binance.com/ws"
    MAX_RECONNECT_DELAY = 60
    INITIAL_RECONNECT_DELAY = 1
    
    def __init__(self, symbols: List[str], output_dir: str = "data"):
        """
        Initialize the collector.
        
        Args:
            symbols: List of trading symbols (e.g., ['btcusdt', 'ethusdt'])
            output_dir: Directory to save NDJSON files
        """
        self.symbols = [s.lower().strip() for s in symbols if s.strip()]
        if not self.symbols:
            raise ValueError("At least one symbol must be provided")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.buffer = []
        self.running = False
        self.reconnect_delays = {symbol: self.INITIAL_RECONNECT_DELAY for symbol in self.symbols}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('collector.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def normalize(self, data: dict) -> dict:
        """
        Normalize Binance trade data to a consistent format.
        
        Args:
            data: Raw WebSocket message data
            
        Returns:
            Normalized trade data
        """
        # Handle both event format (e) and direct format
        timestamp = data.get('T') or data.get('E') or data.get('t')
        if timestamp:
            ts = datetime.fromtimestamp(timestamp / 1000).isoformat()
        else:
            ts = datetime.utcnow().isoformat()
            
        return {
            'symbol': data.get('s', '').lower(),
            'ts': ts,
            'price': float(data.get('p', 0)),
            'size': float(data.get('q', 0))
        }
    
    async def handle_trade(self, symbol: str, message: str):
        """
        Handle incoming trade message.
        
        Args:
            symbol: Trading symbol
            message: Raw WebSocket message
        """
        try:
            data = json.loads(message)
            
            # Only process trade events
            if data.get('e') == 'trade':
                normalized = self.normalize(data)
                self.buffer.append(normalized)
                self.logger.debug(f"Received trade for {symbol}: {normalized}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON for {symbol}: {e}")
        except Exception as e:
            self.logger.error(f"Error handling trade for {symbol}: {e}")
    
    async def connect_symbol(self, symbol: str):
        """
        Connect to WebSocket stream for a symbol with auto-reconnect.
        
        Args:
            symbol: Trading symbol
        """
        url = f"{self.BASE_WS_URL}/{symbol}@trade"
        
        while self.running:
            try:
                self.logger.info(f"Connecting to {symbol} stream...")
                async with websockets.connect(url) as ws:
                    self.logger.info(f"Connected to {symbol} stream")
                    self.reconnect_delays[symbol] = self.INITIAL_RECONNECT_DELAY
                    
                    async for message in ws:
                        if not self.running:
                            break
                        await self.handle_trade(symbol, message)
                        
            except ConnectionClosed:
                self.logger.warning(f"Connection closed for {symbol}, reconnecting...")
            except InvalidURI as e:
                self.logger.error(f"Invalid URI for {symbol}: {e}")
                break
            except Exception as e:
                self.logger.error(f"Error in connection for {symbol}: {e}")
            
            if self.running:
                # Exponential backoff for reconnection
                delay = self.reconnect_delays[symbol]
                self.logger.info(f"Reconnecting {symbol} in {delay} seconds...")
                await asyncio.sleep(delay)
                self.reconnect_delays[symbol] = min(
                    delay * 2, 
                    self.MAX_RECONNECT_DELAY
                )
    
    async def save_buffer(self):
        """Periodically save buffered data to NDJSON file."""
        while self.running:
            await asyncio.sleep(5)  # Save every 5 seconds
            
            if not self.buffer:
                continue
            
            try:
                # Create filename with timestamp
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = self.output_dir / f"trades_{timestamp}.ndjson"
                
                # Write all buffered data
                with open(filename, 'a') as f:
                    for item in self.buffer:
                        f.write(json.dumps(item) + '\n')
                
                self.logger.info(f"Saved {len(self.buffer)} trades to {filename}")
                self.buffer.clear()
                
            except Exception as e:
                self.logger.error(f"Error saving buffer: {e}")
    
    async def run(self):
        """Run the collector."""
        self.running = True
        self.logger.info(f"Starting collector for symbols: {', '.join(self.symbols)}")
        
        # Start connection tasks for each symbol
        tasks = [
            asyncio.create_task(self.connect_symbol(symbol))
            for symbol in self.symbols
        ]
        
        # Start buffer saving task
        save_task = asyncio.create_task(self.save_buffer())
        
        try:
            # Wait for all tasks
            await asyncio.gather(*tasks, save_task)
        except Exception as e:
            self.logger.error(f"Error in collector: {e}")
        finally:
            # Final save of remaining buffer
            if self.buffer:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = self.output_dir / f"trades_{timestamp}.ndjson"
                with open(filename, 'a') as f:
                    for item in self.buffer:
                        f.write(json.dumps(item) + '\n')
                self.logger.info(f"Final save: {len(self.buffer)} trades to {filename}")
            
            self.logger.info("Collector stopped")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Binance Futures Trade Data Collector"
    )
    parser.add_argument(
        'symbols',
        nargs='+',
        help='Trading symbols (e.g., btcusdt ethusdt)'
    )
    parser.add_argument(
        '-o', '--output',
        default='data',
        help='Output directory for NDJSON files (default: data)'
    )
    
    args = parser.parse_args()
    
    collector = BinanceCollector(args.symbols, args.output)
    
    try:
        await collector.run()
    except KeyboardInterrupt:
        collector.logger.info("Interrupted by user")
    except Exception as e:
        collector.logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
