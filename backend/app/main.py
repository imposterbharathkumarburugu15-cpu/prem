from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.v1 import api_router
from backend.app.core.database import engine, Base
from backend.app.services.ai_dispatcher import ai_dispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP:
    # 1. Initialize tables if not already created
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database init during lifespan startup: {e}")

    # 2. Start asynchronous AI task dispatcher background worker
    ai_dispatcher.start()

    yield

    # SHUTDOWN:
    # Gracefully stop the AI task dispatcher
    await ai_dispatcher.stop(timeout_seconds=2.0)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Praman-Sequence"],
)

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve web_console static assets if present
web_console_static = Path(__file__).resolve().parent.parent.parent / "web_console" / "static"
if web_console_static.exists():
    app.mount("/static", StaticFiles(directory=str(web_console_static)), name="static")

web_console_template = Path(__file__).resolve().parent.parent.parent / "web_console" / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
def root_web():
    if web_console_template.exists():
        with open(web_console_template, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>PRAMAN Unified Platform Online</h2>")


@app.get("/verify/{opaque_token}", response_class=HTMLResponse)
def verify_qr_route(opaque_token: str):
    if web_console_template.exists():
        with open(web_console_template, "r", encoding="utf-8") as f:
            html = f.read()
            # Auto-switch to verify tab in script
            html = html.replace('loadTransporterData();', f'openCustomerVerify("{opaque_token}");')
            return HTMLResponse(content=html)
    return HTMLResponse("<h2>PRAMAN Customer QR Verification</h2>")


@app.get("/api/health")
def api_health():
    return {
        "project": "PRAMAN Evidence Intelligence Platform",
        "status": "ONLINE",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
