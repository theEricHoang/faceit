from fastapi import FastAPI

from app.api.routes import auth
from app.api.routes import courses
from app.api.routes import users
from app.api.routes import enrollment

app = FastAPI(title="FaceIT API", version="0.1.0")

# Include routers
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(enrollment.router)

@app.get("/")
def read_root():
	return {"message": "Hello, world!"}
