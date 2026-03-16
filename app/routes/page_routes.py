"""Page route definitions."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.runzo import SingleUploadResultView, create_default_form_values, create_default_single_upload_form_values
from app.services.session_service import get_or_create_session_id, write_session_cookie
from app.services.task_manager_service import task_manager

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
template_engine = Jinja2Templates(directory=str(TEMPLATE_DIR))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request) -> HTMLResponse:
    """Render the multi-upload page."""
    session_id, is_new_session = get_or_create_session_id(request)
    response = template_engine.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_module": "多数据上传",
            "default_form_values": create_default_form_values(),
            "task_view": task_manager.get_current_task_view(session_id),
            "status_message": "",
        },
    )
    if is_new_session:
        write_session_cookie(response, session_id)
    return response


@router.get("/单数据上传", response_class=HTMLResponse)
def single_upload_page(request: Request) -> HTMLResponse:
    """Render the single-upload page."""
    session_id, is_new_session = get_or_create_session_id(request)
    response = template_engine.TemplateResponse(
        request=request,
        name="single_upload.html",
        context={
            "current_module": "单数据上传",
            "default_form_values": create_default_single_upload_form_values(),
            "result_view": SingleUploadResultView(),
            "task_view": task_manager.get_current_task_view(session_id),
        },
    )
    if is_new_session:
        write_session_cookie(response, session_id)
    return response


@router.get("/任务状态片段", response_class=HTMLResponse)
def task_status_fragment(request: Request) -> HTMLResponse:
    """Return task status partial template."""
    session_id, is_new_session = get_or_create_session_id(request)
    response = template_engine.TemplateResponse(
        request=request,
        name="_task_status_content.html",
        context={
            "task_view": task_manager.get_current_task_view(session_id),
            "status_message": "",
        },
    )
    if is_new_session:
        write_session_cookie(response, session_id)
    return response
