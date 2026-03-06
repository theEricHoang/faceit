"""Routes for attendance session reports."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_instructor
from app.schemas.attendance import AttendanceSessionResponse
from app.schemas.user import CurrentUser
from app.services.attendance_service import (
    AttendanceService,
    SessionNotFoundError,
)
from app.services.classes.class_query_service import ClassService as ClassQueryService

router = APIRouter(prefix="/classes", tags=["attendance"])


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def get_query_service() -> ClassQueryService:
    return ClassQueryService()


def get_attendance_service() -> AttendanceService:
    return AttendanceService()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{class_id}/attendance/sessions/{session_id}",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_attendance_session_report(
    class_id: UUID,
    session_id: UUID,
    current_user: CurrentUser = Depends(require_instructor),
    query_service: ClassQueryService = Depends(get_query_service),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> AttendanceSessionResponse:
    """Return a display-ready attendance report for a single session.

    Access control: the requesting instructor must own the class.
    Returns 404 (not 403) to avoid leaking class existence.
    """
    if not query_service.instructor_has_class(current_user.user_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    try:
        report = attendance_service.get_session_report(session_id, class_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return AttendanceSessionResponse(**report)
