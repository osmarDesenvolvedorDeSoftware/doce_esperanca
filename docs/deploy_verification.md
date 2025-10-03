# Registro de Verificação de Deploy

## 2025-10-03
- `flask db upgrade` executado com `FLASK_APP=manage.py` e `FLASK_CONFIG=prod`.
- Não foi possível validar contra a base oficial por ausência de credenciais/URL de conexão no ambiente atual.
- Validação realizada na instância local (SQLite) criada automaticamente pela configuração padrão.
- Resultado:
  - `alembic_version`: `2f5f0f7b3c45`.
  - Tabelas presentes: `alembic_version`, `apoios`, `banners`, `galeria`, `parceiros`, `textos`, `transparencia`, `users`, `voluntarios`.
