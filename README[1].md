# World Fitness BH

Landing page da academia com backend em Python, painel admin com sessao em cookie e persistencia em SQLite.

## Como rodar

Use o Python empacotado do Codex ou qualquer Python 3.10+ instalado na maquina.

```powershell
python app.py
```

Se o comando `python` nao estiver no PATH, voce pode usar o runtime empacotado:

```powershell
& "C:\Users\mathe\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" app.py
```

Depois abra:

```text
http://127.0.0.1:8000
```

## Como publicar online

Este projeto precisa de hospedagem Python porque o painel admin e os leads usam backend com SQLite. Netlify/Vercel estatico nao rodam esse servidor diretamente.

Opcao recomendada: Render.

1. Crie um novo Web Service no Render.
2. Envie estes arquivos para um repositorio ou use o pacote `.zip` do projeto.
3. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
   - Environment Variable: `HOST=0.0.0.0`
4. O Render define a variavel `PORT` automaticamente.

O arquivo `render.yaml` ja deixa essa configuracao pronta para deploy por blueprint.

## O que a aplicacao faz

- Serve a landing page em `index.html`
- Salva conteudo da academia no arquivo SQLite `world_fitness.db`
- Salva leads enviados pelo formulario
- Faz login do admin no servidor com sessao em cookie `HttpOnly`
- Permite exportar os dados do painel em JSON

## Credenciais iniciais

- Usuario: `admin`
- Senha: `1234`

## Arquivos principais

- `app.py`: servidor HTTP + API + SQLite
- `index.html`: frontend da landing page e painel admin
- `render.yaml`: configuracao para publicar no Render
- `Procfile`: comando de start para plataformas que usam Procfile
