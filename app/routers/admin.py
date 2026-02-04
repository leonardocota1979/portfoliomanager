# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, crud
from ..database import get_db, GlobalAssetClass
from .. import database
from ..dependencies import get_current_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.get("/global-classes/", response_model=List[schemas.GlobalAssetClass])
def list_global_classes(
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin_user)
):
    """Lista todas as classes globais disponíveis"""
    return db.query(GlobalAssetClass).all()


@router.get("/users", response_class=HTMLResponse)
def admin_users_page(
    request: Request,
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin_user)
):
    page = max(1, page)
    limit = max(5, min(100, limit))
    query = db.query(database.User)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (database.User.username.ilike(like)) |
            (database.User.email.ilike(like))
        )
    total = query.count()
    users = query.order_by(database.User.id.asc()).offset((page - 1) * limit).limit(limit).all()
    total_pages = (total + limit - 1) // limit
    from ..main import templates
    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "title": "Administração de Usuários",
            "users": users,
            "current_user": current_user,
            "q": q or "",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        }
    )
