# app/routers/users.py
# Rotas CRUD de usuários

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas
from ..database import get_db
from .. import database
from ..dependencies import get_current_active_user, get_current_admin_user

router = APIRouter()

@router.post("/", response_model=schemas.User, status_code=201)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin_user)
):
    """Cria um novo usuário"""
    # Verifica se username já existe
    existing_user = crud.get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username já existe")
    return crud.create_user(db, user)

@router.get("/", response_model=List[schemas.User])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin_user)
):
    """Lista todos os usuários"""
    return crud.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=schemas.User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin_user)
):
    """Busca usuário por ID"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin_user)
):
    """Atualiza username/email/is_admin."""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if payload.username and payload.username != user.username:
        existing = crud.get_user_by_username(db, payload.username)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Username já existe")

    if payload.email and payload.email != user.email:
        # email é único
        existing = db.query(database.User).filter(database.User.email == payload.email).first()
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Email já existe")

    return crud.update_user(db, user, payload)

@router.post("/{user_id}/reset-password", response_model=schemas.User)
def reset_password(
    user_id: int,
    payload: schemas.UserResetPassword,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin_user)
):
    """Reseta a senha do usuário."""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return crud.set_user_password(db, user, payload.password)

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.User = Depends(get_current_admin_user)
):
    """Remove usuário."""
    if current_admin.id == user_id:
        raise HTTPException(status_code=400, detail="Não é permitido remover o próprio usuário admin")
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    crud.delete_user(db, user)
    return {"success": True}
