from uuid import UUID
from supabase import Client

from app.db.supabase import get_supabase_client


class EnrollmentServiceError(Exception):
    pass


class EnrollmentService:
    """Service to enroll a student into a class by course code."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def join_by_section(self, student_user_id: UUID, section_value: str) -> dict:
        """
        Enroll the current student (by their user UUID) into a class identified by section.

        Steps:
        - Find class by section in 'classes'
        - Validate student exists in 'students' (id == user id)
        - Insert into 'student_classes' with class_id and student_id
        Returns inserted student_classes row.
        """
        try:
            # Lookup class by section
            sec = section_value.strip()
            class_result = (
                self.client
                .table("classes")
                .select("id, course_code, course_name, section")
                .ilike("section", sec)
                .limit(1)
                .execute()
            )
            rows = class_result.data or []
            if len(rows) == 0:
                raise EnrollmentServiceError("Class not found for given section")
            cls = rows[0]
            class_id = cls["id"]
            course_name = cls.get("course_name")
            section = cls.get("section")

            # Ensure student exists (students.id equals user UUID)
            student_result = (
                self.client
                .table("students")
                .select("id")
                .eq("id", str(student_user_id))
                .single()
                .execute()
            )
            if not student_result.data:
                raise EnrollmentServiceError("Student record not found")

            # Check if already enrolled
            existing = (
                self.client
                .table("student_classes")
                .select("id, class_id, student_id")
                .eq("class_id", str(class_id))
                .eq("student_id", str(student_user_id))
                .limit(1)
                .execute()
            )
            if existing.data:
                raise EnrollmentServiceError("you already joined this class")

            # Insert enrollment; let DB assign 'id' if present
            insert_result = (
                self.client
                .table("student_classes")
                .insert({
                    "class_id": str(class_id),
                    "student_id": str(student_user_id),
                })
                .execute()
            )
            if not insert_result.data:
                raise EnrollmentServiceError("Failed to create enrollment record")
            return {
                "class_id": str(class_id),
                "student_id": str(student_user_id),
                "course_name": course_name,
                "section": section,
            }
        except EnrollmentServiceError:
            raise
        except Exception as e:
            raise EnrollmentServiceError(f"Enrollment failed: {e}")

    def withdraw_from_class(self, student_user_id: UUID, class_id: UUID) -> dict:
        """
        Withdraw the current student from a class: delete row from student_classes.
        Returns {class_id, student_id} on success.
        """
        try:
            # Ensure enrollment exists
            existing = (
                self.client
                .table("student_classes")
                .select("id, class_id, student_id")
                .eq("class_id", str(class_id))
                .eq("student_id", str(student_user_id))
                .limit(1)
                .execute()
            )
            if not existing.data:
                raise EnrollmentServiceError("Not enrolled in this class")

            # Perform deletion
            _ = (
                self.client
                .table("student_classes")
                .delete()
                .eq("class_id", str(class_id))
                .eq("student_id", str(student_user_id))
                .execute()
            )
            return {
                "class_id": str(class_id),
                "student_id": str(student_user_id),
            }
        except EnrollmentServiceError:
            raise
        except Exception as e:
            raise EnrollmentServiceError(f"Withdraw failed: {e}")
