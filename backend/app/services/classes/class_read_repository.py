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

	def get_all_classes(self) -> List[dict]:
		"""Fetch all classes regardless of user enrollment/instructor ownership."""
		try:
			result = (
				self.client
				.table("classes")
				.select("id, course_code, course_name, section, term, schedule, room")
				.execute()
			)
			return result.data or []
		except Exception as e:
			raise ClassReadError(f"Failed to fetch all classes: {e}")

	def get_class_with_instructor(self, class_id: UUID) -> dict:
		"""Fetch a single class and join instructor profile to get full name."""
		try:
			cls_res = (
				self.client
				.table("classes")
				.select("id, course_code, course_name, section, schedule, room, instructor_id")
				.eq("id", str(class_id))
				.single()
				.execute()
			)
			cls = cls_res.data
			if not cls:
				raise ClassReadError("Class not found")
			inst_id = cls.get("instructor_id")
			first_name = ""
			last_name = ""
			if inst_id:
				prof_res = (
					self.client
					.table("profiles")
					.select("first_name, last_name")
					.eq("id", str(inst_id))
					.single()
					.execute()
				)
				prof = prof_res.data or {}
				first_name = prof.get("first_name") or ""
				last_name = prof.get("last_name") or ""
			return {
				"id": cls["id"],
				"course_code": cls.get("course_code"),
				"course_name": cls.get("course_name"),
				"section": cls.get("section"),
				"schedule": cls.get("schedule"),
				"room": cls.get("room"),
				"instructor_name": (first_name + (" " if first_name and last_name else "") + last_name) or "",
			}
		except ClassReadError:
			raise
		except Exception as e:
			raise ClassReadError(f"Failed to fetch class details: {e}")
		
	def get_students_by_class(self, class_id: UUID) -> List[dict]:
		"""Fetch all students enrolled in a specific class."""
		try:
			# First, get all student_ids from the junction table
			enrollment_result = (
				self.client
				.table("student_classes")
				.select("student_id")
				.eq("class_id", str(class_id))
				.execute()
			)
			
			student_ids = [row["student_id"] for row in (enrollment_result.data or [])]
			
			if not student_ids:
				return []
			
			# Now fetch profile data for all these students
			# We need to get first_name, last_name, and email from profiles table
			students_data = []
			for student_id in student_ids:
				profile_result = (
					self.client
					.table("profiles")
					.select("id, first_name, last_name")
					.eq("id", str(student_id))
					.single()
					.execute()
				)
				if profile_result.data:
					profile = profile_result.data
					# Get email from Supabase users table (auth)
					# For now, we'll try to get it; if not available, use a placeholder
					email = ""
					try:
						# Try to fetch user email if available
						user_result = (
							self.client
							.auth.admin
							.get_user_by_id(str(student_id))
						)
						email = user_result.user.email if user_result.user else ""
					except Exception:
						# If we can't get email from auth, that's okay
						email = ""
					
					students_data.append({
						"id": profile.get("id"),
						"first_name": profile.get("first_name"),
						"last_name": profile.get("last_name"),
						"email": email,
					})
			
			return students_data
		except Exception as e:
			raise ClassReadError(f"Failed to fetch students for class: {e}")
