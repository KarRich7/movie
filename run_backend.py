"""
Launcher script for FastAPI Movie Catalog Backend.
Usage: python run_backend.py
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("🎬 Starting Movie Catalog Backend on http://127.0.0.1:8000 ...")
    print("📖 Interactive Swagger Documentation: PJ0YOQVH52JS55FD27A4B43E")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
