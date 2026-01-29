from fastapi import FastAPI

from app.api.routes import auth

app = FastAPI(title="FaceIT API", version="0.1.0")

# Include routers
app.include_router(auth.router)


@app.get("/")
def read_root():
	return {"message": "Hello, world!"}
