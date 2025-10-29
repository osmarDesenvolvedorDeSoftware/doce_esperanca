# Atualização do rodapé pelo painel administrativo

O rodapé público agora lê os dados diretamente do texto institucional **"Contato"**. Não é necessário editar arquivos HTML para atualizar endereço, telefone, mensagem de apoio ou links sociais.

## Onde alterar
1. Acesse o painel administrativo e entre em **Conteúdo > Textos Institucionais**.
2. Localize o item **Contato** (identificado como conteúdo institucional) e clique em **Editar**.
3. No formulário, preencha os campos específicos do rodapé:
   - **Texto de apoio** – frase curta exibida ao lado da logo no rodapé.
   - **Endereço** – pode usar quebras de linha para separar rua, bairro e cidade.
   - **Telefone** – número exibido e transformado em link para ligação.
   - **Facebook, Instagram, YouTube e WhatsApp** – informe a URL completa de cada rede.
4. O campo **Resumo** continua sendo o e-mail usado pelo formulário público de contato.
5. Salve as alterações. O sistema converte automaticamente os dados em JSON e armazena no campo `conteudo` do registro, sem necessidade de ajustes manuais.

## Como funciona
- Valores em branco utilizam os padrões exibidos no painel como placeholder (tagline, endereço, telefone e links).
- As informações são carregadas no rodapé de todas as páginas assim que o registro é salvo.
- Caso o conteúdo antigo do rodapé tenha sido editado manualmente, ele é substituído pelos campos estruturados. Não é preciso atualizar outros arquivos.

Com isso, todo o rodapé pode ser mantido pelo painel existente, mantendo compatibilidade com o fluxo atual de textos institucionais.
