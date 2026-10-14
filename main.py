from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Request, Depends,status,HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
 
from sqlalchemy import select,text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_db
from Routers import user
import models
# from schemas import 


#=================================={app creation}=====================================
@asynccontextmanager
async def lifespan(_app:FastAPI):
    yield
    # shutdown
    await engine.dispose()
app=FastAPI(lifespan=lifespan)
#==================================={files connection}=================================
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/media', StaticFiles(directory='media'), name='media')
templates= Jinja2Templates("templates")
#===================================={API Routers}=====================================
app.router.include_router(router=user.router,prefix='/api/users',tags=['users'])
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
