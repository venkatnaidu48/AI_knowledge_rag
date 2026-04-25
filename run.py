#!/usr/bin/env python
"""
Application startup script that reads environment variables and starts the server
"""
import uvicorn
import os

if __name__ == "__main__":
    host = os.getenv("API_HOST", "localhost")
    port = int(os.getenv("API_PORT", "8000"))
    app_module = os.getenv("APP_MODULE", "src.main:app")
    
    print(f"Starting RAG Application on http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"App module: {app_module}")
    
    uvicorn.run(
        app_module,
        host=host,
        port=port,
        log_level="info"
    )
