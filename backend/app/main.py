from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.endpoints import auth, users, companies

app = FastAPI(
    title="Nitro Finance API",
    description="Sistema de gestão de despesas e assinaturas corporativas",
    version="1.0.0",
)

# Registrar rotas
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")


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