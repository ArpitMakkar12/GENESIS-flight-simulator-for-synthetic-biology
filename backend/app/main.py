import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import simulate, constructs, parts, knowledge, results, export, knockout


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: warm the SAME runner the /simulate endpoint uses, so the first
    # request doesn't pay for model loading (~4-5 s otherwise).
    print("GENESIS API starting up...")
    try:
        import time
        t0 = time.perf_counter()
        runner = simulate.get_runner()          # the shared singleton

        # 1. AI predictor (gene table + regulator sets)
        predictor = runner._get_predictor()
        status = predictor.load_models(include_hyenadna=True)

        # 2. iML1515 + gene rules for the bound compiler
        runner.fba_solver.load_model()
        runner.bound_compiler._load_data()      # kinetics + gene->reaction map
        runner.bound_compiler.set_gpr_rules(
            {r.id: r.gene_reaction_rule for r in runner.fba_solver.model.reactions}
        )

        # 3. One throwaway solve so the LP solver is initialised too
        runner.fba_solver.solve(bounds=[], exchange_constraints={})

        print(f"  Warm-up done in {time.perf_counter() - t0:.1f} s: "
            f"{status.get('genes', 0)} genes, "
            f"{len(runner.fba_solver.model.reactions)} reactions, "
            f"expression model {'loaded' if status.get('expression') else 'MISSING'}, "
            f"HyenaDNA {'loaded' if status.get('hyenadna') else 'MISSING'}")
    except Exception as e:
        print(f"  Warm-up failed (non-fatal, first request will be slow): {e}")
    yield
    # Shutdown: cleanup resources
    print("GENESIS API shutting down...")


app = FastAPI(
    title="GENESIS API",
    description="AI-powered E. coli simulation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def time_requests(request: Request, call_next):
    """How long the server worked on each request.

    Printed to the log, and sent as a Server-Timing header, which the
    browser shows in DevTools (Network tab -> click a request -> Timing),
    next to the time spent on the network.
    """
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    response.headers["Server-Timing"] = f"app;dur={ms:.0f}"
    response.headers["Timing-Allow-Origin"] = "*"   # let the frontend's origin see it
    if request.method != "OPTIONS" and request.url.path != "/health":
        print(f"  {request.method} {request.url.path} -> {response.status_code} in {ms:.0f} ms", flush=True)
    return response

# Register routers
app.include_router(simulate.router, prefix="/api/v1", tags=["Simulation"])
app.include_router(constructs.router, prefix="/api/v1", tags=["Constructs"])
app.include_router(parts.router, prefix="/api/v1", tags=["Parts"])
app.include_router(knowledge.router, prefix="/api/v1", tags=["Knowledge"])
app.include_router(results.router, prefix="/api/v1", tags=["Results"])
app.include_router(export.router, prefix="/api/v1", tags=["Export"])
app.include_router(knockout.router, prefix="/api/v1", tags=["Knockout"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "genesis-api"}
