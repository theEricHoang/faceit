from typing import List
from uuid import UUID
from app.services.classes.class_read_repository import ClassReadRepository, ClassReadError

class InvalidUserTypeError(Exception):
	pass

class ClassService:
	def __init__(self, read_repo: ClassReadRepository | None = None):
		self.read_repo = read_repo or ClassReadRepository()

	def get_classes_for_user(self, user_id: UUID, user_type: str) -> List[dict]:
		if user_type == "instructor":
			return self.read_repo.get_classes_by_instructor(user_id)
		elif user_type == "student":
			return self.read_repo.get_classes_by_student(user_id)
		else:
			raise ValueError("Invalid user type")

	def get_all_classes(self) -> List[dict]:
		"""Return all classes (for Open Classes browsing)."""
		return self.read_repo.get_all_classes()

	def get_class_details(self, class_id: UUID) -> dict:
		return self.read_repo.get_class_with_instructor(class_id)

	def instructor_has_class(self, instructor_id: UUID, class_id: UUID) -> bool:
		return self.read_repo.instructor_has_class(instructor_id, class_id)

	def get_class_enrolled_students(self, class_id: UUID) -> List[dict]:
		return self.read_repo.get_class_enrolled_students(class_id)
