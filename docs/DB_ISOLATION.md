# Isolamento de Banco por Schema (PostgreSQL)

## Propósito
Este projeto usa isolamento por schema para compartilhar o mesmo PostgreSQL com outros sistemas sem misturar tabelas.

## Schema deste projeto
- Schema oficial: `portfolio_manager`
- Variável de ambiente: `DB_SCHEMA=portfolio_manager`

## Convivência com outros sistemas no mesmo Postgres
- Cada sistema deve usar schema próprio (`app_a`, `app_b`, etc.).
- Este sistema força `search_path` para `DB_SCHEMA` na conexão Postgres.
- Tabelas criadas por `create_db_and_tables()` ficam no schema ativo do projeto.
- O nome técnico do banco (`portfoliomanager_db`) pode permanecer; o isolamento acontece no nível de schema.

## Impacto de `ENFORCE_DB_SCHEMA`
- `ENFORCE_DB_SCHEMA=true`:
  - No startup, o sistema valida `current_schema()`.
  - Se o schema ativo for diferente de `DB_SCHEMA`, o startup falha com erro claro.
- `ENFORCE_DB_SCHEMA=false`:
  - O sistema tenta usar `DB_SCHEMA`, mas não bloqueia startup quando há divergência.

## Checklist de diagnóstico (falha por schema incorreto)
1. Verifique `DATABASE_URL` no ambiente (Render): deve apontar para o **Internal Database URL** do `General-db`.
2. Verifique `DB_SCHEMA`: deve ser `portfolio_manager`.
3. Verifique `ENFORCE_DB_SCHEMA`: recomendado `true`.
4. Confirme formato do schema:
   - somente `[a-zA-Z0-9_]`
   - deve iniciar com letra ou `_`
5. Confira logs de startup:
   - erro esperado quando divergente: `Schema ativo divergente. Esperado=... Atual=...`
6. Se necessário, valide direto no Postgres:
   - `SELECT current_schema();`
   - `SHOW search_path;`
7. Após ajuste de env no Render, faça `Manual Deploy -> Deploy latest commit`.

## Observação sobre SQLite local
- Em ambiente local com SQLite, `DB_SCHEMA` não se aplica.
- O fluxo local permanece funcional com `DATABASE_URL=sqlite:///./data/portfoliomanager.db`.
