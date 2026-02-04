# app/routers/auth.py
"""
Router de autenticação de usuários com JWT completo.
Versão: 2.0.0 (JWT Real Implementado)
Data: 26 de janeiro de 2026
"""

from datetime import timedelta
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..dependencies import (
    create_access_token,
    get_current_active_user,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()


def authenticate_user(db: Session, username: str, password: str):
    """
    Autentica usuário verificando username e senha.
    
    Args:
        db: Sessão do banco de dados
        username: Nome de usuário
        password: Senha em texto plano
        
    Returns:
        User object se autenticado, False caso contrário
    """
    user = crud.get_user_by_username(db, username)
    if not user:
        return False
    if not crud.verify_password(password, user.hashed_password):
        return False
    return user


# ==============================================================================
# ENDPOINTS HTML (Para navegação web)
# ==============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Renderiza a página de login HTML"""
    from ..main import templates
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login"}
    )


@router.post("/login", response_class=RedirectResponse)
async def login_for_access_token_html(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db)
):
    """
    Processa login do usuário via formulário HTML e redireciona para home.
    Token JWT é armazenado em cookie httpOnly.
    
    Args:
        request: Request object
        username: Username do formulário
        password: Password do formulário
        db: Sessão do banco
        
    Returns:
        RedirectResponse para /home com cookie de token
    """
    user = authenticate_user(db, username, password)
    
    if not user:
        print(f"❌ Tentativa de login falhou para: {username}")
        # Redireciona de volta para login com parâmetro de erro
        response = RedirectResponse(
            url="/auth/login?error=true",
            status_code=status.HTTP_303_SEE_OTHER
        )
        return response

    # Cria token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    print(f"✅ Login bem-sucedido para: {username}")
    
    # Redireciona para lista de carteiras com token no cookie
    response = RedirectResponse(
        url="/portfolios/list",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # Protege contra XSS
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Em segundos
        samesite=os.getenv("COOKIE_SAMESITE", "lax"),
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
    )
    
    return response


@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    """
    Realiza logout removendo cookie de token.
    
    Returns:
        RedirectResponse para página de login
    """
    response = RedirectResponse(
        url="/auth/login",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(key="access_token")
    return response


# ==============================================================================
# ENDPOINTS API (Para requisições JSON)
# ==============================================================================

@router.post("/token", response_model=Token)
async def login_for_access_token_api(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    Endpoint de autenticação OAuth2 para APIs.
    Retorna token JWT em formato JSON.
    
    Este endpoint é usado por:
    - Clientes mobile
    - SPAs (Single Page Applications)
    - Ferramentas de API (Postman, Insomnia)
    
    Args:
        form_data: Formulário OAuth2 (username + password)
        db: Sessão do banco
        
    Returns:
        Token JWT e tipo (Bearer)
        
    Raises:
        HTTPException 401: Credenciais inválidas
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)]
):
    """
    Retorna informações do usuário logado.
    
    Este endpoint requer autenticação (token JWT).
    
    Args:
        current_user: Usuário autenticado (injetado pela dependência)
        
    Returns:
        Dados do usuário atual
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)]
):
    """
    Gera um novo token para o usuário atual.
    
    Útil para renovar tokens antes de expirarem.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        Novo token JWT
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ==============================================================================
# ENDPOINT DE TESTE (Remover em produção)
# ==============================================================================

@router.get("/protected-example")
async def protected_route_example(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)]
):
    """
    Exemplo de rota protegida que requer autenticação.
    
    Este endpoint só pode ser acessado por usuários autenticados.
    Use como referência para criar outras rotas protegidas.
    
    Args:
        current_user: Usuário autenticado
        
    Returns:
        Mensagem de sucesso com dados do usuário
    """
    return {
        "message": f"Olá {current_user.username}! Esta é uma rota protegida.",
        "user_id": current_user.id,
        "email": current_user.email
    }
