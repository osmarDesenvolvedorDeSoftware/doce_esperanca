# Doce Esperança

Este repositório contém a aplicação Flask da ONG Doce Esperança.

## Deploy com Gunicorn

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
