# Testes realizados — 17/09/2026

Ambiente: Linux, Python 3.12, FastAPI 0.141.1, SQLite e Chromium 153 headless. Bancos temporários separados do pacote e dos dados do usuário.

Resultado automatizado: **21 casos passaram** em `python -m pytest tests -q`. O tempo observado foi aproximadamente 0,6 s para a suíte de API e regras; isso não é benchmark de carga nem medição de desempenho no Windows.

| Função | Resultado esperado | Encontrado / status |
|---|---|---|
| Tabelas Super Pole/C1/C2, posições 1–11 | Valores iguais ao regulamento | Iguais — OK |
| Melhor volta e punição | 18 + 1 - 3 = 16 | 16 — OK |
| Super Pole com bônus | Recusar | Recusado — OK |
| Punição em segundos sem -3 | Recusar inconsistência | Recusado — OK |
| DNF, DNS, DSQ | Zero conforme estado/decisão | Zero — OK |
| DNF pontuando posição | Exigir decisão e pontuar | 18; sem decisão recusado — OK |
| Piloto/posição/melhor volta duplicados | Recusar | Recusado — OK |
| DSQ com melhor volta | Recusar | Recusado — OK |
| Visitante anônimo | Pedir identificação antes dos dados | HTTP 401 — OK |
| Visitante identificado | Consultar, sem editar ou acessar cadastro privado | Consulta 200; gravação/cadastro/backup 403 — OK |
| Chave incorreta | Não autorizar edição | 403 — OK |
| Vídeo e regulamento | Servir MP4 com Range e PDF | 206 e assinatura PDF — OK |
| Cadastro, edição, ativo/inativo | Persistir sem mudar ID, filtrar disponíveis | OK |
| Grupos | Salvar e carregar; proteger após baterias | OK |
| Calcular/salvar/reabrir/corrigir | Mesmo ID; pontos mantidos | OK |
| Versão desatualizada | Evitar sobrescrita de outra revisão | Recusado — OK |
| Nova cópia da mesma bateria | Não duplicar pontos | Recusada — OK |
| Criação de nova etapa | Preservar anterior; recusar nome/data duplicados | OK |
| Nova conexão/reinicialização do banco | Resultados preservados | 3 registros preservados — OK |
| Consolidação | 11 + 18 + 18 = 47 | 47 — OK |
| Sessão faltante/participantes diferentes | Bloquear final | Bloqueado — OK |
| Desempate | Menor melhor volta vence | 58 s antes de 60 s — OK |
| Final completo isolado | PDF disponível | PDF válido — OK |
| Backup/exclusão | SQLite íntegro e cópia antes da exclusão | OK |
| Notas globais e resolvidas | Salvar/marcar/consultar | OK |
| Meteorologia sem rede | Mostrar indisponível; cálculo independente | OK |
| Meteorologia com resposta simulada | Extrair probabilidade da hora atual | 20% — OK |
| Migração de tabela antiga | Preservar registro/ID | OK |
| Requisição de origem externa | Bloquear gravação | 403 — OK |

## Interface real no Chromium

Executados login de organizador, cadastro e edição de piloto, organização de grupo, carregar bateria, calcular 18 pontos, salvar, reabrir, acesso de visitante e mudança de viewport para 390 px. Nenhum erro de JavaScript foi registrado. Não houve rolagem horizontal da página na viewport móvel. O primeiro teste visual usou um seletor exato que incluía o rótulo “Disponível”; ajustado o seletor de teste, o fluxo passou sem alteração funcional.

Capturas `dashboard.png` e `mobile.png` documentam a revisão visual. PDF final renderizado e inspecionado: cabeçalhos, tabela e rodapé legíveis, sem cortes ou sobreposição. O protótipo tinha destaque vermelho/dourado; interface atual usa amarelo e logo vetorial.

## Limites da validação

- Atalhos BAT e abertura automática do Chrome no Windows: **não executados neste ambiente Linux**. Código revisado.
- Cloudflare Tunnel e link público: **não iniciados no computador do usuário**. O script gera o link quando executado ali. Não foi feita validação externa de conectividade.
- Meteorologia real: **não confirmada**; coordenadas exatas não verificadas. A integração foi testada com resposta simulada e erro de rede.
- MP4: carregamento e requisição parcial verificados; não é uma revisão da fidelidade esportiva do traçado.
- Descarte do campeonato: **não implementado**; não é coberto como regra aprovada.
- Não foram feitos testes de carga com dezenas de conexões, antivírus/firewall do Windows, queda abrupta de energia ou compatibilidade com todo banco legado possível.
- Esses limites impedem afirmar “100% testado”, “extremamente rápido” ou homologação integral para premiação do campeonato. O uso real deve começar com uma cópia de teste do banco e conferência da organização.

## Revisão Web 3.2 Mobile — 19/09/2026

- `node --check static/app.js`: aprovado.
- `node --check static/upgrade.js`: aprovado.
- `python3 -m pytest -q`: **21 testes aprovados**.
- Revisão visual estática em Chromium headless, viewport **390 × 844 px**: dashboard e bateria sem overflow horizontal.
- Verificação de `scrollWidth <= innerWidth` nas views: Baterias, Pilotos, Resultados, Grupos, Notas e Configurações — aprovada em 390 px.
- Capturas adicionadas: `docs/mobile_3_2.png` e `docs/mobile_bateria_3_2.png`.
- O smoke test completo contra `127.0.0.1` não pôde ser reexecutado neste ambiente porque o navegador headless bloqueou localhost por política administrativa (`ERR_BLOCKED_BY_ADMINISTRATOR`). A suíte Python e as validações estáticas/JS foram executadas normalmente.
