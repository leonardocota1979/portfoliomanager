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

## Segurança
Recomendações:
- Defina `COOKIE_SECURE=true` em produção
- Troque as chaves de API periodicamente
- Restrinja acesso ao servidor
