from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Request, Depends, status, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

 
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_db
from Routers import user, authentication, files, Appointment, dashboard, chat, payment
from Routers.Doctor import bokingtype, block
import models
from config import settings
# from schemas import 
#=================================={app creation}=====================================
@asynccontextmanager
async def lifespan(_app:FastAPI):
    yield
    # shutdown
    await engine.dispose()
app=FastAPI(lifespan=lifespan)
#============================{setup session middleware}===============================
# 1. Add SessionMiddleware properly
app.add_middleware(
    SessionMiddleware,
    secret_key=f"{settings.secret_key}",
)

# 2. Add CORSMiddleware properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#==================================={files connection}=================================
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/media', StaticFiles(directory='media'), name='media')
templates= Jinja2Templates("templates")
#===================================={API Routers}=====================================
app.router.include_router(router=authentication.router,prefix='/api/authentication',tags=['Authentication'])
app.router.include_router(router=user.router,prefix='/api/users',tags=['Users'])
app.include_router(router=chat.router, prefix='/api/chats', tags=['Chat'])
app.router.include_router(router=dashboard.router,prefix='/api/dashboard',tags=['Dashboard'])
app.router.include_router(router=files.router,prefix='/api/clients/files',tags=['Files'])
app.router.include_router(router=Appointment.router,prefix='/api/clients/appointments',tags=['Appointments'])
app.router.include_router(router=bokingtype.router,prefix='/api/doctors/bookingtypes',tags=['Doctor bookingtypes'])
app.router.include_router(router=block.router,prefix='/api/doctors/blocked',tags=['Doctor Blocked Emails'])
app.router.include_router(router=payment.router,prefix="/api/payment",tags=["Payment"])
# =================================={ Helth Chick Route }=========================================
@app.get('/health')
async def health_chick(db:Annotated[AsyncSession,Depends(get_db)]):
    try:
        await db.execute(text('SELECT 1'))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='database unavailable'
        )from exc
    return{'status':'healthy'}
# {Template Route}
@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
