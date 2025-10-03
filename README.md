# Doce Esperança

Este repositório contém a aplicação Flask da ONG Doce Esperança.

## Deploy com Gunicorn

Antes do deploy, instale as dependências listadas no `requirements.txt` (incluindo o
driver PostgreSQL `psycopg2-binary`) com o comando:

```bash
pip install -r requirements.txt
```

Para executar a aplicação em produção utilizando o Gunicorn, certifique-se de que as
dependências estão instaladas e execute o comando abaixo no diretório raiz do projeto:

```bash
gunicorn wsgi:app
```

Para testes locais, você pode expor a aplicação vinculando-a a todas as interfaces de
rede:

```bash
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

O módulo `wsgi.py` carrega a aplicação com a configuração de produção (`config.ProdConfig`).

## Configuração de variáveis de ambiente

Defina o `SECRET_KEY` em um arquivo `.env` ou diretamente no ambiente antes de iniciar a aplicação. Utilize um valor forte e aleatório; consulte o guia em `docs/secret_key_rotation.md` para instruções de geração e rotação.

Configure também a variável `DATABASE_URL` apontando para a instância PostgreSQL utilizada no deploy. A aplicação espera uma string de conexão no formato:

```
postgresql://<usuario>:<senha>@<host>:5434/<nome_do_banco>
```

Substitua `<usuario>` e `<senha>` pelos valores corretos do ambiente de produção. Armazene essas credenciais apenas em variáveis de ambiente seguras (por exemplo, secrets do provedor de deploy) e evite versioná-las em repositórios públicos.
