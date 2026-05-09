from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.users import router as users_router
from app.api.routes.wallet import router as wallet_router
from app.api.routes.billing import router as billing_router
from app.api.routes.ml_models import router as ml_models_router
from app.api.routes.predictions import router as predictions_router

app = FastAPI(title="Review classification ML service", version="0.1.0")

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

app.include_router(health_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(wallet_router, prefix="/wallet", tags=["wallet"])
app.include_router(billing_router, prefix="/billing", tags=["billing"])
app.include_router(ml_models_router, prefix="/models", tags=["models"])
app.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
