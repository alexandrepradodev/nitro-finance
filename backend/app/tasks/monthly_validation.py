from datetime import date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import expense_validation_service


def _get_current_month_date() -> date:
    """Retorna o primeiro dia do mês atual no timezone configurado (APP_TIMEZONE)."""
    tz = ZoneInfo(settings.APP_TIMEZONE)
    today = datetime.now(tz).date()
    return today.replace(day=1)


def create_monthly_validations_task(month_date: date | None = None) -> dict:
    """
    Tarefa para criar validações mensais baseado na periodicidade das despesas.
    Se month_date não for fornecido, usa o primeiro dia do mês atual (APP_TIMEZONE).
    Também marca validações atrasadas do mês anterior.
    """
    if month_date is None:
        month_date = _get_current_month_date()
    else:
        # Garantir que é o primeiro dia do mês
        month_date = month_date.replace(day=1)
    
    db: Session = SessionLocal()
    try:
        # Criar validações para o mês especificado
        validations = expense_validation_service.create_monthly_validations(db, month_date)
        
        # Marcar validações atrasadas
        overdue_count = expense_validation_service.mark_overdue_validations(db)
        
        return {
            "success": True,
            "month": month_date.isoformat(),
            "validations_created": len(validations),
            "overdue_marked": overdue_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


def advance_renewal_dates_task() -> dict:
    """
    Avança renewal_date de despesas recorrentes ativas cuja data já passou
    para a próxima ocorrência (ex: anual 23/05/2025 -> 23/05/2026).
    """
    db: Session = SessionLocal()
    try:
        count = expense_validation_service.advance_renewal_dates(db)
        return {"success": True, "advanced": count}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()
