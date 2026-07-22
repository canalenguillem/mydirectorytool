from fastapi import FastAPI
from app.api import auth, places, blog, queue
from app.models.database import init_db
from app.services.publication_queue import start_worker

import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()
    start_worker()


@app.middleware("http")
async def require_login(request, call_next):
    from fastapi.responses import JSONResponse

    public_paths = {"/auth/login", "/docs", "/openapi.json", "/redoc"}
    if request.method != "OPTIONS" and request.url.path not in public_paths:
        if not auth.valid_session(request.cookies.get(auth.COOKIE_NAME)):
            return JSONResponse(status_code=401, content={"detail": "No autenticado"})
    return await call_next(request)

origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:8091").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(places.router, prefix="/places", tags=["Places"])
app.include_router(blog.router, prefix="/blog", tags=["blog"])
app.include_router(queue.router, prefix="/queue", tags=["Queue"])
