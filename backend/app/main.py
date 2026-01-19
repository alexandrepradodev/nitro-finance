from fastapi import FastAPI

app = FastAPI(
    title="Nitro Finance API",
    description="Sistema de gstão de despesas e assinaturas corporativas",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Nitro Finance API", "status": "online"}

@app.get("/health")
def health_check():
    return {"status": "Health"}