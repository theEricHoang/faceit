from fastapi import FastAPI

from app.api.routes import courses

app = FastAPI()
app.include_router(courses.router)

@app.get("/")
def read_root():
	return {"message": "Hello, world!"}
