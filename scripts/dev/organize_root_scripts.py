#!/usr/bin/env python3
"""
organize_root_scripts.py

Script para organizar os arquivos da raiz do projeto PortifolioManager
nas pastas corretas dentro de scripts/

Autor: Assistente de IA
Data: 27 de janeiro de 2026
"""

import shutil
import os
from pathlib import Path

# Diretório raiz do projeto
PROJECT_ROOT = Path(".")

# Mapeamento: arquivo -> pasta destino
FILE_MAPPING = {
    # ═══════════════════════════════════════════════════════════════════
    # SCRIPTS ÚTEIS - Mover para subpastas apropriadas
    # ═══════════════════════════════════════════════════════════════════
    
    # Setup - Scripts de configuração inicial
    "bootstrap.sh": "scripts/setup/",
    
    # Dev - Scripts de desenvolvimento
    "start_server.sh": "scripts/dev/",
    "check_routes.py": "scripts/dev/",
    "create_sample_data.py": "scripts/dev/",
    "diagnostico_projeto.py": "scripts/dev/",
    
    # Maintenance - Scripts de manutenção
    "manage_users.py": "scripts/maintenance/",
    "migrate_database.py": "scripts/maintenance/",
    "upgrade_database.py": "scripts/maintenance/",
    "setup_existing_portfolio.py": "scripts/maintenance/",
    "fix_global_classes.py": "scripts/maintenance/",
    
    # ═══════════════════════════════════════════════════════════════════
    # SCRIPTS OBSOLETOS/EXECUTADOS - Mover para scripts/old/
    # ═══════════════════════════════════════════════════════════════════
    
    # Fixes que já foram aplicados
    "fix_all_issues.py": "scripts/old/",
    "fix_dashboard_complete.py": "scripts/old/",
    "fix_dashboard_final.py": "scripts/old/",
    "fix_dashboard_py.py": "scripts/old/",
    "fix_create_route.py": "scripts/old/",
    "fix_duplicate_prefix.py": "scripts/old/",
    "fix_imports.py": "scripts/old/",
    "fix_list_button.py": "scripts/old/",
    "fix_portfolio_routes.py": "scripts/old/",
    
    # Scripts de criação que já foram executados
    "add_cash_class.py": "scripts/old/",
    "add_setup_route.py": "scripts/old/",
    "create_admin_router.py": "scripts/old/",
    "update_schemas.py": "scripts/old/",
    
    # Scripts de organização (meta-scripts)
    "organize_project.py": "scripts/old/",
    "organize_operations.py": "scripts/old/",
    "organize_utils.py": "scripts/old/",
}

def main():
    print("=" * 60)
    print("🗂️  ORGANIZADOR DE SCRIPTS DO PROJETO")
    print("=" * 60)
    
    # Verifica se estamos na raiz do projeto
    if not Path("app").exists():
        print("❌ Execute este script na raiz do projeto PortifolioManager!")
        return
    
    # Cria pastas se não existirem
    for folder in ["scripts/setup", "scripts/dev", "scripts/maintenance", "scripts/old", "scripts/docs"]:
        Path(folder).mkdir(parents=True, exist_ok=True)
    
    moved = 0
    skipped = 0
    not_found = 0
    
    print("\n📁 Movendo arquivos...\n")
    
    for filename, destination in FILE_MAPPING.items():
        source = PROJECT_ROOT / filename
        dest_folder = PROJECT_ROOT / destination
        dest_file = dest_folder / filename
        
        if not source.exists():
            print(f"  ⏭️  {filename} - não encontrado (já movido?)")
            not_found += 1
            continue
        
        if dest_file.exists():
            print(f"  ⚠️  {filename} - já existe em {destination}")
            skipped += 1
            continue
        
        try:
            shutil.move(str(source), str(dest_file))
            print(f"  ✅ {filename} → {destination}")
            moved += 1
        except Exception as e:
            print(f"  ❌ {filename} - erro: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 RESUMO:")
    print(f"   ✅ Movidos: {moved}")
    print(f"   ⏭️  Não encontrados: {not_found}")
    print(f"   ⚠️  Já existiam: {skipped}")
    print("=" * 60)
    
    # Estrutura final
    print("\n📂 ESTRUTURA FINAL DE SCRIPTS:")
    print("""
scripts/
├── setup/           # Configuração inicial do projeto
│   └── bootstrap.sh
├── dev/             # Desenvolvimento e debug
│   ├── start_server.sh
│   ├── check_routes.py
│   ├── create_sample_data.py
│   └── diagnostico_projeto.py
├── maintenance/     # Manutenção do sistema
│   ├── manage_users.py
│   ├── migrate_database.py
│   ├── upgrade_database.py
│   ├── setup_existing_portfolio.py
│   └── fix_global_classes.py
├── docs/            # Documentação (vazio por enquanto)
└── old/             # Scripts obsoletos/já executados
    └── (vários fix_*.py e outros)
""")
    
    print("\n✅ Organização concluída!")
    print("\n💡 Dica: Você pode deletar scripts/old/ se não precisar mais deles.")

if __name__ == "__main__":
    main()
