import asyncio
import logging
import time
from datetime import datetime, date
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.v1.endpoints import auth, users, companies, departments, categories, expenses, expense_validations, alerts, dashboard

logger = logging.getLogger(__name__)

RENEWAL_CHECK_INTERVAL_SECONDS = 6 * 3600  # 6 horas
SCHEDULER_TICK_SECONDS = 60
VALIDATION_TRIGGER_SLOTS = {(0, 5), (6, 0), (12, 0)}
_last_validation_slot: tuple[date, int, int] | None = None
_last_alert_run_ts: float = 0.0


async def _background_scheduler():
    """Scheduler em background para validações mensais e alertas de renovação."""
    from app.tasks.alert_tasks import check_and_create_renewal_alerts_7_3_1
    from app.tasks.monthly_validation import (
        advance_renewal_dates_task,
        create_monthly_validations_task,
    )

    global _last_validation_slot, _last_alert_run_ts
    app_tz = ZoneInfo(settings.APP_TIMEZONE)

    while True:
        try:
            now = datetime.now(app_tz)

            # Dia 1: criar validações em horários de segurança
            if now.day == 1 and (now.hour, now.minute) in VALIDATION_TRIGGER_SLOTS:
                current_slot = (now.date(), now.hour, now.minute)
                if _last_validation_slot != current_slot:
                    result_validations = await asyncio.to_thread(create_monthly_validations_task)
                    logger.info("Validações mensais (scheduled): %s", result_validations)
                    if result_validations.get("success"):
                        _last_validation_slot = current_slot

            # Alertas de renovação: manter ciclo de 6 horas
            current_ts = time.time()
            if (current_ts - _last_alert_run_ts) >= RENEWAL_CHECK_INTERVAL_SECONDS:
                await asyncio.to_thread(advance_renewal_dates_task)
                logger.info("Iniciando verificação automática de alertas de renovação...")
                result = await asyncio.to_thread(check_and_create_renewal_alerts_7_3_1)
                logger.info("Verificação de renovação concluída: %s", result)
                _last_alert_run_ts = current_ts
        except Exception:
            logger.exception("Erro no scheduler de background")
        await asyncio.sleep(SCHEDULER_TICK_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia tarefas em background durante o ciclo de vida da aplicação."""
    from app.tasks.monthly_validation import create_monthly_validations_task

    # Catch-up no startup para garantir validações do mês atual.
    startup_result = await asyncio.to_thread(create_monthly_validations_task)
    logger.info("Validações mensais (startup catch-up): %s", startup_result)

    task = asyncio.create_task(_background_scheduler())
    logger.info("Scheduler de background iniciado")
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
    "https://subs.nitrofund.com.br",
    "https://subs.nitrofund.com.br/",
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