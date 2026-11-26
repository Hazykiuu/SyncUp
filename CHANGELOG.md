# Changelog — SyncUp

## Não lançado

### Mudado
- **Privacidade, prazos de verdade:** o histórico do Last.fm guardado no navegador agora vence depois de 7 dias sem uso, e a página não diz mais "Fechou a página, sumiu". No app para PC, a limpeza passou a cumprir o prazo de 1 hora.
- **"Capas e som" é uma escolha sua, antes:** a opção aparece no topo de cada modo, ligada por padrão e lembrada no navegador. Desligada, nada é pedido ao Spotify, ao MusicBrainz nem à Apple. Os textos que diziam "Nada sai do seu aparelho" agora dizem o que sai.
- **O app abre sem o unpkg:** o Preact com htm passa a vir do próprio site, o mesmo arquivo de antes. Com o CDN fora do ar ou bloqueado, a tela ficava no esqueleto para sempre.
- **Mesma sintonia no PC e no navegador:** o app para PC passa a usar por padrão a ponderação logarítmica, a mesma do navegador. Antes o PC usava a bruta, e os mesmos arquivos davam números diferentes. Dá para trocar na própria tela.
- **Wrapped com histórico curto:** com menos de 100 plays de 30 s ou mais, o app avisa "Histórico curto demais" em vez de montar os stories. Antes, 1 play virava um Wrapped com "0 horas" e arquétipo. "Em 1 dias" virou "em 1 dia".
- **Match com poucos dados:** com menos de 30 artistas em um dos rankings, a faixa vira "Amostra pequena" (a porcentagem continua). Antes, 1 artista em comum podia dar "Sintonia rara". As faixas passam a aparecer como provisórias, e o `VALIDACAO.md` registra de onde vieram.

### Corrigido
- **Serviços externos:** quando o Last.fm, o Spotify, o MusicBrainz ou o ListenBrainz pedem uma pausa longa, o SyncUp para de insistir. O iTunes recebe no máximo 3 buscas por vez. Um download do Last.fm interrompido continua de onde parou.
- **Windows:** encerrar o app à força não deixa mais processos de leitura parados na memória.
- **ListenBrainz:** resposta inesperada aparece em português (antes, "Expecting value: line 1 column 1"), erro do servidor não culpa mais a sua internet, e depois de 3 demoras seguidas o Match não espera pelas próximas pessoas.
- **Capas:** um erro do servidor do Spotify ou do MusicBrainz não vira mais "sem capa" por 30 dias.
- **Cache de gêneros:** um arquivo editado ou corrompido não vira mais "gêneros" de uma letra nem derruba o Match. O cache antigo é refeito uma vez.
- **Teclado no app para PC:** o player de stories mostra onde está o foco e se apresenta aos leitores de tela.
- **Teclado no celular:** o item em foco não fica mais escondido atrás da barra de modos.
- **Match sem dados comparáveis:** quem tem rankings só com nomes de pontuação ou emoji (como a banda "!!!") aparecia com 0% "Mundos diferentes", virava par e puxava a média do grupo. Agora sai do Match, com aviso, no PC e no navegador.

## [1.27.0] — 2026-11-24

Pedir o histórico ao Spotify ficou mais fácil de entender. O resto do app não muda.

### Novo
- **Guia "Como pedir o histórico"** no primeiro passo do "Como usar": o link da página de privacidade do Spotify, a opção "Histórico ampliado de streams", o e-mail de confirmação e o ZIP, que não precisa ser extraído. O topo da página ganha o botão "Como pedir o histórico".
- **No app**, abaixo do texto de cada modo: "Ainda não tem o ZIP? Veja como pedir", que leva ao guia.

### Mudado
- **Prazo real:** "até 30 dias" virou "menos de 1 dia" no passo 01, e o rodapé agora diz "Peça hoje, compare amanhã". Os 34 históricos estendidos pedidos para testar o SyncUp chegaram todos em menos de 24 h.

### Corrigido
- O README traz o mesmo caminho, o nome da opção e o prazo do guia.
- As regras dos passos do "Como usar" valiam para qualquer item de lista dentro deles; agora só valem para os passos.

## [1.26.0] — 2026-11-24

O projeto volta a ter a análise acadêmica, nas 6 fases do CRISP-DM.

### Novo
- **Notebook acadêmico** (`notebook/SyncUp_CRISP-DM.ipynb`): Entendimento do Negócio e dos Dados, Preparação, Modelagem, Avaliação e Implantação, com Pandas e Seaborn. `describe()` interpretado (tempo por reprodução, plays por dia e por artista), Jaccard e cosseno (bruto e log) para todas as duplas, matriz de todos com todos, duplas ótimas (como o Match) e recomendações. Aceita de 2 a 8 pessoas; no Colab pede os ZIPs.
- **`requirements-notebook.txt`**: Seaborn e Matplotlib só para o notebook; o app continua sem eles.
- **`tools/gerar_notebook.py`**: gera o notebook sem saídas (nenhum dado real no repositório).
- README: seção "Projeto acadêmico (CRISP-DM)", ligando cada fase ao código.
- Teste `tests/test_notebook_academico.py`: 6 fases, `describe()`, Seaborn, sem saídas e igual ao gerador.

## [1.25.0] — 2026-11-19

A entrada no app ganha uma animação: a logo entra em sintonia.

### Novo
- **Entrada em sintonia:** vindo de "Abrir o app", a logo do SyncUp aparece grande com as 4 barras fora de sintonia enquanto o app carrega. Quando ele fica pronto, as barras param juntas e a logo voa até o lugar dela (a lateral no computador, o topo no celular), com o app aparecendo em volta. Depois, a logo do app pulsa com as barras juntas. Só `transform` e `opacity`; com "menos movimento", o app só aparece. Se algo falhar, o app aparece sozinho em 3,2 s.

### Mudado
- A subida antiga do app ao abrir (550 ms) saiu: quem traz o app agora é a entrada.

## [1.24.0] — 2026-11-19

Página inicial com as cores da logo. O app não muda.

### Mudado
- **As 4 barras da logo dão a cor** (verde → lilás, "você → a outra pessoa"):
  - cada modo com a sua barra no número, no link e num painel com brilho atrás do mock, agora maior;
  - "O seu histórico não sai daqui." em degradê verde → lilás;
  - os três números (0, 2,4 s e 100%) e os passos do "Como usar", ligados por um fio verde → lilás;
  - ícones da privacidade nas cores da logo e duas auras leves.
- **"Do ZIP ao story" mostra o app:** o cartão "Seu histórico", a leitura com barra de progresso e o story com a barra de segmentos, sobre um painel com o brilho da logo. Cada passo traz um detalhe: as partes do ZIP, o que o navegador faz com elas e os stories que saem.

### Corrigido
- No rodapé, as barras da pauta cobriam o texto ao lado do botão "Pedir o histórico ao Spotify".
- A aura verde dos modos era cortada reta no topo da seção.

## [1.23.0] — 2026-11-19

Importação do Last.fm no app web e testes que abrem o app num navegador de verdade.

### Novo
- **Usar o Last.fm:** sem o ZIP do Spotify, dá para buscar as escutas pelo nome de usuário, no Wrapped, na Dupla, na Batalha e no Match. Só o nome vai ao Last.fm, e as escutas vêm de lá direto para o navegador, sem servidor do SyncUp no meio.
  - Escolha entre "Todo o histórico" e "Último ano"; o download mostra o progresso e o tempo restante, e pode ser cancelado.
  - O cartão mostra "Do Last.fm", o período, as reproduções e a fatia com duração real.
  - O Last.fm não diz quanto cada música tocou: horas e minutos vêm da duração das músicas (a das 3.000 mais ouvidas, e a mediana no resto) e aparecem com "≈" e uma nota. Pulos não aparecem.
  - Capas: as músicas usam a capa do álbum que o Last.fm manda com cada escuta (os scrobbles não têm o código do Spotify); as fotos de artista continuam vindo do Spotify.
  - As escutas ficam guardadas no navegador: na próxima vez, só as novas são baixadas. "Apagar dados guardados" (antes "Apagar capas guardadas") limpa também isso.
  - Erros explicados: usuário que não existe, perfil com "Ocultar escutas recentes" e pausa pedida pelo Last.fm (o SyncUp tenta de novo sozinho).
- **Testes de navegador:** 11 testes com Playwright abrem o app no Chromium (exemplo dos quatro modos até os stories, pré-leitura, "menos movimento", celular de 375 px, página inicial e Last.fm com a API simulada). Rodam no CI no job "Navegador".

### Corrigido
- Com "menos movimento", o foco não ia para os stories do Wrapped: o player era remontado quando as capas chegavam. Agora o player novo herda o foco.

## [1.22.0] — 2026-11-19

Acabamento visual no app web e na página inicial. Cálculos e funções não mudam, e o vidro (blur) continua só no que flutua.

### Novo
- **Do envio aos stories sem corte:** o cartão "Lendo…" cresce até virar o player, e a barra e os botões dos stories entram um depois do outro. Vale nos quatro modos. Com "menos movimento" ou sem suporte no navegador, a troca é direta. No fim, o foco vai para o player.
- **Leitura do histórico em painel:** antes de montar, o cartão mostra período, reproduções (o número sobe uma vez) e partes, separados por fios, com o aviso "Lido neste aparelho".
- **Capa que acompanha o mouse:** no computador, a capa grande dos stories se desloca até 6 px com o ponteiro. A capa inteira se move, sem corte nem texto por cima.
- **Página inicial:**
  - "Do ZIP ao story": a tela fica presa enquanto os três passos rolam ao lado e troca do arquivo para a leitura e para o story. Sem suporte ou com "menos movimento", os passos aparecem empilhados.
  - Uma frase grande sobre o histórico não sair do aparelho, com o botão do app.
  - Três números: 0 servidores com os seus dados, 2,4 s para montar o Wrapped (Redmi Note 15, 300 mil reproduções) e o histórico estendido inteiro.

### Mudado
- **Uma curva só para as animações do site**, que responde na hora e para sem arrasto.
- **Cartões com um fio de luz no topo,** ainda sólidos.
- **Rótulos em cinza:** o branco fica para o dado principal de cada bloco.
- **A luz de fundo dos stories troca por opacidade,** sem repintar a tela a cada quadro (mais leve no celular).

## [1.21.0] — 2026-11-19

Limpeza do que soava a texto e tela feitos por IA, no app web e na página inicial. Cálculos e funções não mudam.

### Mudado
- **Demos com nomes que parecem de verdade:** Rafa, Lu, Teo e Nina no lugar de Ana, Bruno, Carla e Davi, com artistas e músicas inventados. No modo exemplo, nada vai à rede: as capas e os trechos de som são os locais.
- **"Ver um exemplo"** nos quatro modos, no lugar de "Testar com dados fictícios". Na página inicial, um selo só avisa que as telas usam nomes e números de exemplo.
- **Textos reescritos:** as ressalvas dizem o que a conta mede, sem a fórmula "não mede X, mede Y". Os tempos de montagem só aparecem com `?fps=1`.
- **Ícones em SVG** nos arquétipos do Wrapped e no "Ver de novo", no lugar de emoji e glifos.
- **Animações sem quique:** o story do topo, o encontro dos avatares, o cartão da Dupla e a troca de modo param sem passar do ponto. Só a agulha do afinador oscila.
- **Página inicial mais enxuta:**
  - o topo perdeu a etiqueta e o segundo botão;
  - o rodapé chama para pedir o histórico ao Spotify, em vez de repetir "Abrir o app";
  - saiu a contagem de testes.
- **"Abrir o app" sem cortina nem som:** a página inicial fica na tela até o app abrir, e o app entra subindo.

### Corrigido
- **Rolagem lateral no celular,** causada pela luz do palco no topo da página inicial.

## [1.20.0] — 2026-11-17

Duas mudanças de cálculo na Dupla, escolhidas depois de um estudo com 12 históricos reais. Valem no app web e no app de PC, com o mesmo número nos dois.

### Mudado
- **"Favoritos em comum" passa a usar o RBO dos 50 artistas mais ouvidos** no lugar do Jaccard do top 20. O RBO compara os rankings e pesa mais o topo. No estudo, reconheceu a mesma pessoa em 95,8% dos casos, contra 83,3% do Jaccard.
  - **O número muda de escala** para quem já comparou antes: não dá para comparar com o valor antigo.
  - O campo da API `jaccard_top20` virou `rbo_top50`.

### Novo
- **Opção "Dar mais peso ao que vocês ouvem agora"**, nas Opções de dados (desligada por padrão).
  - Com ela, uma escuta de 1 ano atrás vale metade no cosseno, no Ruzicka e nos favoritos.
  - No estudo, prevendo os últimos 30 dias, o acerto subiu de 91,7% para 95,8%.
  - O resultado avisa quando a opção está ligada.
  - A API `comparar_dupla` do app de PC ganha a entrada `recente`.

## [1.19.1] — 2026-11-17

### Mudado
- **Resumo do Wrapped (último story) e pôster PNG refeitos:**
  - o período fica embaixo do logo (antes ficava sob o botão de pausa);
  - "Sua retrospectiva" aparece com as iniciais;
  - as horas ficam em destaque;
  - o fundo é escuro, com a luz da capa atrás do Artista da vida;
  - os blocos se distribuem pela altura.

### Corrigido
- **Nenhum texto é mais cortado com reticências** no resumo e no pôster. Nomes e músicas longos quebram a linha ou diminuem a fonte, e as cinco músicas viram uma lista.

## [1.19.0] — 2026-11-17

Menos efeitos, mais personalidade: uma avaliação externa apontou recursos estéticos demais ao mesmo tempo (vidro, gradientes, animações, cartões e etiquetas). O SyncUp fica mais enxuto e editorial, sem mudar cálculos nem funções.

### Mudado
- **O Match vira dueto.** Cada par aparece com:
  - os nomes na cor de cada pessoa, ligados por "×";
  - a nota (a comparação dos rankings, a mesma de antes) e o nível em texto;
  - duas faixas cujo trecho do meio mostra os artistas em comum;
  - o "Refrão em comum" e o "Lado B" de cada um.
  - Tela, stories e pôster usam os mesmos dados.
  - No trio, cada um dos três pares tem a sua nota; o refrão é o dos três, e o Lado B vem agrupado por quem indica.
  - Saem a renda, os corações e os bilhetes. "O casal do grupo" vira "O dueto mais afinado".
- **Vidro só no que flutua:** barra do topo, barra de modos, dock, controles dos stories e a placa do palco. Os cartões viram superfícies sólidas (#181818, com fio de 1 px), sem aro de luz, brilho ou cor vazando. Na Dupla com stories, os elementos com blur caem de 23 para 6.
- **Só animações funcionais:** saem a aurora e o vinil do fundo, as entradas por rolagem, o brilho dos botões e as notas caindo no rodapé. Ficam os stories, o equalizador, a troca de modo, o progresso do trecho, a entrada do topo e as barras do espectro.
- **Página inicial editorial:** cada modo é uma faixa com número, texto, fatos em texto corrido, o story de exemplo e o link para abrir. Saem a prateleira "Comece por aqui", os filtros e as caixas. As etiquetas que repetiam o título das seções também saem.
- **Batalha:** as rodadas viram uma lista com fios. **Palco no computador:** a fila vira uma lista simples.

### Corrigido
- O story de um trio no Match mostrava só a nota do primeiro par.

## [1.18.1] — 2026-11-17

### Mudado
- **Pôsteres em PNG no tema novo dos stories** (Wrapped, Dupla, Batalha e Match): fundo "capa de playlist" (a cor vem do alto e se apaga no escuro), cartões e pílulas de vidro com borda de luz e o kicker no estilo do Spotify. Era a pendência da 1.18.0.

## [1.18.0] — 2026-11-17

Os stories entram no tema novo, ganham painéis no computador e a página inicial fica viva.

### Novo
- **Stories no computador (a partir de 1240 px):** três colunas, como o Spotify.
  - Esquerda: a fila dos stories. Clicar pula para o story; se estava pausado, continua pausado.
  - Meio: o player.
  - Direita: "Tocando agora", com a capa grande do trecho, faixa, progresso e silenciar, mais os botões e a nota do som.
  - Abaixo de 1240 px fica uma coluna só, como antes. Redimensionar a janela não reinicia a música nem o story.
- **Página inicial viva:**
  - a luz do fundo muda de cor com a seção (verde na Dupla, violeta no espectro, laranja e rosa na Batalha e no Match);
  - um vinil gira devagar ao fundo;
  - cada seção entra com uma animação ligada à rolagem.
  - Tudo fica parado com "menos movimento".
- **Batalha e Match na página inicial** com um story de verdade no cartão: o pódio e o cartão do par.

### Mudado
- **Tema único nos stories:** todos os modos usam a mesma moldura, a "capa de playlist", com a cor do story vindo do alto e se apagando no escuro. Os cartões têm o vidro com borda de luz, e as listas viram linhas no estilo do Spotify.
  - A Dupla deixa o fundo dividido em verde e violeta; o violeta fica na pessoa B.
  - O contraste do texto no topo dos slides passa de 8:1 (6,6:1 no rosa-claro do Match).
- **Cascata:** a faixa de cor do topo de cada modo virou uma luz só, que passa por baixo da barra lateral e some sem borda.
- **"Baixar pôster"** também fica nos botões embaixo dos stories.

### Corrigido
- **Dock no celular:** ele cobria "Ver de novo" e "Playlist comum · CSV". Agora some quando os botões estão na tela.

### Pendente conhecido
- **Pôsteres em PNG:** continuam no visual antigo e vão para o tema novo na **1.18.1**.

## [1.17.0] — 2026-11-17

Visual: o vidro ficou de verdade e o SyncUp ficou com mais cara de Spotify.

### Novo
- **Topo de playlist:** cada modo do app abre como a página de uma playlist, com a faixa de cor do modo descendo do alto, uma "capa" com o ícone do modo e o título grande.
- **Prateleira "Comece por aqui"** na página inicial: uma capa por modo; o botão verde de play aparece ao passar o mouse (no celular, sempre visível) e abre o modo direto.
- **Filtros em pílulas** nos recursos da página inicial (Tudo, Dupla, Wrapped, Batalha, Match), feitos só com CSS e rádios de verdade, que funcionam com teclado e leitor de tela.
- **Progresso do trecho no dock:** uma linha verde mostra os 30 s do trecho que está tocando.

### Mudado
- **Vidro de verdade:** borda com luz (clara no alto, apagada embaixo), brilho no topo e a cor do modo vazando no vidro (verde, laranja ou rosa; na página inicial, cada recurso com a sua). Na página inicial, uma faixa de luz atravessa o cartão ao passar o mouse.
- **Barra de modos:** a página atual virou uma gota de vidro com brilho verde, no lugar do bloco branco.
- **Blur só no que flutua** (topo, barra de modos, dock e a placa do palco). Os cartões do meio ficam translúcidos sem blur, mais leves para celular simples.
- **Títulos** mais pesados e apertados.
- **Página inicial:** o título dos recursos inclui o Match.

### Corrigido
- **Campos de nome do Match sem rótulo:** repetiam os IDs da Batalha (as duas telas ficam carregadas juntas); tocar em "Nome" levava ao campo escondido da Batalha e o leitor de tela lia o campo sem nome.

## [1.16.0] — 2026-11-17

O Match chega ao navegador, com cara de cartão de namoro, e a Batalha ganha som nos stories.

### Novo
- **Match no navegador:** de 2 a 16 pessoas, por histórico ZIP ou por convite colado. O SyncUp compara todos com todos e forma os pares que somam a maior compatibilidade do grupo (com número ímpar, um trio). O cálculo é o mesmo do app para PC, conferido em teste com os mesmos arquivos.
- **Convite no navegador:** "Gerar o meu convite" cria o código `SYNCUP1.` a partir do seu ZIP, com botão de copiar. Só os rankings viajam. Um código feito no navegador abre no app para PC e vice-versa; código cortado ou alterado fica de fora com o motivo, sem derrubar os outros.
- **Visual do Match:** cada par é um cartão de namoro, com renda, as iniciais dos dois e um coração batendo, a nota em porcentagem e em cinco corações, a fita do nível, "Vocês dois amam" e bilhetinhos com o que cada um deveria ouvir. Os cartões entram animados (parados com "menos movimento"), e a área inteira do Match fica em rosa.
- **Stories, som e pôster do Match:** abertura, um story por par e o "casal do grupo" por último. Cada par toca um trecho do artista que mais os une; o pôster em PNG traz o casal do grupo.
- **Som nos stories da Batalha:** cada rodada toca o artista favorito de quem venceu, a dupla mais afinada toca o artista que une os dois e o pódio, o favorito do campeão. Só os nomes dos artistas vão à Apple (iTunes), como diz a nota abaixo dos stories.

### Fora desta versão
- No navegador, o Match ainda não tem ListenBrainz, gêneros nem a sintonia (ouvir junto). Continuam no app para PC.

## [1.15.0] — 2026-11-17

Um visual novo, Liquid Glass, na página inicial e no app, sem mudar o que o SyncUp calcula.

### Novo
- **Página inicial:**
  - O topo tem um palco em 3 camadas: a luz das capas, uma placa de vidro com o "tocando agora" e o story da Dupla na frente. As capas são abstratas e do próprio projeto, nunca capas reais.
  - Os recursos viraram um bento: Dupla, Wrapped, o espectro de escuta das 24 horas e a Batalha. O espectro agora é interativo: mouse, toque ou setas mostram os plays de cada hora.
  - "Como usar" virou uma tracklist: o número da faixa vira ▶ quando você passa por cima.
  - A privacidade aparece em três colunas, sem caixas. Licença, testes e releases foram para o rodapé.
- **Upload:** o espaço de soltar arquivos é um slot de vidro. Assim que o arquivo entra, ele mostra o período e o número de reproduções. Se o arquivo estiver errado, você vê o erro ali mesmo, antes de comparar.
- **Dock dos stories:** uma cápsula fixa na base mostra a música que está tocando (com a capa), o botão de mudo e "Baixar pôster".
- **Luz ambiente:** o fundo acende com as cores da capa que está na tela. Só a cor sai da capa; a capa em si continua nítida.
- **Abertura do app:** um esqueleto com o logo pulsando aparece enquanto o app carrega.

### Mudado
- **Vidro:** tokens novos (fundo #0a0a0c, superfícies #121212 e #181818, verde #1ed760 com hover #3be477, raio de 26 px, botões em cápsula). Todos os cartões têm blur, com fundo sólido para quem pede menos transparência no sistema.
- **Fundo:** saíram as manchas de cor fixas.
- **Ícones:** desenhados no lugar dos emoji nos controles de som.
- **Barra de baixo do app:** mostra só os modos que funcionam no navegador.
- **Demos:** usam "Ana" e "Bruno".
- **Página inicial:** passa a mostrar a Batalha. Match e Grupo ficaram num cartão só, "Só no app para PC".
- **Bordas:** o arredondamento segue uma escala única (campo, cartão e painel).

### Desempenho
- **Leitura dupla:** cada histórico agora é lido duas vezes, uma para o resumo do upload e outra para o cálculo (veja `benchmark/web.md`).
- **Blur:** o FPS com blur em todos os cartões ainda precisa ser medido num celular.

## [1.14.0] — 2026-11-16

Uma versão de cuidado com o app no navegador: acessibilidade, ciclo de vida e medições, sem recursos novos.

### Corrigido
- **Stories com "menos movimento":** eles não avançavam mais, porque o tempo dependia de uma animação CSS que essa preferência desliga. Agora um relógio em JavaScript marca o tempo, e a barra só mostra o progresso.
- **Espaço e Enter** nos botões dos stories fazem a ação do botão (antes pausavam).
- **Celular estreito (360 px):** os nomes dos arquétipos voltam a aparecer, com a barra numa linha própria.
- **Corrida dos artistas:** para de vez ao sair da aba Gráficos. Um arraste cancelado não deixa mais o controle preso.

### Mudado
- **Corrida pelo teclado:** setas, PageUp/PageDown e Home/End. O leitor de tela anuncia o mês, e a área de toque tem 44 px.
- **Home e End nos stories:** vão ao primeiro e ao último story.
- **Rolagem até o resultado:** respeita "menos movimento".
- **Alto contraste do Windows:** as barras de progresso e de dados usam as cores do sistema. Ainda falta conferir nos temas de contraste do próprio Windows.
- **Sinais além da cor:** os anos do top 5 ganham ★; o placar da Batalha escreve as medalhas ("2 ouros, 1 prata").
- **"Silenciar":** fica guardado no navegador entre visitas.
- **Workers:** os três modos falam com eles por um módulo só (`js/worker.js`). Cancelar tem fim definido, e uma resposta ilegível vira mensagem clara.

### Interno
- **Constantes e tokens:** constantes repetidas, a cor média das capas e tokens de cor passam a ter uma fonte só. Os dois `fmtNum` continuam separados, de propósito (paridade de cada lado com o Python).
- **Testes novos:** contrato dos Workers, relógio dos stories, zip bomb pela soma declarada, e um teste de que o tempo dos stories não volta a depender de CSS.

### Documentação
- **Benchmark do app no navegador:** `benchmark/web.md`, antes e depois, com cenários reproduzíveis. Nenhuma otimização foi necessária.
- **Login com o Spotify:** README e `docs/decisao-spotify.md` explicam por que não há login (regras do Spotify em novembro de 2026, com as fontes).

## [1.13.0] — 2026-11-16

A Batalha chega ao app no navegador: de 3 a 6 pessoas disputam rodadas com os números do período.

### Novo
- **Batalha** (no lugar do "Grupo — em breve" do app web): cada pessoa envia o seu histórico e o app compara o mesmo período de todos (recorte comum, como no Grupo do PC).
  - **10 rodadas:** Maratonista, Play infinito, Explorador(a), Colecionador(a), Sem parar, Dia mais insano, Coruja, Repeteco, Fã nº 1 e Paciência (menos pulos vence). Rodada sem dado ou sem disputa fica de fora, com o motivo.
  - **Quadro de medalhas:** ouro, prata e bronze, com empates olímpicos; o campeão tem mais ouros, depois pratas, depois bronzes; empate total vira co-campeões.
  - **Disputa:** selos "Por um triz" e "Massacre", "Dedinho nervoso" na Paciência, título de classe do campeão ("Enciclopédia Musical", "Modo Obsessão"…), "Decidido no detalhe" e uma resenha da partida.
  - **Dupla mais afinada** (cosseno log1p) e o artista que mais une os dois.
  - **Stories:** cada rodada com um desenho próprio (pista, vinis, constelação, estante, luas…); o pódio é sempre o último.
  - **Tela:** pódio de vidro que sobe quando aparece, cartões das rodadas e a tabela completa.
  - **Pôster** em PNG 1080×1920 e "Compartilhar pôster".
  - Lê um histórico por vez num Worker (a memória não cresce com o grupo) e para ao trocar de modo. Demo com 4 pessoas fictícias (Ana, Bruno, Carla e Davi).

### Mudado
- A troca de modo desliza na ordem da barra (Dupla, Wrapped, Batalha).

## [1.12.0] — 2026-11-16

O app no navegador deixa de baixar o CSS e o JS do app para PC.

### Mudado
- **Visual próprio no app web:** o `nucleo.css` (10 KB) traz só as regras do `styles.css` que o app web usa (listas dos Rankings, corrida dos artistas, moldura dos stories e detalhe dos arquétipos). Antes ele baixava o `styles.css` inteiro (58 KB) como `componentes.css`. A tela não muda: capturas de antes e depois iguais no celular e no PC.
- **Corrida e onda nos botões em módulo próprio:** o `js/corrida.js` (7,6 KB) faz o mesmo que o `syncup.js` (13 KB, antes `componentes.js`), sem vigiar a página inteira. A corrida começa ao aparecer e respeita o "menos movimento".
- O `tools/empacotar_web.py` gera só as duas demos do "Testar com dados fictícios". O app para PC (`styles.css` e `syncup.js`) não mudou.

## [1.11.0] — 2026-11-16

A Dupla roda em JavaScript no navegador, sem baixar o Python, e os gráficos foram refeitos para o celular.

### Mudado
- **Dupla sem Pyodide:** a comparação roda em JavaScript num Web Worker, como o Wrapped desde a 1.5.0. Não baixa mais o Python (~15 MB na primeira visita). A demo da Dupla caiu de 18,7 s para 1,0 s no PC. Os resultados são os mesmos do Python: paridade em testes a cada etapa, inclusive a resposta inteira do app e o CSV da playlist, byte a byte.
- **"Testar com dados fictícios"** usa dois históricos prontos (Ana e Bruno), sem gerar nada no aparelho.
- **Gráficos da Dupla no app web, sem Plotly:** quatro gráficos em HTML, pensados primeiro para o celular. Cada um tem no título o fato principal, os números escritos (sem depender do mouse) e uma tabela para leitor de tela. Saíram o mapa de 168 células e os "Rankings comparados", que repetiam os artistas lado a lado. A aba não baixa mais ~5 MB e não prende a rolagem no celular. O app para PC segue com o Plotly.

### Corrigido
- **Empates com regra explícita no Python e no JS:** as contribuições ao cosseno desempatam pelo valor com 15 casas, e os 12 artistas do gráfico desempatam pelo nome. Antes, a ordem de empates podia variar.

## [1.10.0] — 2026-11-13

Os stories da Dupla agora tocam as músicas que vocês dois têm em comum.

### Mudado
- **Som na Dupla:** cada story toca um trecho de 30 s ligado ao que ele mostra: a música em comum mais ouvida na abertura e no pôster, uma música dos artistas em comum, os favoritos de cada um, os artistas que um apresenta ao outro e, em "Em sintonia", a música que tocou para os dois ao mesmo tempo. Começa sozinho, como no Wrapped, com o mesmo botão "Silenciar".
- Dupla e Wrapped dividem o mesmo áudio: trocar de modo pausa a música, e cada modo retoma a sua ao voltar.

### Privacidade
- Para o som da Dupla, só os nomes das músicas e dos artistas em comum das duas pessoas vão para a Apple (iTunes), com o endereço IP. Os históricos e os nomes não saem do aparelho. A nota no app, a página inicial e o README dizem isso.

## [1.9.0] — 2026-11-13

Auditoria completa: correções de experiência, privacidade e paridade, e cortes do que não se pagava.

### Corrigido
- **Som do Wrapped** para quando você troca para a Dupla; o clique do fader usa o mesmo áudio dos stories e respeita o "Silenciar"; sem Web Audio no navegador, o Wrapped monta igual.
- **Rede ruim:** buscas de capas, trechos e imagens do pôster desistem em 8 s (antes podiam ficar em "Buscando…" para sempre); cada música é buscada uma vez só no iTunes.
- **"Tentar de novo"** usa os arquivos e opções que estão na tela; se o motor cair por falta de memória, o erro pede para recarregar em vez de ficar em "Comparando…".
- Foco das abas do resultado sem corte; no alto contraste do Windows, gráficos e barras não somem.
- Arquivo de formato errado mostra aviso; uma busca de som antiga não reinicia um resultado novo; o Python do navegador libera a memória mesmo quando a leitura falha.
- **Python e JS com a mesma regra:** data sem hora ou sem segundos entra; datas antes de 1970 e plays de mais de 24 h saem (arquivo corrompido).
- "Pular para o conteúdo" não tira mais a pessoa do Wrapped.
- Match (app para PC): nome repetido acusa logo no começo, antes de ler os históricos.

### Mudado
- Ponderação do cosseno no app do navegador começa em **Logaritmo (ln(1+x))**.
- Rótulo "em breve" da barra em 12 px; no story "Fiel", o ano escolhido e o foco do teclado têm marcas diferentes; ícone na aba do navegador.
- User-Agent do MusicBrainz e do ListenBrainz com a versão atual.

### Segurança e privacidade
- Scripts de CDN (htm, Lenis e Plotly) carregam com verificação de integridade.
- Textos atualizados: o Wrapped começa com capas e som (sem "opt-in"), e os nomes dos artistas também vão à Apple para os trechos.

### Removido
- **Login do Spotify no app para PC** (só servia a 5 contas cadastradas à mão): o Match e o convite seguem com ZIP, ListenBrainz e convite. Saem os perfis salvos e o "Apagar perfil".
- `medir_desempenho.py`, `docs/PASSO_3.md`, as fixtures `tests/fixtures/v05_passo1` e a função `arquetipo()` sem uso; regras de CSS e tokens mortos. Cerca de 1.800 linhas a menos.

## [1.8.0] — 2026-11-13

Transições com cara de música e chegadas suaves no site e no app do navegador.

### Mudado
- **"Abrir o app"**: 12 barras de equalizador, do verde ao violeta, sobem a partir do clique e cobrem a tela, com um sopro baixo; o app nasce coberto e as barras descem. Substitui o círculo.
- **Troca entre Dupla e Wrapped como crossfader**: o conteúdo desliza de um lado para o outro, o destaque corre pela barra como o botão de um fader e toca um clique curto (mais agudo para o Wrapped, mais grave para a Dupla).
- **Chegadas**: o resultado, os avisos, os erros e os arquivos escolhidos entram com um movimento curto, uma vez só; "Ver mais" abre crescendo; o ponto verde pulsa quando o app fica pronto; o ícone da barra de modos responde ao toque.
- Com "menos movimento" ligado, nada disso anima nem toca.

### Corrigido
- "Pular para o conteúdo" tirava a pessoa do Wrapped e levava para a Dupla.

## [1.7.0] — 2026-11-12

Visual novo no site e no app do navegador, com vidro, movimento e detalhes musicais.

### Mudado
- **Página inicial nova**: os stories de verdade da Dupla no topo (com dados fictícios), recursos com prévias ao vivo, "Quando cada um ouve" (as 24 horas de duas pessoas), passos como faixas de um disco e uma pauta no rodapé.
- **App do navegador**: barra de modos embaixo no celular e na lateral no computador; Match e Grupo marcados como "em breve"; cartões "Lado A" e "Lado B"; carregamento em forma de equalizador.
- **Vidro**: desfoque real só no computador; no celular, painéis sem desfoque para manter a rolagem leve.
- **Afinador da sintonia**: na abertura da Dupla, o % de escuta em comum aparece num afinador (100% = afinados, A4 · 440 Hz; abaixo disso, desvio em cents).
- **Transição ao abrir o app**: um círculo que se abre a partir do clique (navegadores com View Transitions; com "menos movimento", sem animação).
- **Stories** com coreografia de entrada; no Wrapped, cada story dura 13 s (antes 10 s).
- **Wrapped começa sempre com capas e som**: o toque em "Montar meu Wrapped" já libera o áudio. A nota do que vai para a internet fica sempre visível.
- **Pôsteres**: a pessoa em destaque (nome, horas e artista maiores); o convite virou uma linha discreta no pé.
- README e imagens atualizados: o app do navegador vem primeiro.

### Corrigido
- Gráficos da Dupla que não apareciam e o relógio do Wrapped encolhido (regra de ícones larga demais).
- Texto encostado na borda dos botões.
- Rolagem lateral no celular de 390 px.
- No Wrapped, o topo dizia "Nada é enviado para nenhum servidor"; agora diz que o histórico não sai do aparelho.
- Som bloqueado pelo navegador leva de volta ao botão "Ligar capas e som".

## [1.6.0] — 2026-11-12

Dupla do app no navegador em stories: uma história no topo e os detalhes embaixo.

### Mudado
- **Dupla "stories primeiro"**: 7 stories no mesmo player do Wrapped (abertura com o % de escuta em comum, o que une vocês, frente a frente, para apresentar, relógios, em sintonia e o pôster). Verde = pessoa A, violeta = pessoa B, rosa = os dois juntos; todo valor tem o nome ao lado.
- **3 abas em vez de 7**: Rankings (no celular, uma pessoa por vez), Gráficos (com a corrida de artistas) e Detalhes técnicos (as 4 medidas, cada uma com uma frase dizendo o que mede).
- **Pôster da dupla em PNG desenhado no navegador** (Canvas), com "Compartilhar pôster" no celular; "Playlist comum · CSV" e "Ver de novo" embaixo dos stories. O app web não baixa mais o Pillow.
- A Dupla não calcula mais o Wrapped de cada pessoa: a comparação ficou mais leve.
- Vidro "Sintonia" no app: borda em degradê verde → violeta, painéis sem blur (mais leve no celular), espaços e cantos em uma escala só.

### Corrigido
- Erros com "Tentar de novo", estados vazios que explicam o que falta, anúncio do resultado para leitor de tela e confirmação antes de apagar as capas guardadas.

## [1.5.1] — 2026-11-10

Correções de uma auditoria de segurança e resiliência.

### Corrigido
- **ListenBrainz**: um 429 (serviço ocupado) não derruba mais a coleta na hora; o SyncUp tenta de novo até 3 vezes, esperando o tempo que o servidor pede.
- **App do navegador**: arquivo de mais de 64 MB dentro do ZIP é recusado com uma mensagem clara, em vez de fechar a aba no celular; a conferência de partes repetidas ficou 8× mais rápida.
- **Perfis no Linux e no macOS**: um novo login de "ana" criava um segundo arquivo ao lado do "Ana.json"; agora substitui o da mesma pessoa, como no Windows.
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
