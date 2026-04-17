#!/usr/bin/env python
"""
Application startup script that reads environment variables and starts the server
"""
import uvicorn
import os

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "3000"))
    app_module = os.getenv("APP_MODULE", "src.main_enhanced:app")
    
    print(f"Starting RAG Application on {host}:{port}")
    print(f"App module: {app_module}")
    
    uvicorn.run(
        app_module,
        host=host,
        port=port,
        log_level="info"
    )
