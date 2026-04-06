from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from web.backend.routers import operations, users, reports

app = FastAPI(title="Fuel Tracker API")

# Настройки CORS для React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(operations.router)
app.include_router(users.router)
app.include_router(reports.router)

# Простой эндпоинт для проверки здоровья сервера
@app.get("/api/health")
def health_check():
    return {"status": "ok"}