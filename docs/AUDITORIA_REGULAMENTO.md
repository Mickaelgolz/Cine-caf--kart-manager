# Auditoria funcional — regulamento 2026

Fonte: PDF fornecido “GRANDE PRÊMIO CINE CAFÉ DE KART RENTAL – REGULAMENTO GERAL”, 4 páginas. Revisão desta auditoria: 17/09/2026. O documento não informa um identificador de revisão. Trata-se de comparação de regras esportivas com o software, não de validação jurídica do regulamento.

| Regra / fonte | Comportamento de origem | Implementação / decisão nesta versão | Situação |
|---|---|---|---|
| §7: Super Pole 11,10,9,8,7,6,5,4,3,2,1 | Tabela correta | `core/scoring.py`, `core/heat_calculator.py`; bônus/punição de corrida recusados na Super Pole | Testada |
| §9: C1/C2 18,15,13,11,9,7,5,4,3,2,1 | Tabela correta | Mesma fonte para cálculo, gravação e PDF | Testada |
| §9: +1 melhor volta da corrida | Marca manual | Exatamente uma marca; DNS/DSQ recusados; sem bônus na Super Pole | Testada |
| §10: punição implica perda de 3 pontos na corrida | Booleano -3 | Preservado -3 por piloto punido na corrida. O texto não define acúmulo por ocorrência; não foi inventado -3 multiplicado | Testada; confirmar direção se houver múltiplas ocorrências |
| §10: +5/+10/+15 segundos | Não representado na interface web | Campo de segundos e motivo. **Posição oficial deve ser lançada já corrigida** pela direção. Sem tempo total da corrida, não há reordenação automática | Implementação parcial, controle humano |
| §10: desclassificação por peso/bandeiras etc. | DSQ zerava pontos | DSQ zero, sem melhor volta; decisão esportiva continua com direção | Testada |
| DNF/DNS | Opção de regra DNF sem fundamentação visível | PDF não estabelece regra. Exigir texto da decisão. DNF pode pontuar posição ou zero; DNS zero conforme decisão registrada | Caso omisso, precisa decisão humana |
| §9: desempate pela melhor volta geral | Empate por total e ordenação de nome | Registro de milissegundos, menor volta geral entre registros válidos; nomes usados só para exibição estável. Falta de tempo ou tempos iguais bloqueia PDF final | Testada |
| §3: 90/110 kg; 22 vagas, 11 por grupo; quantidades podem variar | Organização não exposta na versão web | Grupos A–J persistentes. Mostra referência de 11, sem limite rígido que contrarie a flexibilização expressa | Testada |
| §3: grupos conforme pontuação; novos em B/C | Não integrado na web | Organização manual preservada; organizador deve usar classificação e colocar estreantes em B/C. Não há distribuição automática regulamentar | Controle humano |
| §8: duas corridas de 15 minutos | Tipos já existentes | Consolidação exige Super Pole, C1 e C2 por grupo conhecido; duração e operação em pista são humanas | Testada para completude |
| §8: C1 grid pela Super Pole; C2 inverte grid e kart | Não exposto | Esta versão lança **resultados**, não opera sorteio/troca de karts nem produz grid oficial invertido. Organização aplica em pista | Fora da automação implementada |
| Resultado da etapa | Cálculos web e classificação usavam fontes diferentes | `heat_calculations` é a fonte usada pelo histórico, consolidação e soma do dashboard. Revisões legadas: última por evento/categoria/grupo/sessão | Testada |
| Pilotos diferentes entre sessões / duplicados entre grupos | Parcialmente validado | Comparação de conjuntos e IDs, bloqueio do resultado final em inconsistência | Testada |
| §1: descarte do pior resultado de uma etapa, exceto final | Saldo inicial acumulado sem discriminação suficiente | **Não implementado automaticamente nesta versão.** Dashboard identificado como parcial sem descarte. É necessário obter histórico por etapa, marcar a final e implementar/reconciliar esse fechamento | Pendente; não declarar campeão oficial a partir do dashboard |
| Saldo inicial das imagens | Valores já embutidos no código de origem | Preservados; imagens não convertidas em etapas fictícias. Nomes e inscrições adicionais do projeto foram preservados | Requer reconciliação se banco importado repetir pontos no saldo |
| §2/4/5/6/10/11/12: idade, inscrição, reembolso, chegada, pesagem, comportamento e premiação | Sem automação | PDF íntegro disponível para consulta. Fiscalização e decisões permanecem com organização | Controle humano |

## Preservação e auditoria técnica

- `core/heat_calculator.py`: pontuação e consolidação; tabelas em `core/scoring.py`.
- `web_services.py`: migração, gravação com revisão, validação final, grupos e permissões.
- `core/heat_reports.py`: PDF da bateria e da etapa.
- `docs/regulamento.pdf`: fonte integral local.
- Notas ao desenvolvedor não são usadas para decisões esportivas; decisões DNF/DNS pertencem ao registro do piloto na bateria.
- Migração mantém tabelas legadas e registros anteriores. IDs de pilotos não mudam ao editar nome/status. Backups antecedem migração, correção e exclusão.

**Conclusão de escopo:** há um fluxo testado de organização, lançamento, gravação e resultado final de etapa. Não há conformidade integral automatizada do campeonato: descarte, regras operacionais em pista, grupos por ranking e casos omissos dependem das ações descritas acima.
