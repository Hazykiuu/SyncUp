# Validação — SyncUp v0.5 final

## Correção de empates — 08/10/2026

- Causa reproduzida no pacote anterior: com `NPY_DISABLE_CPU_FEATURES=AVX512F,AVX2`, ambos os testes pytest de regressão falham por ordem/seleção diferente entre contagens empatadas. Isso demonstra dependência do caminho nativo de ordenação, sem importar NumPy diretamente. Não é uma validação do Windows do usuário.
- Rankings atuais usam contagem decrescente e desempate por nome crescente; faixas usam música e depois artista. O mesmo critério vale no corte do top 20.
- Golden masters e fontes históricas permanecem byte a byte iguais. A regressão mantém contagens/tipos/métricas e identidade acima do empate no corte, além de validar todo o ranking contra contagens independentes. Novos testes adversariais verificam que erros reais continuam sendo rejeitados.
- Suíte atual: **128 testes aprovados**, um aviso de depreciação de Starlette/AnyIO, em Python 3.12.14/Linux. Os 22 testes direcionados também passam com as extensões AVX512F/AVX2 desativadas.
- Golden master de 300 mil eventos/3 mil artistas por perfil: **3 testes aprovados**. Ruff: lint sem erros, 30 arquivos atuais formatados. Sintaxe dos arquivos Python atuais conferida com AST de Python 3.10.
- O Windows não foi executado neste ambiente. Instruções do pacote usam Python 3.12 explicitamente, sem prometer compatibilidade das dependências fixadas com Python 3.14.

Os resultados abaixo registram a entrega anterior, de 120 testes. A execução do notebook registrada abaixo não foi repetida nesta correção, que não altera suas células.


Entrega do Passo 4, Fase 7, em 08/10/2026.

## Ambiente executado

Python 3.12.14, pandas 2.2.3, Gradio 5.50.0, Plotly 6.9.0, Pillow 11.3.0, pytest 8.3.5, Ruff 0.11.13, PyArrow 17.0.0.

As dependências diretas foram instaladas a partir de `requirements-dev.txt` e `requirements-parquet.txt`. Requisitos de Python das versões diretas inspecionados: compatíveis com 3.10. Dependências transitivas são resolvidas pelo pip conforme o ambiente, sem lock universal.

## Resultado

| Verificação | Resultado |
|---|---|
| `python -m pytest -q` | **120 testes aprovados**, incluindo Parquet, golden masters e fluxo HTTP Gradio |
| `python -m ruff check .` | Sem erros |
| `python -m ruff format --check .` | 28 arquivos atuais formatados; fontes congeladas excluídas |
| Golden master com 300.000 eventos/3.000 artistas por perfil | 3 testes aprovados; recorte comum e histórias completas |
| `python tools/verificar_notebook.py` | 18 células totais; 9 células de código executadas; zero erros |
| Sintaxe mínima | AST Python 3.10 válida nos módulos, ferramentas, testes e células |
| Métricas puras | Nenhum import direto de NumPy na implementação atual |
| Benchmark CLI | Fluxo com cache frio/quente/Parquet e relatórios JSON/CSV/Markdown executado em entradas fictícias pequenas |

Os 120 testes incluem os casos parametrizados pytest novos e a suíte unittest dos passos anteriores. Nenhum histórico pessoal foi usado. Os arquivos e referências em `tests/golden/` e `tests/fixtures/` permanecem os mesmos; os testes verificam hashes das fontes congeladas.

Casos numéricos extremos revelaram e protegeram uma correção: o reescalonamento evita overflow e falsas normas nulas, preservando cosseno/contribuições, volumes do Ruzicka e diversidade. Comparações gerais de floats têm tolerância explícita; o caso analítico 3–4–5 verifica soma exatamente igual a 1.

A execução pytest apresenta um aviso de depreciação de Starlette/AnyIO (`BlockingPortal`), sem falha. Avisos sobre uma futura migração do Gradio para 6 são filtrados especificamente, pois esta entrega fixa Gradio 5.

## Limites da validação

- Python 3.10 foi inspecionado por sintaxe/metadados; o interpretador efetivamente executado foi Python 3.12.14.
- O código real do notebook foi executado em IPython, numa cópia temporária, com dados fictícios e interface desativada. Células de EDA, plots, grupo, métricas, CSV e PNG foram exercitadas; o protocolo de kernel e a interface gráfica do Jupyter não foram validados. A execução de um kernel de rede não foi permitida neste ambiente.
- A interface foi montada e seu fluxo HTTP foi testado em processo; não foi feita auditoria visual completa em navegador ou leitor de tela. Contrastes dos pares principais têm teste numérico.
- O benchmark pequeno foi verificação de funcionamento do CLI, não evidência de desempenho representativo. `benchmark/300k.*` continua sendo o relatório histórico do Passo 2 e não foi reatribuído à v0.5 final.

O notebook distribuído está sem saídas e sem arquivos de dados/exports reais. O verificador cria e remove seus exemplos temporários, sem alterar o notebook.

## v0.6 — verificações desta entrega (2026-10-09)

- `pytest`: 137 testes aprovados em Python 3.12 (dependências fixadas), 3.13 e 3.14 (pandas 2.3.3, PyArrow 26), instalando somente binários (`--only-binary=:all:`).
- `ruff check` e `ruff format --check` sem pendências.
- Golden master em escala grande (`--escala-grande`, 300 mil eventos) aprovado; `tools/verificar_notebook.py` executou todas as células.
- Momentos sincronizados: totais e exemplos idênticos à implementação anterior nos dados fictícios de 300 mil eventos.
- `tests/test_v06.py` reproduz os erros corrigidos (ZIP com `__MACOSX`, nomes `None`) — ambos falham na v0.5 e passam na v0.6.
- Interface conferida no Chromium: animações aplicadas (contagem, anel, barras, mapa, listas, corrida), ripple nos botões e nenhum erro de JavaScript.
- Benchmark local (2 núcleos, 300k eventos por perfil, sem Parquet), mediana do caminho completo da interface: dupla fria 9,2 s → 4,8 s; dupla em memória 1,8 s → 1,2 s (já incluindo os novos blocos); grupo 4 perfis frio 12,7 s → 6,4 s.

## v0.7 — Wrapped e arquétipos (2026-10-09)

- `pytest`: 142 testes aprovados (Python 3.12; 141 no 3.14 sem o teste de notebook, que depende de dependências de desenvolvimento); `ruff` sem pendências; golden master em escala grande e verificador do notebook aprovados.
- `tests/test_wrapped.py` confere à mão rankings, sequência de dias no fuso local, recorde, hábitos, anos, fidelidade, ausência de dados do aparelho, exportações sem hábitos, escolha de arquétipos e escapes de HTML.
- Calibração dos limiares com quatro históricos reais (2017–2026): cada um recebe um principal coerente com os números (Do começo ao fim, Maratonista ×2, Devoto(a)); Wrapped calculado em 0,2–0,6 s por histórico, já com a leitura.
- Stories conferidos no Chromium em 1400 px e 390 px: 14 slides, navegação, contagens, PNG e nenhum erro de JavaScript.

## v0.8 — Match e login com Spotify (2026-11-03)

- `pytest`: 151 testes aprovados; `ruff` sem pendências.
- `tests/test_match.py`: conversão ZIP → rankings nas janelas da API, pesos por posição, nomes normalizados entre fontes, emparelhamento comparado com busca exaustiva (6 pessoas) e trio com número ímpar, JSON sem token, PKCE (desafio S256 conferido), coleta completa e rotas do servidor com a API do Spotify **simulada**.
- O login real não pôde ser testado aqui (exige um app no Developer Dashboard e contas cadastradas); o redirecionamento para `accounts.spotify.com/authorize` com PKCE foi conferido no servidor local.
- Match com 4 históricos reais conferido no Chromium: matriz, duplas ótimas, trocas sugeridas e ranking, sem erros de JavaScript.

## v0.95 — repaginação e revisão de QA (2026-11-04)

- Medição com dois históricos fictícios de 285 mil eventos cada (`tools/gerar_dados_falsos.py`, seeds 41 e 97): **Em sintonia de 19,06 s para 0,55 s**, com o mesmo resultado (118 momentos, 283 min). A análise "Quase juntos" leva 0,29 s.
- Testes novos que falham na versão anterior: um play repetido e dois aparelhos sobrepostos não dobram os minutos; um usuário do ListenBrainz com 404 ou sem rede fica de fora com aviso e o Match segue com os demais; o cartão "Em sintonia" abre a sub-aba certa.
- No Chromium: Início e Dupla em 1280 px, navegação fixa ao rolar, botões "Abrir…" levando às abas; em 375 px, sem rolagem horizontal.

## v0.9 — estilo, playlist da festa, stories do Match e código aberto (2026-11-03)

- `pytest`: 180 testes aprovados e 3 pulados (PyArrow não instalado), em Python 3.12.10 no Windows; `ruff check` e `ruff format --check` sem pendências.
- Testes que falham na versão anterior e passam nesta: trio comparado com busca exaustiva (5 e 7 pessoas) e duas leituras simultâneas de históricos (antes ficavam em fila na trava global).
- `tests/test_generos.py`: MusicBrainz **simulado**, com intervalo de 1 s (relógio injetado), score mínimo, cache em disco, falha de rede fora do cache e gêneros do Spotify preservados. A API real do MusicBrainz não foi chamada.
- `tests/test_festa.py`: cobertura de todo o grupo, determinismo, CSV protegido, XSPF válido e escapado, stories com nomes escapados, cartão com e sem gêneros.
- App real (`python app.py`) com 5 ZIPs fictícios de 20 mil eventos, pela API HTTP do Gradio: Match com trio em 1,63 s e repetido em 0,16 s (cache do perfil), playlist da festa com 30 faixas (CSV e XSPF) e cartão PNG da dupla.
- No Chromium: a fonte Figtree carregada localmente, nenhuma requisição a `fonts.googleapis.com`/`gstatic` e nenhum erro de JavaScript.
- Revisão de código (correção, segurança e qualidade): 10 achados corrigidos, entre eles o pré-carregamento de ZIPs já em cache, a escala do "meio peso" da festa e a falha silenciosa do MusicBrainz. Nenhuma vulnerabilidade encontrada. Suíte: 186 testes aprovados.
- **MusicBrainz real**: Legião Urbana, Pitty, Radiohead e Anitta com gêneros corretos e score 100, intervalo de ~1 s entre consultas e banda inexistente sem gênero, depois lida do cache sem rede. A primeira consulta de uma sessão falhou uma vez de forma passageira; agora há uma nova tentativa.
- **Login real no Spotify** (dono do app): perfil salvo com 3 rankings de 50 artistas, 50 recentes e 61 seguidos, sem token. O Spotify não enviou gêneros em modo de desenvolvimento. Uma segunda conta recebeu 403 em `/me/top/artists` mesmo depois de autorizar: é a regra da lista de usuários do modo de desenvolvimento. Por isso entrou o ListenBrainz.
- **ListenBrainz real** (usuário público `rob`): rankings de semestre e ano e 50 listens; o mês sem estatística (204) vira ranking vazio; usuário inexistente dá 404 com mensagem clara.
- **Em sintonia**: teste conferido à mão (3 min de sobreposição contados; outra faixa no mesmo horário e sobreposição de 20 s ignoradas; hora local no fuso de A). Com dados fictícios de 20 mil eventos: 11 momentos e 25 min em 0,6 s. Pela interface real (botão de dados fictícios da Dupla): 5 stories montados, linha do tempo com os meses vazios preenchidos.
- Suíte: 198 testes aprovados e 3 pulados.
- **Stories do Match no Chromium**, com o HTML devolvido pelo endpoint real `encontrar_matches` (5 ZIPs fictícios): o player montou 4 slides (abertura, trio, dupla, resumo) com barras de progresso, as setas avançam e voltam, as contagens animadas mostram os valores finais e o nome com `<b>` aparece como texto.

## v0.96 — sintonia no Match (2026-11-04)

- `pytest`: 212 testes aprovados e 3 pulados (PyArrow não instalado); `ruff check` e `ruff format --check` sem pendências.
- `tests/test_sintonia_match.py`: o cruzamento novo é comparado com uma **força bruta** (todos os intervalos contra todos) em 5 sorteios com muitas sobreposições; nomes de fontes diferentes se encontram; paginação do ListenBrainz **simulada** (`max_ts`, listens sem duração descartados, artista principal, espera pela cota); Match com 3 históricos mostrando a dupla mais sincronizada (7 min, conferidos à mão), nome com `<b>` escapado e story PNG 1080×1920.
- Os testes antigos da sintonia da Dupla passaram sem mudança; nos dados fictícios de 285 mil eventos, a Dupla dá os mesmos 118 momentos e 282,8 min de antes.
- **ListenBrainz real** (usuário público `rob`): 2.000 listens em 2 chamadas, em 3,7 s, com início e duração. Não foi possível conferir uma conta que importa do Spotify (a do `rob` usa o Navidrome).
- App real numa porta de teste (7861), pela API HTTP do Gradio: Match com 5 ZIPs fictícios de 20 mil eventos em 3,7 s, com o prêmio e a linha de sintonia nos pôsteres. Pôsteres conferidos no navegador do app e story PNG conferido em imagem.

## v0.97 — confiança (2026-11-05)

- `pytest`: 221 testes aprovados e 3 pulados (PyArrow não instalado), em 3 rodadas seguidas; `ruff check` e `ruff format --check` sem pendências.
- `tests/test_v097.py`: versão igual no pyproject, no README e na barra; Match com limite 1 e o resto com limite 4; upload com o teto de 1 GB; ZIP e JSON acima do teto recusados (teto reduzido no teste); login aceito sem cabeçalho, `none` e `same-origin`, e recusado em `cross-site` e `same-site`.
- `test_cache_e_hash` falhou 1 vez em 4 rodadas antes da correção (arquivo regravado com o mesmo tamanho no mesmo instante).
- O CI roda no GitHub em Python 3.10 e 3.12; localmente só o 3.12 foi executado.

## v0.98 — privacidade e organização (2026-11-05)

- `pytest`: 227 testes aprovados e 3 pulados (PyArrow não instalado); `ruff check` e `ruff format --check` sem pendências.
- Divisão do `ui.py`: os 221 testes anteriores passaram sem mudar nenhuma asserção (só o alvo das trocas de funções de rede, agora `ui.match`).
- `tests/test_privacidade.py`: lista com tamanho e data; `../app` não apaga nada fora da pasta; limpar o cache apaga só `.parquet`, `.json` e `.tmp` de topo (arquivo alheio e subpasta ficam); cancelar o `confirm()` não apaga nada; nome com `<b>` aparece como texto.
- No navegador do app: o Início mostra os três cartões de privacidade, inclusive em largura de celular, e o painel lista o perfil real salvo. Os botões de apagar não foram clicados no app real (o perfil é verdadeiro); o fluxo foi coberto nos testes.
- Envio aos poucos (relatado pelo Carlos): reproduzido no navegador do app. O 2º arquivo já era somado pelo ícone pequeno do Gradio, mas ele ficava escondido sobre o título. O botão novo abre o seletor do próprio campo (`#su-envio-match`) e a lista mostra os dois arquivos. `tests/test_envio.py` garante o botão nos 5 campos. Suíte: 228 testes aprovados.

## v0.99 — visual, convite e Gradio 6 (2026-11-05)

- Spike num ambiente separado com o Gradio 6.31.0: 235 de 242 testes passaram sem mudança; as 7 falhas tinham 3 causas mecânicas (botão de copiar, `api_name=False`, tema no `Blocks`).
- Depois da migração: 242 testes aprovados e 3 pulados no `.venv` do projeto; `ruff` sem pendências. Resolução das dependências conferida também para o Python 3.10 (Starlette 1.7 lá; 1.10 no 3.12).
- No navegador do app: tema, Figtree, abas fixas, gaveta lateral (o conteúdo monta ao abrir), "Meus dados", cartões do convite e nenhum erro de JS. Match real pela API: os mesmos 11 endpoints públicos.
- Repaginação (Match em grade 2×2, convite em acordeão, Grupo com "Detalhes técnicos"): mesmos componentes e mesma ordem de saídas; `tests/test_ui.py` e `tests/test_smoke_ui.py` passaram sem mudança. Grupo conferido com 3 ZIPs fictícios no navegador.
- Acessibilidade conferida no navegador do app em 390 px (as cinco abas; Dupla, Wrapped e Grupo com resultado), 768 px (Match) e 1280 px: nenhuma rolagem lateral. Pelo teclado: Tab chega nos acordeões e no botão de pausar dos stories com o contorno verde, e Enter/Espaço funcionam. Corrigidos: rolagem lateral de todos os acordeões (Gradio 6), botão de pausar e links de download abaixo de 44 px, abas no celular.
- Final: 242 testes aprovados e 3 pulados; `ruff check` e `ruff format --check` sem pendências. Leitor de tela não foi testado; o menu de abas extras do Gradio se anuncia em inglês ("More tabs").
- Auditoria pelas skills `accessibility` (web-quality-skills) e `huggingface-gradio`: página em `pt-BR`; todos os campos com rótulo, imagens com `alt` e botões com nome; regiões `main`, `header` e `footer`. Corrigidos a ordem dos títulos do Início e o rótulo "More tabs". O axe-core não rodou (carregar script externo no navegador foi bloqueado); sem link de pular navegação, já que a barra tem só 5 abas e a página tem `main` e títulos. `gradio info` no app local: os 11 endpoints públicos do contrato.

## v1.0.0 — lançamento (2026-11-05)

- `pytest`: 237 testes aprovados e 3 pulados; `ruff check` e `ruff format --check` sem pendências. Saíram os 6 testes do notebook; entrou 1 de créditos.
- `iniciar.bat` num clone limpo do repositório: achou o Python 3.14 pelo `py -3` (neste PC, `python` é o atalho da Microsoft Store), criou a `.venv`, instalou sem seaborn e matplotlib e o app respondeu em 127.0.0.1:7860 em cerca de 80 s.
- No navegador do app: créditos na barra em 390 px (sem rolagem lateral, links com 44 px) e em 1280 px. Capturas do README feitas com dados fictícios; o perfil real salvo foi desmarcado no Match antes da captura.
