import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.v1.endpoints import auth, users, companies, departments, categories, expenses, expense_validations, alerts, dashboard

logger = logging.getLogger(__name__)

RENEWAL_CHECK_INTERVAL_SECONDS = 6 * 3600  # 6 horas


async def _renewal_alert_loop():
    """Loop em background que verifica alertas de renovação a cada 6 horas."""
    from app.tasks.alert_tasks import check_and_create_renewal_alerts_7_3_1

    while True:
        try:
            logger.info("Iniciando verificação automática de alertas de renovação...")
            result = await asyncio.to_thread(check_and_create_renewal_alerts_7_3_1)
            logger.info("Verificação de renovação concluída: %s", result)
        except Exception:
            logger.exception("Erro na verificação automática de alertas de renovação")
        await asyncio.sleep(RENEWAL_CHECK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia tarefas em background durante o ciclo de vida da aplicação."""
    task = asyncio.create_task(_renewal_alert_loop())
    logger.info("Scheduler de alertas de renovação iniciado (intervalo: %ds)", RENEWAL_CHECK_INTERVAL_SECONDS)
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Scheduler de alertas de renovação encerrado")


app = FastAPI(
    title="Nitro Finance API",
    description="Sistema de gestão de despesas e assinaturas corporativas",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: dev (localhost) + origens de produção (CORS_ORIGINS)
_origins = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]
if settings.CORS_ORIGINS:
    _origins.extend(o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(expense_validations.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Nitro Finance API", "status": "online"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}