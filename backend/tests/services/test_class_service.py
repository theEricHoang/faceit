"""Unit tests for ClassService."""

import pytest
from uuid import uuid4
from app.services.class_service import ClassService, CreateClassError

import types

@pytest.mark.asyncio
async def test_create_class_success(monkeypatch):
    # Arrange
    fake_client = types.SimpleNamespace()
    fake_result = types.SimpleNamespace(data=[{"id": "1", "course_code": "CSC4352"}])
    fake_client.table = lambda name: types.SimpleNamespace(insert=lambda data: types.SimpleNamespace(execute=lambda: fake_result))
    service = ClassService(client=fake_client)

    # Act
    result = await service.create_class(
        instructor_id=uuid4(),
        course_code="CSC4352",
        course_name="Capstone II",
        section="19884",
        term="Spring 2026",
        schedule="M-W 9AM-10AM",
        room="Langdale Hall 400"
    )

    # Assert
    assert result["course_code"] == "CSC4352"

@pytest.mark.asyncio
async def test_create_class_failure(monkeypatch):
    # Arrange
    fake_client = types.SimpleNamespace()
    fake_result = types.SimpleNamespace(data=None)
    fake_client.table = lambda name: types.SimpleNamespace(insert=lambda data: types.SimpleNamespace(execute=lambda: fake_result))
    service = ClassService(client=fake_client)

    # Act & Assert
    with pytest.raises(CreateClassError):
        await service.create_class(
            instructor_id=uuid4(),
            course_code="CSC4352",
            course_name="Capstone II",
            section="19884",
            term="Spring 2026",
            schedule="M-W 9AM-10AM",
            room="Langdale Hall 400"
        )
