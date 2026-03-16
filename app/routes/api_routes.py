"""API route definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.models.runzo import SingleUploadResultView, TaskApiResponse, TaskView
from app.services.session_service import get_or_create_session_id, write_session_cookie
from app.services.single_upload_service import execute_single_upload
from app.services.task_manager_service import task_manager
from app.services.validation_service import build_single_upload_params_from_form, build_task_params_from_form

router = APIRouter(prefix="/api/runzo", tags=["runzo"])
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
template_engine = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _is_htmx_request(request: Request) -> bool:
    """Return whether the request comes from HTMX."""
    return request.headers.get("HX-Request", "").lower() == "true"


def _render_status_fragment(
    request: Request,
    task_view: TaskView,
    status_message: str,
    status_code: int = 200,
) -> HTMLResponse:
    """Render the task status partial template."""
    return template_engine.TemplateResponse(
        request=request,
        name="_task_status_content.html",
        context={"task_view": task_view, "status_message": status_message},
        status_code=status_code,
    )


def _render_single_upload_result_fragment(
    request: Request,
    result_view: SingleUploadResultView,
    status_code: int = 200,
) -> HTMLResponse:
    """Render the single-upload result partial template."""
    return template_engine.TemplateResponse(
        request=request,
        name="_single_upload_result.html",
        context={"result_view": result_view},
        status_code=status_code,
    )


def _attach_session_cookie(response: Union[HTMLResponse, JSONResponse], session_id: str, is_new_session: bool):
    """Write cookie for newly created sessions."""
    if is_new_session:
        write_session_cookie(response, session_id)
    return response


def _resolve_app_version(request: Request) -> Optional[str]:
    """Read app version from request headers."""
    return request.headers.get("ts-app-version") or request.headers.get("x-ts-app-version")


@router.post("/start")
async def start_task(request: Request):
    """Parse form data and start a task."""
    session_id, is_new_session = get_or_create_session_id(request)
    try:
        form_data = await request.form()
        params = build_task_params_from_form(form_data, app_version=_resolve_app_version(request))
        response = task_manager.start_task(session_id, params)
    except Exception as exc:  # noqa: BLE001
        if _is_htmx_request(request):
            return _attach_session_cookie(
                _render_status_fragment(
                    request,
                    task_manager.get_current_task_view(session_id),
                    f"启动失败：{exc}",
                    status_code=400,
                ),
                session_id,
                is_new_session,
            )
        return _attach_session_cookie(
            JSONResponse(
                status_code=400,
                content=TaskApiResponse(
                    success=False,
                    message=f"启动失败：{exc}",
                    data=task_manager.get_current_task_view(session_id),
                ).model_dump(mode="json"),
            ),
            session_id,
            is_new_session,
        )

    if _is_htmx_request(request):
        return _attach_session_cookie(
            _render_status_fragment(request, response.data, response.message),
            session_id,
            is_new_session,
        )
    return _attach_session_cookie(JSONResponse(content=response.model_dump(mode="json")), session_id, is_new_session)


@router.post("/continue")
def continue_task(request: Request):
    """Continue a paused task."""
    session_id, is_new_session = get_or_create_session_id(request)
    try:
        response = task_manager.continue_task(session_id)
    except Exception as exc:  # noqa: BLE001
        if _is_htmx_request(request):
            return _attach_session_cookie(
                _render_status_fragment(
                    request,
                    task_manager.get_current_task_view(session_id),
                    f"继续失败：{exc}",
                    status_code=400,
                ),
                session_id,
                is_new_session,
            )
        return _attach_session_cookie(
            JSONResponse(
                status_code=400,
                content=TaskApiResponse(
                    success=False,
                    message=f"继续失败：{exc}",
                    data=task_manager.get_current_task_view(session_id),
                ).model_dump(mode="json"),
            ),
            session_id,
            is_new_session,
        )

    if _is_htmx_request(request):
        return _attach_session_cookie(
            _render_status_fragment(request, response.data, response.message),
            session_id,
            is_new_session,
        )
    return _attach_session_cookie(JSONResponse(content=response.model_dump(mode="json")), session_id, is_new_session)


@router.post("/cancel")
def cancel_task(request: Request):
    """Cancel the current task."""
    session_id, is_new_session = get_or_create_session_id(request)
    try:
        response = task_manager.cancel_task(session_id)
    except Exception as exc:  # noqa: BLE001
        if _is_htmx_request(request):
            return _attach_session_cookie(
                _render_status_fragment(
                    request,
                    task_manager.get_current_task_view(session_id),
                    f"终止失败：{exc}",
                    status_code=400,
                ),
                session_id,
                is_new_session,
            )
        return _attach_session_cookie(
            JSONResponse(
                status_code=400,
                content=TaskApiResponse(
                    success=False,
                    message=f"终止失败：{exc}",
                    data=task_manager.get_current_task_view(session_id),
                ).model_dump(mode="json"),
            ),
            session_id,
            is_new_session,
        )

    if _is_htmx_request(request):
        return _attach_session_cookie(
            _render_status_fragment(request, response.data, response.message),
            session_id,
            is_new_session,
        )
    return _attach_session_cookie(JSONResponse(content=response.model_dump(mode="json")), session_id, is_new_session)


@router.get("/status")
def current_status(request: Request):
    """Return current task JSON status."""
    session_id, is_new_session = get_or_create_session_id(request)
    response = JSONResponse(
        content=TaskApiResponse(
            success=True,
            message="获取成功。",
            data=task_manager.get_current_task_view(session_id),
        ).model_dump(mode="json")
    )
    return _attach_session_cookie(response, session_id, is_new_session)


@router.post("/single-upload/execute")
async def execute_single_upload_endpoint(request: Request):
    """Execute single-upload flow."""
    session_id, is_new_session = get_or_create_session_id(request)
    try:
        form_data = await request.form()
        params = build_single_upload_params_from_form(form_data, app_version=_resolve_app_version(request))
        result_view = execute_single_upload(params)
        status_code = 200 if result_view.success else 400
    except Exception as exc:  # noqa: BLE001
        result_view = SingleUploadResultView(
            success=False,
            execution_status="执行失败",
            summary="单数据上传执行失败。",
            error_message=str(exc),
        )
        status_code = 400

    if _is_htmx_request(request):
        return _attach_session_cookie(
            _render_single_upload_result_fragment(request, result_view, status_code),
            session_id,
            is_new_session,
        )
    return _attach_session_cookie(
        JSONResponse(status_code=status_code, content=result_view.model_dump(mode="json")),
        session_id,
        is_new_session,
    )
