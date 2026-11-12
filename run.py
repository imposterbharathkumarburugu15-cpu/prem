import os
import uvicorn

if __name__ == "__main__":
    port_str = os.getenv("PORT", "10000")
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 10000

    print(f"[RUNNER] Starting PRAMAN Backend on 0.0.0.0:{port}...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
