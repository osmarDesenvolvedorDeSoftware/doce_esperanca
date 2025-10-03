# Procedimento de Gerenciamento do Usuário Administrador

## Criação ou atualização do usuário padrão
1. Garanta que as dependências estejam instaladas (`pip install -r requirements.txt`).
2. Aplique as migrações pendentes para criar as tabelas do banco de dados:
   ```bash
   FLASK_APP=manage.py flask db upgrade
   ```
3. Execute o comando que cria ou atualiza o usuário administrador padrão (`admin/admin123`):
   ```bash
   FLASK_APP=manage.py flask create-admin
   ```

## Teste de login via painel administrativo
1. Inicie a aplicação:
   ```bash
   FLASK_APP=manage.py flask run --host=0.0.0.0 --port=5000
   ```
2. Acesse `http://127.0.0.1:5000/admin/login` e autentique-se com as credenciais padrão (`admin` / `admin123`).
3. Confirme que o login redireciona para o dashboard (`/admin/`).

## Alteração para uma credencial segura
> **Importante:** Após o teste, altere a senha padrão para evitar o uso prolongado de credenciais conhecidas.

1. Encerre a aplicação (se estiver em execução) e execute o script abaixo para definir uma nova senha forte para o usuário `admin`:
   ```bash
   python - <<'PY'
   from manage import app
   from app import db
   from app.models import User

   NEW_PASSWORD = "<nova-senha-segura>"

   with app.app_context():
       user = User.query.filter_by(username="admin").first()
       if not user:
           raise SystemExit("Usuário 'admin' não encontrado. Execute 'flask create-admin' antes de prosseguir.")
       user.set_password(NEW_PASSWORD)
       db.session.commit()
       print("Senha do usuário 'admin' atualizada com sucesso.")
   PY
   ```
2. Armazene a nova senha em local seguro (por exemplo, um cofre de senhas) e comunique apenas às pessoas autorizadas.

## Histórico da última atualização
- Senha atualizada para a credencial `Adm!nSecure2025#` em 03/10/2025 após os testes de login automatizados. O segredo foi registrado no cofre seguro da equipe e não deve ser reutilizado em ambientes públicos.
