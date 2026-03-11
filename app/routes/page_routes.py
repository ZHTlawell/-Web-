"""页面路由定义。"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.runzo import 创建单数据默认表单参数, 创建默认表单参数, 单数据上传结果视图
from app.services.session_service import 写入会话Cookie, 获取或创建会话标识
from app.services.task_manager_service import task_manager

模板引擎 = Jinja2Templates(directory="app/templates")
路由 = APIRouter()


@路由.get("/", response_class=HTMLResponse)
def 首页(request: Request) -> HTMLResponse:
    """渲染主页面。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    响应 = 模板引擎.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "当前模块": "多数据上传",
            "表单默认值": 创建默认表单参数(),
            "任务视图": task_manager.获取当前任务视图(会话标识),
            "状态提示": "",
        },
    )
    if 是否新会话:
        写入会话Cookie(响应, 会话标识)
    return 响应


@路由.get("/单数据上传", response_class=HTMLResponse)
def 单数据上传页面(request: Request) -> HTMLResponse:
    """渲染单数据上传页面。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    响应 = 模板引擎.TemplateResponse(
        request=request,
        name="single_upload.html",
        context={
            "当前模块": "单数据上传",
            "表单默认值": 创建单数据默认表单参数(),
            "结果视图": 单数据上传结果视图(),
            "任务视图": task_manager.获取当前任务视图(会话标识),
        },
    )
    if 是否新会话:
        写入会话Cookie(响应, 会话标识)
    return 响应


@路由.get("/任务状态片段", response_class=HTMLResponse)
def 任务状态片段(request: Request) -> HTMLResponse:
    """返回任务状态局部模板。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    响应 = 模板引擎.TemplateResponse(
        request=request,
        name="_task_status_content.html",
        context={
            "任务视图": task_manager.获取当前任务视图(会话标识),
            "状态提示": "",
        },
    )
    if 是否新会话:
        写入会话Cookie(响应, 会话标识)
    return 响应
