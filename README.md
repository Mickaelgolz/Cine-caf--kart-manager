
## Interface móvel (Web 3.2 Mobile)

A interface foi revisada para operação em smartphones: navegação inferior, menu lateral por toque, formulários empilhados, tabelas convertidas em cards nas telas estreitas, modais em formato bottom sheet e suporte a safe-area do iPhone. A lógica de pontuação e o banco permanecem os mesmos da versão 3.1.

# CineCafe Kart Manager — Web 3.2.0 Mobile

Aplicativo para abrir no Google Chrome, com servidor Python e banco SQLite no computador do organizador. Versão única, com acesso de consulta para visitantes e edição para o organizador.

## Comece aqui — Windows 10/11 de 64 bits

1. Extraia TODO o ZIP para uma pasta própria, por exemplo `C:\CineCafe`. Não execute dentro do ZIP.
2. Na primeira utilização, abra `INSTALAR_WEB.bat`. É necessário Python 3.11 ou superior (https://www.python.org/downloads/windows/) e internet para baixar as dependências. A instalação cria um ambiente isolado `.venv` dentro da pasta.
3. Abra `INICIAR_WEB.bat`. O Chrome abre automaticamente quando instalado; caso contrário, abre o navegador padrão. Endereço local: **http://127.0.0.1:8765**.
4. Informe seu nome. Para editar, abra “Sou organizador” e use a chave que aparece no Bloco de Notas. Ela fica em `data/CHAVE_ORGANIZADOR.txt`; o atalho `VER_CHAVE_ORGANIZADOR.bat` abre esse arquivo novamente.
5. Mantenha a janela do servidor aberta enquanto usa o sistema. Para encerrar, pressione Ctrl+C nela.

Este pacote é código executável em Python, não um `.exe` autônomo e não inclui Python para Windows. A preparação inicial requer internet. Depois dela, cálculo, cadastro, salvamento, vídeo e PDF funcionam sem internet.

## Compartilhar com outras pessoas

Com o programa aberto, execute **COMPARTILHAR.bat**. Na primeira vez, ele baixa `cloudflared` do repositório oficial da Cloudflare. Requer Windows x64 e internet.

O terminal mostrará um endereço `https://…trycloudflare.com`. Esse é o link para compartilhar; ele também é gravado em `LINK_PARA_COMPARTILHAR.txt`. Envie somente esse link, nunca a chave do organizador.

O visitante informa seu nome e consulta dashboard, histórico, consolidação, vídeo e regulamento. Nome e horário são registrados. O nome informado não é uma identidade verificada. Cadastro, notas, configuração e dados pessoais ficam restritos ao organizador.

O computador deve continuar ligado, conectado à internet e com **as duas janelas abertas**. O endereço muda ao reiniciar o túnel. Fechar a janela do compartilhamento interrompe o acesso externo, mas não o uso local.

O link não vem pronto no ZIP: precisa ser gerado no computador que hospeda. Os arquivos BAT foram revisados, mas não executados em Windows nesta entrega; a conexão externa também depende da rede local. Quick Tunnels são temporários e não têm garantia de disponibilidade. Para uso público contínuo, configure um túnel gerenciado e domínio próprio.

Referência oficial: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/

## Fluxo do campeonato

1. **Configurações**: confira nome, data `DD/MM/AAAA` e local. Para uma nova etapa, preencha os campos e clique em “Criar nova etapa”. A anterior fica no histórico.
2. **Pilotos**: cadastre ou edite com duplo clique (ou botão Editar). Clique em Ativo/Inativo para alternar sem apagar histórico. Categorias no cadastro adicionam inscrições; inscrições antigas não são removidas automaticamente.
3. **Grupos**: escolha evento, categoria e grupo A–J. Marque participantes e salve. Selecionar piloto de outro grupo o move. Desmarcar o retira. A referência é 11 pilotos; o regulamento permite variar a quantidade. A organização fica protegida depois que houver resultados na categoria.
4. **Baterias**: ao mudar categoria/grupo/sessão, carregam-se os participantes ou a bateria já salva. Lance a classificação oficial, situação e melhor volta. **Calcular** exibe pontos; **Salvar resultado** grava no SQLite. Ctrl+S também salva.
5. **Resultados**: abra para corrigir. Salvar uma correção atualiza o mesmo registro, com backup; uma versão desatualizada é recusada para não sobrescrever a correção de outro operador.
6. Selecione um evento e clique em **Consolidar etapa**. Pendências aparecem explicitamente. O PDF final é liberado somente quando a etapa está completa e sem desempates pendentes.
7. **Notas do desenvolvedor**: registre erros e melhorias; marque Resolvido ou Reabrir. São globais, não observações esportivas.

## Regras e limites relevantes

- Super Pole: 11 a 1 ponto. Corridas: 18, 15, 13, 11, 9, 7, 5, 4, 3, 2, 1. Melhor volta nas corridas: +1. Uma marca de punição: -3.
- **Punições em tempo**: informe os segundos e a **posição oficial já corrigida** pela direção/cronometragem. O sistema não recalcula a ordem por tempo total, pois esse dado não existe no arquivo original.
- **DNF/DNS**: o regulamento não fixa a regra. É obrigatório registrar uma decisão da direção. DNF pode pontuar a posição ou zero; DNS/DSQ ficam com zero.
- **Desempate**: melhor volta geral em milissegundos, inserida como segundos na tela. Se faltarem tempos ou o empate persistir, o PDF final é bloqueado.
- **Campeonato**: o dashboard soma o saldo anterior do programa e as baterias lançadas, identificando o resultado como parcial **sem descarte**. As imagens fornecidas não trazem pontos por etapa nem tempos. Não é possível aplicar com confiabilidade o descarte de uma etapa (exceto a final) a esse saldo acumulado. O fechamento oficial do campeonato com descarte permanece pendente do histórico detalhado e de sua implementação; não confundir com o resultado final de cada etapa, que está disponível.
- **Meteorologia**: integração Open-Meteo com cache de 10 minutos, falha isolada do cálculo. Não foi possível verificar as coordenadas exatas do kartódromo. Informe latitude/longitude confirmadas em Configurações. Nenhum ponto aproximado é apresentado como se fosse o kartódromo. A consulta real não foi validada nesta rede; testes cobriram retorno simulado e falta de internet.
- O regulamento e o vídeo enviados estão incluídos em `docs/regulamento.pdf` e `static/tracado.mp4`.

## Seus dados e atualização

Banco: `data/apresentacao_v12.db`. Backups: `data/backups`. Logs: `data/cinecafe.log`. A chave do organizador é criada individualmente no primeiro uso; não é incluída na distribuição.

O ZIP de origem não contém banco de resultados. Sem banco importado, é mantida a carga inicial de pilotos/pontos existente no código original. Não houve invenção de resultados das etapas anteriores.

Para trazer seu banco, feche o programa e o compartilhamento e execute `MIGRAR_DADOS_EXISTENTES.bat`, escolhendo o banco antigo. O procedimento verifica integridade e cria backup do destino. Sempre guarde uma cópia externa da pasta `data` antes de atualizar. Nunca copie um `.db` isolado enquanto o programa está gravando; use o botão **Baixar backup** ou feche o programa primeiro.

A migração renomeia a antiga tabela de cálculos para `heat_calculations`, preserva seus IDs e importa sessões legadas concluídas que não têm equivalente. As tabelas legadas permanecem para recuperação; os resultados web e a classificação usam a mesma fonte. Saldo inicial é tratado como anterior às baterias importadas: se seu banco antigo já embutir essas baterias no saldo, faça reconciliação antes de usar a classificação acumulada.

## Verificação

`python -m pip install pytest httpx` e `python -m pytest tests -q`.

Teste de navegador opcional: instale `playwright`, execute `python -m playwright install chromium` e `python tests/browser_smoke.py` (ou defina `CINECAFE_BROWSER` para um executável Chromium).

Leia `docs/TESTES_REALIZADOS.md`, `docs/AUDITORIA_REGULAMENTO.md` e `CHANGELOG.md`. Testes usam pasta temporária, não o banco real. Capturas de revisão visual estão em `docs`.
