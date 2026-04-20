#!/usr/bin/env python
"""
Entry point for AI Benchmarking application.
Run with: python run.py
"""
import os
import time
import threading
import webbrowser
from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Open browser automatically when app starts
    def open_browser():
        time.sleep(2)  # Give Flask time to start
        webbrowser.open('http://127.0.0.1:5000/')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     AI Benchmarking Application - Starting                 ║
    ║     Server: http://127.0.0.1:5000                          ║
    ║     Press Ctrl+C to stop                                   ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    app.run(debug=False, port=5000)
