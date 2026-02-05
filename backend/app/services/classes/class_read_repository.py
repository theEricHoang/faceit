from typing import List
from uuid import UUID
from supabase import Client
from app.db.supabase import get_supabase_client

class ClassReadError(Exception):
	pass

class ClassReadRepository:
	def __init__(self, client: Client | None = None):
		self.client = client or get_supabase_client()

	def get_classes_by_instructor(self, instructor_id: UUID) -> List[dict]:
		try:
			result = self.client.table("classes").select("*").eq("instructor_id", str(instructor_id)).execute()
			return result.data or []
		except Exception as e:
			raise ClassReadError(f"Failed to fetch classes for instructor: {e}")

	def get_classes_by_student(self, student_id: UUID) -> List[dict]:
		try:
			result = self.client.table("student_classes").select("classes(*)").eq("student_id", str(student_id)).execute()
			return [row["classes"] for row in (result.data or [])]
		except Exception as e:
			raise ClassReadError(f"Failed to fetch classes for student: {e}")

	def get_students_by_class(self, class_id: UUID) -> List[dict]:
		try:
			result = self.client.table("student_classes").select("users(id, first_name, last_name, email)").eq("class_id", str(class_id)).execute()
			return [row["users"] for row in (result.data or [])]
		except Exception as e:
			raise ClassReadError(f"Failed to fetch students for class: {e}")
