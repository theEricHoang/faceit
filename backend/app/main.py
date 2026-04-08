from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import attendance
from app.api.routes import auth
from app.api.routes import courses
from app.api.routes import users
from app.api.routes import enrollment
from app.api.routes import jobs
from app.core.config import get_settings

app = FastAPI(title="FaceIT API", version="0.1.0")

settings = get_settings()

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.parsed_cors_allow_origins(),
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Include routers
app.include_router(attendance.router)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(enrollment.router)
app.include_router(jobs.router)

@app.get("/")
def read_root():
	return {"message": "Hello, world!"}
