#!/usr/bin/env python3
"""
Simple launcher script for the application.
Run: python run.py
"""

import subprocess
import sys

if __name__ == "__main__":
    print("Starting Binance Futures Analytics Dashboard...")
    print("Dashboard will open in your browser at http://localhost:8501")
    print("\nPress Ctrl+C to stop the application\n")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user.")
