#!/usr/bin/env python3

print("="*60)
print("🔧 CONFIGURAR PORTFOLIO EXISTENTE")
print("="*60)

from app.database import SessionLocal, Portfolio, AssetClass, GlobalAssetClass

db = SessionLocal()

# Lista portfolios
portfolios = db.query(Portfolio).all()

if not portfolios:
    print("❌ Nenhum portfolio encontrado!")
    db.close()
    exit()

print("\n📂 Portfolios disponíveis:")
for i, p in enumerate(portfolios, 1):
    print(f"  {i}. {p.name} (ID: {p.id}) - Valor: ${p.total_value:,.2f}")

escolha = input("\n👉 Qual portfolio você quer configurar? (número): ")

try:
    idx = int(escolha) - 1
    portfolio = portfolios[idx]
except:
    print("❌ Escolha inválida!")
    db.close()
    exit()

print(f"\n✅ Selecionado: {portfolio.name}")

# Define valor total
print("\n💰 Definir Valor Total:")
valor = input("Digite o valor total do portfolio (ex: 1000000): ")

try:
    portfolio.total_value = float(valor)
    print(f"✅ Valor definido: ${portfolio.total_value:,.2f}")
except:
    print("❌ Valor inválido!")
    db.close()
    exit()

# Define moeda
moedas = ["USD", "BRL", "EUR"]
print(f"\n💵 Moeda atual: {portfolio.currency}")
print("Moedas disponíveis: USD, BRL, EUR")
moeda = input("Mudar moeda? (deixe vazio para manter USD): ").upper() or "USD"

if moeda in moedas:
    portfolio.currency = moeda
    print(f"✅ Moeda: {portfolio.currency}")

db.commit()

# Configurar classes
print("\n" + "="*60)
print("📊 CONFIGURAR CLASSES DE ATIVOS")
print("="*60)

global_classes = db.query(GlobalAssetClass).all()

print("\n📋 Classes disponíveis:")
for cls in global_classes:
    print(f"  • {cls.name} - {cls.description}")

print("\n⚠️  A soma dos percentuais deve ser 100%")
print("\n👉 Digite o percentual para cada classe (0 para pular):\n")

total_pct = 0
classes_config = []

for cls in global_classes:
    while True:
        try:
            pct = float(input(f"  {cls.name} (%): ") or "0")
            if pct >= 0 and pct <= 100:
                if pct > 0:
                    classes_config.append({"class": cls, "percentage": pct})
                    total_pct += pct
                break
            else:
                print("    ❌ Digite um valor entre 0 e 100")
        except:
            print("    ❌ Valor inválido")

print(f"\n📊 Total: {total_pct}%")

if total_pct != 100:
    print(f"❌ A soma deve ser 100%, não {total_pct}%")
    confirma = input("Deseja continuar mesmo assim? (s/N): ")
    if confirma.lower() != 's':
        print("Cancelado!")
        db.close()
        exit()

# Cria as classes no portfolio
print("\n🔨 Criando classes no portfolio...")

for config in classes_config:
    # Verifica se já existe
    existing = db.query(AssetClass).filter(
        AssetClass.portfolio_id == portfolio.id,
        AssetClass.name == config["class"].name
    ).first()
    
    if not existing:
        asset_class = AssetClass(
            name=config["class"].name,
            target_percentage=config["percentage"],
            rebalance_threshold_percentage=5.0,
            portfolio_id=portfolio.id,
            is_custom=False,
            pending_approval=False
        )
        db.add(asset_class)
        print(f"  ✅ {config['class'].name}: {config['percentage']}%")
    else:
        existing.target_percentage = config["percentage"]
        print(f"  🔄 {config['class'].name}: {config['percentage']}% (atualizado)")

db.commit()

print("\n" + "="*60)
print("✅ PORTFOLIO CONFIGURADO COM SUCESSO!")
print("="*60)
print(f"\n📊 {portfolio.name}")
print(f"💰 Valor Total: ${portfolio.total_value:,.2f} {portfolio.currency}")
print(f"📋 Classes configuradas: {len(classes_config)}")

db.close()

print("\n👉 Agora rode: python3 create_sample_data.py")
print("="*60)

