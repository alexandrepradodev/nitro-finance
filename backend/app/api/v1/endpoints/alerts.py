from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.permissions import _role_value as role_value
from app.models.user import User, UserRole
from app.models.alert import AlertStatus
from app.schemas.alert import AlertResponse, AlertWithRelationsResponse, AlertStatsResponse
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Apenas admins podem ver todas validações
admin_only = require_roles([UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN])


@router.get("/me", response_model=list[AlertWithRelationsResponse])
def get_my_alerts(
    status_filter: AlertStatus | None = Query(None, alias="status", description="Filtrar por status"),
    limit: int = Query(50, le=100, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista alertas do usuário logado.
    """
    from app.models.alert import Alert
    from sqlalchemy.orm import joinedload
    
    query = db.query(Alert).options(
        joinedload(Alert.recipient),
        joinedload(Alert.expense)
    ).filter(Alert.recipient_id == current_user.id)
    
    if status_filter:
        query = query.filter(Alert.status == status_filter)
    
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    return alerts


@router.get("", response_model=list[AlertWithRelationsResponse])
def list_alerts(
    recipient_id: UUID | None = Query(None, description="Filtrar por destinatário"),
    status_filter: AlertStatus | None = Query(None, alias="status", description="Filtrar por status"),
    limit: int = Query(50, le=100, description="Limite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Lista todos os alertas (apenas admins).
    """
    from app.models.alert import Alert
    from sqlalchemy.orm import joinedload
    
    query = db.query(Alert).options(
        joinedload(Alert.recipient),
        joinedload(Alert.expense)
    )
    
    if recipient_id:
        query = query.filter(Alert.recipient_id == recipient_id)
    
    if status_filter:
        query = query.filter(Alert.status == status_filter)
    
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    return alerts


@router.get("/{alert_id}", response_model=AlertWithRelationsResponse)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca alerta específico"""
    from app.models.alert import Alert
    from sqlalchemy.orm import joinedload
    
    alert = db.query(Alert).options(
        joinedload(Alert.recipient),
        joinedload(Alert.expense)
    ).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta não encontrado"
        )
    
    # Verificar permissão (usuário só vê seus próprios alertas, exceto admins)
    if current_user.role not in [UserRole.FINANCE_ADMIN, UserRole.SYSTEM_ADMIN]:
        if alert.recipient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a este alerta"
            )
    
    return alert


@router.post("/{alert_id}/read", response_model=AlertResponse)
def mark_alert_as_read(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marca alerta como lido"""
    from app.models.alert import Alert
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta não encontrado"
        )
    
    # Verificar permissão
    if role_value(current_user.role) not in (UserRole.FINANCE_ADMIN.value, UserRole.SYSTEM_ADMIN.value):
        if alert.recipient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a este alerta"
            )
    
    try:
        alert = alert_service.mark_as_read(db, alert_id)
        return alert
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/process-pending", response_model=dict)
def process_pending_alerts(
    limit: int = Query(50, le=100, description="Limite de alertas a processar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Processa alertas pendentes e tenta enviá-los.
    Apenas admins podem executar.
    """
    stats = alert_service.process_pending_alerts(db, limit)
    return stats


@router.post("/check-renewals", status_code=status.HTTP_201_CREATED)
def check_renewal_alerts(
    days_ahead: int = Query(7, ge=1, le=30, description="Dias antes da renovação para criar alerta"),
    current_user: User = Depends(admin_only)
):
    """
    Verifica despesas com renovação próxima e cria alertas.
    Apenas admins podem executar.
    """
    from app.tasks.alert_tasks import check_and_create_renewal_alerts
    
    result = check_and_create_renewal_alerts(days_ahead=days_ahead)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Erro ao verificar renovações")
        )
    
    return result


@router.get("/stats/summary", response_model=AlertStatsResponse)
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Retorna estatísticas de alertas.
    Apenas admins podem acessar.
    """
    from app.models.alert import Alert
    from sqlalchemy import func
    
    total = db.query(func.count(Alert.id)).scalar() or 0
    pending = db.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.PENDING).scalar() or 0
    sent = db.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.SENT).scalar() or 0
    failed = db.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.FAILED).scalar() or 0
    read = db.query(func.count(Alert.id)).filter(Alert.status == AlertStatus.READ).scalar() or 0
    
    return AlertStatsResponse(
        total=total,
        pending=pending,
        sent=sent,
        failed=failed,
        read=read
    )
