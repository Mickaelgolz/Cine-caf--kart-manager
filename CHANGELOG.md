# 3.1.0 — 17/09/2026

- Mantidos Python, FastAPI, SQLite, cálculo e relatórios existentes. Interface única com identidade preta, amarela e branca, logo vetorial, layout responsivo e vídeo fornecido no dashboard.
- Entrada por nome, sessão em cookie HttpOnly e chave local para organização. Visitantes consultam, sem acesso a dados pessoais ou gravação. Funções de edição são verificadas no servidor, não apenas escondidas na tela.
- Uma fonte web de resultados: migração preserva cálculos antigos e incorpora sessões legadas concluídas sem equivalente. Nenhuma tabela histórica é descartada.
- Correções mantêm o ID da bateria, criam backup e verificam a versão antes de gravar. Novas duplicatas da mesma bateria são recusadas. Revisões legadas continuam consolidadas pela última gravação.
- Grupos persistentes por evento/categoria, movimentação e carregamento direto nas baterias. Bloqueio da reorganização depois de resultados salvos evita inconsistências.
- Cadastro com duplo clique e botão acessível no celular; ativação com um clique; campos número, telefone, CPF e cidade. Histórico usa ID estável.
- Consolidação compara participantes entre sessões e grupos. Incompletudes e empates pendentes impedem PDF final.
- Melhor volta geral passa a desempatar pontos; notas documentam decisões da direção para casos omissos. Penalidade em segundos é registrada, mantendo entrada da classificação oficial já corrigida.
- Dashboard soma a mesma fonte de baterias, exibe o acumulado como parcial sem descarte. Não presume etapas anteriores a partir de imagens acumuladas.
- Notas globais com status resolvido; regulamento PDF disponível; meteorologia independente e configurável, sem coordenadas inventadas.
- Banco com WAL e espera por escrita; exportações PDF têm nomes únicos para evitar colisão entre acessos. Backup SQLite captura também dados confirmados em WAL.
- Atalhos Windows para instalar ambiente isolado, abrir no Chrome, ver chave e gerar túnel temporário.

## Escolhas e pendências

A edição no servidor foi protegida por chave, mantendo o simples pedido de nome para os visitantes, pois um nome sozinho não autoriza alteração de resultados. “Organizador/visitante” representa permissões de uso da mesma versão, sem recursos comerciais bloqueados.

A antiga estrutura foi preservada por migração aditiva, em vez de apagar dados. O descarte do campeonato não foi inferido do saldo acumulado. Coordenadas, consulta meteorológica real, execução no Windows e túnel externo exigem validação no ambiente de hospedagem. Detalhes no README e na auditoria.

## Web 3.2 Mobile — 19/09/2026
- Interface touch-first para celulares iOS e Android.
- Barra de navegação inferior nas telas pequenas.
- Menu lateral com overlay e fechamento por toque.
- Baterias, pilotos, resultados e consolidado passam a usar cards legíveis no celular.
- Modais convertidos em bottom sheets no mobile.
- Campos com 16 px para evitar zoom automático no iPhone.
- Botões e áreas de toque ampliados para aproximadamente 44 px ou mais.
- Ajustes de safe-area para iPhones com notch/Dynamic Island.
- Dashboard, vídeo, clima, programação e formulários reorganizados para telas estreitas.
