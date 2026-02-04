# Administração e Segurança

## Usuários
O sistema utiliza autenticação com JWT via cookies.

## Admin
Para criar/promover admin:
- Use o script `scripts/create_admin.py`

Exemplo:
```bash
source venv/bin/activate
python scripts/create_admin.py --username admin --password sua_senha --email admin@email.com
```

## Gestão online de usuários
Rota administrativa (apenas admin):
```
/admin/users
```
Nela é possível criar, editar, resetar senha e remover usuários.

Recursos adicionais:
- Busca por username/email
- Paginação
- Proteção contra remoção do próprio admin logado

## Bootstrap de admin (produção)
Se o ambiente estiver vazio, defina no deploy:
- `ADMIN_BOOTSTRAP_USER`
- `ADMIN_BOOTSTRAP_PASS`
- `ADMIN_BOOTSTRAP_EMAIL`

O sistema cria o admin automaticamente na primeira subida.  
Se o usuário já existir, o sistema força **is_admin = true** e **reseta a senha** para a informada.

## Segurança
Recomendações:
- Defina `COOKIE_SECURE=true` em produção
- Troque as chaves de API periodicamente
- Restrinja acesso ao servidor
