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

## Cache busting para arquivos estáticos

Os templates utilizam o helper `static_url` para gerar URLs versionadas dos arquivos em
`app/static/`. O helper adiciona automaticamente um parâmetro `v` baseado no timestamp da
última modificação do arquivo, garantindo que o navegador baixe uma nova versão sempre
que o conteúdo for atualizado, ao mesmo tempo em que permite cache agressivo para os
arquivos que não mudaram.

### Sugestão de configuração Nginx

Ao servir a aplicação com Nginx, habilite cache de longo prazo para o diretório `static`
aproveitando o versionamento via query string:

```nginx
location /static/ {
    alias /caminho/absoluto/para/app/static/;
    expires 30d;
    add_header Cache-Control "public, max-age=2592000, immutable";
    try_files $uri =404;
}
```

Com essa configuração, o Nginx mantém os arquivos estáticos em cache por 30 dias. Quando
um arquivo é atualizado, o parâmetro `v` muda e o navegador solicita novamente o recurso,
evitando problemas de conteúdo desatualizado.

## Configuração de variáveis de ambiente

Defina o `SECRET_KEY` em um arquivo `.env` ou diretamente no ambiente antes de iniciar a aplicação. Utilize um valor forte e aleatório; consulte o guia em `docs/secret_key_rotation.md` para instruções de geração e rotação.

Configure também a variável `DATABASE_URL` apontando para a instância PostgreSQL utilizada no deploy. A aplicação espera uma string de conexão no formato:

```
postgresql://<usuario>:<senha>@<host>:5434/<nome_do_banco>
```

Substitua `<usuario>` e `<senha>` pelos valores corretos do ambiente de produção. Armazene essas credenciais apenas em variáveis de ambiente seguras (por exemplo, secrets do provedor de deploy) e evite versioná-las em repositórios públicos.
