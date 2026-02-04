from uuid import UUID
from supabase import Client

from app.db.supabase import get_supabase_client


class EnrollmentServiceError(Exception):
    pass


class EnrollmentService:
    """Service to enroll a student into a class by course code."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def join_by_course_code(self, student_user_id: UUID, course_code: str) -> dict:
        """
        Enroll the current student (by their user UUID) into a class identified by course_code.

        Steps:
        - Find class by course_code in 'classes'
        - Validate student exists in 'students' (id == user id)
        - Insert into 'student_classes' with class_id and student_id
        Returns inserted student_classes row.
        """
        try:
            # Lookup class by course_code
            code = course_code.strip()
            class_result = (
                self.client
                .table("classes")
                .select("id, course_code, course_name, section")
                .ilike("course_code", code)
                .limit(1)
                .execute()
            )
            rows = class_result.data or []
            if len(rows) == 0:
                raise EnrollmentServiceError("Class not found for given course code")
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
                return {
                    "class_id": str(class_id),
                    "student_id": str(student_user_id),
                    "course_name": course_name,
                    "section": section,
                }

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
