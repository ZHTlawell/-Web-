"""应用主入口，负责创建 FastAPI 实例并注册路由。"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.api_routes import 路由 as 接口路由
from app.routes.page_routes import 路由 as 页面路由


def 创建应用() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    应用 = FastAPI(title="Runzo 测试执行平台", version="1.0.0")
    应用.include_router(页面路由)
    应用.include_router(接口路由)
    应用.mount("/static", StaticFiles(directory="app/static"), name="static")
    return 应用


app = 创建应用()
