from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Retorna o usuário logado a partir do token JWT (com companies para escopo)."""
    
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )
    
    user_id = payload.get("sub")
    user = db.query(User).options(
        joinedload(User.departments),
        joinedload(User.companies),
    ).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    
    return user


def _role_value(role) -> str:
    """Normaliza role para string (enum ou string do DB)."""
    return role.value if hasattr(role, "value") else str(role)


def require_roles(allowed_roles: list[UserRole]):
    """Verifica se o usuário tem uma das roles permitidas"""
    allowed_values = {_role_value(r) for r in allowed_roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if _role_value(current_user.role) not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso"
            )
        return current_user

    return role_checker