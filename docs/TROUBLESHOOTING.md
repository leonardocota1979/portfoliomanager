# Troubleshooting

## Não sobe o serviço
Verifique:
- `./devctl.sh` com venv ativo
- Dependências instaladas
- Porta liberada
- `DATABASE_URL` apontando para `data/portfoliomanager.db`

## "Não foi possível validar as credenciais"
Causa: usuário não autenticado.
Solução:
- faça login novamente
- limpe cookies se necessário

## OCR não reconhece texto
Verifique:
- `OCR_CMD` apontando para o tesseract
- `OCR_LANG=eng+por`
- imagem nítida

## Preços zerados
Verifique:
- chaves de API válidas
- ticker correto
- conexão internet
