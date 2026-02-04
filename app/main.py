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
from .database import create_db_and_tables
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
