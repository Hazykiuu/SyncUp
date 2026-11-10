# Changelog — SyncUp

## [1.5.1] — 2026-11-10

Correções de uma auditoria de segurança e resiliência.

### Corrigido
- **ListenBrainz**: um 429 (serviço ocupado) não derruba mais a coleta na hora; o SyncUp tenta de novo até 3 vezes, esperando o tempo que o servidor pede.
- **App do navegador**: arquivo de mais de 64 MB dentro do ZIP é recusado com uma mensagem clara, em vez de fechar a aba no celular; a conferência de partes repetidas ficou 8× mais rápida.
- Aviso de depreciação do NumPy no perfil de gosto.

### Segurança
- A página de resposta do login do Spotify escapa o texto sozinha, em vez de depender de cada chamada lembrar disso.

### Documentação
- `salvar_perfil()`: o nome é a identidade do perfil ("Ana" e "ana" são a mesma pessoa); a docstring prometia outra coisa.
- README: como gerar os arquivos do app do navegador para rodar `site/` localmente.

## [1.5.0] — 2026-11-09

Wrapped do app no navegador sem baixar o Python: monta em segundos, até em celular simples.

### Mudado
- **Wrapped em JavaScript**: a aba Wrapped lê o ZIP e calcula tudo em JS, num Worker próprio, com as mesmas regras do núcleo em Python. O Python (Pyodide) só baixa quando a aba Dupla é aberta. Histórico fictício de 300 mil eventos: 2,4 s no Redmi Note 15 (antes 29,9 s + 24,9 s para baixar o motor) e 1,5 s no PC (antes 9,4 s).
- **Empates com regra fixa** (vale também para o app local): artista do dia recorde e plataformas em ordem alfabética, dia da semana favorito de segunda a domingo, a sequência de dias mais antiga e o menor ID da faixa. Antes, a ordem do pandas nos empates podia variar.
- "Como o arquétipo foi calculado" é desenhado pelo app (sem HTML pronto) e a demo do Wrapped usa um histórico fictício baixado só ao clicar.
- Nota "Montado em X s" abaixo dos stories.
- Navegador sem suporte para abrir ZIP (iPhone abaixo do iOS 16.4) recebe o aviso para atualizar.

### Corrigido
- O aviso "Carregando o SyncUp…" sobrava no rodapé do app web.
- Percentuais terminados em 5 arredondam como no Python (6,25% → 6,2%).

### Testes
- Teste de paridade: o mesmo arquivo passa pelo Python e pelo JS (Node) e os resultados são comparados campo a campo, inclusive em empates e casos de borda. O CI do Python roda com Node 22.

## [1.4.0] — 2026-11-09

Wrapped novo no app do navegador: stories com capas, fotos e trilha sonora, e um pôster para compartilhar.

### Novo
- **Aba Wrapped no app web**: 15 stories da vida toda em Preact (visual "Capa Viva + Liquid Glass"), com toque, segurar para pausar, arrastar e teclado.
- **Capas e fotos do Spotify** (opcional, com "Começar com capas e som"): capa exata pelo ID da música do ZIP e foto do artista via MusicBrainz → Spotify. Logo e link "ABRIR NO SPOTIFY" conforme as diretrizes do Spotify.
- **Trilha sonora**: um trecho de 30 s (iTunes) por story, ligado ao dado de cada um, com fade.
- **"Sua trilha"**: mosaico das 9 músicas mais ouvidas.
- **Pôster final** com o convite "Qual é a nossa sintonia? Compare comigo" e o botão **Compartilhar pôster** (PNG 1080×1920 gerado no navegador; no celular abre o compartilhar).
- Ícones próprios dos 12 arquétipos; anos clicáveis no story de fidelidade.
- "Apagar capas guardadas" e `?fps=1` para medir o desempenho.

### Mudado
- O app web baixa ~15 MB em vez de ~26 MB: plotly só na Dupla e Pillow sob demanda.
- O núcleo lê o `spotify_track_uri` e calcula o top 10 de músicas.

### Corrigido
- Story de fidelidade: as bolinhas contavam o top 3 do ano em vez do top 5 (vale também para o app local).

### Segurança e privacidade
- Imagens e trechos só de domínios esperados, em https; cache de capas expira em 30 dias.
- README e site explicam o que vai para Spotify, MusicBrainz e Apple, e só depois do toque.

## [1.3.1] — 2026-11-06

Correções da inspeção de segurança e estabilidade do app no navegador.

### Corrigido
- Pico de memória do histórico gigante de 371 para 309 MB (abaixo do limite do iPhone): o Wrapped é calculado antes da comparação.
- Se o motor parar (falta de memória), a tela avisa em vez de girar para sempre; sem internet, a mensagem fala da conexão.
- Os ZIPs saem da memória do navegador mesmo quando a comparação dá erro.
- Gráficos: aspas aparecem certas ("Guns N' Roses"); se o plotly.js não baixar, cada gráfico avisa e tenta de novo ao reabrir a aba.
- O deploy do site agora também roda quando `styles.css` ou `syncup.js` mudam.

### Novo
- Teto de 50 MB por pessoa no app web.
- Landing com os botões **Abrir o app** e textos do app no navegador.
- Testes de XSS na ponte e dos textos da landing.

## [1.3.0] — 2026-11-06

Primeira tela do SyncUp rodando 100% no navegador.

### Novo
- **App no navegador** em <https://hazykiuu.github.io/SyncUp/app/>, com a tela **Dupla**: o Python (Pyodide 0.29 + pandas, Pillow e plotly) roda num Web Worker e nada sai do aparelho. Envio de vários arquivos por pessoa, opções de dados, demo com dados fictícios, resultado em abas (resumo, sintonia, rankings, gráficos, Wrapped, downloads PNG/CSV e detalhes técnicos). Match, Wrapped e Grupo chegam nas próximas versões.
- `web/ponte.py` (ações do app web) e `tools/empacotar_web.py` (pacote do núcleo gerado no deploy, sem Gradio nem rede).

### Interno
- As funções puras da Dupla saíram de `ui/` para `apresentacao.py`, sem Gradio; o `ui/` reexporta os mesmos nomes.
- O CSS da landing virou `site/estilo.css`, compartilhado com o app.

## [1.2.0] — 2026-11-06

Site novo e um núcleo pronto para rodar no navegador.

### Novo
- **Landing page** em `site/` (HTML único, visual adaptado do modelo Lumora do GetLayers com a identidade do SyncUp): hero com "liquid reveal" das duas pessoas (verde e roxo), vidro líquido, faixa de recursos, as 4 abas com capturas, como funciona, números, privacidade e rodapé com GitHub e X. Publicada pelo GitHub Pages (workflow `site.yml`) em <https://hazykiuu.github.io/SyncUp/>. Respeita "menos movimento", alvos de 44 px e funciona em 390 px.

### Correções
- **Sintonia com pandas 3**: as datas eram convertidas supondo nanossegundos; no pandas 3 (microssegundos) a sintonia saía errada sem erro. Agora `recursos._ns()` fixa a unidade.
- **Site**: a tela de carregamento não bloqueia mais os cliques (contagem pelo relógio, trava de 2,5 s, Lenis sem `await`) e o menu do celular prende o foco (`inert`).

### Desempenho
- **Menos memória** para históricos grandes, pensando no navegador (iOS ~350 MB): nomes repetidos guardados uma vez na leitura, e o `comparar()` solta as cópias do período antes da sintonia. Com 285 mil plays por pessoa, no Pyodide: Dupla 446 → 309 MB, Wrapped 215 MB. Resultados idênticos.

## [1.1.0] — 2026-11-06

Primeira etapa do Roadmap 2.0: cara de produto.

### Novo
- **Badges no README**: Testes, Lint, versão da release, licença e Python. O CI virou dois workflows (`testes.yml` e `lint.yml`), porque a badge do GitHub Actions mostra o estado do workflow inteiro.

### Visual
- Sem "cara de demo de IA": rodapé padrão do Gradio escondido, ícones de traço próprios no lugar dos emojis dos cartões do Início, selo "100% local" sem o cadeado e botão principal sem brilho pulsante.

## [1.0.0] — 2026-11-05

Primeira versão estável: dá para entregar o link do repositório a um colega e ele usa sem ajuda.

### Novo
- **`iniciar.bat`**: no Windows, dois cliques instalam (na primeira vez) e abrem o SyncUp no navegador. Acha o Python 3.10+ (`py -3` ou `python`), cria a `.venv`, instala o `requirements.txt` e mostra a mensagem se algo der errado.
- **README reescrito por tarefa**: começa por "Como rodar o SyncUp na sua máquina" (instalar o Python, baixar, abrir, pedir o histórico ao Spotify, fechar e problemas comuns), depois uma seção por aba com capturas (`docs/img/`, dados fictícios).
- **Créditos na barra**: links para o GitHub e o X (@HazyKiuu), numa constante só (`configuracao.GITHUB_URL`, `X_URL`, `X_USUARIO`).

### Removido
- **Notebook** (`SyncUp.ipynb`), com `tools/verificar_notebook.py` e `tests/test_notebook.py`. O projeto fica só com o app.
- **seaborn e matplotlib**: só o notebook usava. O `requirements-dev.txt` fica com pytest e ruff.

## [0.99] — 2026-11-05

Terceira etapa rumo à 1.0: visual e convite.

### Novo
- **Convite por código** (`convite.py`): cada pessoa gera, no próprio SyncUp, um código curto (~1 mil caracteres) a partir do ZIP ou de um perfil salvo do Spotify, e manda por mensagem. Quem recebe cola no Match, no cartão **Convite**. Sem servidor, sem conta e sem limite de pessoas. Só os rankings viajam: o histórico, as músicas recentes (com horário), os artistas seguidos e os gêneros ficam de fora.
- O código vindo de fora é sempre conferido: tamanho do texto, tamanho descompactado (barra zip bomb), estrutura, tipos e tamanho de cada nome. Um convite cortado ou alterado fica de fora com aviso, e os demais continuam. Códigos quebrados em várias linhas pelo aplicativo de mensagem são remontados.

- **Avisos no tema do app**: erros, alertas e confirmações aparecem num cartão escuro com a cor do tipo (rosa, laranja ou verde) e com título em português: "Não deu certo", "Atenção" e "Pronto". Antes vinham com o título do Gradio em inglês ("Error", "Warning"). Todos passam por `ui.comum.falha`, `aviso` e `info`.

### Visual
- **Match**: as quatro fontes (ZIP, ListenBrainz, Login com Spotify e Convite) ficam numa grade 2×2, e "Criar o meu convite" virou um acordeão fechado abaixo delas.
- **Grupo**: ganhou título e texto de abertura, como as outras abas. As regras dos traços, a nota sobre um arquivo por pessoa e o "Diagnóstico de cada perfil" foram para o acordeão **Detalhes técnicos**, no fim dos resultados (como na Dupla).

### Correções
- **Acordeões** (todos, inclusive "Meus dados"): desde o Gradio 6, a seta girada criava uma barra de rolagem lateral e o título aparecia pequeno e sem negrito.
- **Celular (390 px)**: o selo dos painéis do Match ("sem limite · só o usuário") quebrava em várias linhas; agora desce inteiro para baixo do título. As abas principais usam o espaçamento menor de celular (cabem 3, antes 2), e o botão do menu das outras abas tem 44 px.
- **Alvos de 44 px**: o botão de pausar dos stories (Dupla e Wrapped) media 32 px em qualquer largura; o link de download nas listas de arquivos tinha 17 px de altura.
- **Início no celular**: o título não força mais a quebra depois de "quem", que ficava sozinho numa linha.
- **Leitor de tela**: os títulos do Início seguem a ordem H1 → H2 → H3 (pulavam do H1 para o H3), e o botão do menu de abas extras se anuncia como "Mais abas" (o Gradio escreve "More tabs", sem tradução).

### Dependências
- **Gradio 5.50 → 6.31** (e FastAPI 0.143 → 0.162). Três mudanças do Gradio 6: o botão de copiar do convite virou `buttons=['copy']`; os eventos internos usam `api_visibility='private'` (`api_name=False` passou a criar endpoints chamados "false"); tema, CSS, JS e head saíram do `gr.Blocks` e agora vão no `mount_gradio_app` (`app.py`). O visual e os endpoints públicos ficaram iguais. O filtro de avisos "Gradio 6" do pytest saiu.

### Contrato
- `encontrar_matches` recebe uma entrada a mais no fim: os códigos de convite. Novo endpoint `gerar_convite` (arquivos, nome, perfil salvo e as 6 opções de dados).

## [0.98] — 2026-11-05

Segunda etapa rumo à 1.0: privacidade e organização.

### Novo
- **Meus dados** (gaveta *Opções de dados*): mostra o que o SyncUp guardou no computador (perfis do Spotify, gêneros do MusicBrainz e cache de históricos), com tamanho e data, e permite **apagar um perfil** ou **limpar todo o cache**. As duas ações pedem confirmação. Ao apagar um perfil, a lista do Match é atualizada.
- **Privacidade no Início**: três cartões dizem o que fica no computador, o que vai para a internet (só se você pedir) e o que nunca é guardado.
- `privacidade.py`: listar e apagar dados locais, sem Gradio. Só arquivos criados pelo SyncUp são apagados; o nome do perfil é conferido na lista e nunca vira caminho.

### Correções
- **Enviar históricos aos poucos**: depois do primeiro arquivo, o Gradio só deixava um ícone pequeno no canto, por cima do título, e parecia que não dava para enviar outro. Agora cada campo de envio (Dupla A e B, Match, Wrapped e Grupo) tem o botão **"+ Adicionar mais arquivos"**, que abre o seletor e soma os novos arquivos aos que já estavam.

### Interno
- **`ui.py` dividido** no pacote `ui/`, um módulo por tela: `comum`, `dupla`, `meu_wrapped`, `match`, `meus_dados` e `layout`. O código das funções não mudou e os nomes de antes continuam importáveis de `ui`. O teste de regras (groupby com `observed=True`, sem NumPy) passa a olhar também `ui/*.py`.

### Contrato
- Sem mudanças nos endpoints. Testes que trocam funções de rede do Match agora apontam para `ui.match`.

## [0.97] — 2026-11-05

Primeira etapa rumo à 1.0: confiança.

### Novo
- **CI no GitHub Actions** (`.github/workflows/ci.yml`): `ruff check`, `ruff format --check` e `pytest` em Python 3.10 e 3.12, a cada push na `main` e em toda PR.
- **Versão única**: `configuracao.VERSAO` alimenta a barra do app; o `pyproject.toml` ganhou a seção `[project]` (nome, versão, licença MIT, Python ≥ 3.10). Um teste garante que pyproject, README e barra digam a mesma versão.

### Desempenho
- **Fim da fila única**: até 4 ações rodam ao mesmo tempo (Dupla, Wrapped, Grupo, downloads), então uma pessoa não espera a outra. Só o Match continua um por vez, porque o MusicBrainz aceita 1 consulta por segundo para o app todo.

### Segurança
- **Limite de 1 GB** para o histórico descompactado (ZIP ou JSON) e para o upload. Um ZIP malformado ou malicioso (zip bomb) é recusado antes de descompactar, com mensagem em português.
- **Login do Spotify só pelo próprio app**: `/spotify/login` recusa pedidos vindos de outros sites (cabeçalho `Sec-Fetch-Site`). Antes, qualquer página aberta no navegador podia disparar um cadastro.

### Correções
- `test_cache_e_hash` não falha mais de vez em quando: o arquivo regravado com o mesmo tamanho no mesmo instante agora avança a data, como acontece na vida real.

### Contrato
- Sem mudanças nos endpoints. `app.criar_servidor` passa `max_file_size` ao Gradio.

## [0.96] — 2026-11-04

### Novo
- **Sintonia no Match**: o Match agora mostra quem ouviu a mesma música no mesmo instante, para **todos os pares** do grupo. A **Dupla mais sincronizada** ganha destaque na Revelação e um slide nos stories; cada pôster mostra os minutos em sintonia (ou quantas vezes ficaram "quase juntos", a menos de 1 h); a tabela "Todos com todos" ganha a coluna "Mais em sintonia"; e o story PNG da dupla ganha o painel "Em sintonia".
- **Listens do ListenBrainz na sintonia**: até 5.000 listens por pessoa (5 chamadas de 1.000), respeitando a cota da API (`X-RateLimit`). O ListenBrainz guarda o início do play e a duração da faixa, então o intervalo é `[início, início + duração]`; listens sem duração ficam de fora. O artista principal (`mbid_mapping`) é usado para bater com o do ZIP ("Röyksopp", não "Röyksopp feat. …").
- Quem entra pelo login do Spotify continua no Match, sem sintonia: a API só entrega as 50 músicas recentes, sem quanto tempo tocaram.

### Desempenho
- A sintonia foi dividida em `recursos.escutas` (uma vez por pessoa, guardada no cache do perfil do ZIP) e `recursos.sintonia_entre` (por par, com duas buscas `merge_asof` e sem laço em Python). Com 7 ZIPs fictícios, 2 deles com 285 mil eventos: os 21 pares em 9,7 s na primeira vez (com a leitura dos ZIPs) e em 0,8 s com o cache.
- Na Dupla, a sintonia com 285 mil eventos por pessoa leva ~0,95 s (antes 0,55 s): o custo de normalizar os nomes, para que fontes diferentes se encontrem.

### Correções
- Os nomes de artista e música passam por `normalizar_nome` na sintonia: "Tempo Perdido" e "tempo perdido!" agora são a mesma faixa.

### Contrato
- Sem mudanças nos endpoints: `encontrar_matches` continua com as mesmas entradas e 7 saídas. O estado do Match ganha a chave `sintonias`, e a tabela de ranking ganha a coluna "Mais em sintonia".
- Novos: `recursos.Escutas`, `escutas`, `sintonia_entre`, `sintonia_do_par`, `mais_sincronizada`; `Sintonia.quase_juntos` (padrão 0); `listenbrainz.coletar_escutas_listenbrainz`; `perfil_gosto.escutas_de_arquivos`. `match_html` e `stories_match_html` aceitam `sintonias`; `gerar_cartao_match` aceita `sintonia`.

## [0.95] — 2026-11-04

### Novo
- **Site repaginado**: aba **Início** de apresentação (hero, cartões de recurso que abrem a aba certa, "Como funciona" e faixa de código aberto); barra superior compacta; abas principais fixas no topo com fundo de vidro; "Opções de dados" numa gaveta lateral fechada; Dupla com 5 sub-abas (Wrapped, Em sintonia, Rankings, Gráficos, Compartilhar) e "Detalhes técnicos" num acordeão.

### Desempenho
- **Em sintonia 35× mais rápido**: com 285 mil eventos por pessoa, de 19,06 s para 0,55 s. Os intervalos passaram a ser cruzados numa única fusão de listas ordenadas, no lugar de uma tabela por faixa.

### Correções
- Plays repetidos ou tocados em dois aparelhos ao mesmo tempo não contam mais em dobro na sintonia: os intervalos sobrepostos da mesma pessoa são unidos antes.
- O cartão "Em sintonia" do Início abre a Dupla direto na sub-aba da sintonia.
- No Match, um usuário do ListenBrainz inexistente, sem estatísticas ou com o serviço ocupado (429) fica de fora, com um aviso; os demais continuam. O timeout por chamada caiu de 20 s para 10 s e a barra de progresso avança a cada usuário.
- Acessibilidade: os botões do Início têm texto próprio ("Abrir Dupla →"…) e os ícones são ignorados por leitores de tela.
- O aviso "não medem personalidade" voltou para junto do gráfico de traços.
- O slide final dos stories do Match e da Sintonia não fica mais cortado entre o verde e o preto.

### Contrato
- Sem mudanças nos endpoints. Os componentes da Dupla mudaram de lugar, mas não de ordem nem de quantidade (34 saídas).

## [0.9] — 2026-11-03

### Novo
- **Código aberto**: licença MIT (`LICENSE`) e teste que exige licença aberta em toda dependência declarada. A fonte Figtree (OFL) agora vem no projeto (`fontes/`): a interface não chama mais o Google Fonts e os cartões PNG ficam iguais em qualquer sistema.
- **Estilo musical no Match** (`generos.py`): segundo eixo de compatibilidade por gêneros, para quando os artistas não batem mas o estilo bate. Uma caixa opcional (desligada por padrão) busca os gêneros no **MusicBrainz**, para ZIPs e também para logins do Spotify, que em modo de desenvolvimento não enviam gêneros (base aberta), 1 consulta por segundo e com cache local. O emparelhamento continua só por artistas.
- **Playlist da festa** (`festa.py`): até 30 músicas que cobrem o gosto de todo o grupo, equilibrando quem ainda tem pouco. Exporta CSV e **XSPF** (formato aberto de playlist, abre no VLC).
- **Stories do Match** (revelação animada das duplas e do trio) e **story PNG da dupla** (1080×1920, pronto para o Instagram).
- **ListenBrainz** (`listenbrainz.py`): terceira fonte do Match, aberta e sem limite de pessoas. Basta o nome de usuário público: sem Client ID e sem a lista de usuários do Spotify.
- **Em sintonia** (aba Dupla): a mesma música tocando para os dois **no mesmo instante**. O intervalo de cada play é reconstruído (fim − duração) e os intervalos dos dois são cruzados. Mostra minutos juntos, a primeira vez, a música de vocês, o momento mais longo, a hora e o dia favoritos e a linha do tempo mês a mês, com stories e um story PNG para postar. A janela antiga de 1 h virou "Quase juntos".
- **Aba Match redesenhada**: três fontes lado a lado; a configuração do app do Spotify fica num acordeão só para quem criou o app; o resultado foi dividido em abas (Revelação, Duplas, Todos com todos, Playlist da festa, Para postar); as duplas aparecem como pôsteres 4:5 em degradê.

### Desempenho
- A leitura de um histórico não segura mais a trava global: arquivos e sessões diferentes são lidos ao mesmo tempo.
- O perfil de um ZIP fica em cache pelo SHA-256: repetir um Match não relê os históricos.

### Correções
- A lista de perfis do Spotify é recarregada ao abrir a página, então um perfil salvo depois que o servidor subiu já aparece numa aba nova.

### Contrato
- `Compatibilidade` ganha `pontuacao_generos` (ou `None`) e `generos_comuns`, com valores padrão.
- `encontrar_matches` recebe uma entrada a mais no fim (buscar gêneros) e devolve 7 saídas (+ stories, estado e duplas).
- `encontrar_matches` ganha mais uma entrada no fim: os usuários do ListenBrainz.
- Novos endpoints `playlist_festa`, `baixar_cartao_match` e `baixar_sintonia`. O PNG de `baixar_cartao_match` passou a ser 1080×1920.
- `ResultadoComparacao.sintonia` (novo, padrão `None`). Na saída 15 de `comparar_dupla`, o Markdown dos momentos virou o HTML "Em sintonia".
- A lista "Ranking individual" saiu dos cartões do Match; o mesmo conteúdo continua na tabela da aba "Todos com todos".

### Correções
- Depois de "Atualizar lista", quem acabou de logar no Spotify já aparece marcado. Antes vinha desmarcado e o Match falhava com "pelo menos duas pessoas".
- As sugestões de troca não saem mais da borda do cartão.

## [0.8] — 2026-11-03

### Novo
- **Aba Match**: concilia de 2 a 16 pessoas, mistura histórico ZIP e login com Spotify, forma as duplas que maximizam a compatibilidade total (emparelhamento ótimo exato; trio quando ímpar), explica pelos artistas em comum, sugere trocas e mostra o ranking individual e a matriz.
- **Login com Spotify** (`spotify_api.py`): OAuth 2.0 com PKCE (sem client secret), rotas `/spotify/login` e `/spotify/callback`, coleta de top artistas/músicas nos 3 períodos, últimas 50 e artistas seguidos. Só o perfil é salvo; o token nunca vai para o disco.
- **Perfil unificado** (`perfil_gosto.py`): ZIP convertido para os mesmos rankings e janelas da API, para comparar as duas fontes de forma justa.
- `python app.py` agora sobe FastAPI + Gradio em `127.0.0.1` (necessário para a Redirect URI do Spotify).

### Contrato
- Novo endpoint `encontrar_matches`. Abas principais: Dupla, Match, Wrapped, Grupo.

## [0.7] — 2026-10-09

### Novo
- **Wrapped da vida toda** (aba *Meu Wrapped*): 14 stories animados com horas totais, primeira música, artista e músicas da vida, ano a ano, descobertas, dia recorde, música mais repetida num dia, relógio de 24 h, maior sequência de dias, fidelidade ao top 5, hábitos e arquétipo; resumo em PNG 1080×1920 (`cartao.gerar_cartao_wrapped`).
- **Arquétipos v0.7** (`arquetipos.py`): 12 regras explicáveis, calibradas com históricos reais, com principal, secundários, "quase" e painel de transparência (valor × limiar). Destaque nos cartões da Dupla e do Grupo; Wrapped de A e B lado a lado na Dupla.
- Ingestão lê `skipped`, `shuffle`, `offline`, `reason_end` e a **família** da `platform` (sem modelo/versão do aparelho). Versão do cache Parquet atualizada.

### Correções
- As três regras antigas (favoritos ≥60%, repeat ≥40%, madrugada ≥40%) quase nunca eram atingidas com dados reais, então todos recebiam os mesmos rótulos. Elas continuam como "traços no período comparado", e o destaque passa para os arquétipos novos.
- O filtro padrão de músicas da interface escondia uma música real das análises; agora começa vazio.
- Regras CSS responsivas que miravam `.gradio-container`/`body` dentro de `@media` eram anuladas pelo prefixo que o Gradio aplica; o espaçamento externo agora usa `clamp()`. No celular, o conteúdo agora usa quase toda a largura da tela.
- Abas principais com nomes curtos (*Dupla*, *Meu Wrapped*, *Grupo*) e a cópia que o Gradio mede para decidir o menu "…" agora tem o mesmo tamanho das abas visíveis.

### Contrato
- `executar_dupla` devolve 34 saídas (+ Wrapped da dupla no fim). Novos endpoints: `gerar_wrapped` e `baixar_wrapped`. `COLUNAS_PREPARADAS` ganhou `pulada`, `aleatorio`, `offline`, `plataforma` e `motivo_fim`.

## [0.6] — 2026-10-09

### Correções
- ZIPs recompactados no macOS (`__MACOSX/`, arquivos `._*`) falhavam por inteiro com "JSON inválido/UTF-8"; agora esses metadados e pastas são ignorados.
- Nomes `None` vindos da API/Gradio causavam `AttributeError` em `comparar()`/`comparar_grupo()`; agora usam o nome padrão.
- Instalação falhava no Python 3.13/3.14 (pandas 2.2.3 e PyArrow 17 sem binários). Requisitos agora escolhem versões com binários por versão do Python; suíte validada em 3.12, 3.13 e 3.14.
- Gráficos: legenda sobrepunha a primeira barra do butterfly e os rótulos do radar; título do slope dizia "oito artistas" mesmo com menos; linha vertical espúria no slope; barra de ferramentas do Plotly cobria a legenda.
- Mapa de horários com escala começando em zero deixava tudo da mesma cor; agora a escala comum vai do menor ao maior valor observado.
- Grupo: entropia/Gini nulos quebravam a formatação; diagnóstico era calculado duas vezes por perfil.
- Diagnóstico usava `idxmin/idxmax` (frágil com índices repetidos); agora usa posições.

### Otimizações
- Extração JSON colunar (sem tupla por evento) e `orjson` opcional: extração ~2× mais rápida.
- Limpeza com categorias desde o início: `strip`, filtros e normalização de nomes rodam uma vez por nome distinto (vetorizado); conversão de fuso pelo caminho vetorizado do pandas (~10× mais rápida).
- Momentos sincronizados: uma única fusão ordenada por (chave, instante) com códigos inteiros, sem `groupby.indices` nem `iloc` por exemplo: ~2× mais rápido, resultados idênticos.
- Leitura paralela em processos (interface): dupla 300k+300k fria de ~9,2 s para ~4,8 s e grupo 4×300k de ~12,7 s para ~6,4 s numa máquina de 2 núcleos.
- `tabela_display` coluna a coluna (sem `.at` por célula); fontes do cartão em cache e corte de texto por busca binária.

### Interface
- Novo tema inspirado no Spotify, Blend com anel animado, cartões Wrapped, listas tipo playlist, corrida de artistas com player, Modo Grupo com cartões e "dupla mais sintonizada", botão de dados fictícios.
- Animações em botões, números, gráficos e listas; respeitam `prefers-reduced-motion`.
- Cartão PNG no novo visual (degradê e anel de similaridade).
- **Contrato:** `executar_dupla` devolve 33 saídas (as 26 anteriores nas mesmas posições + 7 novas no fim); `executar_grupo` devolve 7 (5 anteriores + 2).

## [0.5 — correção de empates] — 2026-10-08

- Rankings com desempate explícito: contagem decrescente, nome crescente, inclusive no corte do top 20. Artistas exclusivos usam ordenação estável.
- Golden masters originais e fontes congeladas preservados byte a byte. Os testes continuam verificando métricas, contagens, tipos e itens acima do empate no corte; o ranking completo atual é conferido contra contagens independentes dos eventos.
- Novos testes com 25 itens empatados, títulos homônimos e ordem de entrada invertida. Testes adversariais garantem que o comparador golden recusa nomes, contagens, duplicações, ordem e corte incorretos.
- Instruções Windows corrigidas para um ambiente Python 3.12 explícito; distingue incompatibilidade de binários Python 3.14 de bloqueio de execução Ruff pelo Windows.

## [0.5] — 2026-10-08

Consolidação dos quatro passos de evolução do protótipo acadêmico. Não inclui autenticação Spotify, coleta em tempo real, hospedagem ou inferência psicológica.

### Arquitetura e compatibilidade — Passo 1

- Separação do núcleo em `dados.py`, `metricas.py`, `analise.py` e `perfis.py`, sem dependências circulares ou gráficos no orquestrador.
- Dataclasses `ResultadoComparacao`, `PerfilComparado`, `MetricasComparacao` e `PeriodoComparacao` substituem a interpretação de HTML e os índices posicionais do retorno.
- `app.py` mantém as reexportações `carregar`, `comparar`, `metricas`, `criar_interface` e `limpar_cache`; a interface é construída sob demanda.
- **Mudança de contrato:** os imports antigos continuam funcionando, mas consumidores da tupla de 12 saídas de `comparar()` precisam migrar para campos do resultado. O adaptador `ui.apresentar()` preserva a fronteira antiga de apresentação para notebook/benchmark.
- Regras de arquétipos, quantidades de líderes e limiares centralizados em constantes nomeadas, acompanhados de descrições.
- Gerador `tools/gerar_dados_falsos.py`: ZIPs reproduzíveis por semente, aproximadamente 300 mil eventos/3 mil artistas no padrão, cauda longa, podcasts, Various Artists, duplicações e campos auxiliares realistas.
- Referências v0.4 congeladas e saídas serializadas em `tests/golden/`, com hashes das fontes que geraram a referência.

### Correções de dados e apresentação — Passo 2

- Datas ISO8601 com variantes de offsets, frações e Z, interpretadas em UTC; datas inválidas são descartadas e contadas.
- Contadores exclusivos para podcasts, duração inválida, data inválida, identificação, Various Artists, filtros e duplicações; recebidos = descartados + válidos.
- Durações negativas, booleanas, não numéricas e não finitas recusadas na ingestão.
- Filtro configurável de músicas/artistas, substituindo condição especial fixa. A preferência anterior permanece editável e pode ser desativada.
- Política explícita para manter Various Artists como artista agregado ou descartá-lo; não tenta deduzir intérpretes reais.
- Fuso IANA validado, padrão America/Sao_Paulo, aplicado consistentemente às visualizações, períodos locais e arquétipos.
- Recorte e deduplicação por UTC, preservando instantes distintos durante horas locais repetidas de horário de verão.
- `fmt_num`, `fmt_pct` e `fmt_horas` em pt-BR, sem depender do locale do computador.
- Escapes específicos HTML/Markdown, preservando nomes reais no núcleo; listas limitadas com `itertools.islice`, sem cortar escapes/nomes.
- Mensagens amigáveis para JSON malformado, ZIP incompleto e problemas de leitura.
- Diagnóstico de arquivo, cobertura, filtros, descartes, SHA-256 e origem do cache.

### Performance e caches — Passo 2

- Conversão local uma única vez no loader; pré-cálculo inteiro de hora, ano/mês, dia da semana e dia.
- Artistas/músicas como `category` após limpeza; `observed=True` nos agrupamentos para evitar combinações não observadas.
- Totais e agregações reutilizados por rankings e regras, eliminando consultas repetitivas de Series por artista.
- Ranking de contagens de faixas desacoplado do MultiIndex para evitar operações custosas do Pandas no top 10.
- Cache de históricos em memória por conteúdo/configuração, com cópias nas funções públicas para proteger dados armazenados.
- Cache Parquet opcional por SHA-256 + esquema + filtros/fuso/política/deduplicação, com manifesto, validação de integridade e gravação atômica.
- Cache corrompido é reconstruído a partir do original; ausência de PyArrow informa como instalar a dependência opcional.
- Benchmark em processos isolados: aquecimento fora da medida, ordem alternada antes/depois, medianas frio/memória/Parquet e saída JSON/CSV/Markdown.
- Os relatórios de 300 mil eventos feitos no Passo 2 foram preservados como registros históricos, sem atribuir seus tempos aos novos recursos.

### Métricas e funcionalidades — Passo 3

- Ponderação selecionável de contagens: bruta, raiz quadrada e log1p; implementações em Python puro/biblioteca padrão, sem NumPy direto.
- Contribuição individual por artista para o cosseno, soma verificável e valores completos em DataFrame.
- Jaccard ponderado/Ruzicka com pesos absolutos, entropia normalizada e Gini dos artistas observados.
- Momentos Sincronizados: pares cronológicos por artista ou artista/música em janela inclusiva de uma hora UTC. Emparelhamento linear após ordenação, sem produto cartesiano ou reutilização de eventos dentro de cada análise.
- Contagem completa de pares separada dos até 200 exemplos; análises por artista/música são alternativas, sem soma entre totais.
- Ponte Musical: sugestões de até dez artistas exclusivos por direção, com links Spotify construídos localmente como buscas; não afirma descoberta/influência comprovada.
- Playlist comum por artista/título, prévia limitada e exportação integral CSV UTF-8 BOM, separador brasileiro e proteção contra fórmulas de planilha.
- Cartão PNG local RGB 1080×1350 em Pillow, sem rede, com fontes locais/fallback, limites visuais de texto, métricas, regra/limiar e aviso metodológico.
- União de múltiplas partes de um perfil, categorias preservadas, contadores agregados e deduplicação opcional entre arquivos.
- Arquivos inteiros com SHA repetido no mesmo perfil são rejeitados, evitando dupla contagem por seleção acidental.
- `EntradaPerfil` e `ResultadoGrupo`: comparação de 3–6 perfis, agregações reutilizadas, matriz simétrica e recorte UTC comum global quando solicitado.

### Interface e visualizações — Passo 3

- Gradio 5 com `gr.Blocks`, tema nativo configurado por `Base().set(...)`, uploads múltiplos, progressos e aba própria de grupo.
- Plotly: butterfly divergente, mapas hora × dia lado a lado com escala comum, radar com limiares, slope chart de participações e matriz de grupo.
- Nomes escapados nos gráficos; dados numéricos permanecem numéricos no núcleo.
- CSS externo de largura total, responsividade, foco visível, botões de altura mínima 44px, contraste nos pares de texto principais e redução de movimento.
- Arquétipos exibem proporções, limiares e aviso explícito: não medem personalidade ou afinidade amorosa.
- Exportações por sessão em diretórios temporários privados; arquivos anteriores são limpos pelo ciclo de vida do estado/cache.

### Testes, qualidade e documentação — Passo 4

- Suíte pytest parametrizada para vetores vazios/nulos, ortogonalidade, proporcionalidade, contribuições, Ruzicka, pesos inválidos e diversidade.
- Ingestão testada com JSON malformado, ZIP corrompido, partes internas inválidas, campos obrigatórios/opcionais, podcasts e deduplicação entre arquivos.
- Fluxos sem período comum, identidade de bytes/eventos/recorte, ausência de plays, matriz de grupo e regressão contra os golden masters salvos.
- Smoke test da árvore Gradio sem iniciar servidor; fluxo HTTP e downloads CSV/PNG anteriores continuam incluídos na descoberta pytest.
- Fixtures fictícias de sementes fixas e cache isolado. Testes não regravam as referências esperadas nem usam históricos pessoais.
- **Correção encontrada nos casos de borda:** pesos finitos muito grandes causavam overflow; pesos pequenos podiam virar uma falsa norma zero. Cosseno/contribuições, Ruzicka e diversidade agora reescalam os valores antes das somas. O Ruzicka usa o mesmo divisor em ambos os vetores, preservando a diferença de volumes. Fórmulas e resultados usuais permanecem equivalentes dentro da tolerância numérica.
- Ajuste de comparação de floats no teste de matriz para tolerância explícita, sem alterar os golden masters.
- Dependências diretas fixadas, desenvolvimento separado, PyArrow opcional fixado e suporte HTTPX a proxy SOCKS. Gradio fica em 5.x e pandas em 2.2.x.
- `pyproject.toml` configura pytest e Ruff para Python 3.10, lint/imports/formatação. Fontes históricas ficam excluídas da formatação para preservar hashes.
- Imports e formatação consolidados no código atual, sem modificar as fontes congeladas.
- README reescrito com execução, arquitetura, testes, benchmarks, limites e aviso metodológico; validação e guias anteriores preservados.
- Notebook atualizado nas seis fases do CRISP-DM, importando a arquitetura modular, com demonstração fictícia, EDA Pandas/Seaborn, métricas/traços/grupo e exportações locais.
- Validação estrutural do notebook e verificador de células em IPython sem servidor/kernel de rede; interface automática desativada por padrão e saídas removidas da entrega.

## [0.4] — Referência anterior preservada

Protótipo local de comparação de dois históricos estendidos Spotify, com rankings, cosseno/Jaccard, arquétipos iniciais e interface visual. A orquestração/presentação tinha saídas posicionais e concentração de responsabilidades; não havia o pacote consolidado de dados configuráveis, recursos avançados, grupo e testes pytest da v0.5.

A implementação congelada permanece em `tests/fixtures/v04/` e a referência numérica em `tests/golden/`. É material histórico de regressão, não o código de entrada atual.
