#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

print("🔍 Verificando rotas registradas...\n")

try:
    from app.main import app
    
    print("✅ App carregado com sucesso!\n")
    print("📋 Rotas registradas:")
    print("="*60)
    
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            print(f"{methods:10} {route.path}")
    
    print("="*60)
    
    # Verifica especificamente a rota /portfolios/list
    portfolio_list_found = any(
        hasattr(r, 'path') and '/portfolios/list' in r.path 
        for r in app.routes
    )
    
    if portfolio_list_found:
        print("\n✅ Rota /portfolios/list ENCONTRADA!")
    else:
        print("\n❌ Rota /portfolios/list NÃO ENCONTRADA!")
        print("🔧 Vou verificar o arquivo...")
        
        with open('app/routers/portfolios.py', 'r') as f:
            content = f.read()
            if '@router.get("/list"' in content:
                print("✅ Rota existe no arquivo portfolios.py")
                print("❌ Mas não foi incluída no main.py!")
            else:
                print("❌ Rota NÃO existe no arquivo portfolios.py")

except Exception as e:
    print(f"❌ Erro ao carregar app: {e}")
    import traceback
    traceback.print_exc()

