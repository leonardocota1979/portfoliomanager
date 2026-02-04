#!/usr/bin/env python3
from app.database import SessionLocal
from app import crud, schemas

def list_users():
    db = SessionLocal()
    users = crud.get_users(db)
    
    if not users:
        print("❌ Nenhum usuário encontrado!")
    else:
        print(f"\n✅ Usuários ({len(users)}):")
        for user in users:
            print(f"  - {user.username} | {user.email}")
    
    db.close()

def create_user(username, email, password):
    db = SessionLocal()
    existing = crud.get_user_by_username(db, username)
    
    if existing:
        print(f"❌ Usuário '{username}' já existe!")
        db.close()
        return False
    
    user_data = schemas.UserCreate(username=username, email=email, password=password)
    
    try:
        user = crud.create_user(db, user_data)
        print(f"✅ Usuário '{user.username}' criado!")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.close()
        return False

if __name__ == "__main__":
    print("="*50)
    print("GERENCIADOR DE USUÁRIOS")
    print("="*50)
    list_users()
    print("\n🔧 Criando usuário admin...")
    create_user("admin", "admin@test.com", "admin123")
    list_users()
    print("\n✅ Use 'admin' / 'admin123' para login")
    print("="*50)
