from fastapi import FastAPI

from app.api.routes import auth
from app.api.routes import courses

app = FastAPI(title="FaceIT API", version="0.1.0")

# Include routers
app.include_router(auth.router)
app.include_router(courses.router)

@app.get("/")
def read_root():
	return {"message": "Hello, world!"}
