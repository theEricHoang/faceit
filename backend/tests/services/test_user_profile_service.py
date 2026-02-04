"""Unit tests for UserProfileService."""

from unittest.mock import MagicMock

import pytest

from app.services.user_profile_service import UserProfileService, UserProfileServiceError
from tests.conftest import MockTableResponse, TEST_USER_ID


def _build_profiles_chain(data: dict | None):
    select_chain = MagicMock()
    select_chain.eq.return_value = select_chain
    select_chain.single.return_value = select_chain
    select_chain.execute.return_value = MockTableResponse(data=data)
    return select_chain


def _build_students_chain(number_value: str | None):
    select_chain = MagicMock()
    select_chain.eq.return_value = select_chain
    select_chain.single.return_value = select_chain
    if number_value is None:
        select_chain.execute.return_value = MockTableResponse(data=None)
    else:
        select_chain.execute.return_value = MockTableResponse(data={"number": number_value})
    return select_chain


class TestUserProfileService:
    def test_get_profile_names_and_type_success(self):
        client = MagicMock()
        profiles_chain = _build_profiles_chain({
            "first_name": "John",
            "last_name": "Doe",
            "type": "student",
        })
        table_mock = MagicMock()
        table_mock.select.return_value = profiles_chain
        client.table.return_value = table_mock

        service = UserProfileService(client=client)
        result = service.get_profile_names_and_type(TEST_USER_ID)

        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["type"] == "student"

    def test_get_profile_names_and_type_not_found_raises(self):
        client = MagicMock()
        profiles_chain = _build_profiles_chain(None)
        table_mock = MagicMock()
        table_mock.select.return_value = profiles_chain
        client.table.return_value = table_mock

        service = UserProfileService(client=client)
        with pytest.raises(UserProfileServiceError):
            service.get_profile_names_and_type(TEST_USER_ID)

    def test_get_student_number_success(self):
        client = MagicMock()
        students_chain = _build_students_chain("S9988")
        table_mock = MagicMock()
        table_mock.select.return_value = students_chain
        client.table.return_value = table_mock

        service = UserProfileService(client=client)
        number = service.get_student_number(TEST_USER_ID)
        assert number == "S9988"

    def test_get_student_number_none_when_missing(self):
        client = MagicMock()
        students_chain = _build_students_chain(None)
        table_mock = MagicMock()
        table_mock.select.return_value = students_chain
        client.table.return_value = table_mock

        service = UserProfileService(client=client)
        number = service.get_student_number(TEST_USER_ID)
        assert number is None
