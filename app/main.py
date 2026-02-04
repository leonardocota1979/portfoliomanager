# app/main.py
"""
Arquivo principal da aplicação FastAPI "PortifolioManager".
Configura o servidor, monta arquivos estáticos, inicializa templates
e inclui todos os routers da aplicação.

Versão: 1.1.0 (Corrigida - Sintaxe Python)
Data: 26 de janeiro de 2026
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from dotenv import load_dotenv

# Importa módulos do app
from .database import create_db_and_tables, SessionLocal, GlobalAssetClass
from . import crud, schemas
from .services.price_service import get_price_service

# Importa todos os routers
from .routers import (
    search,
    admin,
    auth,
    users,
    portfolios,
    asset_classes,
    assets,
    portfolio_assets,
    dashboard,
    imports
)

# Carrega variáveis de ambiente (.env)
load_dotenv()

# Cria tabelas do banco de dados ao iniciar
create_db_and_tables()

# Seed global asset classes if empty
def _seed_global_classes():
    defaults = [
        ("Stocks", "Equities/Shares - Ações de empresas"),
        ("Bonds", "Fixed Income - Títulos de renda fixa"),
        ("REITs", "Real Estate Investment Trusts - Fundos Imobiliários"),
        ("Crypto", "Cryptocurrencies - Criptomoedas e ativos digitais"),
        ("Commodities", "Raw materials - Ouro, prata, petróleo, etc"),
        ("Reserva de Valor", "Reserva de valor - Caixa e equivalentes"),
    ]
    db = SessionLocal()
    try:
        existing = db.query(GlobalAssetClass).count()
        if existing > 0:
            return
        for name, desc in defaults:
            db.add(GlobalAssetClass(name=name, description=desc))
        db.commit()
    finally:
        db.close()

_seed_global_classes()

# Bootstrap admin user from env (only if not exists)
def _bootstrap_admin():
    import os
    username = os.getenv("ADMIN_BOOTSTRAP_USER")
    password = os.getenv("ADMIN_BOOTSTRAP_PASS")
    email = os.getenv("ADMIN_BOOTSTRAP_EMAIL")
    if not username or not password or not email:
        return
    db = SessionLocal()
    try:
        existing = crud.get_user_by_username(db, username)
        if existing:
            # Ensure admin + optionally reset password
            existing.is_admin = True
            if password:
                crud.set_user_password(db, existing, password)
            db.commit()
            return
        user = schemas.UserCreate(username=username, email=email, password=password)
        created = crud.create_user(db, user)
        created.is_admin = True
        db.commit()
    finally:
        db.close()

_bootstrap_admin()

# Inicializa FastAPI
app = FastAPI(
    title="Portfolio Manager",
    description="Sistema de gerenciamento de carteira de ativos",
    version="1.1.0"
)


@app.on_event("startup")
async def startup_checks():
    """Valida provedores de preço na inicialização (sem expor chaves)."""
    try:
        service = get_price_service()
        results = await service.validate_providers()
        print(f"✅ Validação de provedores de preço: {results}")
    except Exception as e:
        print(f"⚠️ Falha na validação de provedores de preço: {e}")

# Static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Incluir routers
app.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
app.include_router(users.router, prefix="/users", tags=["Usuários"])
app.include_router(portfolios.router, prefix="/portfolios", tags=["Portfolios"])
app.include_router(asset_classes.router, tags=["Asset Classes"])
app.include_router(assets.router, tags=["Ativos"])
app.include_router(portfolio_assets.router, tags=["Portfolio Assets"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(admin.router)
app.include_router(search.router)
app.include_router(imports.router)


# Rota raiz: serve a página de login
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Renderiza a página de login como a rota raiz."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login"}
    )


# Página inicial pós-login
@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    """Redireciona para lista de carteiras após login."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/portfolios/list")


# Health check
@app.get("/health")
async def health():
    """Endpoint de verificação de saúde da aplicação"""
    return {
        "status": "ok",
        "message": "Portfolio Manager está rodando!",
        "version": "1.1.0"
    }
