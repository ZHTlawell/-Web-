"""API 路由定义。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.models.runzo import Runzo任务接口响应, Runzo任务视图, 单数据上传结果视图
from app.services.session_service import 写入会话Cookie, 获取或创建会话标识
from app.services.single_upload_service import 执行单数据上传
from app.services.task_manager_service import task_manager
from app.services.validation_service import 从表单构建参数, 从表单构建单数据参数

路由 = APIRouter(prefix="/api/runzo", tags=["runzo"])
模板引擎 = Jinja2Templates(directory="app/templates")


def _是否为_htmx请求(request: Request) -> bool:
    """判断当前请求是否来自 HTMX。"""
    return request.headers.get("HX-Request", "").lower() == "true"


def _渲染状态片段(request: Request, 任务视图: Runzo任务视图, 状态提示: str, status_code: int = 200) -> HTMLResponse:
    """渲染任务状态局部模板。"""
    return 模板引擎.TemplateResponse(
        request=request,
        name="_task_status_content.html",
        context={"任务视图": 任务视图, "状态提示": 状态提示},
        status_code=status_code,
    )


def _渲染单数据结果片段(request: Request, 结果视图: 单数据上传结果视图, status_code: int = 200) -> HTMLResponse:
    """渲染单数据上传结果局部模板。"""
    return 模板引擎.TemplateResponse(
        request=request,
        name="_single_upload_result.html",
        context={"结果视图": 结果视图},
        status_code=status_code,
    )


def _附加会话Cookie(response: HTMLResponse | JSONResponse, 会话标识: str, 是否新会话: bool):
    """在首次访问时写入会话 Cookie。"""
    if 是否新会话:
        写入会话Cookie(response, 会话标识)
    return response


@路由.post("/start")
async def 启动任务(request: Request):
    """接收表单并启动任务。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    try:
        表单 = await request.form()
        参数 = 从表单构建参数(表单)
        响应 = task_manager.启动任务(会话标识, 参数)
    except Exception as exc:  # noqa: BLE001
        if _是否为_htmx请求(request):
            return _附加会话Cookie(
                _渲染状态片段(request, task_manager.获取当前任务视图(会话标识), f"启动失败：{exc}", status_code=400),
                会话标识,
                是否新会话,
            )
        return _附加会话Cookie(
            JSONResponse(
            status_code=400,
            content=Runzo任务接口响应(
                成功=False,
                消息=f"启动失败：{exc}",
                数据=task_manager.获取当前任务视图(会话标识),
            ).model_dump(mode="json"),
        ),
            会话标识,
            是否新会话,
        )

    if _是否为_htmx请求(request):
        return _附加会话Cookie(_渲染状态片段(request, 响应.数据, 响应.消息), 会话标识, 是否新会话)
    return _附加会话Cookie(JSONResponse(content=响应.model_dump(mode="json")), 会话标识, 是否新会话)


@路由.post("/continue")
def 继续任务(request: Request):
    """继续已暂停的任务。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    try:
        响应 = task_manager.继续任务(会话标识)
    except Exception as exc:  # noqa: BLE001
        if _是否为_htmx请求(request):
            return _附加会话Cookie(
                _渲染状态片段(request, task_manager.获取当前任务视图(会话标识), f"继续失败：{exc}", status_code=400),
                会话标识,
                是否新会话,
            )
        return _附加会话Cookie(
            JSONResponse(
            status_code=400,
            content=Runzo任务接口响应(
                成功=False,
                消息=f"继续失败：{exc}",
                数据=task_manager.获取当前任务视图(会话标识),
            ).model_dump(mode="json"),
        ),
            会话标识,
            是否新会话,
        )

    if _是否为_htmx请求(request):
        return _附加会话Cookie(_渲染状态片段(request, 响应.数据, 响应.消息), 会话标识, 是否新会话)
    return _附加会话Cookie(JSONResponse(content=响应.model_dump(mode="json")), 会话标识, 是否新会话)


@路由.post("/cancel")
def 终止任务(request: Request):
    """终止当前任务。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    try:
        响应 = task_manager.终止任务(会话标识)
    except Exception as exc:  # noqa: BLE001
        if _是否为_htmx请求(request):
            return _附加会话Cookie(
                _渲染状态片段(request, task_manager.获取当前任务视图(会话标识), f"终止失败：{exc}", status_code=400),
                会话标识,
                是否新会话,
            )
        return _附加会话Cookie(
            JSONResponse(
            status_code=400,
            content=Runzo任务接口响应(
                成功=False,
                消息=f"终止失败：{exc}",
                数据=task_manager.获取当前任务视图(会话标识),
            ).model_dump(mode="json"),
        ),
            会话标识,
            是否新会话,
        )

    if _是否为_htmx请求(request):
        return _附加会话Cookie(_渲染状态片段(request, 响应.数据, 响应.消息), 会话标识, 是否新会话)
    return _附加会话Cookie(JSONResponse(content=响应.model_dump(mode="json")), 会话标识, 是否新会话)


@路由.get("/status")
def 当前状态(request: Request):
    """返回当前任务的 JSON 状态。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    响应 = JSONResponse(
        content=Runzo任务接口响应(
            成功=True,
            消息="获取成功。",
            数据=task_manager.获取当前任务视图(会话标识),
        ).model_dump(mode="json")
    )
    return _附加会话Cookie(响应, 会话标识, 是否新会话)


@路由.post("/single-upload/execute")
async def 执行单数据上传接口(request: Request):
    """执行单数据上传流程。"""
    会话标识, 是否新会话 = 获取或创建会话标识(request)
    try:
        表单 = await request.form()
        参数 = 从表单构建单数据参数(表单)
        结果视图 = 执行单数据上传(参数)
        状态码 = 200 if 结果视图.是否成功 else 400
    except Exception as exc:  # noqa: BLE001
        结果视图 = 单数据上传结果视图(
            是否成功=False,
            执行状态="执行失败",
            摘要="单数据上传执行失败。",
            错误信息=str(exc),
        )
        状态码 = 400

    if _是否为_htmx请求(request):
        return _附加会话Cookie(_渲染单数据结果片段(request, 结果视图, 状态码), 会话标识, 是否新会话)
    return _附加会话Cookie(JSONResponse(status_code=状态码, content=结果视图.model_dump(mode="json")), 会话标识, 是否新会话)
