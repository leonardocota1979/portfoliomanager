# app/dependencies.py
"""
Dependências compartilhadas da aplicação.
Implementa autenticação JWT e middleware de autorização.

Versão: 2.0.0
Data: 26 de janeiro de 2026
"""

from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import crud, database, schemas
from .core.settings import get_settings

# ==============================================================================
# CONFIGURAÇÕES JWT
# ==============================================================================

SETTINGS = get_settings()
SECRET_KEY = SETTINGS.secret_key
ALGORITHM = SETTINGS.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = SETTINGS.access_token_expire_minutes

# OAuth2 scheme para extrair token do header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

# ==============================================================================
# FUNÇÕES JWT
# ==============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT.
    
    Args:
        data: Dados a serem codificados no token (ex: {"sub": username})
        expires_delta: Tempo de expiração customizado
        
    Returns:
        Token JWT assinado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    Verifica e decodifica um token JWT.
    
    Args:
        token: Token JWT a ser verificado
        
    Returns:
        Username extraído do token ou None se inválido
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
            
        return username
        
    except JWTError:
        return None


# ==============================================================================
# DEPENDÊNCIAS DE AUTENTICAÇÃO
# ==============================================================================

async def get_current_user(
    token: Annotated[str | None, Cookie(alias="access_token")] = None,
    authorization: Annotated[str | None, Depends(oauth2_scheme)] = None,
    db: Session = Depends(database.get_db)
) -> database.User:
    """
    Dependência que extrai e valida o usuário atual do token JWT.
    
    Tenta extrair o token de:
    1. Cookie "access_token"
    2. Header Authorization (Bearer token)
    
    Args:
        token: Token do cookie
        authorization: Token do header Authorization
        db: Sessão do banco de dados
        
    Returns:
        Objeto User do banco de dados
        
    Raises:
        HTTPException 401: Se token inválido ou usuário não encontrado
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extrai token do cookie ou header
    jwt_token = None
    
    if token:
        # Remove "Bearer " se presente no cookie
        jwt_token = token.replace("Bearer ", "")
    elif authorization:
        jwt_token = authorization
    
    if not jwt_token:
        raise credentials_exception
    
    # Verifica token
    username = verify_token(jwt_token)
    
    if username is None:
        raise credentials_exception
    
    # Busca usuário no banco
    user = crud.get_user_by_username(db, username=username)
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: Annotated[database.User, Depends(get_current_user)]
) -> database.User:
    """
    Dependência que retorna usuário ativo.
    
    Pode ser estendida no futuro para verificar se usuário está ativo/banido.
    
    Args:
        current_user: Usuário atual autenticado
        
    Returns:
        Objeto User do banco de dados
        
    Raises:
        HTTPException 400: Se usuário inativo (implementação futura)
    """
    # Implementação futura: verificar se user.is_active == True
    return current_user


async def get_current_admin_user(
    current_user: Annotated[database.User, Depends(get_current_active_user)]
) -> database.User:
    """Garante que o usuário atual seja admin."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores"
        )
    return current_user


def verify_portfolio_ownership(
    portfolio_id: int,
    current_user: database.User,
    db: Session
) -> database.Portfolio:
    """
    Verifica se o usuário atual é dono do portfolio.
    
    Args:
        portfolio_id: ID do portfolio
        current_user: Usuário autenticado
        db: Sessão do banco
        
    Returns:
        Objeto Portfolio se usuário é dono
        
    Raises:
        HTTPException 404: Portfolio não encontrado
        HTTPException 403: Usuário não é dono do portfolio
    """
    portfolio = crud.get_portfolio(db, portfolio_id=portfolio_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio com ID {portfolio_id} não encontrado"
        )
    
    if portfolio.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este portfolio"
        )
    
    return portfolio


# ==============================================================================
# SCHEMAS AUXILIARES
# ==============================================================================

class Token(schemas.BaseModel):
    """Schema para resposta de token JWT"""
    access_token: str
    token_type: str


class TokenData(schemas.BaseModel):
    """Schema para dados dentro do token"""
    username: Optional[str] = None
