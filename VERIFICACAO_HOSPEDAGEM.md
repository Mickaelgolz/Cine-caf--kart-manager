# Verificação de hospedagem — CineCafe Web 3.2.0 Mobile

Verificado em 21/09/2026.

## Estrutura confirmada

- `templates/index.html` — interface principal
- `static/app.css` — estilos
- `static/app.js` — lógica da interface
- `static/upgrade.js` — melhorias da versão
- `static/tracado.mp4` — vídeo do traçado
- `docs/regulamento.pdf` — regulamento
- `main.py` — API FastAPI
- `web_services.py` — autenticação, grupos, visitantes, meteorologia, backup e outras rotas
- `core/database.py` — banco SQLite e persistência local
- `requirements-web.txt` — dependências Python
- `README.md` — instruções do projeto
- `CHANGELOG.md` — alterações da versão
- `docs/TESTES_REALIZADOS.md` — documentação de testes
- `docs/AUDITORIA_REGULAMENTO.md` — auditoria do regulamento

## Testes

Executado:

`python -m pytest tests -q`

Resultado: **21 testes aprovados**.

## Importante sobre Netlify

Este projeto **não é um site estático**. Ele usa FastAPI/Python e SQLite no servidor.

Por isso, o ZIP completo **não funciona no Netlify Drop como aplicação completa**. O Netlify pode publicar os arquivos estáticos, mas o backend Python (`main.py`) e o banco SQLite não serão executados pelo deploy estático.

Para manter cadastro, login, baterias, resultados, backups e alterações persistentes, é necessário hospedar o backend em um serviço que execute Python e mantenha os dados de forma persistente, ou migrar o banco para um serviço externo.
