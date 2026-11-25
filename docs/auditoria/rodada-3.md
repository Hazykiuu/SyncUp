# Auditoria SyncUp — Rodada 3: CI no Windows, contratos Python/JS, versionamento, privacidade e métricas

| | |
|---|---|
| **Commit auditado** | `origin/main` = `253985be1d4666c58e33913b06fcdb0f8549fbe2` (merge do PR #45, que só acrescentou `docs/auditoria/rodada-2.md` sobre a v1.27). A `main` local foi conferida com `git switch main` e `git pull --ff-only` antes de medir ("Already up to date"). |
| **Data** | 2026-11-25 |
| **Ambiente** | Windows 11, Windows PowerShell 5.1, Python 3.12.10 (`.venv`), pytest 8.3.5, Gradio 6.31.0 (conferido com `gradio.__version__`), Playwright/Chromium, Node 26.13. Nesta máquina, `py -0p` lista Python 3.14 (padrão do `py -3`) e 3.12. O CI usa Node 22 e Python 3.10/3.12, só em Linux. |
| **Escopo** | Os 5 itens da Rodada 3: Windows no CI, contratos Python/JS, versionamento, privacidade e integrações, métricas. Só relatório: nenhum arquivo do app, de `.github/` ou o `iniciar.bat` foi alterado. |
| **Dados** | Todos fictícios ("Ana", "Banda Ficticia 0", IDs `AAAA…` de 22 letras, as demos `site/app/demo-*.zip` e `exemplos_ficticios/`). Nenhuma API de dados foi chamada: as respostas de ListenBrainz, MusicBrainz, Last.fm, Spotify e iTunes vêm de mocks (`httpx.MockTransport`, `fetch` falso no Node, `page.route` no Chromium). Idas reais à rede: a resolução de dependências do Python 3.14 (`pip install --dry-run`, sem instalar nada) e o download do Preact/htm do `unpkg.com` nos testes e blocos de navegador. |

## 1. Linha de base dos testes (antes de qualquer diagnóstico)

| Comando | Resultado | Tempo |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` | **295 passaram, 3 pulados, 17 desmarcados** (os mesmos pulados das rodadas 1 e 2: `pyarrow`/Parquet opcionais) | 99 s |
| `node --test tests/js/*.test.mjs` | **105 passaram**, 0 falharam | 1,8 s |
| `.venv\Scripts\python.exe -m pytest -m navegador -q -p no:cacheprovider` | **17 passaram** (Playwright/Chromium) | 38,6 s |

Igual às rodadas 1 e 2. Nenhuma falha. Esta linha de base **é** a medição "no Windows", com Python 3.12: as três suítes passam nesta máquina. O que o CI faria num runner Windows está no R3-03 e não foi executado.

> **Como rodar as evidências:** cada bloco `powershell` roda da raiz do repositório, colado inteiro no Windows PowerShell 5.1. Os blocos são 100% ASCII: os textos acentuados aparecem escapados pelo `ascii()` do Python (`\xe1` = á), e os nomes com acento usados nos testes são montados com `chr()` dentro do próprio bloco. Os blocos com navegador servem `site/` localmente. Nenhum bloco chama uma API de dados de verdade. Todos foram extraídos deste arquivo e rodados assim; as saídas abaixo são as obtidas. Se um bloco de navegador esgotar o tempo esperando o app desenhar, é o `unpkg.com` lento: rode de novo.

## 2. Status e cobertura por item

| Item | O que foi verificado | Como | Resultado | Achados |
|---|---|---|---|---|
| **1. Windows** — CI | os 3 workflows, os passos com sintaxe de bash e um `testes.yml` completo com `windows-latest` | leitura + script que compara a proposta com o arquivo atual | Só `ubuntu-latest`; 2 passos usam bash (`testes.yml:js`, `lint.yml`). Proposta pronta, com os mesmos passos e os mesmos nomes de check no Linux; **não rodada no GitHub** | R3-03 |
| 1 — Python que o usuário recebe | `py -0p`; resolução das dependências no 3.14 | `py -3.14 -m pip install --dry-run --only-binary=:all: --target <temp>` com `requirements.txt` e com `requirements-dev.txt` | O `py -3` (1ª escolha do `iniciar.bat:7`, só usada quando o `.venv` ainda não existe, `:15-18`) pega o **3.14** aqui. As dependências resolvem com binário no 3.14 (código 0 nos dois arquivos). **A suíte nunca rodou no 3.14** | R3-03 |
| 1 — caminhos, encoding e ZIP | pasta com espaço, acento e emoji; ZIP com nome UTF-8 e cp437; JSON com BOM; nas duas linguagens | Python + Node (bloco em §4) | **Ok** nos dois motores | — |
| 1 — `iniciar.bat` | cópia do repositório numa pasta `Sync Up Ção`, com o `.venv` por junção; caminho feliz e sem Python no PATH | `cmd /c` com o caminho completo, como o duplo clique (bloco em §4) | **Ok com o ambiente já criado**: o app respondeu; sem Python, a mensagem certa e o `goto erro`, mesmo em LF. A primeira execução (criar o venv e instalar) não foi testada (§5) | — |
| 1 — encerrar o app | pool de leitura (`dados.py:660-702`) quando o processo do app morre | Python (bloco do R3-08) | **Falha** no encerramento à força: 4 processos órfãos, 249 MB. Reproduzido no Windows | R3-08 |
| **2. Contratos** — sincronização | `web/ponte.py`, `tools/empacotar_web.py` | leitura | **Nenhuma sincronização automática.** `empacotar_web.py` só gera as 4 demos (`:20-41`); `web/ponte.py` não é importado por nenhum código do app, só pelos testes de paridade (é a referência Python deles) | R3-04 |
| 2 — constantes duplicadas | 16 pares Python × JS | script que lê o valor no JS e compara (§2.1) | Os 16 são **iguais hoje** | — |
| 2 — o que os testes pegam | 8 mutações (uma constante mudada só no Python) e 2 controles | pytest com plugin de mutação (bloco do R3-04) + suíte inteira com as 6 que passaram, juntas | **6 de 8 mutações passam sem nenhum teste falhar** | R3-04 |
| 2 — invariantes | simetria, identidade, [0,1], determinismo e Python × JS em 500 pares aleatórios | Python + Node (bloco em §4) | **Ok** nas 4 métricas (diferença máxima Python × JS: 1,7e-16). No Python, `tests/test_metricas.py` já confere simetria (`:29`, `:45`, `:62`, `:107`) e identidade (`:143-144`, `:154`) com casos fixos. Faltam: limites [0,1] e determinismo, casos aleatórios e todo o lado JS (só o RBO tem teste JS, `tests/js/rbo.test.mjs`) | proposta no R3-04 |
| **3. Versionamento** | convite atual, futuro (`SYNCUP2.`), com campo novo e sem campo; perfil com `versao` 99, ausente e `'x'` | Python + Node (bloco do R3-11) | Atual e campo novo: ok. Futuro: mensagem enganosa. Sem campo: recusado com mensagem clara. Perfil: qualquer `versao` aceita, mas o perfil não é mais salvo nem lido por ninguém | R3-11, R3-13 |
| 3 — correção de escopo | `perfis.py` | leitura | `perfis.py` são as regras de arquétipo, sem formato persistido. O formato com versão é o `PerfilGosto` (`perfil_gosto.py:36,51,62-75`) | R3-13 |
| 3 — formatos que existem de verdade | convite `SYNCUP1.` (um formato só desde `6887e7b`, conferido com `git log -S"SYNCUP" -- convite.py`), cache do histórico (`dados.py:487-552`), cache de gêneros (sem versão: R1-03), IndexedDB `syncup-capas` v1 e `syncup-lastfm` | leitura | Não há formato antigo para migrar. O cache do histórico (versão + identidade + hash) é o modelo a seguir | — |
| **4. Privacidade** — o que sai do PC | ListenBrainz e MusicBrainz: URL, parâmetros, cabeçalhos e tempo-limite do cliente do próprio app | `httpx.MockTransport` (bloco em §2.2) | Só nome de usuário e nomes de artistas; User-Agent sem e-mail; os dois opcionais | — |
| 4 — o que sai do navegador | pedidos para fora depois de "Montar meu Wrapped", sem outro clique | Chromium com mocks (bloco do R3-05) | **34 a 35 pedidos em 15 s** para iTunes, Spotify, MusicBrainz e CDN de imagem. O mesmo componente roda nos 4 modos, e 3 telas dizem que nada sai | R3-05 |
| 4 — textos de privacidade × comportamento | PC ("apagados em até 1 hora"), landing ("Fechou a página, sumiu"), subtítulos do app | script (bloco do R3-14) | **3 promessas maiores que o comportamento** | R3-05, R3-14 |
| 4 — app sem a rede | app web com `unpkg.com` fora | Chromium | **Falha**: fica no esqueleto, sem o botão "Montar" | R3-02 |
| 4 — APIs fora, lentas ou com limite | ListenBrainz, MusicBrainz (Python); Last.fm, capas (Node); iTunes (leitura) | mocks (blocos do R3-06, R3-07 e §2.2) | Nenhuma falha de API de dados derruba o resultado. Falhas: capa "sumida" por 30 dias depois de um 500; texto técnico em inglês no ListenBrainz; `Retry-After` ignorado (ou cortado em 10 s, no ListenBrainz); o download do Last.fm faz 16 pedidos num 429; o iTunes não tem limitador | R3-06, R3-07, R3-12 |
| **5. Métricas** — texto × código | Cosseno, Jaccard, RBO e Ruzicka em `metricas.py`, `dupla.js`, `resultado.js`, `componentes.py`, `cartao.py`, `ui/layout.py` | leitura + script | As fórmulas fazem o que os nomes dizem. Mas a **ponderação padrão** muda entre PC e navegador e só o PC a mostra; os textos de Jaccard e Ruzicka não dizem que o cálculo usa só plays ≥ 30 s, o período comum e a ponderação | R3-01, R3-10 |
| 5 — calibração × validação | `VALIDACAO.md`, `conciliacao.py:29-30`, `analise.py:43`, `CHANGELOG.md:112` | script (bloco do R3-01) | Não há registro de validação das faixas do Match nem de dados separados (a R1 já deixou isso em aberto) | R3-09 |

### Pendências das rodadas anteriores

| Pendência | Onde ficou | Veredito desta rodada |
|---|---|---|
| Last.fm fora do ar, lento ou com limite | R1 §6. A R2 conferiu as mensagens (fora do ar, limite e perfil vazio) com rota falsa no Chromium | **Fechada na camada de rede**, com o `pedir()` e o download paralelo simulados no Node (bloco do R3-06). Sem rede: 1 pedido e "Sem conexão com o Last.fm…" na hora. Lento (tempo-limite estourado): 5 tentativas e depois "O Last.fm está demorando…"; pela conta (5 × 20 s de `lastfm.js:19` + 15 s de esperas), até ~115 s por pedido, **calculado, não observado**. Limite (HTTP 429 ou `{error: 29}` com HTTP 200): 5 pedidos e depois "O Last.fm pediu uma pausa…"; no download real são 16 pedidos (R3-12). A tela com 429 e lentidão de verdade não foi vista (§5). |
| Calibração × validação do Match | R1 §6 e R1-02 | **Fechada como risco de registro** (R3-09). |
| O que a tela do PC mostra quando o `TypeError` do R1-03 escapa | R1 §6 | Não fechada (não reproduzida nesta rodada); segue em §5. |
| Selo "Lendo neste aparelho…" | R1 §6 | Já fechada pela R2 (§4 da R2: aparece com a CPU 20× mais lenta). |
| Erros de entrada do ZIP no Gradio | R1 §6 | Já fechada pela R2 (§5 da R2: mensagem em português, com o título "Error"). |
| "Não auditados": `opcoes.js`, `ui/meus_dados.py`, `ui/match.py` | R2 §5 | **Parcialmente coberta:** o padrão de `opcoes.js` (R3-01), o texto de `ui/meus_dados.py` (R3-14) e os avisos de `ui/match.py` (R3-07). A tela em si continua sem auditoria de UI. |
| `[data-testid="file"]`, título "Error", app para PC no celular, custo do vidro no celular, `aria-live` dos stories, movimento por `requestAnimationFrame`, rolagem lateral no PC, os 124 seletores nunca casados, alvo de toque de "Ainda não tem o ZIP?" | R1 §6, R2 §5 | Fora do escopo desta rodada (UI); seguem em aberto. |

### 2.1 Constantes copiadas à mão entre Python e JS

Todas iguais hoje (bloco abaixo). A última coluna diz se algum teste falha quando a constante muda **só no Python** (bloco de mutação do R3-04), o que equivale a esquecer de mudar o JS; "não testada" quer dizer que a mutação não foi feita. A mutação do play mínimo trocou as 3 cópias Python juntas.

| Constante | Python | JS | Uma mudança só no Python é pega? |
|---|---|---|---|
| Janelas 28/182/365 dias | `perfil_gosto.py:31` | `match.js:8` | 28→20: **sim** (3 falhas). 182→300 e 365→400: **não** |
| Peso dos períodos 0,6/0,8/1,0 | `perfil_gosto.py:32` | `match.js:9` | não testada |
| Peso das músicas 0,5 | `perfil_gosto.py:33` | `match.js:10` | **sim** (controle: 1 falha) |
| Tamanho do ranking 50 | `perfil_gosto.py:34` | `match.js:11` | não testada (`test_match.py:61` e `match.test.mjs:20` fixam cada lado) |
| Faixas do Match 25/10/5/1 | `conciliacao.py:31-37` | `match.js:15-21` | **não** (25→20 passa) |
| Máximo de pessoas 16 | `conciliacao.py:28` | `match.js:128`, mais os literais `match-tela.js:184` e `main.js:109` | **não** (16→12 passa) |
| Convite: código 20.000, JSON 100.000, nome 60, texto 200 | `convite.py:25-28` (o 200 também é valor padrão de `_texto`, `:47`) | `convite.js:6-9` | texto 200→150: **não**. O JS fixa o código (`convite.test.mjs:37`) e o texto (`:34`) só do lado dele |
| Teto do ZIP 1 GB | `dados.py:40` | `historico.js:4` | não testada |
| Play mais longo aceito 24 h | `dados.py:76` | `historico.js:122` | **não** (24 h→3 h passa) |
| Play mínimo 30 s | `analise.py:40` (cópias em `perfil_gosto.py:35` e `wrapped.py:18`) | `calculo.js:7` | **sim** (27 falhas) |
| Fração mínima de campos conhecidos 0,5 | `wrapped.py:27` | `calculo.js:11` | não testada |
| Meia-vida 365 dias | `analise.py:46` | `dupla.js:77` | **sim** (controle: 3 falhas) |
| Profundidade do RBO 50 | `analise.py:44` | `dupla.js:75` | não testada |
| Entrada máxima por JSON no ZIP 64 MB | — | `historico.js:7` | Diferença **intencional** (protege o iOS; R1-07). Um teste de contrato precisa registrá-la como exceção |

```powershell
@'
import json, re, subprocess
from pathlib import Path
import conciliacao, convite, dados, perfil_gosto, analise, wrapped
JS = 'site/app/js/'
PARES = [  # (constante no Python, valor no Python, arquivo JS, nome no JS)
    ('perfil_gosto.JANELAS_DIAS', perfil_gosto.JANELAS_DIAS, 'match.js', 'JANELAS_DIAS'),
    ('perfil_gosto.PESO_PERIODO', perfil_gosto.PESO_PERIODO, 'match.js', 'PESO_PERIODO'),
    ('perfil_gosto.PESO_MUSICAS', perfil_gosto.PESO_MUSICAS, 'match.js', 'PESO_MUSICAS'),
    ('perfil_gosto.TAMANHO_RANKING', perfil_gosto.TAMANHO_RANKING, 'match.js', 'TAMANHO_RANKING'),
    ('conciliacao.NIVEIS', [[n, a, b] for n, a, b in conciliacao.NIVEIS], 'match.js', 'NIVEIS'),
    ('conciliacao.MAXIMO_PESSOAS', conciliacao.MAXIMO_PESSOAS, 'match.js', 'MAXIMO_PESSOAS'),
    ('convite.MAXIMO_CODIGO', convite.MAXIMO_CODIGO, 'convite.js', 'MAXIMO_CODIGO'),
    ('convite.MAXIMO_JSON', convite.MAXIMO_JSON, 'convite.js', 'MAXIMO_JSON'),
    ('convite.MAXIMO_NOME', convite.MAXIMO_NOME, 'convite.js', 'MAXIMO_NOME'),
    ('convite.MAXIMO_TEXTO', convite.MAXIMO_TEXTO, 'convite.js', 'MAXIMO_TEXTO'),
    ('dados.LIMITE_BYTES', dados.LIMITE_BYTES, 'historico.js', 'LIMITE_BYTES'),
    ('dados.TETO_MS', dados.TETO_MS, 'historico.js', 'TETO_MS'),
    ('analise.TEMPO_MINIMO_PLAY_MS', analise.TEMPO_MINIMO_PLAY_MS, 'calculo.js', 'TEMPO_MINIMO_PLAY_MS'),
    ('wrapped.MINIMO_CONHECIDOS', wrapped.MINIMO_CONHECIDOS, 'calculo.js', 'MINIMO_CONHECIDOS'),
    ('analise.MEIA_VIDA_DIAS', analise.MEIA_VIDA_DIAS, 'dupla.js', 'MEIA_VIDA_DIAS'),
    ('analise.PROFUNDIDADE_RBO', analise.PROFUNDIDADE_RBO, 'dupla.js', 'PROFUNDIDADE_RBO'),
]
NODE = "let s=''; process.stdin.on('data', d => s += d).on('end', () => console.log(JSON.stringify(JSON.parse(s).map(e => Function('return (' + e + ')')()))));"
exprs = []
for _, _, arq, nome in PARES:
    fonte = Path(JS + arq).read_text(encoding='utf-8')
    m = re.search(r'\b' + nome + r'\s*=\s*(\[[\s\S]*?\];|\{[^}]*\}|[^,;]+)', fonte)  # array, objeto ou valor simples
    exprs.append(m.group(1).rstrip(';'))
valores = json.loads(subprocess.run(['node', '-e', NODE], input=json.dumps(exprs).encode(), capture_output=True, check=True).stdout)
for (py, valor, arq, nome), js in zip(PARES, valores):
    igual = json.loads(json.dumps(valor)) == js
    print(('igual  ' if igual else 'DIFERE ') + f'{py} = {arq}:{nome}')
print('literais 16 fora da constante:', [f'{a}:{i}' for a in ('match-tela.js', 'main.js')
      for i, l in enumerate(Path(JS + a).read_text(encoding='utf-8').splitlines(), 1) if re.search(r'(<|a) 16\b', l)])
'@ | .venv\Scripts\python.exe -W ignore -
```

Saída: 16 linhas `igual  …` (de `perfil_gosto.JANELAS_DIAS = match.js:JANELAS_DIAS` a `analise.PROFUNDIDADE_RBO = dupla.js:PROFUNDIDADE_RBO`), nenhuma `DIFERE`, e `literais 16 fora da constante: ['match-tela.js:184', 'main.js:109']`.

### 2.2 O que sai da máquina

| Superfície | Para onde | O que vai | Quando | Fonte |
|---|---|---|---|---|
| PC | `api.listenbrainz.org` | nome de usuário (no caminho), `range`, `count`, `max_ts`; até 12 chamadas por pessoa (6 de estatística, 1 de escutas recentes e até 5 de escutas) | só se a pessoa digita usuários no Match | `listenbrainz.py:26,86-95,131-147`; bloco abaixo |
| PC | `musicbrainz.org` | `artist:"<nome>"`, até 25 artistas por perfil, 1 por segundo | só com a caixa de estilo marcada (desligada por padrão) | `generos.py:30-39,92-96`, `ui/layout.py:635-639` |
| PC | PyPI | os pacotes do `requirements.txt` | o `iniciar.bat` roda `pip install` a cada abertura; só baixa na 1ª vez ou quando falta algo | `iniciar.bat:21` |
| PC | nada mais, pelo código | o servidor escuta só em `127.0.0.1`, e a telemetria do Gradio está desligada | — | `app.py:72`, `ui/layout.py:265` (a página do Gradio no navegador não teve a rede capturada: §5) |
| Landing | `unpkg.com` | pedido do Lenis (IP do visitante) | ao abrir a página, salvo com "menos movimento" | `site/index.html:354-370` |
| Web | `unpkg.com` | pedido do Preact/htm (IP do visitante) | toda vez que o app abre | `site/app/index.html:17` (R3-02) |
| Web | `ws.audioscrobbler.com` | nome de usuário e a chave pública de leitura | só se a pessoa usa o Last.fm | `lastfm.js:8-9,38-40` |
| Web | `itunes.apple.com` | Wrapped: `artista + música` e `artista` do top. Dupla: músicas e artistas em comum. Match: artistas em comum de cada par. Batalha: o favorito de cada pessoa. Sempre `country=BR` | **sozinho**, quando o resultado aparece | `som.js:21,40-47,162-163`; `ponte.py:221-261` e `dupla.js` (Dupla), `match.js:236-245`, `batalha.js:189-204`; bloco do R3-05 |
| Web | `open.spotify.com/oembed` | IDs das faixas mais ouvidas (só IDs com o formato real de 22 caracteres) e, pelo código, o ID Spotify do artista achado no MusicBrainz | **sozinho**, no Wrapped | `capas.js:7,14-16,106,159` |
| Web | `musicbrainz.org` | nomes dos artistas do top e, pelo código, a página do artista achado (`/artist/<mbid>?inc=url-rels`) | **sozinho**, no Wrapped | `capas.js:8,153-157` |
| Web | `i.scdn.co`, `*.spotifycdn.com`, `audio-ssl.itunes.apple.com`, `*.mzstatic.com`, CDN do Last.fm | pedido da imagem ou do trecho (IP) | sozinho, depois das buscas; o pôster recarrega as imagens ao clicar | `capas.js:21-22`, `lastfm.js:61`, `som.js:27-28`, `poster.js:16-21` |

Nos mocks do bloco do R3-05 o MusicBrainz e o iTunes devolvem listas vazias, então a 2ª etapa do MusicBrainz, o oEmbed do artista e os trechos de áudio não chegaram a sair (as linhas "pelo código" acima). Parte dos 19 pedidos ao iTunes são as 3 buscas de exemplo (`som.js:12,173-175`), que não levam dados da pessoa. O `Referer` que sai é só a origem do app (observado). O aviso do que sai está em `som.js:109` (`NOTA_WRAPPED`) e na landing (`site/index.html:297`).

Lado Python, com o cliente que o próprio app monta e respostas falsas:

```powershell
@'
import os, tempfile
import httpx
import listenbrainz
from generos import ConsultaMusicBrainz
esperas, pedidos, resposta_atual = [], [], {}
listenbrainz.time.sleep = esperas.append  # nao dorme de verdade; so registra
def responder(pedido):
    pedidos.append(pedido)
    r = resposta_atual['r']
    if r == 'timeout': raise httpx.ReadTimeout('lento', request=pedido)
    return r
Original = httpx.Client
class Cliente(Original):  # o cliente que o proprio app monta (User-Agent e timeout dele), so com a rede trocada por respostas falsas
    def __init__(self, **kw): super().__init__(transport=httpx.MockTransport(responder), **kw)
httpx.Client = Cliente
casos = {
    'lento (timeout)': 'timeout',
    'HTTP 500': httpx.Response(500, text='erro interno'),
    'HTTP 503': httpx.Response(503),
    '429 com Retry-After: 30': httpx.Response(429, headers={'Retry-After': '30'}),
    'corpo que nao e JSON': httpx.Response(200, text='<html>manutencao</html>'),
}
for nome, resposta in casos.items():
    esperas.clear(); pedidos.clear(); resposta_atual['r'] = resposta
    try: listenbrainz.coletar_perfil_listenbrainz('ana_ficticia'); r = 'ok'
    except ValueError as e: r = 'ValueError -> a tela mostra o texto: ' + ascii(str(e))
    except httpx.HTTPError as e: r = type(e).__name__ + ' -> a tela mostra "o ListenBrainz nao respondeu. Confira a internet."'
    print('ListenBrainz', nome, '| pedidos', len(pedidos), '| esperas', esperas, '|', r)
p = pedidos[0]
print('o que sai:', p.method, p.url.host, p.url.path, dict(p.url.params), '| User-Agent:', p.headers['user-agent'],
      '| cabecalhos:', sorted(p.headers.keys()), '| timeout:', p.extensions['timeout'])
cache = os.path.join(tempfile.mkdtemp(), 'generos.json')
for nome, resposta in casos.items():
    pedidos.clear(); dormidas = []; resposta_atual['r'] = resposta
    c = ConsultaMusicBrainz(cache=cache, relogio=lambda: 0.0, dormir=dormidas.append)
    r = [c.generos(f'Banda {i}') for i in range(5)]
    print('MusicBrainz', nome, '| pedidos', len(pedidos), 'para 5 artistas | falhas', c.falhas, '| generos', r, '| esperas', dormidas[:3])
p = pedidos[0]
print('o que sai:', p.url.host, dict(p.url.params), '| User-Agent:', p.headers['user-agent'], '| timeout:', p.extensions['timeout']['read'],
      '| arquivo de cache gravado?', os.path.exists(cache))
'@ | .venv\Scripts\python.exe -
```

Saída:
- `ListenBrainz lento (timeout) | pedidos 1 | esperas [] | ReadTimeout -> a tela mostra "o ListenBrainz nao respondeu. Confira a internet."`
- `ListenBrainz HTTP 500 | pedidos 1 | esperas [] | HTTPStatusError -> a tela mostra "o ListenBrainz nao respondeu. Confira a internet."`
- `ListenBrainz HTTP 503 | pedidos 1 | esperas [] | HTTPStatusError -> …` (idem)
- `ListenBrainz 429 com Retry-After: 30 | pedidos 3 | esperas [10, 10] | ValueError -> a tela mostra o texto: 'O ListenBrainz est\xe1 ocupado agora. Tente de novo em instantes.'`
- `ListenBrainz corpo que nao e JSON | pedidos 1 | esperas [] | ValueError -> a tela mostra o texto: 'Expecting value: line 1 column 1 (char 0)'`
- `o que sai: GET api.listenbrainz.org /1/stats/user/ana_ficticia/artists {'range': 'month', 'count': '50'} | User-Agent: SyncUp/1.27 ( https://github.com/Hazykiuu/SyncUp ) | cabecalhos: ['accept', 'accept-encoding', 'connection', 'host', 'user-agent'] | timeout: {'connect': 10, 'read': 10, 'write': 10, 'pool': 10}`
- `MusicBrainz <cada um dos 5 casos> | pedidos 3 para 5 artistas | falhas 3 | generos [[], [], [], [], []] | esperas [1.0, 1.0]` (5 linhas iguais)
- `o que sai: musicbrainz.org {'query': 'artist:"Banda 0"', 'fmt': 'json', 'limit': '1'} | User-Agent: SyncUp/1.27 ( https://github.com/Hazykiuu/SyncUp ) | timeout: 15 | arquivo de cache gravado? False`

O MusicBrainz para depois de 3 falhas (`generos.py:38,84-85`) e não grava falha no cache: os 5 artistas custam 3 pedidos, não 10. O ListenBrainz corta o `Retry-After` em 10 s e tenta de novo (R3-12). O tempo-limite do httpx vale por fase (conexão, leitura…), não para o pedido inteiro.

## 3. Achados (ordem de impacto)

### R3-01 — A ponderação padrão é diferente no PC e no navegador: nas demos, 5,1% × 93,0% de "escuta em comum"

- **Classificação:** Problema comprovado (as duas superfícies mostram números diferentes para os mesmos arquivos e só uma diz por quê)
- **Prioridade:** P2
- **Localização:**
  - padrão do PC: `ui/layout.py:361-365` (`value='bruta'`); padrão do navegador: `site/app/js/opcoes.js:4` (`ponderacao: 'log1p'`), mudado na `CHANGELOG.md:349` sem dizer por quê;
  - o PC mostra a ponderação ao lado do número (`componentes.py:70`, "Cosseno · ponderação …"); o navegador não (`site/app/js/resultado.js:59`), e é esse número que abre os stories;
  - a ponderação muda o cosseno e o Ruzicka, não o Jaccard nem o RBO (`analise.py:320-330`, `metricas.py:114-129`). Na 1.20 o projeto destacou que os cálculos dão "o mesmo número nos dois" (`CHANGELOG.md:112`); com os padrões atuais, isso só vale se a pessoa mudar a opção.
- **Evidência:**

```powershell
@'
import re, subprocess, sys
from pathlib import Path
if not Path('site/app/demo-bruno.zip').is_file():
    subprocess.run([sys.executable, 'tools/empacotar_web.py'], check=True, capture_output=True)  # demos ficticias (git-ignoradas)
from web.ponte import comparar_dupla
pc = re.search(r"value='(\w+)',\s*label='Pondera", Path('ui/layout.py').read_text(encoding='utf-8')).group(1)
web = re.search(r"ponderacao: '(\w+)'", Path('site/app/js/opcoes.js').read_text(encoding='utf-8')).group(1)
print('padrao no PC (ui/layout.py):', pc, '| padrao no navegador (opcoes.js):', web, '| iguais?', pc == web)
for modo in dict.fromkeys([pc, web]):
    m = comparar_dupla(['site/app/demo-wrapped.zip'], ['site/app/demo-bruno.zip'], 'Rafa', 'Lu', {'ponderacao': modo})['metricas']
    print(f'{modo:5} -> cosseno {m["cosseno"] * 100:.1f}% | ruzicka {m["ruzicka"] * 100:.1f}% | jaccard {m["jaccard"] * 100:.1f}% | rbo {m["rbo_top50"] * 100:.1f}%')
texto = Path('VALIDACAO.md').read_text(encoding='utf-8')
print('VALIDACAO.md cita as faixas do Match (25/10/5/1)?', bool(re.search(r'Sintonia rara|25 pontos|faixas do Match', texto)),
      '| fala em "12 hist"?', '12 hist' in texto, '| linhas com "4 hist":', [i for i, l in enumerate(texto.splitlines(), 1) if '4 hist' in l])
for arq in ['conciliacao.py', 'analise.py', 'CHANGELOG.md']:
    print(arq, [(i, ascii(l.strip())[:110]) for i, l in enumerate(Path(arq).read_text(encoding='utf-8').splitlines(), 1) if re.search(r'\b(4|12) hist', l)])
'@ | .venv\Scripts\python.exe -W ignore -
```

  Saída:
  - `padrao no PC (ui/layout.py): bruta | padrao no navegador (opcoes.js): log1p | iguais? False`
  - `bruta -> cosseno 5.1% | ruzicka 14.8% | jaccard 100.0% | rbo 2.5%`
  - `log1p -> cosseno 93.0% | ruzicka 75.9% | jaccard 100.0% | rbo 2.5%`
  - `VALIDACAO.md cita as faixas do Match (25/10/5/1)? False | fala em "12 hist"? False | linhas com "4 hist": [73]`
  - `conciliacao.py [(29, "'# Faixas calibradas com 4 hist\\xf3ricos reais (2017\\u20132026). Rankings de top 50 se'")]`
  - `analise.py [(43, '\'# "Favoritos em comum": RBO nos 50 artistas mais ouvidos (estudo com 12 hist\\xf3ricos).\'')]`
  - `CHANGELOG.md [(112, "'Duas mudan\\xe7as de c\\xe1lculo na Dupla, escolhidas depois de um estudo com 12 hist\\xf3ricos reais. Valem no ")]`

  Os números saem da referência Python dos testes de paridade (`web/ponte.py:comparar_dupla`, só com a ponderação trocada e as outras opções no padrão do PC); o navegador dá o mesmo número para as mesmas opções (paridade). Não foram lidos na tela. As 4 últimas linhas são a evidência do R3-09. **O tamanho da diferença vale só para as demos:** elas têm os mesmos 250 artistas (Jaccard 100%) com favoritos diferentes, o que exagera o efeito; com históricos reais a diferença não foi medida. O cálculo é o mesmo nos dois motores (paridade em `test_paridade_dupla.py`, casos `padrao`, `raiz` e `log`); o que difere é só o padrão.
- **Impacto:** quem compara no PC e manda o app web para um amigo vê dois números de "sintonia" diferentes para os mesmos arquivos, sem texto que explique. No navegador nem há como saber qual ponderação valeu sem abrir "Opções de dados".
- **Solução proposta:** decidir com dados (como no estudo dos 12 históricos) um padrão único para as duas superfícies e registrar o porquê no `VALIDACAO.md`. Enquanto isso, mostrar a ponderação ao lado do número também no navegador (`resultado.js:59` e o story de abertura), como o PC já faz.
- **Testes necessários:** Python (novo `tests/test_contratos.py`): se o padrão for unificado, o de `ui/layout.py` e o `PADRAO` de `opcoes.js` são iguais (lidos como na 1ª linha do bloco); se continuarem diferentes, o rótulo do cosseno em `resultado.js` mostra a ponderação. Paridade: nenhuma mudança.
- **Critério de aceitação:** a 1ª linha do bloco dá `iguais? True` (padrão unificado) ou, se a escolha for manter padrões diferentes, o resultado do navegador mostra a ponderação; nos dois casos, o teste de contrato correspondente passa.

### R3-02 — O app no navegador não abre sem o `unpkg.com`

- **Classificação:** Limitação conhecida (a dependência é intencional e protegida por `integrity`, `site/app/index.html:16-17`)
- **Prioridade:** P2 (o escopo pede "funcionar 100% local quando a API estiver fora"; aqui nem o app abre)
- **Localização:** `site/app/index.html:17` (import map para `https://unpkg.com/htm@3.1.1/preact/standalone.module.js`). A landing usa o `unpkg` só para o Lenis e tem plano B (`site/index.html:354-370`). `tests/test_site.py:28-34` fixa os scripts externos da landing, não os do app.
- **Evidência:** a 1ª parte do bloco do R3-05 abre o app com o `unpkg.com` cortado. Saída: `sem unpkg.com: esqueleto ainda na tela = True | botao Montar existe = False | erros: ["'Failed to load resource: net::ERR_FAILED'"]`.
- **Impacto:** a promessa "o histórico não sai do seu aparelho" continua verdadeira, mas o app depende de um serviço de terceiros para existir. Com o CDN fora do ar, bloqueado por rede de escola ou empresa, ou sem internet, a pessoa vê o logo pulsando para sempre, sem mensagem.
- **Solução proposta:** copiar o `standalone.module.js` (um arquivo, versão fixa) para `site/app/vendor/`, com a licença MIT ao lado, e apontar o import map para ele. É a mesma biblioteca, sem trocar de stack, e tira o IP do visitante do `unpkg.com` (§2.2). Se preferir manter o CDN, ao menos mostrar uma mensagem no esqueleto depois de alguns segundos sem desenhar.
- **Testes necessários:** Python (`tests/test_site.py`): `site/app/index.html` sem `https://` no import map. Playwright: com toda a rede externa cortada, o botão "Montar meu Wrapped" aparece (a regra de `tests/navegador/conftest.py:48-62` que hoje libera o `unpkg.com` poderia então cortar tudo).
- **Critério de aceitação:** no bloco do R3-05, a 1ª linha passa a dar `esqueleto ainda na tela = False | botao Montar existe = True`.

### R3-03 — O CI não roda no Windows, nem no Python que o `iniciar.bat` escolhe

- **Classificação:** Oportunidade de melhoria (prioridade alta no pedido)
- **Prioridade:** P2
- **Localização:** `.github/workflows/testes.yml:15`, `:38`, `:51` (`runs-on: ubuntu-latest` nos 3 jobs) e a matriz `python: ['3.10', '3.12']` (`:19`). `iniciar.bat:7` tenta `py -3` primeiro, que pega o Python mais novo instalado. `requirements.txt:1,6-8` promete "Python 3.10–3.14" e troca o pandas no 3.13+ (`:8`), caminho que nenhum CI testa.
- **Evidência:**
  - **Observado nesta máquina (Windows):** as 3 suítes passam com Python 3.12 (§1); ZIP, encoding e `iniciar.bat` ok (§4); o pool órfão do R3-08 foi reproduzido aqui; `py -0p` mostra o 3.14 como padrão; `py -3.14 -m pip install --dry-run --only-binary=:all: --target <temp> -r requirements.txt` e o mesmo com `-r requirements-dev.txt` terminam com código 0. **A suíte nunca rodou no 3.14.**
  - **Rodaria no CI (não executado):** o `testes.yml` completo abaixo. Ele só muda os cabeçalhos dos jobs `testes` e `js`: os passos ficam iguais, e no Linux os nomes dos checks continuam os de hoje ("Python 3.10", "Python 3.12", "JavaScript (node --test)"), então a proteção da `main` não precisa mudar. Os checks novos ganham " (Windows)" no nome.

```yaml
# Testes a cada push e PR: a main só recebe o que passou aqui (badge "Testes" no README).
name: Testes

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  testes:
    # No Linux o nome do check fica igual ao de hoje ("Python 3.10"): a protecao da main nao muda.
    name: Python ${{ matrix.python }}${{ matrix.os == 'windows-latest' && ' (Windows)' || '' }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest]
        python: ['3.10', '3.12']
        include:
          - os: windows-latest
            python: '3.12'
          # O "py -3" do iniciar.bat pega o Python mais novo instalado; o 3.13+ usa o pandas 2.3.3.
          - os: windows-latest
            python: '3.14'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
          cache-dependency-path: requirements*.txt
      # A paridade do Wrapped roda o motor JS do app no Node (sem Node, o teste seria pulado).
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Instalar dependências
        run: python -m pip install -r requirements-dev.txt
      - name: Testes
        run: python -m pytest -q

  js:
    name: JavaScript (node --test)${{ matrix.os == 'windows-latest' && ' (Windows)' || '' }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    defaults:
      run:
        shell: bash  # o passo "Sintaxe do app" e um laco de bash; no Windows o padrao seria o pwsh
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Sintaxe do app
        run: for f in site/app/*.js site/app/js/*.js site/app/js/stories/*.js; do node --check "$f"; done
      - name: Testes da lógica dos stories
        run: node --test tests/js/*.test.mjs

  navegador:
    name: Navegador (Playwright)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: requirements*.txt
      - name: Instalar dependências
        run: python -m pip install -r requirements-e2e.txt
      - name: Instalar o Chromium
        run: python -m playwright install --with-deps chromium
      - name: Gerar as demos do "Ver um exemplo"
        run: python tools/empacotar_web.py
      - name: Testes de navegador
        run: python -m pytest -m navegador --tracing retain-on-failure
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: rastros-playwright
          path: test-results/
```

```powershell
@'
import re, yaml
from pathlib import Path
BASH = re.compile(r'\bfor\b.*\bdo\b|\$\(|\bgrep\b|&&|\bdone\b')
for wf in sorted(Path('.github/workflows').glob('*.yml')):
    d = yaml.safe_load(wf.read_text(encoding='utf-8'))
    for nome, job in d['jobs'].items():
        bash = [ascii(s.get('name')) for s in job['steps'] if 'run' in s and BASH.search(s['run'])]
        print(f'{wf.name}:{nome} runs-on={job["runs-on"]} | passos com sintaxe de bash: {bash}')
# A proposta e o bloco yaml deste relatorio: confere se e YAML valido, se os passos ficaram iguais e que checks ele cria.
CERCA = chr(96) * 3  # tres crases, escritas assim para nao fechar o bloco do relatorio
proposta = yaml.safe_load(re.search(CERCA + r'yaml\n(.*?)' + CERCA, Path('docs/auditoria/rodada-3.md').read_text(encoding='utf-8'), re.S).group(1))
atual = yaml.safe_load(Path('.github/workflows/testes.yml').read_text(encoding='utf-8'))
print('gatilhos e permissoes iguais:', proposta[True] == atual[True] and proposta['permissions'] == atual['permissions'],
      '| jobs:', list(proposta['jobs']), '| passos iguais:', {j: proposta['jobs'][j]['steps'] == atual['jobs'][j]['steps'] for j in atual['jobs']})
def nome(job, ctx):  # avalia o "&& ||" do nome como o GitHub faz
    return re.sub(r"\$\{\{ matrix\.os == 'windows-latest' && ' \(Windows\)' \|\| '' \}\}", ' (Windows)' if ctx.get('os') == 'windows-latest' else '',
                  job['name']).replace('${{ matrix.python }}', str(ctx.get('python')))
for j, job in proposta['jobs'].items():
    m = job.get('strategy', {}).get('matrix')
    combos = [{'os': o, 'python': py} for o in m.get('os', []) for py in m.get('python', [None])] + m.get('include', []) if m else [{}]
    print(f'{j}: checks {[nome(job, c) for c in combos]} | shell: {job.get("defaults", {}).get("run", {}).get("shell", "padrao")}')
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `lint.yml:lint runs-on=ubuntu-latest | passos com sintaxe de bash: ["'Instalar o Ruff (vers\\xe3o do requirements-dev.txt)'"]`
  - `site.yml:publicar runs-on=ubuntu-latest | passos com sintaxe de bash: []`
  - `testes.yml:testes runs-on=ubuntu-latest | passos com sintaxe de bash: []`
  - `testes.yml:js runs-on=ubuntu-latest | passos com sintaxe de bash: ["'Sintaxe do app'"]`
  - `testes.yml:navegador runs-on=ubuntu-latest | passos com sintaxe de bash: []`
  - `gatilhos e permissoes iguais: True | jobs: ['testes', 'js', 'navegador'] | passos iguais: {'testes': True, 'js': True, 'navegador': True}`
  - `testes: checks ['Python 3.10', 'Python 3.12', 'Python 3.12 (Windows)', 'Python 3.14 (Windows)'] | shell: padrao`
  - `js: checks ['JavaScript (node --test)', 'JavaScript (node --test) (Windows)'] | shell: bash`
  - `navegador: checks ['Navegador (Playwright)'] | shell: padrao`

  O script imita as regras do GitHub só para este caso (cada `include` traz um `os` novo, e o nome é trocado por texto, não avaliado); o `actionlint` não foi rodado. O job `testes` não tem passo com bash (`pip install` e `pytest` rodam igual no `pwsh`); o job `js` precisa do `shell: bash` (que no Linux passa a rodar com `-o pipefail`, sem efeito nesses passos) por causa do laço `for f in …; do node --check` (`testes.yml:45`). O `node --test tests/js/*.test.mjs` foi visto passando só no Node 26 local; no Node 22 do runner Windows é "rodaria". `lint.yml` e `site.yml` ficam no Linux (o Ruff e o empacotamento não dependem do sistema). O job `navegador` fica fora: o `playwright install --with-deps` é para Linux e o custo no Windows é alto.
- **Impacto:** quem mais usa o app (o Carlos, no Windows) é o único ambiente que o CI não vê. Regressões só do Windows (encerramento de processos, caminhos, `tzdata`) e o caminho Python 3.13+/pandas 2.3.3 chegam à `main` sem nenhum check.
- **Solução proposta:** trocar o `testes.yml` pelo bloco acima e incluir os 3 checks novos na proteção da `main`. Nada no código muda.
- **Testes necessários:** nenhum teste novo; o critério é o CI.
- **Critério de aceitação:** os checks `Python 3.12 (Windows)`, `Python 3.14 (Windows)` e `JavaScript (node --test) (Windows)` aparecem verdes num PR, e os checks de hoje continuam com o mesmo nome.

### R3-04 — Constantes copiadas à mão: 6 de 8 mudanças de um lado só passam por todos os testes

- **Classificação:** Risco potencial (nenhuma divergência hoje: §2.1)
- **Prioridade:** P3
- **Localização:** os pares da §2.1. Não existe gerador nem teste que compare as constantes: `web/ponte.py` não exporta nada para o JS, e `tools/empacotar_web.py` só gera ZIPs. A paridade (`tests/test_paridade_{match,dupla,wrapped}.py`) compara saídas, e só pega uma constante quando os dados de teste cruzam o valor dela.
- **Evidência:** cada linha muda **uma** constante só no Python, como quem esquece de mudar o JS, e roda os testes que deveriam pegar. As 2 últimas são controles (devem falhar). O bloco troca também o valor padrão de `_texto`, porque trocar só o atributo do módulo não alcança um valor padrão de argumento. Leva ~4 min.

```powershell
@'
import subprocess, sys, tempfile
from pathlib import Path
# Mutacao: muda UMA constante so no Python (como se alguem esquecesse de mudar o JS) e roda os testes que deveriam pegar.
MUTANTES = {
    'JANELAS_DIAS long_term 365 -> 400': ("import perfil_gosto as m; m.JANELAS_DIAS['long_term'] = 400", 'match'),
    'JANELAS_DIAS medium_term 182 -> 300': ("import perfil_gosto as m; m.JANELAS_DIAS['medium_term'] = 300", 'match'),
    'NIVEIS: Sintonia rara 25 -> 20': ("import conciliacao as m; m.NIVEIS = ((20.0,) + m.NIVEIS[0][1:],) + m.NIVEIS[1:]", 'match'),
    'MAXIMO_PESSOAS 16 -> 12': ("import conciliacao as m; m.MAXIMO_PESSOAS = 12", 'match'),
    # _texto(valor, limite=MAXIMO_TEXTO) guardou o 200 como valor padrao: trocar o atributo do modulo nao basta.
    'MAXIMO_TEXTO do convite 200 -> 150': ("import convite as m; m.MAXIMO_TEXTO = 150; m._texto.__defaults__ = (150,)", 'match'),
    'JANELAS_DIAS short_term 28 -> 20': ("import perfil_gosto as m; m.JANELAS_DIAS['short_term'] = 20", 'match'),
    'TETO_MS 24 h -> 3 h': ("import dados as m; m.TETO_MS = 3 * 3_600_000", 'todos'),
    'TEMPO_MINIMO_PLAY_MS 30 s -> 31 s': ("import analise, wrapped, perfil_gosto\nfor m in (analise, wrapped, perfil_gosto): m.TEMPO_MINIMO_PLAY_MS = 31_000", 'todos'),
    'controle: PESO_MUSICAS 0.5 -> 0.6': ("import perfil_gosto as m; m.PESO_MUSICAS = 0.6", 'match'),
    'controle: MEIA_VIDA_DIAS 365 -> 180': ("import analise as m; m.MEIA_VIDA_DIAS = 180", 'dupla'),
}
TESTES = {'match': ['tests/test_paridade_match.py', 'tests/test_match.py', 'tests/test_convite.py'],
          'dupla': ['tests/test_paridade_dupla.py'],
          'todos': ['tests/test_paridade_match.py', 'tests/test_paridade_dupla.py', 'tests/test_paridade_wrapped.py']}
pasta = Path(tempfile.mkdtemp())
for nome, (codigo, alvo) in MUTANTES.items():
    (pasta / 'mutante.py').write_text('def pytest_configure(config):\n    ' + codigo.replace('\n', '\n    ') + '\n')
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-p', 'mutante', *TESTES[alvo]],
                       capture_output=True, text=True, env={**__import__('os').environ, 'PYTHONPATH': str(pasta)})
    fim = r.stdout.strip().splitlines()[-1].split(' in ')[0]
    print(('PEGOU   ' if r.returncode else 'PASSOU  ') + nome + ' | ' + fim)
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `PASSOU  JANELAS_DIAS long_term 365 -> 400 | 31 passed`
  - `PASSOU  JANELAS_DIAS medium_term 182 -> 300 | 31 passed`
  - `PASSOU  NIVEIS: Sintonia rara 25 -> 20 | 31 passed`
  - `PASSOU  MAXIMO_PESSOAS 16 -> 12 | 31 passed`
  - `PASSOU  MAXIMO_TEXTO do convite 200 -> 150 | 31 passed`
  - `PEGOU   JANELAS_DIAS short_term 28 -> 20 | 3 failed, 28 passed`
  - `PASSOU  TETO_MS 24 h -> 3 h | 41 passed`
  - `PEGOU   TEMPO_MINIMO_PLAY_MS 30 s -> 31 s | 27 failed, 14 passed`
  - `PEGOU   controle: PESO_MUSICAS 0.5 -> 0.6 | 1 failed, 30 passed`
  - `PEGOU   controle: MEIA_VIDA_DIAS 365 -> 180 | 3 failed, 23 passed`

  Com as 6 mutações que passaram aplicadas **juntas**, a suíte inteira também passa (~90 s):

```powershell
@'
import os, subprocess, sys, tempfile
from pathlib import Path
# As 6 mutacoes que passaram no bloco anterior, todas juntas, contra a suite inteira (leva ~90 s).
pasta = Path(tempfile.mkdtemp())
(pasta / 'mutante.py').write_text('''def pytest_configure(config):
    import perfil_gosto, conciliacao, convite, dados
    perfil_gosto.JANELAS_DIAS['long_term'] = 400
    perfil_gosto.JANELAS_DIAS['medium_term'] = 300
    conciliacao.NIVEIS = ((20.0,) + conciliacao.NIVEIS[0][1:],) + conciliacao.NIVEIS[1:]
    conciliacao.MAXIMO_PESSOAS = 12
    convite.MAXIMO_TEXTO = 150
    convite._texto.__defaults__ = (150,)
    dados.TETO_MS = 3 * 3_600_000
''')
r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-p', 'mutante'],
                   capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(pasta)})
print('suite inteira com as 6 mutacoes:', r.stdout.strip().splitlines()[-1].split(' in ')[0])
'@ | .venv\Scripts\python.exe -
```

  Saída: `suite inteira com as 6 mutacoes: 295 passed, 3 skipped, 17 deselected, 2 warnings` (os mesmos números da linha de base).
- **Impacto:** nenhum hoje. Mas é o tipo de mudança que os PRs desta auditoria vão fazer (o R1-02 mexe nas faixas): um PR que mude o Python e esqueça o JS passa verde, e o PC e o navegador passam a dar faixas ou limites diferentes.
- **Solução proposta:** um teste `tests/test_contratos.py` no formato do bloco da §2.1 (lê o valor no JS e compara com o Python) para os 16 pares, pulado quando não há Node, como a paridade já faz; mais a igualdade entre as cópias Python do play mínimo e o literal `16` de `match-tela.js:184` e `main.js:109` trocado pela constante. O limite de 64 MB entra como diferença esperada. Gerar um `constantes.js` a partir do Python seria mais robusto, mas cria um passo de build que o projeto não tem.
- **Testes necessários:**
  - Python: `tests/test_contratos.py`.
  - Invariantes nos dois motores (o bloco de §4 serve de molde): simetria, identidade = 1, resultado em [0, 1], determinismo e diferença Python × JS ≤ 1e-12, com tolerância (a simetria do JS varia no último bit).
  - Paridade: uma fixture com plays a ~200 e ~400 dias do fim e um par com nota entre 20 e 25.
  - As tabelas de casos extremos já achados (RBO inválido do R1-04, Unicode do R1-08, datas do R1-09) entram cada uma no PR que corrige a divergência, não neste: aqui elas falhariam.
- **Critério de aceitação:** com `tests/test_contratos.py` acrescentado às três listas `TESTES` do bloco, as 8 linhas de mutação dão `PEGOU`; e o teste cobre também os 6 pares marcados "não testada" na §2.1, as 3 cópias Python do play mínimo e o literal `16` (conferir lendo o teste: o bloco só exercita as 8 mutações).

### R3-05 — O navegador manda nomes de artistas e músicas a terceiros assim que um resultado aparece, sem escolha antes, e 3 subtítulos dizem que nada sai

- **Classificação:** Limitação conhecida (decisão de produto: "o Wrapped começa sempre com capas e som", `capas.js:1`; cada modo mostra, ao lado dos stories, uma nota dizendo o que vai para o iTunes)
- **Prioridade:** P3
- **Localização:**
  - `site/app/js/som.js:162-163` (`useEffect(() => { comecar(); … }, [])`): o `SomStories` busca no iTunes ao aparecer, e ele é montado nos 4 modos (`wrapped.js:174`, `resultado.js:158`, `match-tela.js:73`, `batalha-tela.js:123`); capas e fotos no Wrapped (`wrapped.js:85`, `capas.js:96-160`).
  - No Match e na Batalha os nomes vêm dos históricos e convites **de outras pessoas**: artistas em comum de cada par (`match.js:236-245`) e o favorito de cada pessoa (`batalha.js:189-204`).
  - As notas existem: `NOTA_WRAPPED` (`som.js:109`), `NOTA_DUPLA` (`resultado.js:16`) e `NOTA_SOM` (`match-tela.js:19`, `batalha-tela.js:18`), mostradas em `som.js:260`; e a landing explica antes do app (`site/index.html:297`). Mas os subtítulos de cada modo dizem o contrário: Dupla "Nada é enviado para nenhum servidor" (`main.js:107`), Match e Batalha "Nada sai do seu aparelho" (`main.js:109-110`).
- **Evidência:** o bloco serve `site/`, corta o `unpkg.com` na 1ª parte (R3-02) e, na 2ª, responde todo pedido externo com dados falsos, registrando host, caminho e parâmetros. Só há dois cliques: escolher o arquivo e "Montar meu Wrapped". **Só o Wrapped foi observado**; nos outros 3 modos o envio vem do código (o mesmo `SomStories`, com a trilha de cada modo). Os subtítulos estão no bloco do R3-14.

```powershell
@'
import functools, json, re, tempfile, threading
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
eventos = [{'ts': f'2023-12-{1 + i % 28:02d}T{i % 24:02d}:00:00Z', 'ms_played': 200000,
            'master_metadata_track_name': f'Faixa Ficticia {i % 7}', 'master_metadata_album_artist_name': f'Banda Ficticia {i % 5}',
            'spotify_track_uri': 'spotify:track:' + chr(65 + i % 7) * 22} for i in range(300)]
arq = Path(tempfile.mkdtemp()) / 'Streaming_History_Audio_2023.json'
arq.write_text(json.dumps(eventos))
FALSO = {'open.spotify.com': {'thumbnail_url': 'https://i.scdn.co/image/ficticia', 'title': 'x'},
         'musicbrainz.org': {'artists': []}, 'itunes.apple.com': {'results': []}}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.route('**/*', lambda r: r.abort() if 'unpkg.com' in r.request.url else r.continue_())
    erros = []; pg.on('console', lambda m: m.type == 'error' and erros.append(m.text))
    pg.goto(f'{URL}/app/#wrapped'); pg.wait_for_timeout(8000)
    print('sem unpkg.com: esqueleto ainda na tela =', pg.locator('.esqueleto').count() == 1,
          '| botao Montar existe =', pg.get_by_role('button', name=re.compile('Montar')).count() > 0, '| erros:', [ascii(e[:90]) for e in erros[:2]])
    pg.close()
    saiu = []
    def rota(r):
        u = urlsplit(r.request.url)
        if u.hostname in ('127.0.0.1', 'unpkg.com'): return r.continue_()
        saiu.append((u.hostname, u.path, parse_qsl(u.query), r.request.headers.get('referer')))
        corpo = FALSO.get(u.hostname)
        return r.fulfill(json=corpo) if corpo is not None else r.fulfill(status=404)
    pg = b.new_page(); pg.route('**/*', rota)
    pg.goto(f'{URL}/app/#wrapped')
    tela = pg.get_by_role('region', name=re.compile('Seu hist.rico'))
    tela.locator('input[type=file]').first.set_input_files(str(arq)); pg.wait_for_timeout(1500)
    pg.get_by_role('button', name=re.compile('Montar meu Wrapped')).click()
    pg.locator('.resultado .st-player:visible').first.wait_for(timeout=30000); pg.wait_for_timeout(15000)
    print('pedidos para fora (sem nenhum clique depois de "Montar"):', dict(Counter(h for h, *_ in saiu)))
    for host in dict.fromkeys(h for h, *_ in saiu):
        h, caminho, q, ref = next(x for x in saiu if x[0] == host)
        print(' ', host, caminho, ascii(q)[:150], '| Referer:', ref.replace(URL, '<origem do app>'))
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `sem unpkg.com: esqueleto ainda na tela = True | botao Montar existe = False | erros: ["'Failed to load resource: net::ERR_FAILED'"]`
  - `pedidos para fora (sem nenhum clique depois de "Montar"): {'itunes.apple.com': 19, 'open.spotify.com': 4, 'musicbrainz.org': 5, 'i.scdn.co': 7}` (em outra rodada, 6 pedidos de imagem: depende de quantas buscas terminam nos 15 s)
  - `itunes.apple.com /search [('entity', 'song'), ('country', 'BR'), ('term', 'Banda Ficticia 0 Faixa Ficticia 0'), ('limit', '5')] | Referer: <origem do app>/`
  - `open.spotify.com /oembed [('url', 'https://open.spotify.com/track/AAAAAAAAAAAAAAAAAAAAAA')] | Referer: <origem do app>/`
  - `musicbrainz.org /ws/2/artist/ [('query', 'artist:"Banda Ficticia 0"'), ('fmt', 'json'), ('limit', '3')] | Referer: <origem do app>/`
  - `i.scdn.co /image/ficticia [] | Referer: <origem do app>/`
- **Impacto:** o que sai é pouco (nomes de artistas e músicas, IDs do Spotify e o IP, nunca o histórico) e está escrito na landing e na nota de cada modo. O problema é a ordem e a contradição: a nota aparece junto com o resultado, quando os pedidos já saíram, e o subtítulo da mesma tela diz "Nada sai do seu aparelho" enquanto nomes do histórico dela e dos amigos vão para a Apple. Quem não quer isso não tem como impedir antes.
- **Solução proposta:** trocar os 3 subtítulos por um texto verdadeiro ("O histórico não sai do seu aparelho; para o som, só nomes de artistas vão para o iTunes"). E, respeitando a decisão de começar com som, dar a escolha **antes**: uma preferência global "Capas e som" (marcada por padrão, lembrada no `localStorage` como o mudo, `som.js:74,89`) que o `SomStories` consulta antes de `comecar()`, valendo nos 4 modos. Mudar o padrão fica com o Carlos.
- **Testes necessários:** Playwright: com a preferência desligada, nenhum pedido para fora depois de mostrar o resultado nos 4 modos (o registro do bloco vira a asserção). Python (`tests/test_site.py`): nenhum subtítulo diz que nada sai.
- **Critério de aceitação:** o bloco, estendido para desligar a preferência e repetir nos 4 endereços (`#wrapped`, `#dupla`, `#match`, `#batalha`) com os exemplos de cada modo, dá `{}` na contagem de pedidos para fora; ligada, continua como hoje; e as 3 linhas de `main.js` do bloco do R3-14 mudam.

### R3-06 — Capas: um erro 500 do Spotify ou do MusicBrainz vira "sem capa" por 30 dias

- **Classificação:** Problema comprovado
- **Prioridade:** P3
- **Localização:** `site/app/js/capas.js:108` (`if (r.status !== 429 && r.status !== 503) return null;`) e `:127-128` (o `null` é gravado no cache com validade de 30 dias, `:10`). Só 429/503 e erro de rede escapam do cache. `tests/js/capas.test.mjs` cobre 429, 503 e sem rede, não 500/404.
- **Evidência:** o mesmo bloco fecha a pendência do Last.fm na camada de rede e mostra o download paralelo do R3-12.

```powershell
@'
import { criarBuscador, cacheMemoria } from './site/app/js/capas.js';
import { pedir, baixarScrobbles } from './site/app/js/lastfm.js';
const resp = (status, corpo = {}, headers = {}) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(headers), json: async () => corpo });
const uri = 'spotify:track:' + 'A'.repeat(22); // ID ficticio no formato real
const oembed = { thumbnail_url: 'https://i.scdn.co/image/ficticia', title: 'Faixa' };
for (const status of [500, 404, 503]) {
  const cache = cacheMemoria(); let dia = 0, pedidos = 0;
  const b1 = criarBuscador({ cache, agora: () => dia, esperar: async () => {}, fetch: async () => { pedidos++; return resp(status); } });
  const antes = await b1.faixa(uri);
  dia = 86_400_000; // no dia seguinte, o Spotify ja responde
  const b2 = criarBuscador({ cache, agora: () => dia, esperar: async () => {}, fetch: async () => { pedidos++; return resp(200, oembed); } });
  const depois = await b2.faixa(uri);
  console.log(`capas: HTTP ${status} hoje -> ${antes}; amanha com o Spotify ok -> ${depois ? 'capa' : 'null'} (pedidos no total: ${pedidos})`);
}
const esperou = [];
const esperar = async (ms) => { esperou.push(ms); };
const casos = {
  'HTTP 429 com Retry-After: 60': () => resp(429, null, { 'Retry-After': '60' }),
  'HTTP 200 com {error: 29}': () => resp(200, { error: 29, message: 'Rate Limit Exceeded' }),
  'HTTP 500': () => resp(500, null),
  'lento (TimeoutError em todo pedido)': () => { throw new DOMException('lento', 'TimeoutError'); },
  'sem rede (TypeError)': () => { throw new TypeError('fetch failed'); },
  'HTTP 200 com HTML no corpo': () => ({ ok: true, status: 200, headers: new Headers(), json: async () => { throw new SyntaxError('Unexpected token <'); } }),
};
for (const [nome, falha] of Object.entries(casos)) {
  esperou.length = 0; let pedidos = 0;
  try { await pedir('user.getrecenttracks', { user: 'ana_ficticia' }, { esperar, buscar: async () => { pedidos++; return falha(); } }); }
  catch (e) { console.log(`last.fm pedir(): ${nome} -> ${pedidos} pedidos, esperas ${JSON.stringify(esperou)} ms, mensagem: ${JSON.stringify(e.message)}`); }
}
// O download de verdade: pagina 1 ok (10 paginas no total), da 2 em diante o Last.fm responde 429. Tempo encolhido 100x.
let total = 0, depoisDoErro = 0, progressoDepois = 0, erro = null;
const pagina1 = { recenttracks: { '@attr': { totalPages: '10', total: '2000' }, track: [{ name: 'Faixa', artist: { '#text': 'Banda' }, date: { uts: '1700000000' } }] } };
const buscar = async (url) => { total++; if (erro) depoisDoErro++; return new URL(url).searchParams.get('page') === '1' ? resp(200, pagina1) : resp(429, null); };
try {
  await baixarScrobbles('ana_ficticia', { buscar, esperar: (ms) => new Promise((ok) => setTimeout(ok, ms / 100)), aoProgresso: () => { if (erro) progressoDepois++; } });
} catch (e) { erro = e; }
await new Promise((ok) => setTimeout(ok, 1000));
console.log(`last.fm download: mensagem ${JSON.stringify(erro?.message)} | pedidos no total ${total} | pedidos depois da mensagem ${depoisDoErro} | avisos de progresso depois da mensagem ${progressoDepois}`);
'@ | node --input-type=module -
```

  Saída:
  - `capas: HTTP 500 hoje -> null; amanha com o Spotify ok -> null (pedidos no total: 1)`
  - `capas: HTTP 404 hoje -> null; amanha com o Spotify ok -> null (pedidos no total: 1)`
  - `capas: HTTP 503 hoje -> null; amanha com o Spotify ok -> capa (pedidos no total: 5)`
  - `last.fm pedir(): HTTP 429 com Retry-After: 60 -> 5 pedidos, esperas [1000,2000,4000,8000] ms, mensagem: "O Last.fm pediu uma pausa. Espere um minuto e tente de novo."`
  - `last.fm pedir(): HTTP 200 com {error: 29} -> 5 pedidos, esperas [1000,2000,4000,8000] ms, mensagem: "O Last.fm pediu uma pausa. Espere um minuto e tente de novo."`
  - `last.fm pedir(): HTTP 500 -> 5 pedidos, esperas [1000,2000,4000,8000] ms, mensagem: "O Last.fm recusou o pedido (código 500). Tente de novo daqui a pouco."`
  - `last.fm pedir(): lento (TimeoutError em todo pedido) -> 5 pedidos, esperas [1000,2000,4000,8000] ms, mensagem: "O Last.fm está demorando para responder. Tente de novo daqui a pouco."`
  - `last.fm pedir(): sem rede (TypeError) -> 1 pedidos, esperas [] ms, mensagem: "Sem conexão com o Last.fm. Confira a internet e tente de novo."`
  - `last.fm pedir(): HTTP 200 com HTML no corpo -> 1 pedidos, esperas [] ms, mensagem: "O Last.fm recusou o pedido (código 200). Tente de novo daqui a pouco."`
  - `last.fm download: mensagem "O Last.fm pediu uma pausa. Espere um minuto e tente de novo." | pedidos no total 16 | pedidos depois da mensagem 2 | avisos de progresso depois da mensagem 0`
- **Impacto:** uma instabilidade de minutos no Spotify (500, 502) deixa as capas daquelas músicas sem imagem por um mês para quem abriu o Wrapped naquela hora, até clicar em "Apagar capas guardadas". O 404 é diferente: o ID não existe e guardar `null` é correto.
- **Solução proposta:** em `json()` (`capas.js:103-112`), tratar 5xx como o 503 (esperar, tentar e, se continuar, lançar erro, que não é gravado). Guardar `null` só quando a resposta foi ok e não achou nada, ou 404.
- **Testes necessários:** JS (`tests/js/capas.test.mjs`): 500 hoje e 200 amanhã devolve a capa; 404 continua guardado.
- **Critério de aceitação:** no bloco, a 1ª linha dá `amanha com o Spotify ok -> capa` e a 2ª continua `null`.

### R3-07 — ListenBrainz: resposta que não é JSON aparece como "Expecting value: line 1 column 1", e erro do servidor culpa a internet

- **Classificação:** Problema comprovado
- **Prioridade:** P3
- **Localização:** `listenbrainz.py:65-66` (`resposta.raise_for_status()` e `resposta.json()` sem tratamento), `ui/match.py:103-108` (o `ValueError` vira o texto do aviso; todo `httpx.HTTPError` vira "Confira a internet"). A resposta de um serviço de terceiros é dado não confiável e devia ser validada na fronteira.
- **Evidência:** chama o `executar_match` de verdade com 3 pessoas do ListenBrainz, em que só `ana_ficticia` recebe a falha, e captura o `gr.Warning`:

```powershell
@'
import httpx
import listenbrainz, ui, ui.match
from perfil_gosto import PerfilGosto
listenbrainz.time.sleep = lambda s: None
FALHAS = {'corpo HTML': httpx.Response(200, text='<html>manutencao</html>'), 'HTTP 500': httpx.Response(500), 'lento': 'timeout'}
def responder(resposta):
    def f(pedido):
        if resposta == 'timeout': raise httpx.ReadTimeout('lento', request=pedido)
        return resposta
    return f
for nome, resposta in FALHAS.items():
    def coletar(usuario, resposta=resposta):
        if usuario != 'ana_ficticia':  # as outras duas pessoas respondem normalmente
            return PerfilGosto(usuario, 'listenbrainz', '', {p: ['Banda A', usuario] for p in ('short_term', 'medium_term', 'long_term')})
        return listenbrainz.coletar_perfil_listenbrainz(usuario, cliente=httpx.Client(transport=httpx.MockTransport(responder(resposta))))
    avisos = []
    ui.match.coletar_perfil_listenbrainz = coletar
    ui.match.coletar_escutas_listenbrainz = lambda u, f: (_ for _ in ()).throw(ValueError('sem listens'))
    ui.gr.Warning = lambda m, **_: avisos.append(m)
    ui.executar_match([], '', 'America/Sao_Paulo', '', '', 'manter', False, False, False, 'ana_ficticia\nbia\ncaio', progress=lambda *a, **k: None)
    print(nome, '-> aviso na tela:', [ascii(a) for a in avisos if 'ana_ficticia' in a])
'@ | .venv\Scripts\python.exe -W ignore -
```

  Saída:
  - `corpo HTML -> aviso na tela: ["'Ficaram de fora do Match \\xb7 ana_ficticia: Expecting value: line 1 column 1 (char 0)'"]`
  - `HTTP 500 -> aviso na tela: ["'Ficaram de fora do Match \\xb7 ana_ficticia: o ListenBrainz n\\xe3o respondeu. Confira a internet.'"]`
  - `lento -> aviso na tela: ["'Ficaram de fora do Match \\xb7 ana_ficticia: o ListenBrainz n\\xe3o respondeu. Confira a internet.'"]`
- **Impacto:** com o ListenBrainz em manutenção (página HTML no lugar do JSON), a pessoa lê uma mensagem técnica em inglês. Com 500/503, o app manda conferir a internet, que está funcionando. O Match continua com as outras pessoas (isso está certo).
- **Solução proposta:** em `_get`, transformar corpo inválido em `ValueError('O ListenBrainz respondeu algo inesperado. Tente de novo mais tarde.')` e, em `ui/match.py`, separar `httpx.HTTPStatusError` (5xx: "O ListenBrainz está com problemas agora") de `httpx.TransportError` (sem rede ou lento: a mensagem atual). Para um serviço lento que ainda responde, desistir das próximas pessoas depois de N tempos-limite seguidos, como o MusicBrainz já faz.
- **Testes necessários:** Python (`tests/test_listenbrainz.py`): corpo HTML, 500 e `ReadTimeout`, cada um com a mensagem esperada (hoje não há teste de tempo-limite nem de 5xx); 3 tempos-limite seguidos não chamam a rede para os usuários seguintes.
- **Critério de aceitação:** as 3 linhas do bloco mostram mensagens em português, e só a de "lento" fala da internet.

### R3-08 — Windows: encerrar o app à força deixa 4 processos de leitura órfãos (249 MB)

- **Classificação:** Problema comprovado (reproduzido no Windows; no Linux não foi testado)
- **Prioridade:** P3
- **Localização:** `dados.py:660-676` (`habilitar_leitura_paralela` aquece o pool ao abrir o app), `:690-702` (`ProcessPoolExecutor` persistente com `spawn`, até 4 processos), chamado em `ui/layout.py:262`.
- **Evidência:** o bloco imita o app (liga a leitura paralela e manda uma tarefa ao pool, para ele existir de certeza), e encerra o processo de dois jeitos.

```powershell
@'
import json, os, signal, subprocess, sys, time
# O app liga a leitura paralela ao abrir (dados.py:660-676): o pool "spawn" sobe na hora. O submit garante que o pool existe.
FILHO = ("import time; from dados import habilitar_leitura_paralela, _executor; habilitar_leitura_paralela();"
         "_executor(2).submit(abs, -1).result(); time.sleep(5); print('pronto', flush=True); time.sleep(120)")
def ps(comando):
    v = json.loads(subprocess.run(['powershell', '-NoProfile', '-Command', comando], capture_output=True, text=True).stdout or '[]')
    return v if isinstance(v, list) else [v]
def descendentes(pid):
    return ps("$t = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId; $f = @(" + str(pid) + "); $i = 0;"
              "while ($i -lt $f.Count) { $f += @($t | Where-Object { $_.ParentProcessId -eq $f[$i] } | ForEach-Object { $_.ProcessId }); $i++ };"
              "ConvertTo-Json -Compress @($f | Select-Object -Skip 1)")
vivo = lambda pid: str(pid) in subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout
for como in ['terminate() (TerminateProcess) no processo do app', 'Ctrl+Break no grupo do console']:
    p = subprocess.Popen([sys.executable, '-W', 'ignore', '-c', FILHO], stdout=subprocess.PIPE, text=True,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    p.stdout.readline()
    antes = descendentes(p.pid)
    p.terminate() if como.startswith('terminate') else os.kill(p.pid, signal.CTRL_BREAK_EVENT)
    p.wait(); time.sleep(5)
    sobram = [x for x in antes if vivo(x)]
    mb = sum(ps('ConvertTo-Json -Compress @(' + ','.join(map(str, sobram)) + ' | ForEach-Object { (Get-Process -Id $_).WorkingSet64 })')) / 2**20 if sobram else 0
    print(f'{como}: processos abaixo do app = {len(antes)}; vivos 5 s depois = {len(sobram)} (memoria somada: {mb:.0f} MB)')
    for x in sobram: subprocess.run(['taskkill', '/PID', str(x), '/F'], capture_output=True)  # limpeza
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `terminate() (TerminateProcess) no processo do app: processos abaixo do app = 5; vivos 5 s depois = 4 (memoria somada: 249 MB)`
  - `Ctrl+Break no grupo do console: processos abaixo do app = 5; vivos 5 s depois = 0 (memoria somada: 0 MB)`

  "5" é o processo Python real (o `.venv\Scripts\python.exe` é um lançador, e é ele que leva o `terminate()`) mais os 4 do pool. O bloco mata os órfãos no fim. Antes desta rodada, nesta máquina, `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -match 'spawn_main'` listava **24** processos assim (6 grupos de 4, das 09h42 às 10h22 de hoje), todos com o processo pai já morto. A origem provável são as rodadas anteriores, que abriram o app num subprocesso e o encerraram com `terminate()`; isso não é reproduzível agora.
- **Impacto:** testado: o encerramento à força (`TerminateProcess`, a mesma chamada do "Finalizar tarefa" do Gerenciador de Tarefas, aqui feita no lançador) deixa ~250 MB parados até reiniciar o PC, mais 4 processos a cada vez; e o Ctrl+Break mandado ao grupo do console não deixa órfãos. Não testados: Ctrl+C, fechar a janela do console e o "Finalizar tarefa" no Python real (§5).
- **Solução proposta:** passar um `initializer` ao `ProcessPoolExecutor` com uma thread que espera `multiprocessing.parent_process().sentinel` e chama `os._exit(0)` quando o pai some (biblioteca padrão, ~6 linhas). Só "criar o pool na primeira leitura grande" não resolve: o pool continua órfão depois da primeira leitura.
- **Testes necessários:** Python (Windows, depois do R3-03): o bloco acima como teste, com `terminate()` e 0 vivos.
- **Critério de aceitação:** a 1ª linha do bloco dá `vivos 5 s depois = 0` (o bloco já força a criação do pool, então a alternativa preguiçosa não passa sem resolver).

### R3-09 — Calibração e validação do Match: nenhum registro de dados separados, e o estudo de 12 históricos fora do `VALIDACAO.md`

- **Classificação:** Risco potencial (registro ausente; se houve problema de método não dá para saber)
- **Prioridade:** P3 (vai no mesmo PR do R1-02, que já pede o mínimo de amostra documentado no `VALIDACAO.md`)
- **Localização:** `conciliacao.py:29-30` ("Faixas calibradas com 4 históricos reais"; o R1 citou `:28`), `match.js:14` (repete), `VALIDACAO.md:73` ("Match com 4 históricos reais conferido no Chromium…", uma checagem de interface). O estudo com 12 históricos que escolheu o RBO e o "peso pelo tempo" aparece em `analise.py:43` e `CHANGELOG.md:112-123`, mas não no `VALIDACAO.md`.
- **Evidência:** as 4 últimas linhas do bloco do R3-01. O ponto "não está documentado se houve dados separados" já estava na R1 (§6 da R1); o que esta rodada acrescenta é a ausência do estudo de 12 históricos no `VALIDACAO.md`.
- **Impacto:** as faixas ("Sintonia rara" a partir de 25) não têm validação registrada; se os mesmos 4 históricos serviram para escolher e para conferir, as faixas podem só descrever esses 4. Junto do R1-02 (1 artista em comum dá "Sintonia rara"), a nota do Match é a parte com menos base registrada.
- **Solução proposta:** uma seção "Match" no `VALIDACAO.md` com: quais dados escolheram as faixas, quais as conferiram (outros históricos, ou validação deixando um de fora), a distribuição das notas e o resultado; e uma seção com o estudo dos 12 históricos (números agregados e método, sem nomes). Se não houver dados separados, dizer isso e marcar as faixas como provisórias na tela (o R2-07 já pede a escala da nota).
- **Testes necessários:** nenhum de código.
- **Critério de aceitação:** o `VALIDACAO.md` tem as duas seções, cada uma dizendo quais dados calibraram, quais validaram (ou que não houve validação separada) e os números obtidos. O bloco do R3-01 só confere que as palavras aparecem; o conteúdo é revisão humana.

### R3-10 — Nomes e descrições das métricas divergem entre superfícies e não dizem tudo o que o cálculo faz

- **Classificação:** Oportunidade de melhoria
- **Prioridade:** P4
- **Localização:**
  - cosseno: "Escuta em comum" (`resultado.js:59`), "Similaridade musical" (`componentes.py:70`, `apresentacao.py:115`), "SIMILARIDADE DE ESCUTA · COSSENO" (`cartao.py:152`);
  - Ruzicka: "Plays em comum" (`resultado.js:62`, parecido demais com "Escuta em comum") e "Contagens compartilhadas" (`componentes.py:73`); o aviso "sensível ao volume de escuta" só existe no rodapé do PC (`ui/layout.py:871`);
  - Jaccard: "De todos os artistas que aparecem nos dois históricos" (`resultado.js:60`) e "todos os artistas" (`componentes.py:71`), mas o cálculo usa só plays ≥ 30 s e, por padrão, só o período em comum (`analise.py:307-330`); o Ruzicka "pesando pela quantidade de plays", mas no navegador o padrão pesa ln(1 + plays) (R3-01).
- **Evidência:**

```powershell
@'
import re
from pathlib import Path
# Ancorado no dado (chave ou campo da metrica), nao no rotulo: o bloco continua valendo depois de trocar os nomes.
ALVOS = {'site/app/js/resultado.js': r"\['(cosseno|jaccard|ruzicka)'", 'componentes.py': r"\(\s*'[^']+', m\.(cosseno|jaccard|jaccard_ponderado)\b",
         'ui/layout.py': r'volume de escuta'}
for arq, padrao in ALVOS.items():
    for i, linha in enumerate(Path(arq).read_text(encoding='utf-8').splitlines(), 1):
        if re.search(padrao, linha):
            print(f'{arq}:{i}', ascii(linha.strip())[:150])
cartao = Path('cartao.py').read_text(encoding='utf-8').splitlines()
i = next(n for n, l in enumerate(cartao) if 'resultado.metricas.cosseno' in l)  # o rotulo e a linha antes do numero
print(f'cartao.py:{i}', ascii(cartao[i - 1].strip())[:150])
print('"volume" em algum texto do app web:', [str(p) for p in Path('site').rglob('*.js') if 'volume de escuta' in p.read_text(encoding='utf-8')])
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `site/app/js/resultado.js:59 "['cosseno', 'Escuta em comum', 'Cosseno', 'Compara quanto cada um ouviu de cada artista. \xc9 o n\xfamero da abertura dos stories.'],"`
  - `site/app/js/resultado.js:60 "['jaccard', 'Artistas em comum', 'Jaccard', 'De todos os artistas que aparecem nos dois hist\xf3ricos, quantos os dois ouviram.'],"`
  - `site/app/js/resultado.js:62 "['ruzicka', 'Plays em comum', 'Ruzicka', 'Como o de artistas em comum, mas pesando pela quantidade de plays.'],"`
  - `componentes.py:70 "('Similaridade musical', m.cosseno, f'Cosseno \xb7 pondera\xe7\xe3o {resultado.ponderacao}'),"`
  - `componentes.py:71 "('Artistas em comum', m.jaccard, 'Jaccard \xb7 todos os artistas'),"`
  - `componentes.py:73 "('Contagens compartilhadas', m.jaccard_ponderado, 'Ruzicka \xb7 pondera\xe7\xe3o selecionada'),"`
  - `ui/layout.py:871 "'O Ruzicka usa pesos absolutos e \xe9 sens\xedvel ao volume de escuta. ' + AVISO_TRACOS,"`
  - `cartao.py:152 "texto(100, 415, 'SIMILARIDADE DE ESCUTA \xb7 COSSENO', 26, SECUNDARIO)"`
  - `"volume" em algum texto do app web: []`

  As fórmulas fazem o que os nomes prometem: cosseno sobre contagens de plays (`metricas.py:49-51`), Jaccard sobre conjuntos de artistas (`metricas.py:54-58`), RBO extrapolado do top 50 com p = 0,9 (`metricas.py:61-82`, "pesa mais o topo"), Ruzicka com o mesmo divisor nos dois perfis, sem normalizar volume (`metricas.py:85-97`). No Match, o cosseno é sobre rankings ponderados por posição (`perfil_gosto.py:206-226`), e a tela diz "compara só os rankings" (`match-tela.js:20`): bate.
- **Impacto:** quem usa as duas superfícies não sabe que "Escuta em comum" e "Similaridade musical" são o mesmo número; no navegador ninguém avisa que o Ruzicka favorece quem ouve mais; e "todos os artistas" sugere mais do que o cálculo usa.
- **Solução proposta:** um nome por métrica nas três superfícies e descrições que digam o recorte ("artistas com plays de 30 s ou mais, no período em comum") e a ponderação; a frase do volume também em `resultado.js:62`.
- **Testes necessários:** Python (`tests/test_contratos.py`): os rótulos das 4 métricas iguais em `resultado.js` e `componentes.py`.
- **Critério de aceitação:** no bloco, o rótulo do cosseno é o mesmo nas linhas de `resultado.js`, `componentes.py` e `cartao.py`, o do Ruzicka é o mesmo nas duas primeiras, e a última linha deixa de ser `[]`.

### R3-11 — Convite: um `SYNCUP2.` futuro diz "Isso não parece um convite do SyncUp", e uma mudança de sentido sob `SYNCUP1.` passaria sem aviso

- **Classificação:** Oportunidade de melhoria (versionamento)
- **Prioridade:** P4 (só importa no dia em que o formato mudar)
- **Localização:** `convite.py:62-63`, `site/app/js/convite.js:55`. O prefixo é o único versionamento; não há campo de versão no JSON, e campos desconhecidos são ignorados (`convite.py:76-88`).
- **Evidência:**

```powershell
@'
import base64, json, subprocess, zlib
from convite import PREFIXO, gerar_convite, ler_convite
from perfil_gosto import PerfilGosto
def codigo(d, prefixo=PREFIXO):
    return prefixo + base64.urlsafe_b64encode(zlib.compress(json.dumps(d).encode())).decode().rstrip('=')
base = {'n': 'Ana', 'a': {'short_term': ['Banda A']}, 'm': {'short_term': [['Faixa 1', 'Banda A']]}}
casos = {
    'atual': codigo(base),
    'futuro SYNCUP2.': codigo(base, 'SYNCUP2.'),
    'campo novo (v)': codigo({**base, 'v': 2, 'g': ['rock']}),
    'sem m': codigo({k: v for k, v in base.items() if k != 'm'}),
    'sem n': codigo({k: v for k, v in base.items() if k != 'n'}),
}
NODE = ("import {lerConvite} from './site/app/js/convite.js'; let s=''; process.stdin.on('data', d => s += d).on('end', async () => {"
        " const r = []; for (const c of JSON.parse(s)) { try { const p = await lerConvite(c); r.push('ok ' + p.nome); } catch (e) { r.push('erro: ' + e.message); } }"
        " console.log(JSON.stringify(r)); });")
js = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE], input=json.dumps(list(casos.values())).encode(),
                               capture_output=True, check=True).stdout.decode('utf-8'))
for (nome, c), j in zip(casos.items(), js):
    try: py = 'ok ' + ler_convite(c).nome
    except ValueError as e: py = 'erro: ' + str(e)
    print(nome, '| py:', ascii(py), '| js:', ascii(j))
for extra in ({'versao': 99}, {}, {'versao': 'x'}):
    p = PerfilGosto.de_dict({'nome': 'Ana', 'top_artistas': {'short_term': ['Banda A']}, **extra})
    print('de_dict', extra, '-> aceito, versao =', repr(p.versao))
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `atual | py: 'ok Ana' | js: 'ok Ana'`
  - `futuro SYNCUP2. | py: 'erro: Isso n\xe3o parece um convite do SyncUp (ele come\xe7a com "SYNCUP1.").' | js: 'erro: Isso n\xe3o parece um convite do SyncUp (ele come\xe7a com "SYNCUP1.").'`
  - `campo novo (v) | py: 'ok Ana' | js: 'ok Ana'`
  - `sem m | py: 'erro: O convite est\xe1 incompleto ou foi alterado. Copie o c\xf3digo inteiro de novo.' | js: (igual)`
  - `sem n | py: 'erro: O convite est\xe1 incompleto ou foi alterado. Copie o c\xf3digo inteiro de novo.' | js: (igual)`
  - `de_dict {'versao': 99} -> aceito, versao = 99`
  - `de_dict {} -> aceito, versao = 1`
  - `de_dict {'versao': 'x'} -> aceito, versao = 'x'`

  As 3 últimas linhas são do R3-13.
- **Impacto:** se o formato mudar de prefixo, quem tem a versão antiga lê "não parece um convite do SyncUp" e acha que o amigo mandou algo errado, quando o certo é atualizar. Se mudar sem trocar o prefixo (por exemplo, um campo `v: 2` que muda o sentido de `a`), a versão antiga aceita em silêncio. Acrescentar um campo opcional sem mudar o sentido funciona hoje, e campo obrigatório ausente é recusado com mensagem clara.
- **Solução proposta:** reconhecer `SYNCUP<n>.` com `n > 1` e reservar o campo `v` (recusar se `v > 1`), respondendo nos dois casos "Este convite foi feito numa versão mais nova do SyncUp. Atualize o app para ler." Nos dois motores, com o mesmo texto. Não há migração a fazer: `SYNCUP1.` é o único formato desde que o convite existe.
- **Testes necessários:** `tests/test_convite.py` e `tests/js/convite.test.mjs` com `SYNCUP2.` e com `v: 2`; paridade da mensagem (o round trip de `test_paridade_match.py:141-152` já existe).
- **Critério de aceitação:** as linhas `futuro SYNCUP2.` e `campo novo (v)` do bloco mostram a mensagem de atualização nos dois lados.

### R3-12 — Limite de taxa: nenhum cliente respeita um `Retry-After` longo, o iTunes não tem limitador e o download do Last.fm multiplica as tentativas

- **Classificação:** Risco potencial
- **Prioridade:** P3
- **Localização:**
  - Last.fm: `lastfm.js:15,54` (esperas fixas de 1, 2, 4 e 8 s para qualquer falha passageira); o download tem 3 páginas em paralelo (`:14,108-111`), e cada uma tenta 5 vezes sozinha; o que já baixou só vai para o cache depois do sucesso completo (`:178-181`, pelo código).
  - Capas: `capas.js:109` (2, 4, 8 s). MusicBrainz no PC: `generos.py:83-103` (429 conta como falha comum; o próximo pedido sai 1 s depois). ListenBrainz: `listenbrainz.py:34,38-44,53` (corta o `Retry-After` em 10 s e tenta de novo).
  - iTunes: `som.js:20-24,48-51,163-171` (todas as buscas saem juntas por `Promise.all`, sem limitador, sem nova tentativa e sem teste).
- **Evidência:** bloco do R3-06 (`HTTP 429 com Retry-After: 60 -> 5 pedidos, esperas [1000,2000,4000,8000] ms` e, no download, `pedidos no total 16 | pedidos depois da mensagem 2`) e bloco da §2.2 (ListenBrainz com `Retry-After: 30`: `esperas [10, 10]`, 3 pedidos; MusicBrainz: próximos pedidos 1 s depois, até parar na 3ª falha). O iTunes foi lido, não simulado.
- **Impacto:** depois das tentativas o app desiste com a mensagem certa. Mas, quando o Last.fm pede pausa, saem 16 pedidos com a chave pública compartilhada por todos os visitantes, 2 deles depois que a pessoa já leu "pediu uma pausa"; isso pode prolongar o bloqueio. Uma falha no meio de um download longo joga fora todas as páginas já baixadas. O iTunes recebeu 19 buscas de uma vez no Wrapped observado (3 delas as de exemplo); nos outros modos, pelo código, a rajada tem o tamanho da trilha de cada um.
- **Solução proposta:** nos clientes com tentativas (Last.fm, capas, MusicBrainz, ListenBrainz), ler `Retry-After` (segundos) e, se for maior que um teto de 10 s (o do ListenBrainz hoje), desistir logo com a mensagem de pausa; abaixo do teto, esperar o maior entre ele e a espera atual. No Last.fm, um 429 ou erro 29 numa página pausa as outras (um `AbortController` interno), e as páginas já baixadas vão para o cache. No iTunes, o mesmo limitador de `capas.js:80-94`. Os testes devem usar o status que cada serviço documenta (o MusicBrainz, pela documentação pública, responde 503 ao limite; isso não foi verificado aqui).
- **Testes necessários:** JS (`tests/js/lastfm.test.mjs`): `pedir` com 429 e `Retry-After: 60` desiste em 1 pedido; `baixarScrobbles` com 429 a partir da página 2 faz no máximo 1 rodada de tentativas no total e 0 pedidos depois da rejeição. JS (novo `tests/js/som.test.mjs`): N candidatas dão no máximo K pedidos em voo. Python (`tests/test_listenbrainz.py`): 429 com `Retry-After: 30` dá 1 pedido.
- **Critério de aceitação:** no bloco do R3-06, a linha do 429 dá `1 pedidos` e a do download dá `pedidos depois da mensagem 0`; no bloco da §2.2, o ListenBrainz com `Retry-After: 30` dá `pedidos 1`.

### R3-13 — `PerfilGosto.de_dict` aceita qualquer versão, e o perfil salvo que ele lia não existe mais

- **Classificação:** Oportunidade de melhoria (código morto)
- **Prioridade:** P4
- **Localização:** `perfil_gosto.py:51` (campo `versao`), `:62-75` (`para_json`, `de_dict`). Os perfis salvos saíram com o login do Spotify (`CHANGELOG.md:358`); `git grep -n -w -e de_dict -e para_json` acha só a definição (`perfil_gosto.py:62,66`) e os blocos de evidência da Rodada 1 (`docs/auditoria/rodada-1.md:106` e `:175`, nos R1-01 e R1-03); o bloco do R3-11 também usa `de_dict`. Nenhum código do app, de `tools/`, do `notebook/` ou de `tests/` usa. `VERSAO_PERFIL` continua útil: entra na chave do cache em memória (`perfil_gosto.py:142`). O comentário de `rotulo_fonte` sobre "convites antigos" (`:56`) também não vale mais: `ler_convite` sempre grava `fonte='convite'` (`convite.py:95`).
- **Evidência:** as 3 últimas linhas do bloco do R3-11 (`versao` 99 e `'x'` aceitos sem aviso).
- **Impacto:** nenhum para o usuário hoje. Quem lê o código acha que existe um formato de perfil salvo com versão, e `de_dict` aceita perfis de versões futuras sem aviso. É usado só pelos blocos de evidência das auditorias.
- **Solução proposta:** o mais barato é manter `de_dict` (os blocos de evidência das R1-01, R1-03 e R3-11 dependem dele) e recusar `versao > VERSAO_PERFIL` com "Perfil de uma versão mais nova do SyncUp"; `para_json` pode sair. Remover `de_dict` também só se os três blocos forem reescritos para montar `PerfilGosto(...)` direto, porque os critérios de aceitação do R1-01 e do R1-03 apontam para eles. `VERSAO_PERFIL` fica (chave do cache).
- **Testes necessários:** Python (`tests/test_match.py` ou novo): `de_dict` com `versao` 99 recusa e sem `versao` aceita.
- **Critério de aceitação:** no bloco do R3-11, a linha `de_dict {'versao': 99}` passa a mostrar a recusa (e `{'versao': 'x'}` também); a linha sem `versao` continua aceita. Se a escolha for remover, `git grep -n -w -e de_dict -e para_json -- "*.py"` não acha nada e os blocos das R1-01, R1-03 e R3-11 rodam sem `de_dict`.

### R3-14 — Textos de privacidade prometem mais do que o app faz: "apagados em até 1 hora" e "Fechou a página, sumiu"

- **Classificação:** Problema comprovado pela configuração e pela documentação do Gradio (a limpeza em si não foi cronometrada)
- **Prioridade:** P3
- **Localização:**
  - PC: `ui/meus_dados.py:19` ("apagados em até 1 hora") × `ui/layout.py:266` (`delete_cache=(3600, 3600)`): pela regra do Gradio, a cada 3600 s apaga o que tem mais de 3600 s, então um arquivo enviado logo depois de uma limpeza fica até ~2 h; se o app morrer, só é apagado quando o servidor subir de novo (o encerramento à força é o caso do R3-08).
  - Landing: `site/index.html:296` ("Os históricos são lidos no próprio navegador… Fechou a página, sumiu.") × `lastfm.js:181` (o histórico inteiro do Last.fm fica no IndexedDB `syncup-lastfm`; o campo `quando` é gravado e nunca lido, então não há prazo). Existe "Apagar dados guardados" (`wrapped.js:135-139`).
  - App web: os subtítulos de `main.js:107,109-110` (R3-05).
- **Evidência:**

```powershell
@'
import inspect, re
from pathlib import Path
import gradio as gr
ler = lambda arq: Path(arq).read_text(encoding='utf-8')
def linhas(arq, padrao):
    return [f'{arq}:{i} ' + ascii(l.strip())[:140] for i, l in enumerate(ler(arq).splitlines(), 1) if re.search(padrao, l)]
print(*linhas('ui/meus_dados.py', r'apagados em'), *linhas('ui/layout.py', r'delete_cache'), sep='\n')
doc = ' '.join((inspect.getdoc(gr.Blocks.__init__) or inspect.getdoc(gr.Blocks)).split())
regra = re.search(r'delete_cache: .*?(Every `frequency` seconds.*?created\.).*?(The cache will be deleted entirely when the server restarts\.)', doc)
print('Gradio', gr.__version__, '- delete_cache:', ascii(regra.group(1)), ascii(regra.group(2)))
print('site/index.html:', ascii(re.search(r'<h3>Fica no seu aparelho</h3><p>(.*?)</p>', ler('site/index.html')).group(1)))
js = ler('site/app/js/lastfm.js').splitlines()
print('lastfm.js: "quando" gravado em', [i for i, l in enumerate(js, 1) if 'quando:' in l], '| lido em', [i for i, l in enumerate(js, 1) if re.search(r'\.quando\b', l)])
print(*linhas('site/app/js/main.js', r'Nada sai|Nada . enviado'), sep='\n')
print('SomStories montado em:', [f'{a}:{i}' for a in ('resultado.js', 'match-tela.js', 'batalha-tela.js', 'wrapped.js')
      for i, l in enumerate(ler('site/app/js/' + a).splitlines(), 1) if '${SomStories}' in l])
'@ | .venv\Scripts\python.exe -W ignore -
```

  Saída:
  - `ui/meus_dados.py:19 '<li>Os hist\xf3ricos que voc\xea envia: lidos nesta sess\xe3o e apagados em at\xe9 1 hora.</li>'`
  - `ui/layout.py:266 'delete_cache=(3600, 3600),'`
  - ``Gradio 6.31.0 - delete_cache: 'Every `frequency` seconds, the temporary files created by this Blocks instance will be deleted if more than `age` seconds have passed since the file was created.' 'The cache will be deleted entirely when the server restarts.'``
  - `site/index.html: 'Os hist\xf3ricos s\xe3o lidos no pr\xf3prio navegador e nunca v\xe3o para um servidor. Fechou a p\xe1gina, sumiu.'`
  - `lastfm.js: "quando" gravado em [181] | lido em []`
  - `site/app/js/main.js:107 "dupla: ['Compare dois hist\xf3ricos', 'Envie o Hist\xf3rico Estendido do Spotify de duas pessoas. Nada \xe9 enviado para nenhum servidor.']`
  - `site/app/js/main.js:109 "match: ['Match do grupo', … Nada sai do seu aparelho.'],"` e `main.js:110` (Batalha, igual)
  - `SomStories montado em: ['resultado.js:158', 'match-tela.js:73', 'batalha-tela.js:123', 'wrapped.js:174']`

  A janela de ~2 h é a regra documentada do Gradio aplicada aos números configurados; a limpeza em si não foi cronometrada.
- **Impacto:** as promessas de privacidade são a principal razão de usar o SyncUp. Quem usou o Last.fm e fechou a página acredita que nada ficou, mas o histórico inteiro continua no navegador até alguém clicar em "Apagar dados guardados".
- **Solução proposta:** PC: `delete_cache=(600, 3000)` (limpa a cada 10 min o que tem mais de 50 min: no pior caso, 1 hora) ou o texto "em até 2 horas, ou ao fechar o app". Landing e app: dizer que o Last.fm fica guardado neste navegador até apagar (e onde apagar), ou dar uma validade ao cache (`quando` já existe). Os subtítulos, como no R3-05.
- **Testes necessários:** Python (`tests/test_smoke_ui.py`): a soma de `delete_cache` ≤ o prazo do texto. Python (`tests/test_site.py`): se o cache do Last.fm não tem validade, a landing não diz "sumiu".
- **Critério de aceitação:** no bloco, as duas primeiras linhas ficam coerentes (ou o texto muda), a linha do `index.html` deixa de prometer que tudo some (ou `quando` passa a ser lido), e as linhas de `main.js` mudam.

## 4. O que já funciona bem

- **Windows de verdade:** as 3 suítes passam aqui (295 + 105 + 17). Com o ambiente já criado, o `iniciar.bat` abre o app numa pasta com espaço e acento e, sem Python, mostra a mensagem certa e para no `pause`, mesmo com o arquivo em LF:

```powershell
@'
import io, os, shutil, socket, subprocess, tarfile, tempfile, threading, time, urllib.request
from pathlib import Path
raiz = Path(tempfile.mkdtemp()) / ('Sync Up ' + chr(0xc7) + chr(0xe3) + 'o')
tarfile.open(fileobj=io.BytesIO(subprocess.run(['git', 'archive', 'HEAD'], capture_output=True, check=True).stdout)).extractall(raiz, filter='data')
juncao = raiz / '.venv'  # juncao para o .venv do repositorio: nada e instalado nem copiado
subprocess.run(['cmd', '/c', 'mklink', '/J', str(juncao), str(Path('.venv').resolve())], capture_output=True, check=True)
print('pasta:', ascii(raiz.name), '| iniciar.bat com CRLF?', b'\r\n' in (raiz / 'iniciar.bat').read_bytes())
def rodar(env, esperar_url=None):
    p = subprocess.Popen(['cmd', '/c', str(raiz / 'iniciar.bat')], cwd=raiz,  # como no duplo clique: caminho completo
                         env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    saida = []
    threading.Thread(target=lambda: saida.extend(p.stdout), daemon=True).start()
    resposta = None
    if esperar_url:
        for _ in range(240):
            if p.poll() is not None: break
            try: resposta = urllib.request.urlopen(esperar_url, timeout=1).read(); break
            except Exception: time.sleep(0.5)
        subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True)
    codigo = p.wait(timeout=60)
    linhas = [ascii(x.decode('utf-8', 'replace').strip()) for x in saida if x.strip()]
    return codigo, linhas, resposta
s = socket.socket(); s.bind(('127.0.0.1', 0)); porta = s.getsockname()[1]; s.close()
env = {**os.environ, 'SYNCUP_PORTA': str(porta), 'BROWSER': 'C:/Windows/System32/where.exe /q %s'}  # nao abre aba de navegador
codigo, linhas, resposta = rodar(env, f'http://127.0.0.1:{porta}/')
print('caminho feliz: app respondeu', resposta is not None and b'gradio' in resposta.lower(), '| saida:', linhas[:4])
sem_python = {**os.environ, 'PATH': r'C:\Windows\System32'}
codigo, linhas, _ = rodar(sem_python)
print('sem Python no PATH: codigo', codigo, '| saida:', linhas)
os.rmdir(juncao)  # remove so a juncao, nunca o .venv de verdade
assert not juncao.exists() and Path('.venv/Scripts/python.exe').is_file()
shutil.rmtree(raiz.parent)
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `pasta: 'Sync Up \xc7\xe3o' | iniciar.bat com CRLF? False`
  - `caminho feliz: app respondeu True | saida: ["'Conferindo as dependencias (na primeira vez leva alguns minutos)...'"]`
  - `sem Python no PATH: codigo 1 | saida: ["'Nao achei o Python 3.10 ou mais novo.'", '\'Instale pelo site https://www.python.org/downloads/ marcando "Add python.exe to PATH".\'', "'Algo deu errado. Leia a mensagem acima.'", "'Pressione qualquer tecla para continuar. . .'"]`

  O `.venv` da cópia é uma junção para o `.venv` do repositório (nada é instalado; o `pip install` do `.bat` só confere). O `BROWSER` aponta para um comando que não abre aba. O bloco remove a junção (sem tocar no `.venv` real) e apaga a cópia.
- **ZIP e encoding:** nome de membro UTF-8 e cp437, JSON com BOM, pasta com acento e emoji, títulos com `ã`, `ç`, `É` e japonês: os dois motores leem igual.

```powershell
@'
import json, subprocess, tempfile, zipfile
from pathlib import Path
from dados import carregar
pasta = Path(tempfile.mkdtemp()) / ('Sync Up ' + chr(0xc7) + chr(0xe3) + 'o ' + chr(0x1F3B5))
pasta.mkdir()
reg = [{'ts': '2023-12-30T03:00:00Z', 'ms_played': 200000, 'master_metadata_track_name': 'Can' + chr(0xe7) + chr(0xe3) + 'o ' + chr(0x3042),
        'master_metadata_album_artist_name': 'Banda ' + chr(0xc9), 'spotify_track_uri': 'spotify:track:x'}]
corpo = json.dumps(reg, ensure_ascii=False).encode('utf-8')
utf8 = pasta / ('Hist' + chr(0xf3) + 'rico utf8.zip')
with zipfile.ZipFile(utf8, 'w') as z:
    z.writestr('Spotify Extended Streaming History/Streaming_History_Audio_' + chr(0xe7) + '_2023.json', corpo)
cp437 = pasta / 'Historico cp437.zip'
original = zipfile.ZipInfo._encodeFilenameFlags
zipfile.ZipInfo._encodeFilenameFlags = lambda self: (self.filename.encode('cp437'), self.flag_bits)
with zipfile.ZipFile(cp437, 'w') as z:
    z.writestr('Streaming_History_Audio_' + chr(0xe7) + '_2023.json', corpo)
zipfile.ZipInfo._encodeFilenameFlags = original
bom = pasta / ('com BOM ' + chr(0xe9) + '.json')
bom.write_bytes(b'\xef\xbb\xbf' + corpo)
NODE = ("import {lerHistorico} from './site/app/js/historico.js'; import fs from 'node:fs'; import path from 'node:path';"
        "for (const c of process.argv.slice(1)) { const h = await lerHistorico([{ nome: path.basename(c), bytes: new Uint8Array(fs.readFileSync(c)) }]);"
        " console.log(JSON.stringify([path.basename(c), h.utc.length, h.musica[0], h.artista[0]]));}")
for c in (utf8, cp437, bom):
    df = carregar(c)
    print('py', ascii(c.name), 'linhas', len(df), ascii(df['musica'].iloc[0]), ascii(df['artista'].iloc[0]))
r = subprocess.run(['node', '--input-type=module', '-e', NODE, str(utf8), str(cp437), str(bom)], capture_output=True)
for linha in r.stdout.decode('utf-8').splitlines(): print('js', ascii(json.loads(linha)))
print('js stderr', ascii(r.stderr.decode('utf-8')[-300:]))
'@ | .venv\Scripts\python.exe -
```

  Saída: 3 linhas `py '<arquivo>' linhas 1 'Can\xe7\xe3o \u3042' 'Banda \xc9'` (para `'Hist\xf3rico utf8.zip'`, `'Historico cp437.zip'` e `'com BOM \xe9.json'`), 3 linhas `js ['<arquivo>', 1, 'Can\xe7\xe3o \u3042', 'Banda \xc9']` e `js stderr ''`. Pela leitura, os `open()` do código do app têm `encoding=` explícito ou são binários, e os testes que chamam o Node decodificam bytes como UTF-8 (`dados.py`, `generos.py`, `exportacoes.py`, `tests/test_paridade_*.py`).
- **Invariantes das métricas:** em 500 pares aleatórios (pesos de 0,01 a 1 milhão, nomes Unicode), as 4 métricas são simétricas, dão 1 para o mesmo perfil, ficam em [0, 1], são determinísticas, e Python × JS diferem no máximo 1,7e-16:

```powershell
@'
import json, random, subprocess
from metricas import cosseno, jaccard, jaccard_ponderado, rbo
rnd = random.Random(7)
nomes = [f'Banda {i}' for i in range(40)] + ['Banda ' + chr(0x3042), 'Banda ' + chr(0x1F3B5)]
casos = []
for _ in range(500):
    a = {n: rnd.choice([1, 2, 3, 10, 250, 1e6]) * rnd.random() + 0.01 for n in rnd.sample(nomes, rnd.randint(1, 30))}
    b = {n: rnd.choice([1, 2, 3, 10, 250, 1e6]) * rnd.random() + 0.01 for n in rnd.sample(nomes, rnd.randint(1, 30))}
    casos.append((a, b, sorted(a, key=a.get, reverse=True), sorted(b, key=b.get, reverse=True)))
def metricas_py(a, b, ra, rb):
    return [cosseno(a, b), jaccard(a, b), jaccard_ponderado(a, b), rbo(ra, rb, 0.9, 50)]
NODE = ("import {cosseno, jaccard, ruzicka, rbo} from './site/app/js/dupla.js'; let s=''; process.stdin.on('data', d => s += d).on('end', () => {"
        " const M = (o) => new Map(Object.entries(o)); const f = ([a, b, ra, rb]) => [cosseno(M(a), M(b)), jaccard(Object.keys(a), Object.keys(b)), ruzicka(M(a), M(b)), rbo(ra, rb, 0.9, 50)];"
        " console.log(JSON.stringify(JSON.parse(s).map((c) => [f(c), f([c[1], c[0], c[3], c[2]]), f([c[0], c[0], c[2], c[2]]), f(c)]))); });")
js = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE], input=json.dumps(casos).encode(), capture_output=True, check=True).stdout)
rotulos = ['cosseno', 'jaccard', 'ruzicka', 'rbo']
for i, rot in enumerate(rotulos):
    py_ab = [metricas_py(*c)[i] for c in casos]
    py_ba = [metricas_py(c[1], c[0], c[3], c[2])[i] for c in casos]
    py_aa = [metricas_py(c[0], c[0], c[2], c[2])[i] for c in casos]
    js_ab, js_ba, js_aa, js_ab2 = ([r[k][i] for r in js] for k in range(4))
    print(f'{rot:8} simetria py max|ab-ba| = {max(abs(x - y) for x, y in zip(py_ab, py_ba)):.1e}, js = {max(abs(x - y) for x, y in zip(js_ab, js_ba)):.1e}'
          f' | identidade py min = {min(py_aa):.15f}, js min = {min(js_aa):.15f}'
          f' | limites [0,1] py {all(0 <= x <= 1 for x in py_ab)}, js {all(0 <= x <= 1 for x in js_ab)}'
          f' | determinismo js {js_ab == js_ab2}, py {py_ab == [metricas_py(*c)[i] for c in casos]}'
          f' | max|py-js| = {max(abs(x - y) for x, y in zip(py_ab, js_ab)):.1e}')
'@ | .venv\Scripts\python.exe -
```

  Saída (4 linhas, uma por métrica):
  - `cosseno  simetria py max|ab-ba| = 0.0e+00, js = 1.1e-16 | identidade py min = 1.000000000000000, js min = 1.000000000000000 | limites [0,1] py True, js True | determinismo js True, py True | max|py-js| = 1.7e-16`
  - `jaccard  simetria py max|ab-ba| = 0.0e+00, js = 0.0e+00 | identidade … 1.000000000000000 … | limites [0,1] py True, js True | determinismo js True, py True | max|py-js| = 0.0e+00`
  - `ruzicka  simetria py max|ab-ba| = 0.0e+00, js = 1.2e-16 | identidade … | limites … True | determinismo … True | max|py-js| = 1.1e-16`
  - `rbo      simetria py max|ab-ba| = 0.0e+00, js = 0.0e+00 | identidade … | limites … True | determinismo … True | max|py-js| = 0.0e+00`

  A simetria do JS difere no último bit (1e-16) porque a ordem da soma muda; os testes propostos no R3-04 devem usar tolerância. "Identidade min = 1.000000000000000" está arredondado a 15 casas.
- **A paridade pega o que mais importa:** mudar o play mínimo de 30 s quebra 27 testes; a janela de 28 dias, o peso das músicas e a meia-vida também são pegos (R3-04).
- **Cache do histórico bem versionado** (`dados.py:487-580`): versão do esquema, identidade das opções, hash do Parquet, contadores conferidos e gravação atômica. É o modelo para o cache de gêneros (R1-03).
- **Convite:** acrescentar um campo opcional não quebra a versão de hoje, e campo obrigatório ausente é recusado com a mesma mensagem nos dois motores (R3-11).
- **Rede no PC:** servidor só em `127.0.0.1`, telemetria do Gradio desligada, ListenBrainz e MusicBrainz opcionais, User-Agent sem e-mail (visto no cliente do próprio app). O MusicBrainz espaça 1 s, para depois de 3 falhas e não guarda falha no cache (§2.2).
- **Rede no navegador:** URLs de imagem e áudio só de hosts esperados e https (`capas.js:21-25`, `lastfm.js:61`); IDs fictícios nunca saem (`capas.js:14-16`; o pedido do bloco do R3-05 só saiu porque o ID tinha o formato real); o Last.fm tem tempo-limite por pedido, tentativas com espera, "Cancelar" e mensagens em português para sem rede, lento e limite.
- **Quando uma API de dados falha** (ListenBrainz, MusicBrainz, Last.fm, capas, nos casos simulados), o resultado continua aparecendo; só some a capa, o som ou a pessoa que dependia dela. O CDN do Preact é a exceção (R3-02).

Também valem os pontos fortes das rodadas 1 e 2 (paridade, golden master, ZIP endurecido, foco e ARIA na web).

## 5. Necessita investigação

- **CI no Windows:** a proposta do R3-03 não foi rodada no GitHub. A suíte no Python 3.14 e o Node 22 no Windows não foram executados nesta máquina (o 3.14 só resolveu dependências).
- **Primeira execução do `iniciar.bat`:** criar o venv com o `py -3` (3.14 aqui) numa pasta com acento e instalar tudo. Testado só com o ambiente já criado.
- **Encerrar o app de outros jeitos:** Ctrl+C, fechar a janela do console (`CTRL_CLOSE`) e o "Finalizar tarefa" no Python real (não no lançador). O pool órfão também não foi testado no Linux (R3-08).
- **Rede da página do Gradio:** ninguém capturou os pedidos que o frontend do Gradio faz no navegador; "nada mais sai do PC" (§2.2) vem da leitura. Um teste Playwright com toda a rede externa abortada fecharia isso.
- **Last.fm na tela com 429 e lentidão reais** (respostas que demoram menos que os 20 s e nunca estouram o tempo-limite), e o ListenBrainz lento de verdade (até 12 chamadas por pessoa, 10 s por fase): só a camada de rede foi simulada.
- **`TypeError` do R1-03 na tela do PC** (`ui/match.py:185` só traduz `ValueError`): não reproduzido.
- **Arquivo `.bat` em LF:** funcionou aqui nos dois caminhos. O `cmd` tem um problema conhecido com rótulos em arquivos LF quando o rótulo cai numa fronteira de bloco de leitura; não foi reproduzido.
- **Comportamento real das APIs:** limites do iTunes por IP, frequência real de 500 no oEmbed, status de limite do MusicBrainz (503 pela documentação) e o `Referer` no GitHub Pages não foram medidos, por regra.
- **Tamanho real da diferença do R3-01** com históricos reais.
- **"Downloads … apagados ao fim da sessão"** (`ui/meus_dados.py:20`): pode ser uma 4ª promessa governada pelo mesmo `delete_cache` ou pelo `rmtree` de `ui/comum.py:69-76`; não conferido.

## 6. Lista curta (fora dos 14 achados)

- `iniciar.bat` está em LF (`.gitattributes:2`, `* text=auto eol=lf`). Funcionou, mas `*.bat text eol=crlf` no `.gitattributes` evitaria o risco do `cmd` com rótulos. Não muda nenhum hash testado.
- Os testes de paridade são pulados sem Node no PATH (aparecem só no resumo `-ra`, `pyproject.toml:17`): um ambiente sem Node fica verde sem comparar os motores. No CI, falhar quando o Node falta seria mais seguro.
- `SYNCUP_PORTA` não numérico derruba o app ao importar (`app.py:16`), sem mensagem.
- Sem `Content-Security-Policy` no `site/`: uma CSP com `connect-src` só para os hosts da §2.2 transformaria a lista do que sai em regra do navegador.
- Last.fm com HTTP 200 e corpo HTML diz "recusou o pedido (código 200)" (bloco do R3-06); "resposta inesperada" seria mais claro.
- `web/ponte.py` ainda se descreve como ponte do Pyodide (`:1`), mas hoje só serve aos testes de paridade; e `site.yml:8` republica o site quando `web/**` muda.
- `VALIDACAO.md` ainda se chama "v0.5 final" no título (`:1`) e para na v1.3.1.
- Correções de linha da Rodada 1: o comentário das faixas do Match está em `conciliacao.py:29` (não `:28`).

## 7. Plano de PRs desta rodada (um item por PR, nesta ordem)

| # | PR | Achado | Toca |
|---|---|---|---|
| 1 | CI no Windows (3.12 e 3.14) e JS no Windows | R3-03 | `.github/workflows/testes.yml` |
| 2 | Teste de contrato das constantes e das invariantes | R3-04 | `tests/test_contratos.py` (novo), `tests/js/` (invariantes), `match-tela.js`, `main.js` |
| 3 | Mesma ponderação padrão (ou ponderação visível no navegador) | R3-01 | `opcoes.js` ou `ui/layout.py`, `resultado.js`, `VALIDACAO.md`, `tests/test_contratos.py` |
| 4 | Preact/htm servido pelo próprio site | R3-02 | `site/app/index.html`, `site/app/vendor/`, `tests/test_site.py`, `tests/navegador/conftest.py` |
| 5 | Subtítulos verdadeiros e preferência "Capas e som" | R3-05 | `main.js`, `som.js`, `wrapped.js`, teste de navegador, `tests/test_site.py` |
| 6 | Textos de privacidade coerentes (PC e landing) | R3-14 | `ui/layout.py` ou `ui/meus_dados.py`, `site/index.html`, `lastfm.js`, testes |
| 7 | Capas: 5xx não vira "sem capa" por 30 dias | R3-06 | `capas.js`, `tests/js/capas.test.mjs` |
| 8 | Mensagens do ListenBrainz | R3-07 | `listenbrainz.py`, `ui/match.py`, `tests/test_listenbrainz.py` |
| 9 | Pool de leitura encerra junto com o app | R3-08 | `dados.py`, teste (Windows, depende do PR 1) |
| 10 | Limite de taxa nos 5 clientes | R3-12 | `lastfm.js`, `capas.js`, `som.js`, `generos.py`, `listenbrainz.py`, testes |
| 11 | Seções de validação do Match e do estudo de 12 históricos | R3-09 | `VALIDACAO.md` (junto do PR do R1-02) |
| 12 | Nomes e descrições das métricas | R3-10 | `resultado.js`, `componentes.py`, `cartao.py`, `apresentacao.py` |
| 13 | Convite de versão futura | R3-11 | `convite.py`, `convite.js`, testes |
| 14 | `de_dict` recusa versão futura | R3-13 | `perfil_gosto.py`, teste |

Conflitos: 2 e 3 mexem em `tests/test_contratos.py` (o 2 cria, o 3 acrescenta); 3 e 12 em `resultado.js`; 5 e 10 em `som.js`; 6 e 10 em `lastfm.js`; 7 e 10 em `capas.js`; 8 e 10 em `listenbrainz.py`. O 1 sai primeiro, porque o teste do 9 precisa do runner Windows; o 10 vai depois de 5 a 8.

## 8. Skills aplicadas

- `agent-skills:ci-cd-and-automation` — a matriz do R3-03 (sem pular nenhum gate, `fail-fast: false`, Windows só onde o sistema importa, `shell: bash` onde o passo é bash, nomes de check preservados para a proteção da `main`) e o "deslocar para a esquerda": o teste de contrato do R3-04 pega no CI o que hoje só apareceria no uso.
- `agent-skills:api-and-interface-design` — contratos Python/JS como interface (R3-04); "preferir adição" e seus limites no convite (R3-11); resposta de terceiros como dado não confiável (R3-07); a Lei de Hyrum para manter o texto das mensagens igual nos dois motores.
- `agent-skills:deprecation-and-migration` — antes de propor remover, contar os consumidores: o `git grep` achou os blocos de evidência das auditorias usando `de_dict`, e por isso o R3-13 prefere recusar versões futuras a remover ("remover só com uso zero comprovado"); não há migração a desenhar para o convite (um formato só).
- `agent-skills:security-and-hardening` (e o revisor `agent-skills:security-auditor`, em contexto limpo) — fronteiras de confiança e "enviar o mínimo": a tabela do que sai (§2.2), o envio antes da escolha (R3-05), prazo de retenção e textos de privacidade (R3-14), CSP (lista curta).
- `agent-skills:test-driven-development` — cada achado traz o teste que falha hoje; as mutações do R3-04 são o "vermelho" do teste de contrato proposto.
- `engineering:testing-strategy` — pirâmide para os testes propostos: contrato estático e invariantes (pequenos), paridade (médios), Playwright só para o que é tela (R3-02, R3-05).
- `agent-skills:doubt-driven-development` — revisão adversarial do relatório antes da entrega (§9).

## 9. Revisão adversarial deste relatório

Três revisores em contexto limpo, cada um com uma lente (evidência e correção; escopo, duplicação e planos; privacidade, este com o agente `security-auditor`), receberam só o relatório, o repositório e as regras do pedido, com a instrução de achar erros e não validar. Juntos fizeram cerca de 50 apontamentos. Os válidos mudaram o relatório:

- **Uma mutação não fazia nada:** `MAXIMO_TEXTO` é valor padrão de argumento em `convite._texto`, e trocar o atributo do módulo não o alcança. O bloco passou a trocar `_texto.__defaults__`, ganhou a mutação da janela de 28 dias, e o placar virou "6 de 8 mutações, mais 2 controles".
- **O YAML não estava pronto para colar** (só cabeçalhos, e mudava os nomes dos checks da proteção da `main`). Virou o `testes.yml` completo, com os nomes de hoje no Linux, e o bloco compara os passos com o arquivo atual.
- **Contradições e exageros corrigidos:** o ListenBrainz não "respeita" o `Retry-After` (corta em 10 s e tenta de novo); "nenhum teste fixa simetria" era falso (`tests/test_metricas.py` confere simetria e identidade por métrica no Python; a 1ª correção ainda dizia o contrário e foi refeita no 2º ciclo); "~80 MB" não tinha medida (medido: 249 MB); o `iniciar.bat` só foi testado com o ambiente pronto; o 3.14 só resolveu dependências; o cabeçalho escondia as idas ao `unpkg.com`; "nada derruba o app" contradizia o R3-02.
- **Evidência mais fiel:** o User-Agent do ListenBrainz agora vem do cliente do próprio app (antes, do teste); o bloco do R3-01 lê os padrões dos arquivos; o do R3-10 se ancora na chave da métrica; o do R3-08 força a criação do pool.
- **O que faltava:** o download paralelo do Last.fm (16 pedidos num 429, 2 depois da mensagem) e o iTunes sem limitador entraram no R3-12; os modos Dupla, Match e Batalha e os subtítulos "Nada sai do seu aparelho" entraram no R3-05; os textos de privacidade viraram o R3-14; a §2.2 ganhou a landing, o PyPI e a 2ª etapa das capas.
- **Planos:** R1-10 e R3-11 voltaram a PRs separados; as promoções de prioridade estão marcadas; o PR do teste de contrato não leva as tabelas de casos extremos (elas falhariam antes das correções); a nota sobre o R1-07 foi corrigida (ele não iguala limites); o plano consolidado foi para o fim.
- **Linhas corrigidas:** `testes.yml:51`, `listenbrainz.py:65-66`, `dados.py:660-676`, `match.js:14`, `requirements.txt:8`, e as fontes da linha de imagens da §2.2.

Um 2º ciclo, em contexto limpo, revisou só as partes reescritas e achou mais 14 pontos, corrigidos: a frase sobre testes de simetria ainda errada; `delete_cache=(600, 3600)` contradizia o teste proposto no próprio R3-14; as notas de cada modo sobre o iTunes (R3-05 exagerava); critérios que o bloco não verificava (R3-01, R3-05, R3-12); o teto do `Retry-After` sem número; pendências da R2 §5 que faltavam; conflitos de arquivo entre rodadas no plano consolidado; o bloco da suíte com as 6 mutações, que só existia em prosa; e mais linhas.

Ficaram de fora, como ruído ou trade-off: rodar a primeira instalação do `iniciar.bat` e o app do PC com a rede capturada (foram para §5). Não houve segunda opinião de outro modelo nesta rodada.

## 10. Plano consolidado das 3 rodadas (P1 → P4)

Uma ordem só, para os 38 achados (R1-01 a R1-10, R2-01 a R2-14, R3-01 a R3-14), em 36 PRs. Dentro de cada prioridade, primeiro o que protege os PRs seguintes (CI e teste de contrato), depois o que o usuário sente. Quando um achado sobe de prioridade para ir junto de outro, a linha diz.

| Ordem | Prioridade | PR | IDs | Observação |
|---|---|---|---|---|
| 1 | P1 | Match: pessoa sem dados comparáveis sai com aviso | R1-01 | Único P1 das 3 rodadas |
| 2 | P2 | CI no Windows | R3-03 | Protege todos os seguintes no ambiente do Carlos |
| 3 | P2 | Teste de contrato e invariantes | R3-04 (P3, adiantado) | Adiantado para nascer antes dos PRs que mexem em regras copiadas entre os motores (4, 11, 23, 27 a 29). O 1 vem antes por ser o único P1. Sem as tabelas de casos extremos (vão nos PRs 11, 27 e 28) |
| 4 | P2 | Match: amostra pequena + validação documentada | R1-02 + R3-09 (P3, promovido para ir junto) | Mesmo `VALIDACAO.md`; depois do 1 (mesmos arquivos) |
| 5 | P2 | Wrapped: "histórico curto demais" | R2-01 | Precisa de paridade e de piso decidido com dados |
| 6 | P2 | Ponderação padrão igual (ou visível) | R3-01 | |
| 7 | P2 | Preact/htm no próprio site | R3-02 | |
| 8 | P2 | Foco sob a barra fixa no celular | R2-02 | |
| 9 | P2 | Player do PC com papel e foco visível | R2-03 | |
| 10 | P3 | Cache de gêneros: tipos, versão e teto | R1-03 | Seguir o modelo do cache do histórico |
| 11 | P3 | RBO: validação igual nos dois motores | R1-04 | Com a tabela de inválidos nos dois lados |
| 12 | P3 | Gradio: regra morta + teste de seletores | R1-05 + R2-12 (P4, promovido para ir junto) | R2 §7 já sugere juntar |
| 13 | P3 | Testes de navegador dos erros de entrada | R1-06 | |
| 14 | P3 | Subtítulos verdadeiros e preferência "Capas e som" | R3-05 | A preferência é decisão de produto do Carlos |
| 15 | P3 | Textos de privacidade coerentes | R3-14 | |
| 16 | P3 | Capas: 5xx sem cache de 30 dias | R3-06 | |
| 17 | P3 | Mensagens do ListenBrainz | R3-07 | |
| 18 | P3 | Pool encerra com o app | R3-08 | Depois do 2 |
| 19 | P3 | Limite de taxa nos 5 clientes (Last.fm, capas, MusicBrainz, ListenBrainz e iTunes) | R3-12 | Depois de 14 a 17 (mesmos arquivos) |
| 20 | P3 | Stories da Dupla com nomes longos | R2-04 | |
| 21 | P3 | Painel do som lê o motivo | R2-05 | |
| 22 | P3 | Cancelar o cálculo | R2-06 | |
| 23 | P3 | Match: escala da nota | R2-07 | Depois do 4 (faixas) |
| 24 | P3 | Vidro e transparência reduzida | R2-08 | |
| 25 | P3 | Paridade `nucleo.css` ↔ `styles.css` | R2-09 | |
| 26 | P3 | Paridade de tokens e escala de texto | R2-10 | |
| 27 | P4 | Normalização Unicode igual | R1-08 | Com a tabela de nomes nos dois lados |
| 28 | P4 | Datas: mesmo subconjunto ISO | R1-09 | Com a tabela de datas nos dois lados |
| 29 | P4 | Mensagem dos 64 MB e tabela de limites | R1-07 | Não iguala limites; a tabela documenta as diferenças esperadas, que o teste de contrato registra como exceção |
| 30 | P4 | Convite: música malformada recusa | R1-10 | |
| 31 | P4 | Convite de versão futura | R3-11 | Depois do 30 (mesmos arquivos) |
| 32 | P4 | Nomes e descrições das métricas | R3-10 | |
| 33 | P4 | `de_dict` recusa versão futura | R3-13 | |
| 34 | P4 | Hover protegido e flash do toque | R2-13 | |
| 35 | P4 | Textos do PC sem "describe()" | R2-14 | |
| 36 | P4 | Sobrescritas no fim dos CSS (um arquivo por PR) | R2-11 | Por último entre os de CSS (R2 §7) |

As dependências de arquivo dentro de cada rodada estão nos planos de cada uma (R1 §8, R2 §7 e §7 acima). Entre rodadas, os arquivos em comum são: `som.js` (14, 19, 21); `main.js` (3, 14, 22); `match-tela.js` (1, 3, 22, 23); `resultado.js` (6, 32); `VALIDACAO.md` (4, 5, 6); `generos.py` (10, 19); `convite.py`/`convite.js` (30, 31). Sair na ordem da tabela, rebaseando cada PR sobre o anterior. Os dois "+" juntam achados que mexem nos mesmos arquivos e no mesmo assunto; continuam sendo um assunto por PR.
