import os
import gc
import uvicorn

# Restrict glibc memory arena allocation in Linux containers (Render Free Tier 512MB limit)
os.environ.setdefault("MALLOC_ARENA_MAX", "2")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

if __name__ == "__main__":
    port_str = os.getenv("PORT", "10000")
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 10000

    print(f"[RUNNER] Starting PRAMAN Backend on 0.0.0.0:{port} with low-memory profile (MALLOC_ARENA_MAX=2)...")
    gc.collect()

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        limit_concurrency=25,
        backlog=128,
        timeout_keep_alive=15,
    )
