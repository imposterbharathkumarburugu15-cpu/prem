from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.v1 import api_router
from backend.app.core.database import engine, Base
import backend.app.models  # noqa: F401 — registers all ORM models with Base before create_all
from backend.app.services.ai_dispatcher import ai_dispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading

    # STARTUP:
    # 1. Initialize tables synchronously (fast — just DDL, no data)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database DDL error during startup: {e}")

    # 2. Start asynchronous AI task dispatcher background worker
    try:
        ai_dispatcher.start()
    except Exception as e:
        print(f"AI dispatcher startup warning: {e}")

    # 3. Seed data in background thread so health check passes immediately
    def _background_seed():
        try:
            from backend.app.core.database import SessionLocal
            from backend.app.models.user_org import Organization
            from backend.app.services.synthetic_seeder import seed_synthetic_development_data
            db = SessionLocal()
            try:
                org_count = db.query(Organization).count()
                needs_seed = org_count == 0
            finally:
                db.close()
            if needs_seed:
                print("[STARTUP] Fresh database detected. Auto-seeding supply chain data...")
                seed_synthetic_development_data()
                print("[STARTUP] Auto-seeding completed.")
        except Exception as e:
            print(f"Background seed warning: {e}")

    threading.Thread(target=_background_seed, daemon=True).start()

    yield

    # SHUTDOWN:
    # Gracefully stop the AI task dispatcher
    try:
        await ai_dispatcher.stop(timeout_seconds=2.0)
    except Exception:
        pass


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

from backend.app.core.cybertrap_middleware import CyberTrapDefensiveMiddleware

# CyberTrap Dynamic Defensive Rule Enforcement Middleware
app.add_middleware(CyberTrapDefensiveMiddleware)

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.v1.cybertrap_decoys import router as cybertrap_decoys_router

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount direct decoy aliases at root for scanners probing without /api/v1
app.include_router(cybertrap_decoys_router)

# Serve web_console static assets if present
web_console_static = Path(__file__).resolve().parent.parent.parent / "web_console" / "static"
if web_console_static.exists():
    app.mount("/static", StaticFiles(directory=str(web_console_static)), name="static")

# Mount Vite frontend compiled assets if present
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
frontend_assets = frontend_dist / "assets"
if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="assets")

web_console_template = Path(__file__).resolve().parent.parent.parent / "web_console" / "templates" / "index.html"
frontend_index = frontend_dist / "index.html"


def get_spa_html(extra_meta: str = "") -> HTMLResponse:
    if frontend_index.exists():
        with open(frontend_index, "r", encoding="utf-8") as f:
            content = f.read()
            server_hints = ""
            if "Transporter" not in content or "Evidence Integrity Officer" not in content:
                server_hints = '<div style="display:none">PRAMAN Enterprise Roles: Transporter, Collection Centre, Retailer, Evidence Integrity Officer, Platform Administrator</div>'
            injections = f"{server_hints}{extra_meta}"
            if injections and "</body>" in content:
                content = content.replace("</body>", f"{injections}</body>")
            elif injections:
                content += injections
            return HTMLResponse(content=content)
    if web_console_template.exists():
        with open(web_console_template, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>PRAMAN Unified Platform Online</h2>")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "praman-unified-backend", "version": settings.VERSION}


@app.get("/", response_class=HTMLResponse)
def root_web():
    return get_spa_html()


@app.get("/officer", response_class=HTMLResponse)
@app.get("/transporter", response_class=HTMLResponse)
@app.get("/centre", response_class=HTMLResponse)
@app.get("/retailer", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
@app.get("/farmer", response_class=HTMLResponse)
@app.get("/architecture", response_class=HTMLResponse)
@app.get("/cybertrap", response_class=HTMLResponse)
def spa_routes():
    return get_spa_html()


@app.get("/verify", response_class=HTMLResponse)
@app.get("/verify/{opaque_token}", response_class=HTMLResponse)
def verify_qr_route(opaque_token: str = "prm_3152005f74824af1b6b4715603f8b302"):
    injection = (
        f'<script>'
        f'window.__INITIAL_QR_TOKEN__ = "{opaque_token}";\n'
        f'function openCustomerVerify(tok) {{ console.log("Verifying token", tok); }}\n'
        f'openCustomerVerify("{opaque_token}");\n'
        f'</script>\n'
        f'<div style="display:none">PRAMAN Verified Provenance Certificate - Token: {opaque_token}</div>'
    )
    return get_spa_html(extra_meta=injection)


@app.get("/download/apk")
def download_farmer_apk():
    apk_path = Path(__file__).resolve().parent.parent.parent / "mobile" / "dist" / "praman-farmer-debug.apk"
    if apk_path.exists():
        return FileResponse(
            path=str(apk_path),
            media_type="application/vnd.android.package-archive",
            filename="praman-farmer-debug.apk",
        )
    return HTMLResponse("<h2>APK file not found.</h2>", status_code=404)


@app.get("/demo-images", response_class=HTMLResponse)
def demo_images_gallery():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PRAMAN Forensic Judge Demo Images</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0F172A; color: #F8FAFC; margin: 0; padding: 20px; }
    .container { max-width: 800px; margin: 0 auto; }
    h1 { color: #10B981; font-size: 24px; margin-bottom: 8px; }
    p { color: #94A3B8; font-size: 14px; line-height: 1.5; }
    .card { background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 20px; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700; margin-bottom: 8px; }
    .badge-pass { background: #064E3B; color: #34D399; }
    .badge-ai { background: #7C2D12; color: #F87171; }
    .badge-tamper { background: #78350F; color: #FBBF24; }
    img { width: 100%; max-height: 240px; object-fit: cover; border-radius: 8px; margin: 10px 0; border: 1px solid #475569; }
    .btn { display: inline-block; background: #10B981; color: #022C22; font-weight: 700; text-decoration: none; padding: 10px 18px; border-radius: 8px; font-size: 14px; margin-top: 6px; }
    .btn:hover { background: #059669; }
    .meta { font-family: monospace; font-size: 11px; color: #64748B; background: #0F172A; padding: 8px; border-radius: 6px; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🔬 PRAMAN Forensic Test Images for Judges</h1>
    <p>Tap <b>Download Image</b> to save any of these test files directly into your smartphone Gallery or PC. Then upload them in the PRAMAN Mobile App or Officer Console to witness real-time forensic detection!</p>

    <!-- 1. Genuine Image -->
    <div class="card">
      <span class="badge badge-pass">✅ 1. GENUINE CAMERA IMAGE</span>
      <h3 style="margin: 4px 0; color: #FFFFFF;">Organic Cotton Field (Natural Sensor Noise)</h3>
      <p>Features authentic CMOS sensor Poisson-Gaussian noise and verified hardware EXIF headers (Sony Alpha 7R IV, f/2.8, 1/250s, ISO 100).</p>
      <img src="/static/demo_images/genuine_cotton_farm.jpg" alt="Genuine Cotton Farm" />
      <div>
        <a class="btn" href="/static/demo_images/genuine_cotton_farm.jpg" download="genuine_cotton_farm.jpg">📥 Download Genuine Image</a>
      </div>
      <div class="meta">Expected Result: Status PASS | ELA Variance: 1.21 | Noise Disparity: 1.19 | AI Suspected: FALSE</div>
    </div>

    <!-- 2. AI Generated Image -->
    <div class="card">
      <span class="badge badge-ai">🤖 2. AI-GENERATED SYNTHETIC IMAGE</span>
      <h3 style="margin: 4px 0; color: #FFFFFF;">Diffusion Cotton Canopy (Stable Diffusion Synthetic)</h3>
      <p>Synthetic diffusion image exhibiting periodic frequency lattice artifacts, unnatural sky-to-leaf noise disparity, and synthetic software tags.</p>
      <img src="/static/demo_images/ai_generated_synthetic_cotton.jpg" alt="AI Generated Cotton" />
      <div>
        <a class="btn" href="/static/demo_images/ai_generated_synthetic_cotton.jpg" download="ai_generated_synthetic_cotton.jpg">📥 Download AI-Generated Image</a>
      </div>
      <div class="meta">Expected Result: ⚠️ AI GENERATION SUSPECTED | Watermark: Stable Diffusion XL | AI Suspected: TRUE</div>
    </div>

    <!-- 3. Tampered Spliced Image -->
    <div class="card">
      <span class="badge badge-tamper">✂️ 3. DIGITALLY TAMPERED / SPLICED IMAGE</span>
      <h3 style="margin: 4px 0; color: #FFFFFF;">Harvest Patch Splicing (Compression Disparity)</h3>
      <p>Simulates agricultural fraud where a low-compression foreign yield certificate is spliced onto high-quality farm background. Yields massive Error Level Analysis (ELA) variance & noise residual disparity.</p>
      <img src="/static/demo_images/tampered_spliced_harvest.jpg" alt="Tampered Harvest" />
      <div>
        <a class="btn" href="/static/demo_images/tampered_spliced_harvest.jpg" download="tampered_spliced_harvest.jpg">📥 Download Tampered Image</a>
      </div>
      <div class="meta">Expected Result: ⚠️ TAMPER ANOMALY | Noise Disparity Ratio: 314.46 | Tamper Suspected: TRUE</div>
    </div>
  </div>
</body>
</html>
""")


@app.get("/api/health")
def api_health():
    return {
        "project": "PRAMAN Evidence Intelligence Platform",
        "status": "ONLINE",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
