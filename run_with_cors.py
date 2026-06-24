"""
run_with_cors.py
────────────────────────────────────────────────────────────
Starts the ResumeMate AI backend with CORS enabled so the
frontend (served from http://localhost:5500) can talk to it.

Usage:
    python run_with_cors.py

This does NOT modify main.py – it imports the app and wraps it.
"""
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi.middleware.cors import CORSMiddleware
from main import app
import uvicorn

# ── Add CORS middleware (frontend <-> backend) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # change to ["http://localhost:5500"] for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Metadata", "Content-Disposition"],
)

if __name__ == "__main__":
    print("\n🚀  ResumeMate AI backend  →  http://localhost:8000")
    print("🌐  Open frontend         →  http://localhost:5500")
    print("📖  API docs              →  http://localhost:8000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
