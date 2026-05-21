"""
AgentForge 后端入口

FastAPI 应用主入口，包含生命周期管理和路由注册。
"""
import sys
import os
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent_forge.api.routes import tasks_router, agents_router, auth_router, metrics_router, keys_router
from agent_forge.config.settings import settings
from agent_forge.core.error_handler import AppException
from agent_forge.database.connection import init_db, close_db
from agent_forge.utils.logging import setup_logging, get_logger


setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 — 初始化数据库，关闭时清理连接"""
    logger.info(f"🚀 {settings.APP_NAME} 正在启动...")
    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        if settings.ENVIRONMENT == "production":
            raise
    logger.info(f"✅ {settings.APP_NAME} 启动完成!")
    yield
    logger.info(f"🛑 {settings.APP_NAME} 正在关闭...")
    try:
        await close_db()
        logger.info("✅ 数据库连接已关闭")
    except Exception as e:
        logger.error(f"❌ 数据库关闭异常: {e}")
    logger.info(f"✅ {settings.APP_NAME} 已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="企业级多智能体协作任务执行平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — 生产环境限制具体域名，开发环境允许所有
origins = (
    [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    if settings.ENVIRONMENT == "production" and settings.CORS_ORIGINS
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# 全局异常处理
# ============================================

@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """处理应用自定义异常"""
    logger.error(f"应用异常: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """处理通用异常"""
    logger.error(f"未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": "10000",
            "message": "服务器内部错误",
            "details": {"error": str(exc)} if settings.DEBUG else {},
            "status_code": 500
        }
    )


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    }


app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(metrics_router, prefix="/api/v1", tags=["metrics"])
app.include_router(keys_router, prefix="/api/v1", tags=["keys"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
