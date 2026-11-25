# Auditoria SyncUp — Rodada 2: design system, UI/UX e acessibilidade

| | |
|---|---|
| **Commit auditado** | `origin/main` = `de3ae1c5987fd8b0a03a8a2bfaca9d6c99512423` (merge do PR #44, que só acrescentou `docs/auditoria/rodada-1.md` sobre a v1.27). A `main` local foi atualizada com `git switch main` e `git pull --ff-only` antes de medir. |
| **Data** | 2026-11-25 |
| **Ambiente** | Windows 11, Windows PowerShell 5.1, Python 3.12.10 (`.venv`), pytest 8.3.5, Gradio 6.31.0, Playwright/Chromium, Node 26.13 |
| **Escopo** | Os 5 CSS, a hierarquia dos resultados, entrada e estados, stories/pôsteres/gráficos e acessibilidade, nas três superfícies (landing `site/`, app web `site/app/`, app para PC em Gradio). Só relatório: nenhum arquivo do app foi alterado. |
| **Dados** | Todos fictícios: as demos `site/app/demo-*.zip`, "Rafa", "Banda 0", "Orquestra Filarmonica Imaginaria…", arquivos gerados na hora numa pasta temporária. Nenhum histórico real. |
| **Capturas** | `docs/auditoria/rodada-2/` (só "antes": nada foi corrigido). |

## 1. Linha de base dos testes (antes de qualquer diagnóstico)

| Comando | Resultado | Tempo |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` | **295 passaram, 3 pulados, 17 desmarcados** (os mesmos pulados da Rodada 1: `pyarrow`/Parquet opcionais) | 81,5 s |
| `node --test tests/js/*.test.mjs` | **105 passaram**, 0 falharam | 2,4 s |
| `.venv\Scripts\python.exe -m pytest -m navegador -q -p no:cacheprovider` | **17 passaram** (Playwright/Chromium) | 35,7 s |

Igual à Rodada 1. Nenhuma falha.

> **Como rodar as evidências:** cada bloco `powershell` roda da raiz do repositório, colado inteiro no Windows PowerShell 5.1. Os blocos são 100% ASCII: os acentos da interface aparecem escapados pelo `ascii()` do Python (`\xe1` = á) e os seletores usam `.` no lugar da letra acentuada (`Seu hist.rico`). Os blocos com navegador servem `site/` localmente e cortam toda rede externa menos o `unpkg.com` (de onde vem o Preact), como o `tests/navegador/conftest.py`. Todos foram extraídos deste arquivo e rodados assim; as saídas abaixo são as obtidas. Se um bloco de navegador esgotar o tempo esperando o app desenhar, é o `unpkg.com` lento: rode de novo (aconteceu uma vez com dois blocos nesta rodada).

## 2. Status e cobertura por área

| Área | O que foi verificado | Como | Resultado | Achados |
|---|---|---|---|---|
| Tokens entre superfícies | cor, raio, espaço e tipo nos 5 CSS; `var()` sem definição por página | script estático | Duas famílias de tokens com os mesmos valores; nenhuma escala de tipo. (Nenhum `var()` sem definição numa página: observado num roteiro exploratório, sem bloco) | R2-10 |
| Regras duplicadas e anti-remendo | seletores repetidos, sobrescritas no fim do arquivo, cópia `nucleo.css` ↔ `styles.css` | script estático | Seção "9. Tema único" do `stories.css` reescreve 4 peças e os tamanhos do resumo; `nucleo.css` é cópia sem teste de igualdade | R2-09, R2-11 |
| Seletores mortos | web: 1.144 seletores casados em tempo de execução nos 4 modos + landing + Last.fm, em 1280 e 390 px; PC: classes `su-*` procuradas no Python e no `syncup.js` | Chromium + script | 2 mortos na web, 5 classes mortas no PC | R2-12 |
| `backdrop-filter` no celular | camadas com blur na tela, transparência reduzida, uso no fluxo × flutuante | Chromium (emulação) + leitura | Todo vidro flutua, menos 2 chips do PC; `.dock` ignora "transparência reduzida". **Sem medição em celular real.** | R2-08 |
| Hierarquia em 3 camadas | Wrapped, Dupla, Match, Batalha | capturas + leitura | As 3 camadas existem nos 4 modos (§2.1); a Dupla é a mais completa; o Match não explica a escala da nota | R2-07 |
| Progresso e duplo envio | duplo clique em "Ver um exemplo" nos 4 modos; selo "Lendo neste aparelho…" | Chromium | **Ok**: 1 cálculo por duplo clique (bloco do R2-06); o selo aparece com a CPU 20× mais lenta (observado, §4) | — |
| Cancelamento | botão durante o cálculo | Chromium | Só o Last.fm tem "Cancelar" | R2-06 |
| Vazio / insuficiente / indisponível / rede | 1 play e 20 plays; Last.fm fora do ar, limite e perfil vazio; som sem rede | Python, Node e Chromium | Last.fm: mensagens próprias. Wrapped com amostra mínima vira zeros; o som fica "Preparando…" | R2-01, R2-05 |
| Gestos e teclado dos stories | toque esquerda/direita, setas, espaço, Home/End | Chromium com toque emulado + leitura | **Ok** na web (observado, §4). No PC, o player recebe foco sem indicador | R2-03 |
| Nomes longos | pessoa 4–47 caracteres, artista 11–73 | Chromium, 390 px | Stories da Dupla vazam com pessoa de 47 (25 cabe) e artista de 73 (41 cabe); o limite exato fica entre esses pontos | R2-04 |
| Nitidez da exportação | tamanho do PNG do pôster | Chromium + leitura | **Ok**: 1080×1920 fixo, não depende do `devicePixelRatio` (observado, §4) | — |
| Eixos em tela estreita | gráficos da Dupla em 320, 390 e 1280 px | Chromium + leitura | **Ok**: rótulos em HTML, 0,75 rem, regra de 15% entre rótulos do eixo dos meses (observado, §4) | — |
| Contraste WCAG AA | texto fora dos stories (DOM); texto dos stories (pixels, com capa branca forçada); app para PC | Chromium | **Ok** fora dos stories (bloco de §4, com os limites do método); stories e app para PC observados sem bloco (§4) | — |
| Teclado e foco visível | Tab pela landing e pelo resultado da Dupla (1280 px), pelo resultado em 390 px e pelo app para PC | Chromium | **Ok** na web em 1280 px; em 390 px o foco fica sob a barra fixa (R2-02); 1 falha no PC (R2-03) | R2-02, R2-03 |
| `prefers-reduced-motion` | animações CSS ainda rodando 2,5 s depois de abrir landing, app e stories | Chromium | **Ok**: nenhuma. Movimento feito por JS não foi medido | — |
| ARIA | abas (`role=tablist`), player (`role=region` + `aria-roledescription`), menu (`role=dialog` + `inert` + Esc) | leitura + Chromium | **Ok** na web; `div` com `aria-label` sem papel no PC (R2-03) | R2-03 |
| Rolagem horizontal | telas de **resultado** dos 4 modos em 320/360/390 px (a landing já tem teste em 375 px) | Chromium | **Ok** na web: 0 px em todas. No app para PC a medida não vale (§5) | — |
| Arquivos de entrada do escopo | `envio.js` e `worker.js` (lidos, R2-06), `lastfm.js` (estados observados, §4), `chegada.js` e `entrada.js` (já cobertos por `tests/navegador/test_app.py:69-89`) | leitura + testes existentes | `opcoes.js` e `ui/meus_dados.py` **não foram auditados** nesta rodada (§5) | — |
| App para PC aberto | Wrapped e Dupla com os dados fictícios, ZIP quebrado, 1 play | Chromium | Ver R2-01, R2-03, R2-14; pendências da Rodada 1 fechadas em §5 | — |

### 2.1 Hierarquia dos resultados (3 camadas)

Avaliado nas capturas do resultado de exemplo em 1280 px (leitura, sem bloco próprio):

| Modo | Síntese principal | Explicação contextual | Detalhe sob demanda | Captura |
|---|---|---|---|---|
| Wrapped | story 1: horas de música e dias | os 15 stories, com a fila de títulos ao lado | `<details>` "Como o arquétipo foi calculado" | [`hierarquia-wrapped-desktop.png`](rodada-2/hierarquia-wrapped-desktop.png) |
| Dupla | story 1: % de escuta em comum, com o afinador | os 7 stories; abas "Rankings" e "Gráficos" | aba "Detalhes técnicos" | [`hierarquia-dupla-desktop.png`](rodada-2/hierarquia-dupla-desktop.png) |
| Batalha | "4 na arena" e o pódio no último story | um cartão por rodada ("Maratonista por um triz"…) | `<details>` "Placar completo" | [`hierarquia-batalha-desktop.png`](rodada-2/hierarquia-batalha-desktop.png) |
| Match | "Os duetos do grupo" e a nota de cada par | frase do nível + refrão e lado B | `<details>` "Com quem cada um mais combina" | [`hierarquia-match-desktop.png`](rodada-2/hierarquia-match-desktop.png) |

As três camadas existem nos quatro modos. A Dupla é a mais completa (abas com nome claro, "Detalhes técnicos" separado). A falha está no Match: a nota em % não tem escala e a frase explica o nível, não o número (R2-07). Os nomes da camada de detalhe variam por modo ("Detalhes técnicos", "Como … foi calculado", "Placar completo"); padronizar é opcional. A tela de Match do app para PC (`ui/match.py`) não foi avaliada (§5).

Correção de caminho do pedido: `tools/gerar_zip.py` não existe. O gerador de dados do repositório é `tools/gerar_dados_falsos.py`; esta rodada gerou os arquivos dentro de cada bloco.

## 3. Achados (ordem de impacto)

### R2-01 — Wrapped sem amostra mínima: 1 play vira um Wrapped completo com "0 horas" e arquétipo

- **Classificação:** Problema comprovado nos dois motores e na tela web (blocos abaixo); na tela do app para PC, observado sem bloco
- **Prioridade:** P2 (é o item "insuficiente diferente de 0%" desta rodada e acontece nos dois motores; o gatilho é um arquivo pequeno, menos comum que o uso normal)
- **Localização:**
  - Python: `wrapped.py:153` (`calcular_wrapped`, sem piso de plays nem de dias); PC: `ui/meu_wrapped.py:22`.
  - JS: `site/app/js/calculo.js:93` (`calcularWrapped`, idem).
  - Texto: `site/app/js/stories/slides.js:114` e `stories.py:132-133` ("em {n} dias com música", também com `n = 1`).
  - Contraste: o Match já recusa perfil vazio e a Dupla recusa dados insuficientes (R1-01, `analise.py:332`); o Wrapped não tem nada equivalente.
- **Evidência (motores):**

```powershell
@'
import json, os, subprocess, tempfile
from web import ponte
d = tempfile.mkdtemp()
for n, dias in [(1, 1), (20, 2)]:
    cam = os.path.join(d, f'h{n}.json')
    regs = [{'ts': f'2023-12-{29 + i % dias:02d}T{(3 + i) % 24:02d}:00:00Z', 'ms_played': 200000,
             'master_metadata_track_name': f'Faixa {i % 5}', 'master_metadata_album_artist_name': f'Banda {i % 3}',
             'spotify_track_uri': f'spotify:track:{i % 5}'} for i in range(n)]
    with open(cam, 'w') as f: json.dump(regs, f)
    py = ponte.wrapped([cam], 'Teste', {})['dados']
    saida = subprocess.run(['node', 'tests/js/rodar_wrapped.mjs', '{}', 'Teste', cam], capture_output=True, check=True)
    js = json.loads(saida.stdout.decode('utf-8'))['dados']
    for motor, r in [('Python', py), ('JS', js)]:
        a = r['arquetipos']['principal']
        print(f"{n} play(s), {motor}: horas {r['horas']:.2f}, dias com musica {r['dias_com_musica']}, "
              f"artistas {r['quantidade_artistas']}, arquetipo {ascii(a['nome']) if a else None}")
'@ | .venv\Scripts\python.exe -W ignore -
```

  Saída: 
  - `1 play(s), Python: horas 0.06, dias com musica 1, artistas 1, arquetipo 'Coruja'`
  - `1 play(s), JS: horas 0.06, dias com musica 1, artistas 1, arquetipo 'Coruja'`
  - `20 play(s), Python: horas 1.11, dias com musica 2, artistas 3, arquetipo 'Devoto(a)'`
  - `20 play(s), JS: horas 1.11, dias com musica 2, artistas 3, arquetipo 'Devoto(a)'`

- **Evidência (tela web):**

```powershell
@'
import functools, json, re, tempfile, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
arq = Path(tempfile.mkdtemp()) / 'Streaming_History_Audio_2023.json'
arq.write_text(json.dumps([{'ts': '2023-12-30T03:00:00Z', 'ms_played': 200000, 'master_metadata_track_name': 'Faixa Ficticia',
                            'master_metadata_album_artist_name': 'Banda Ficticia', 'spotify_track_uri': 'spotify:track:x'}]))
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
    pg.goto(f'{URL}/app/#wrapped')
    tela = pg.get_by_role('region', name=re.compile('Seu hist.rico'))
    tela.locator('input[type=file]').first.set_input_files(str(arq)); pg.wait_for_timeout(1500)
    pg.get_by_role('button', name=re.compile('Montar meu Wrapped')).click()
    pl = pg.locator('.resultado .st-player:visible').first; pl.wait_for(timeout=30000); pl.focus(); pg.keyboard.press(' ')
    pg.wait_for_timeout(2500)
    print('stories:', pl.locator('.st-contador').inner_text())
    print('1o story:', ascii(' '.join(pl.locator('.st-slot.ativo').inner_text().split())))
    pg.keyboard.press('End'); pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(2500)
    print('penultimo:', ascii(' '.join(pl.locator('.st-slot.ativo').inner_text().split())[:120]))
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `stories: 1/11`
  - `1o story: 'SYNCUP WRAPPED \xb7 VIDA TODA Voc\xea, sua vida no Spotify dez/2023 \u2192 dez/2023 0 horas de m\xfasica Isso d\xe1 0,0 dias inteiros sem parar, em 1 dias com m\xfasica.'`
  - `penultimo: 'SEU ARQU\xc9TIPO DE ESCUTA \U0001f989 CORUJA 100,0% dos seus plays foram entre 0h e 5h59. Devoto(a) Explorador(a) Arqu\xe9tipos s\xe3o reg'`

  Captura: [`wrapped-1-play-celular.png`](rodada-2/wrapped-1-play-celular.png) e [`wrapped-1-play-arquetipo-celular.png`](rodada-2/wrapped-1-play-arquetipo-celular.png). No app para PC, o mesmo arquivo mostrou o mesmo primeiro story ("0 horas de música … em 1 dias com música") numa rodada exploratória sem bloco próprio; pelo código, o PC usa o mesmo `calcular_wrapped` do bloco de motores e o mesmo texto (`stories.py:132-133`).
- **Impacto:** quem testa com um arquivo pequeno (um JSON parcial, a primeira semana de conta) recebe "0 horas de música", "artista do coração", "fiel" e um arquétipo com "100,0% dos seus plays" tirados de 1 a 20 plays, sem nenhum aviso. É um resultado sem base nos dados, apresentado como retrato da "vida toda".
- **Solução proposta:** calcular, junto do Wrapped, se a amostra é suficiente (plays válidos e dias com música). Abaixo do piso, mostrar um estado "histórico curto demais" com o que fazer (enviar todas as partes, pedir o Histórico Estendido) em vez dos stories; ou, num meio-termo, esconder os stories de ranking e arquétipo e avisar. O piso deve ser decidido com dados e documentado em `VALIDACAO.md`; esta auditoria não propõe número. Corrigir também o plural "1 dias".
- **Testes necessários:** Python (`tests/test_wrapped.py` ou equivalente) e JS (`tests/js/`) com 1 play e 20 plays; paridade em `tests/test_paridade_wrapped.py` (mesmo veredito de amostra nos dois motores); Playwright: o estado "curto demais" aparece no lugar dos stories.
- **Critério de aceitação:** com o arquivo de 1 play, o bloco de tela web não mostra mais o story "0 horas de música" nem o arquétipo, e sim o estado de histórico curto (o texto exato fica para o PR); o bloco de motores devolve, nos dois motores, um sinal de amostra insuficiente; no app para PC, o mesmo arquivo mostra o mesmo estado (conferir no navegador, como no bloco do R2-14); e "1 dias" não aparece. O caso de 20 plays segue o piso que for decidido e documentado.

### R2-02 — No celular, o foco do teclado fica inteiro atrás da barra de navegação fixa

- **Classificação:** Problema comprovado (WCAG 2.2, critério 2.4.11 "Foco não obscurecido (mínimo)", nível AA)
- **Prioridade:** P2
- **Localização:** `site/app/app.css:37` (abaixo de 900 px, `.nav-app` vira barra fixa em `inset: auto 0 0`) e `site/app/app.css:502` (o `.dock` sobe para cima dela). Não há `scroll-padding-bottom` (nem `scroll-padding-block`) em nenhum CSS; o único `scroll-padding` é o `-inline` das sub-abas (`app.css:253`); o navegador rola o elemento focado até a borda de baixo da janela, que fica sob a barra.
- **Evidência:**

```powershell
@'
import functools, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
COBERTO = """() => { const e = document.activeElement; if (!e || e === document.body || e.closest('.nav-app')) return null; const r = e.getBoundingClientRect();
  const n = document.querySelector('.nav-app').getBoundingClientRect();
  return r.top >= n.top - 1 && r.bottom <= n.bottom + 1 ? (e.innerText || e.tagName).split('\\n').slice(0, 3).join(' ') : null; }"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for modo in ['wrapped', 'dupla']:
        pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
        pg.goto(f'{URL}/app/#{modo}'); pg.get_by_role('button', name='Ver um exemplo').click()
        pl = pg.locator('.resultado .st-player:visible').first; pl.wait_for(timeout=45000); pl.focus()
        cobertos = []
        for _ in range(80):
            pg.keyboard.press('Tab'); pg.wait_for_timeout(60)
            c = pg.evaluate(COBERTO)
            if c: cobertos.append(c)
        print(modo, '- paradas de Tab: 80, foco inteiro sob a barra:', len(cobertos), [ascii(c) for c in cobertos[:3]])
        pg.close()
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `wrapped - paradas de Tab: 80, foco inteiro sob a barra: 3 ["'Op\\xe7\\xf5es de dados per\\xedodo, fuso e filtros'", "'Op\\xe7\\xf5es de dados per\\xedodo, fuso e filtros'", "'Op\\xe7\\xf5es de dados per\\xedodo, fuso e filtros'"]`
  - `dupla - paradas de Tab: 80, foco inteiro sob a barra: 17 ["'3 M Meio-Dia'", "'4 \\xc1D \\xc1gua Doce'", "'5 SB Sil\\xeancio Bom'"]`

  (No Wrapped, as 80 paradas dão a volta na página e passam 3 vezes pelo mesmo "Opções de dados".)

  Captura: [`foco-coberto-celular.png`](rodada-2/foco-coberto-celular.png) (o foco está no item 3 do top de músicas da Rafa, "Meio-Dia", inteiro atrás da barra "Dupla · Wrapped · Batalha · Match"; nada focado aparece na tela).
- **Impacto:** quem navega por teclado no celular ou no tablet (teclado Bluetooth, acesso por switch) perde de vista onde está, em listas longas como os rankings da Dupla.
- **Solução proposta:** um `scroll-padding-bottom` no `html` igual à altura da barra mais o `safe-area` (e mais a altura do `.dock` quando ele está visível), na mesma regra de mídia que fixa a barra em `app.css:37`. Um token para a altura da barra evita repetir o número.
- **Testes necessários:** Playwright (`tests/navegador/test_app.py`): em 390 px, depois de N Tabs pelo resultado da Dupla, nenhum foco fica inteiro sob `.nav-app`.
- **Critério de aceitação:** o bloco acima imprime `0` nas duas linhas.

### R2-03 — App para PC: o player de stories recebe foco sem nenhum indicador e tem `aria-label` numa `div` sem papel

- **Classificação:** Problema comprovado (WCAG 2.4.7 "Foco visível" e 4.1.2 "Nome, função, valor")
- **Prioridade:** P2
- **Localização:** `stories.py:383`, `:527` e `:625` (`<div class="su-stories" data-stories tabindex="0" aria-label="…">`, sem `role`); `syncup.js:271` (as setas funcionam nele); `styles.css:49-51` (a lista de `:focus-visible` não inclui `.su-stories`). Na web, o mesmo player usa `role="region"` e `aria-roledescription="stories"` (`site/app/js/stories/player.js:175-176`) e tem contorno de foco (`site/app/stories.css:12`).
- **Evidência:** o bloco do R2-14 abre o app para PC com os dados fictícios do Wrapped e da Dupla, percorre 70 paradas de Tab e compara o estilo de cada elemento focado com o mesmo elemento sem foco. Os players alcançados são os de `stories.py:383` ("Wrapped de …"; a aba Dupla também mostra o Wrapped de cada pessoa); os de `:527` (Match) e `:625` ("Sintonia de …") têm a mesma marcação, mas não foram alcançados nas 70 paradas. Saída: 
  - `Wrapped - 70 Tabs; sem mudanca visual ao focar: ["'su-stories Wrapped de Ana (fict\\xedcia) role=null'"] | [data-testid=file] no DOM: 0 | rolagem lateral em 360 px: 0`
  - `Dupla - 70 Tabs; sem mudanca visual ao focar: ["'su-stories Wrapped de Ana (fict\\xedcia) role=null'", "'su-stories Wrapped de Bruno (fict\\xedcio) role=null'"] | [data-testid=file] no DOM: 0 | rolagem lateral em 360 px: 0`
  Relacionado: os botões de toque invisíveis do mesmo player (`.su-tap`, `syncup.js:225-229`) têm como único sinal de foco um fundo branco a 6% (`styles.css:558`, `outline: none`), que o detector conta como mudança, mas que dificilmente passa no contraste de 3:1 exigido para indicadores (WCAG 1.4.11); não foi medido.
- **Impacto:** quem usa teclado no app para PC chega ao player, as setas funcionam, mas não há sinal de onde o foco está. O leitor de tela pode ignorar o `aria-label` (uma `div` sem papel não tem nome acessível pela especificação ARIA).
- **Solução proposta:** acrescentar `role="region" aria-roledescription="stories"` às três `div` de `stories.py`, como na web, e `.su-stories:focus-visible` à regra de `styles.css:49`.
- **Testes necessários:** Python (`tests/test_stories.py` ou equivalente): o HTML gerado tem `role="region"`. Playwright no app para PC (como o bloco do R2-14): o player focado muda de aparência.
- **Critério de aceitação:** no bloco do R2-14, a lista "sem mudança visual ao focar" fica vazia.

### R2-04 — Stories da Dupla: nomes longos empurram o texto para fora da moldura

- **Classificação:** Problema comprovado
- **Prioridade:** P3 (nomes de artista com mais de ~70 caracteres são raros; nomes de pessoa com ~47, nem tanto)
- **Localização:** `site/app/js/stories/dupla.js:25-37` (abertura: nomes + afinador + nota) e `:56-62` (frente a frente); `site/app/stories.css:215-219` (`.st-frente b` a `8cqw`, quebra com `overflow-wrap: anywhere`, mas o slide não encolhe). O Wrapped já resolve o mesmo problema no resumo com `useCaber` (`site/app/js/stories/slides.js:352`, o fator `--e` em `stories.css:488-501`), e o pôster corta com reticências (`site/app/js/poster.js:256-262`).
- **Evidência:**

```powershell
@'
import functools, json, random, re, tempfile, threading, zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
d = Path(tempfile.mkdtemp())
def zip_(nome, semente, art):
    rnd = random.Random(semente); regs = []
    for i in range(400):
        regs.append({'ts': f'2023-{1 + i % 12:02d}-{1 + i % 27:02d}T{i % 24:02d}:00:00Z', 'ms_played': 200000,
                     'master_metadata_track_name': f'Faixa {rnd.randrange(30)}', 'spotify_track_uri': f'spotify:track:{i % 40}',
                     'master_metadata_album_artist_name': art if i % 3 == 0 else f'Banda {rnd.randrange(12)}'})
    with zipfile.ZipFile(d / nome, 'w') as z: z.writestr('Streaming_History_Audio_2023.json', json.dumps(regs))
    return str(d / nome)
FORA = """() => { const p = [...document.querySelectorAll('.st-player')].find(e => e.offsetParent);
  const f = p.querySelector('.st-slot.ativo').getBoundingClientRect(); const out = [];
  p.querySelectorAll('.st-slot.ativo *').forEach(e => { if (e.childElementCount || !e.textContent.trim() || e.closest('.st-avatares')) return;
    const b = e.getBoundingClientRect(); const px = Math.max(f.top - b.top, b.bottom - f.bottom, f.left - b.left, b.right - f.right);
    if (b.width && px > 1) out.push(e.textContent.trim().slice(0, 18) + ' ' + Math.round(px) + 'px'); });
  return [p.querySelector('.st-slot.ativo section').className.split(' ').find(c => c.startsWith('s-')), out]; }"""
CASOS = [('Rafa', 'Lu', 'Banda Longa'), ('Rafa', 'Lu', 'Artista Com Nome de Quarenta Caracteres X'),
         ('Rafa', 'Lu', 'Orquestra Filarmonica Imaginaria de Instrumentos Antigos e Sintetizadores'),
         ('Maria Eduarda Albuquerque', 'Ana Clara Vasconcelos', 'Banda Longa'),
         ('Maria Eduarda Albuquerque Figueiredo dos Santos', 'Ana Clara Vasconcelos Bittencourt', 'Banda Longa')]
with sync_playwright() as p:
    b = p.chromium.launch()
    for k, (pa, pb, art) in enumerate(CASOS):
        pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
        pg.goto(f'{URL}/app/#dupla')
        pessoas = pg.locator('#principal section.pessoa:visible')
        for j, nome in enumerate([pa, pb]):
            pessoas.nth(j).locator('input.entrada').fill(nome)
            pessoas.nth(j).locator('input[type=file]').set_input_files(zip_(f'{k}-{j}.zip', j, art))
        pg.wait_for_timeout(2000); pg.get_by_role('button', name=re.compile('Comparar hist')).first.click()
        pl = pg.locator('.resultado .st-player:visible').first; pl.wait_for(timeout=45000); pl.focus(); pg.keyboard.press(' ')
        ruins = []
        for _ in range(int(pl.locator('.st-contador').inner_text().split('/')[1])):
            pg.wait_for_timeout(250); s, o = pg.evaluate(FORA)
            if o: ruins.append(f'{s}: ' + ', '.join(ascii(x) for x in o[:3]))
            pg.keyboard.press('ArrowRight')
        print(f'pessoa {len(pa)}/{len(pb)}, artista {len(art)} caracteres ->', ruins or 'nada fora da moldura')
        pg.close()
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `pessoa 4/2, artista 11 caracteres -> nada fora da moldura`
  - `pessoa 4/2, artista 41 caracteres -> nada fora da moldura`
  - `pessoa 4/2, artista 73 caracteres -> ["s-frente: 'Frente a frente 6px', 'Rafa 4px', 'Lu 48px'"]`
  - `pessoa 25/21, artista 11 caracteres -> nada fora da moldura`
  - `pessoa 47/33, artista 11 caracteres -> ["s-abertura: 'Conta s\\xf3 o que voc 8px'"]`

  Capturas: [`dupla-nome-longo-celular.png`](rodada-2/dupla-nome-longo-celular.png) (tirada numa rodada exploratória com os dois nomes longos juntos, pessoa de 47 e artista de 83 caracteres; "Frente a frente": o primeiro cartão passa por baixo da barra de progresso e o contador "3/7" fica em cima do nome) e, para comparar, [`poster-dupla-nome-longo.png`](rodada-2/poster-dupla-nome-longo.png) (o pôster corta com reticências e fica certo).
- **Impacto:** o print do story, feito para postar, sai com texto cortado em cima e em baixo e com o contador por cima do nome.
- **Solução proposta:** reaproveitar o `useCaber` do resumo do Wrapped nos slides "abertura" e "frente" da Dupla (encolher pelo fator `--e` quando o conteúdo passa da moldura) (sem reticências, seguindo a decisão "Nada de reticências" que o projeto tomou para o resumo do Wrapped, `stories.css:476-477`; estender a regra à Dupla é sugestão desta auditoria).
- **Testes necessários:** Playwright: com os casos de 47 (pessoa) e 73 (artista) caracteres, nenhum texto fora da moldura nos 7 slides.
- **Critério de aceitação:** as cinco linhas do bloco acima dizem "nada fora da moldura".

### R2-05 — Sem rede, o painel do som fica em "Preparando o som…" ao lado do aviso de que o som falhou

- **Classificação:** Problema comprovado
- **Prioridade:** P3 (estado de falha de rede, um dos estados que esta rodada pede para separar)
- **Localização:** `site/app/js/stories/palco.js:47` (o texto depende só de `comSom`, que é fixo: `wrapped.js:173`, `resultado.js:157`, `match-tela.js:67`, `batalha-tela.js:117`); `site/app/js/som.js:178` (o aviso visto, quando nenhum trecho chega) e `:140` (o estado `carregando | tocando | sem` é local do componente; o `useSom()` de `:82-86` só compartilha trecho, tocando e mudo). O mesmo `sem` também é usado quando o navegador bloqueia o som automático (`:155`), caso que o botão "Ligar capas e som" resolve, e quando `iniciarSom` falha (`:159`, "Não deu para preparar o som").
- **Evidência:** bloco do R2-06 (Wrapped de exemplo, rede externa cortada, leitura depois de 15 s). Saída: 
  - `  painel do som: 'Preparando o som\u2026' | aviso: 'N\xe3o deu para buscar os trechos (sem internet?). Os stories seguem sem som.'`. Captura: [`som-preparando-sem-rede.png`](rodada-2/som-preparando-sem-rede.png) (só o painel; o aviso contrário está na saída do bloco).
- **Impacto:** a tela diz duas coisas opostas ao mesmo tempo: "Preparando o som…" (espere) e "Os stories seguem sem som" (desista). Quem está sem internet fica esperando um som que não vem.
- **Solução proposta:** levar para o estado compartilhado (`estadoSom`, `som.js:79`) o motivo do "sem som" e fazer o `Agora` do `palco.js` ler esse motivo: "Stories sem som" quando os trechos não chegaram ou o som não pôde ser preparado; quando foi o navegador que bloqueou, um texto que aponte para "Ligar capas e som". Nenhum dos três casos pode continuar em "Preparando o som…".
- **Testes necessários:** Playwright: com a rede externa cortada, depois que o aviso aparece, o painel não diz "Preparando".
- **Critério de aceitação:** no bloco do R2-06, a linha do som mostra "Stories sem som".

### R2-06 — Não dá para cancelar o cálculo da Dupla, Batalha, Match e Wrapped

- **Classificação:** Oportunidade de melhoria
- **Prioridade:** P3 (com as demos o cálculo leva segundos; com um histórico de vários anos no celular pode levar bem mais, e a única saída é trocar de modo ou recarregar)
- **Localização:** `site/app/js/main.js:37` e `:83` e `site/app/js/wrapped.js:166` (fase "processando": só texto e um giro); na Batalha e no Match o Worker tem `cancelar()` (`batalha-tela.js:147`, `match-tela.js:124`), chamado internamente (troca de modo, nova rodada, erro; `batalha-tela.js:152-175`, `match-tela.js:128-137`), nunca por um botão; na Dupla e no Wrapped o cálculo usa `rodarNoWorker` (`site/app/js/worker.js:39`, chamado em `main.js:20` e `wrapped.js:22`), que não devolve nenhum jeito de cancelar. O único botão "Cancelar" do app é o do Last.fm (`site/app/js/envio.js:75`).
- **Evidência (vale também para o R2-05):**

```powershell
@'
import functools, re, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
CONTA = 'window.__w = 0; const W = window.Worker; window.Worker = class extends W { constructor(...a) { super(...a); window.__w++; } };'
with sync_playwright() as p:
    b = p.chromium.launch()
    for modo in ['wrapped', 'dupla', 'batalha', 'match']:
        pg = b.new_page(viewport={'width': 1280, 'height': 900})
        pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
        pg.add_init_script(CONTA); pg.goto(f'{URL}/app/#{modo}'); pg.wait_for_timeout(800)
        antes = pg.evaluate('window.__w')
        pg.get_by_role('button', name='Ver um exemplo').dblclick(); pg.wait_for_timeout(100)
        cancelar = pg.get_by_role('button', name='Cancelar').locator('visible=true').count()
        pg.locator('.resultado .st-player:visible').first.wait_for(timeout=45000)
        print(modo, '- calculos pelo duplo clique:', pg.evaluate('window.__w') - antes, '| botao Cancelar durante o calculo:', cancelar)
        if modo == 'wrapped':
            pg.wait_for_timeout(15000)
            print('  painel do som:', ascii(pg.locator('.palco-agora:visible .palco-faixa small').first.inner_text()),
                  '| aviso:', ascii(pg.get_by_text(re.compile('buscar os trechos')).first.inner_text()))
        pg.close()
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `wrapped - calculos pelo duplo clique: 1 | botao Cancelar durante o calculo: 0`
  - `  painel do som: 'Preparando o som\u2026' | aviso: 'N\xe3o deu para buscar os trechos (sem internet?). Os stories seguem sem som.'`
  - `dupla - calculos pelo duplo clique: 1 | botao Cancelar durante o calculo: 0`
  - `batalha - calculos pelo duplo clique: 1 | botao Cancelar durante o calculo: 0`
  - `match - calculos pelo duplo clique: 1 | botao Cancelar durante o calculo: 0`
- **Impacto:** quem enviou o arquivo errado ou cansou de esperar não tem um botão para parar. O duplo envio, por outro lado, está bem resolvido (1 cálculo por duplo clique).
- **Solução proposta:** um botão "Cancelar" ao lado do "Lendo os históricos e calculando a sintonia…", com a mesma aparência do botão do Last.fm, que volta à fase inicial. Na Batalha e no Match ele chama o `cancelar()` que já existe; na Dupla e no Wrapped o `rodarNoWorker` precisa passar a aceitar um `AbortSignal` (ou devolver `cancelar`, como o `abrirWorker` de `worker.js:10`). Atenção: os bytes dos arquivos vão para o Worker como transferíveis (`main.js:20`, `wrapped.js:22`); depois de cancelar, a tela precisa ler os arquivos de novo (ou mandar uma cópia), senão o segundo envio quebra.
- **Testes necessários:** Playwright: clicar em "Cancelar" durante o cálculo volta à tela de envio sem erro no console; JS (`tests/js`): o `rodarNoWorker` rejeita com `AbortError` e encerra o Worker quando o sinal é abortado.
- **Critério de aceitação:** com a CPU desacelerada (CDP `Emulation.setCPUThrottlingRate`), enquanto `.processando` está na tela, há um botão "Cancelar" nos quatro modos, e clicar nele volta à tela de envio. (A amostra de 100 ms do bloco acima mostra que hoje não há botão, mas não serve de critério com um cálculo rápido.)

### R2-07 — Match: a nota em % não diz qual é a escala, e 7,3% aparece como "Boa compatibilidade"

- **Classificação:** Oportunidade de melhoria (hierarquia: falta a camada de explicação da síntese)
- **Prioridade:** P3
- **Localização:** `site/app/js/match-tela.js:35` (nota grande + nível), `:76` ("Média dos pares"), `:20` (o único aviso: "compara só os rankings"); faixas em `site/app/js/match.js:15-21` (25% já é "Sintonia rara", 5% é "Boa"). A barra embaixo da nota mostra os **artistas em comum** (Jaccard, `site/app/js/stories/match.js:15-20`), não a nota.
- **Evidência:**

```powershell
@'
import functools, re, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
    pg.goto(f'{URL}/app/#match'); pg.get_by_role('button', name='Ver um exemplo').click()
    pg.locator('.dueto:visible').first.wait_for(timeout=45000)
    for par in pg.locator('.dueto-par:visible').all():
        print('nota:', ascii(' '.join(par.locator('.dueto-nota').inner_text().split())), '| frase:', ascii(par.locator('.dueto-frase').inner_text()),
              '| barra:', ascii(par.locator('.faixas').get_attribute('aria-label')))
    texto = pg.locator('.resultado:visible').first.inner_text()
    print('a tela fala da escala da nota?', any(t in texto for t in ['de 100', '25%', 'escala']) or bool(re.search('m.ximo', texto)))
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `nota: '7,3% Boa compatibilidade' | frase: 'Uma base em comum para come\xe7ar a trocar m\xfasicas.' | barra: 'Faixas de Rafa e Teo: o trecho do meio s\xe3o os 6 artistas em comum'`
  - `nota: '17,9% Alta compatibilidade' | frase: 'V\xe1rios favoritos em comum, com espa\xe7o para descobertas.' | barra: 'Faixas de Lu e Nina: o trecho do meio s\xe3o os 16 artistas em comum'`
  - `a tela fala da escala da nota? False`

  Captura: [`match-dueto-desktop.png`](rodada-2/match-dueto-desktop.png).
- **Impacto:** "7,3%" se lê como "quase nada" (de 100), mas o nível ao lado diz "Boa". A frase explica o nível, não o número, e a barra logo abaixo mede outra coisa. A síntese e a explicação brigam. (O tamanho da amostra por trás da nota é outro problema, já registrado no R1-02.)
- **Solução proposta:** uma linha de contexto junto da nota, por exemplo "Nesta escala, 25% já é sintonia rara", ou trocar o número por uma régua com as cinco faixas e a posição do par. A explicação técnica (cosseno entre os rankings de artistas ponderados, `site/app/js/match.js:2` e `:110-111`; a barra é outra medida, o Jaccard dos artistas, `:122`) vai para um `<details>` "Como a nota é calculada", como o Wrapped faz com o arquétipo.
- **Testes necessários:** Playwright: cada `.dueto-par` tem um elemento próprio de escala que cita o limite da faixa mais alta. Sem mudança de cálculo, sem paridade.
- **Critério de aceitação:** esse elemento existe em todos os pares do exemplo. (O detector do bloco acima é só um indício: "25%" poderia aparecer por acaso numa nota.)

### R2-08 — Vidro: o `.dock` ignora "transparência reduzida", há 6 camadas com blur nos stories no celular, e o PC usa blur em chips no fluxo

- **Classificação:** Problema comprovado na parte do `.dock` (ignora a preferência do sistema, medido no Chromium); o custo de GPU das camadas é só Risco potencial (não medido em celular real)
- **Prioridade:** P3
- **Localização:**

  | Peça | Arquivo | Blur | Flutua? | Fallback de transparência reduzida |
  |---|---|---|---|---|
  | `.nav-app` (barra) | `site/app/app.css:24` | 20 px, saturate 150% | sim (fixa) | sim (`:60`) |
  | `.dock` | `site/app/app.css:486-488` | **32 px, saturate 200%** | sim (fixa) | **não** |
  | `.vidro-ctrl` (barra, pausa e os 2 botões ocultos de 2×2 px) | `site/app/stories.css:16` | 16 px | sim | sim (`:306-307`) |
  | `.topo-barra` (landing) | `site/estilo.css:93` | 24 px | sim | sim (`:105`) |
  | `.palco-placa` (landing, 359×588 px no celular, sobre imagens já com `filter: blur(64px)` em `estilo.css:137`) | `site/estilo.css:437-438` | 28 px, saturate 185% | sim | sim (`:440`) |
  | `.su-nav > .tab-wrapper` (PC) | `styles.css:76-78` | 18 px | sim (sticky) | não há nenhum no `styles.css` |
  | `.su-chips span`, `.su-match-card .su-chip` (PC) | `styles.css:163`, `:650` | 6 px | **não** (chips no fluxo, `componentes.py:319-330`) | não |
- **Evidência:**

```powershell
@'
import functools, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
CAMADAS = """() => [...document.querySelectorAll('*')].filter(e => { const c = getComputedStyle(e), r = e.getBoundingClientRect();
  return c.backdropFilter !== 'none' && r.width && r.bottom > 0 && r.top < innerHeight && c.visibility !== 'hidden' && +c.opacity > 0; })
  .map(e => String(e.className).split(' ').slice(0, 2).join('.') + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for transp in ['no-preference', 'reduce']:
        ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page()
        pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
        ctx.new_cdp_session(pg).send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-transparency', 'value': transp}]})
        pg.goto(f'{URL}/app/#wrapped'); pg.get_by_role('button', name='Ver um exemplo').click()
        pl = pg.locator('.resultado .st-player:visible').first; pl.wait_for(timeout=45000); pl.scroll_into_view_if_needed(); pg.wait_for_timeout(1500)
        print(transp, '- stories:', pg.evaluate(CAMADAS))
        pg.goto(URL + '/'); pg.wait_for_timeout(1500)
        print(transp, '- landing:', pg.evaluate(CAMADAS))
        ctx.close()
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `no-preference - stories: ['nav-app 390x65', 'st-barra.vidro-ctrl 329x13', 'st-botao.vidro-ctrl 2x2', 'st-botao.vidro-ctrl 2x2', 'st-botao.st-pausa 44x44', 'dock.visivel 195x62']`
  - `no-preference - landing: ['topo-barra 366x64', 'palco-placa 359x588', 'st-barra.vidro-ctrl 286x12']`
  - `reduce - stories: ['dock.visivel 195x62']`
  - `reduce - landing: []`
- **Impacto:** com "transparência reduzida" ligada no sistema, o `.dock` continua borrado (é a única peça da web que esquece a preferência). Com os stories na tela do celular há 6 camadas com blur: 4 no player (barra de progresso, pausa e dois botões de 2×2 px que só aparecem com foco, recortados por `clip-path`) sobre um fundo que muda a cada slide, mais a barra de navegação e o `.dock` sobre a página. No PC, os chips de blur no fluxo contrariam a regra do projeto (vidro só no que flutua). O efeito em frames por segundo **não foi medido**: precisa de gravação num celular de gama média (a emulação do Chromium no desktop não mede GPU).
- **Solução proposta:** acrescentar o `.dock` à regra de `prefers-reduced-transparency` (e ao `@supports not`); opcionalmente, tirar o `backdrop-filter` dos `.st-botao.sr-only-foco` enquanto estão ocultos (limpeza sem custo medido); trocar o blur dos chips do PC por fundo sólido. Antes de mexer no raio dos outros, gravar o Performance do DevTools num celular real.
- **Testes necessários:** Playwright: com `prefers-reduced-transparency: reduce`, nenhuma camada com `backdrop-filter` na tela. Gravação manual em celular (fica registrada no PR).
- **Critério de aceitação:** a linha `reduce - stories` do bloco acima fica vazia.

### R2-09 — `nucleo.css` é uma cópia de 72 regras do `styles.css` sem teste de igualdade, e parte dela é anulada pelo `stories.css`

- **Classificação:** Risco potencial (deriva entre PC e web)
- **Prioridade:** P3
- **Localização:** `site/app/nucleo.css` (107 linhas); `tests/test_web.py:45` (o teste só confere se cada classe `su-` usada tem regra, não se a regra é a mesma). A animação de `.su-js .su-story.ativo` (`nucleo.css:63`) e a regra `.su-story::before` (`:64`, blur de 30 px animado sem fim) são desligadas logo depois por `site/app/stories.css:32-33`. A cópia foi uma decisão do projeto: o comentário de `tests/test_web.py:46` diz "O nucleo.css é um recorte do styles.css"; então a proposta não é juntar os arquivos.
- **Evidência:**

```powershell
@'
import re, collections
def regras(arq):
    t = re.sub(r'/\*.*?\*/', '', open(arq, encoding='utf-8').read(), flags=re.S)
    t = re.sub(r'@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', t)
    d = collections.defaultdict(list)
    for m in re.finditer(r'([^{}@;]+)\{([^{}]*)\}', t):
        d[' '.join(m.group(1).split())].append(re.sub(r'\s+', '', m.group(2)).rstrip(';'))
    return d
n, s = regras('site/app/nucleo.css'), regras('styles.css')
iguais = [k for k in n if k in s and any(c in s[k] for c in n[k])]
diferentes = [k for k in n if k in s and k not in iguais]
print('seletores no nucleo.css:', len(n), '| iguais ao styles.css:', len(iguais), '| mesmo seletor, corpo diferente:', len(diferentes), '| so no nucleo:', len(n) - len(iguais) - len(diferentes))
print('diferentes:', diferentes)
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `seletores no nucleo.css: 82 | iguais ao styles.css: 72 | mesmo seletor, corpo diferente: 7 | so no nucleo: 3`
  - `diferentes: [':root', '.su-race', '.su-race-progress::before', '.su-stories', '.su-stories:not(.su-js) .su-story', '.su-arch-detail', '.su-arch-detail li']`
  Leitura da saída: os 3 "só no núcleo" não faltam no `styles.css`: são listas de seletores separadas por vírgula que o script trata como uma chave só (por exemplo `.su-race-progress:focus-visible`, que no `styles.css:49-51` está numa lista maior). O script também junta regras de dentro e de fora de `@media`; os números são uma aproximação, e o teste proposto deve comparar regra a regra.
- **Impacto:** nenhum hoje para o usuário. Uma correção feita no `styles.css` (contraste, foco) não chega à web, e o contrário também, sem nenhum teste avisar; e quem lê o `nucleo.css` vê animações que nunca rodam.
- **Solução proposta:** um teste de paridade em `tests/test_web.py`: cada seletor do `nucleo.css` que também existe no `styles.css` tem o mesmo corpo, salvo uma lista curta de diferenças intencionais escrita no teste (hoje 7). Tirar do `nucleo.css` só o que o `stories.css` anula: a declaração `animation`/`background-size` de `:63` (o `display: flex` da mesma regra precisa ficar, senão o slide ativo some, porque `:62` esconde todos) e a regra `.su-story::before` de `:64`.
- **Testes necessários:** o próprio teste novo (Python).
- **Critério de aceitação:** o teste passa na `main` com a lista de exceções e falha se uma regra copiada mudar só de um lado.

### R2-10 — Duas famílias de tokens com os mesmos valores, sem teste que as mantenha iguais, e nenhuma escala de tipo

- **Classificação:** Oportunidade de melhoria
- **Prioridade:** P3
- **Localização:** `styles.css:6-19` (`--su-bg`, `--su-card`, `--su-green`, `--su-sub`, `--su-radius`…) × `site/estilo.css:3-23` (`--sup-1`, `--sup-2`, `--verde`, `--sub`, `--r-vidro`…); `site/app/nucleo.css:4` faz a ponte (`--su-green: var(--verde)`). A escala de espaço existe só no app web (`site/app/app.css:5`, `--e1` a `--e7`).
- **Evidência:**

```powershell
@'
import re, collections
F = ['styles.css', 'site/app/app.css', 'site/app/stories.css', 'site/estilo.css', 'site/app/nucleo.css']
cores = collections.defaultdict(set)
for f in F:
    bruto = open(f, encoding='utf-8').read(); t = re.sub(r'/\*.*?\*/', '', bruto, flags=re.S)
    fora_root = re.sub(r':root\s*\{[^}]*\}', '', t)
    raios = {r.strip() for r in re.findall(r'border-radius\s*:\s*([^;}]+)', t) if 'var(' not in r}
    fs = re.findall(r'font-size\s*:\s*([^;}]+)', t)
    print(f'{f}: {bruto.count(chr(10))} linhas, {len(set(re.findall(r"(--[\w-]+)\s*:", t)))} tokens, '
          f'{len(re.findall(r"#[0-9a-fA-F]{3,8}", fora_root))} cores hex fora do :root, {len(raios)} raios literais diferentes, '
          f'font-size {len(fs)} ({sum("var(" in x for x in fs)} com var)')
    for nome, val in re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\b', t): cores[val.lower()].add(nome)
print('mesma cor, nomes diferentes:', {v: sorted(n) for v, n in cores.items() if len(n) > 1})
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `styles.css: 728 linhas, 14 tokens, 96 cores hex fora do :root, 28 raios literais diferentes, font-size 122 (0 com var)`
  - `site/app/app.css: 633 linhas, 25 tokens, 18 cores hex fora do :root, 12 raios literais diferentes, font-size 68 (0 com var)`
  - `site/app/stories.css: 501 linhas, 8 tokens, 50 cores hex fora do :root, 15 raios literais diferentes, font-size 110 (15 com var)`
  - `site/estilo.css: 447 linhas, 39 tokens, 17 cores hex fora do :root, 13 raios literais diferentes, font-size 53 (0 com var)`
  - `site/app/nucleo.css: 107 linhas, 6 tokens, 22 cores hex fora do :root, 5 raios literais diferentes, font-size 16 (0 com var)`
  - `mesma cor, nomes diferentes: {'#121212': ['--su-bg', '--sup-1'], '#181818': ['--su-card', '--sup-2'], '#ffffff': ['--su-text', '--texto'], '#b3b3b3': ['--su-sub', '--sub'], '#1ed760': ['--su-green', '--verde'], '#c4b7ff': ['--roxo', '--su-violet']}`
- **Impacto:** nenhum visível hoje (as cores batem). Mas mudar o verde ou o cinza de apoio exige achar o mesmo valor com nomes diferentes em quatro arquivos, e os 122 `font-size` do PC, sem nenhuma variável, deixam a tipografia derivar entre as superfícies.
- **Solução proposta:** o app para PC carrega só o `styles.css` (`ui/comum.py:34`), então ele não pode simplesmente apontar para o `estilo.css`. Manter as duas famílias, com um teste que exija valores iguais para os pares (verde, cinzas, cartão, texto, violeta), e anotar o par em cada `:root`. Depois, uma escala curta de tamanhos de texto (hoje 0 `font-size` com variável em 4 dos 5 arquivos). Os raios do app web já têm escala (`app.css:6`, campo / cartão / painel); o PC não (28 raios literais). Sem mudar nenhum valor visível.
- **Testes necessários:** Python (`tests/test_web.py`): os pares de tokens do `styles.css`, do `estilo.css` e os valores fixos do `nucleo.css:4` (`--su-card`, `--su-line`) têm o mesmo valor. Fica no mesmo arquivo do teste do R2-09, que deve deixar o `:root` para este.
- **Critério de aceitação:** o teste passa hoje (os 6 pares do bloco batem) e falha se um lado mudar sozinho.

### R2-11 — Sobrescritas no fim do arquivo (contra a regra anti-remendo)

- **Classificação:** Oportunidade de melhoria
- **Prioridade:** P4
- **Localização:** `site/app/stories.css:448-501` ("9. Tema único (1.18)") redefine `.st-fundo` (`:34` → `:456`), `.st-veu` (`:40` → `:459`), `.st-vidro` (`:47` → `:470`), `.st-kicker` (`:49` → `:466`) e os tamanhos do resumo (`:480-486` → `:488-501`, o mesmo seletor duas vezes no mesmo bloco); `site/estilo.css:434-444`; `site/app/app.css:531-536`.
- **Evidência:**

```powershell
@'
import re
for arq, depois in [('site/app/stories.css', 448), ('site/estilo.css', 434), ('site/app/app.css', 531)]:
    t = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group().count('\n'), open(arq, encoding='utf-8').read(), flags=re.S)
    linhas = {}
    for m in re.finditer(r'(?:^|[;{}])\s*([^@{};]+?)\s*\{', t):
        for s in m.group(1).split(','):
            linhas.setdefault(' '.join(s.split()), []).append(t.count('\n', 0, m.start(1)) + 1)
    sob = {s: l for s, l in linhas.items() if min(l) < depois and max(l) >= depois and not re.fullmatch(r'(from|to|[\d.]+%)', s)}
    print(arq, f'- definidos antes e de novo a partir da linha {depois}:', len(sob))
    for s, l in list(sob.items())[:8]: print('   ', s[:50], l)
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `site/app/stories.css - definidos antes e de novo a partir da linha 448: 13`
  - `    :root [5, 452]`
  - `    .vidro-ctrl [16, 305, 307, 310, 471, 476, 477]`
  - `    .st-fundo [34, 456]`
  - `    .st-veu [40, 308, 310, 459]`
  - `    .st-vidro [47, 307, 310, 470, 476, 477]`
  - `    .st-kicker [49, 466]`
  - `    .s-resumo .st-poster-topo small [163, 488]`
  - `    .s-resumo .st-poster-horas [168, 492]`
  - `site/estilo.css - definidos antes e de novo a partir da linha 434: 4`
  - `    :root [3, 435]`
  - `    .titulo-secao [87, 444]`
  - `    .hero h1 [123, 443]`
  - `    .palco-placa [139, 170, 437, 439, 440]`
  - `site/app/app.css - definidos antes e de novo a partir da linha 531: 8`
  - `    .nav-item[aria-current="page"] [30, 64, 536, 538, 540]`
  - `    .nav-item[aria-current="page"] svg [44, 537]`
  - `    .app-corpo[data-modo="dupla"] [82, 533]`
  - `    .app-corpo[data-modo="batalha"] [83, 534]`
  - `    .app-corpo[data-modo="match"] [84, 535]`
  - `    .app-cabeca [85, 86, 544]`
  - `    .app-cabeca h1 [87, 551]`
  - `    .dock [486, 502, 539, 554]`

  A lista mistura dois casos, e por isso serve de **candidatos**, conferidos a olho: sobrescrevem de fato `.st-fundo` (fundo), `.st-veu` (degradê), `.st-vidro` (fundo, borda, sombra e blur), `.st-kicker` (peso, espaçamento e cor) e os tamanhos do `.s-resumo` (o mesmo seletor duas vezes, `:480-486` e `:488-501`); só **acrescentam** propriedades `.vidro-ctrl` em `:471`, o `:root` de `estilo.css:435` (`--tinta`) e o `.dock` em `app.css:539` e `:554`; as linhas dentro de `@media` (por exemplo `stories.css:305-310` e `:476-477`) são variações legítimas. Em `app.css:82-84` × `:533-535` as propriedades são outras (`--tinta-2` × `--tinta`).
- **Impacto:** nenhum para o usuário. Quem lê `.st-vidro` na linha 47 vê um vidro com degradê que não existe mais; o valor real está 420 linhas abaixo. Cada correção futura tende a virar mais uma camada no fim.
- **Solução proposta:** levar cada valor final para a regra original e apagar o bloco de baixo, um arquivo por PR, conferindo as capturas antes e depois. Não usar `@layer` só em parte dos arquivos: CSS sem camada vence CSS com camada, então os outros arquivos da mesma página passariam a ganhar; se um dia houver camadas, que sejam em todos os arquivos de uma superfície de uma vez.
- **Testes necessários:** os testes de navegador existentes, mais uma comparação de capturas dos 4 modos antes e depois.
- **Critério de aceitação:** no `stories.css`, `.st-fundo`, `.st-veu`, `.st-vidro`, `.st-kicker` e cada seletor `.s-resumo …` têm uma única regra fora de `@media`, e as capturas dos 4 modos não mudam.

### R2-12 — Seletores mortos: 5 classes no app para PC e 2 na web

- **Classificação:** Problema comprovado (código morto; sem efeito visível)
- **Prioridade:** P4
- **Localização:**
  - PC: `styles.css:656` (`.su-chip-label`), `:660` (`.su-srcs`), `:662` (`.su-match-h`), `:663-669` (`.su-best-list`), `:687-688` (`.su-steps`, que não é o `.su-steps-home` usado em `ui/layout.py:157`).
  - Web: `site/app/stories.css:69` (`.st-capa-vazia`) e `:175` (`.st-capa.pequena`).
  - `.wrap.svelte-12ioyct` (`styles.css:184`) já é o R1-05; a outra metade da mesma regra está em §5.
- **Evidência:** varredura em tempo de execução (cada seletor testado com `querySelector` a cada passo, nos 4 modos + landing + Last.fm, em 1280 e 390 px) seguida da busca do nome da classe no código:

```powershell
@'
import functools, json, pathlib, re, threading, collections
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
CASA = r"""() => { const out = []; const limpa = (s) => s.replace(/::?(before|after|placeholder|marker|selection|-webkit-[\w-]+|backdrop)\b/g, '')
    .replace(/:(hover|focus-visible|focus-within|focus|active|visited|target|checked|disabled|invalid|placeholder-shown)\b/g, '');
  const anda = (rs, h) => { for (const r of rs) { if (r.selectorText) for (const s of r.selectorText.split(/,(?![^(]*\))/)) { let m;
      try { m = !!document.querySelector(limpa(s).trim() || '*'); } catch (e) { m = null; } out.push([h, s.trim(), m]); }
    else if (r.cssRules) anda(r.cssRules, h); } };
  for (const sh of document.styleSheets) if (sh.href && sh.href.endsWith('.css')) anda(sh.cssRules, sh.href.split('/').slice(3).join('/'));
  return out; }"""
todos, vivos = collections.defaultdict(set), collections.defaultdict(set)
def olhar(pg):
    for h, s, m in pg.evaluate(CASA):
        todos[h].add(s)
        if m is not False: vivos[h].add(s)
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1280, 390):
        for alvo in ['/', 'lastfm', 'wrapped', 'dupla', 'batalha', 'match']:
            pg = b.new_page(viewport={'width': w, 'height': 900})
            pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort())
            if alvo == '/':
                pg.goto(URL + '/'); pg.wait_for_timeout(1500); olhar(pg)
                if w == 390: pg.click('#abrir-menu'); pg.wait_for_timeout(300); olhar(pg)
            elif alvo == 'lastfm':
                pg.goto(URL + '/app/#wrapped'); pg.wait_for_timeout(800); olhar(pg)
                pg.get_by_role('button', name=re.compile('Usar o Last.fm')).click(); pg.wait_for_timeout(400); olhar(pg)
                for s in pg.locator('summary:visible').all(): s.click()
                olhar(pg)
            else:
                pg.goto(f'{URL}/app/#{alvo}'); pg.wait_for_timeout(800); olhar(pg)
                pg.get_by_role('button', name='Ver um exemplo').click()
                pl = pg.locator('.resultado .st-player:visible').first; pl.wait_for(timeout=45000); pl.focus(); pg.keyboard.press(' '); olhar(pg)
                for _ in range(int(pl.locator('.st-contador').inner_text().split('/')[1])):
                    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(150); olhar(pg)
                for t in pg.get_by_role('tab').all():
                    if t.is_visible(): t.click(); pg.wait_for_timeout(400); olhar(pg)
                for s in pg.locator('summary:visible').all(): s.click()
                olhar(pg)
            pg.close()
    b.close()
web = ''.join(a.read_text(encoding='utf-8') for a in [*pathlib.Path('site').rglob('*.js'), *pathlib.Path('site').rglob('*.html')])
def ausentes(sel, codigo):
    return [c for c in re.findall(r'\.([a-zA-Z][\w-]*)', sel) if not re.search(r'(?<![\w-])' + re.escape(c) + r'(?![\w-])', codigo)
            and not re.search(re.escape(c.rsplit('-', 1)[0]) + r'-\$\{', codigo)]
total = sum(len(v) for v in todos.values()); nunca = {h: todos[h] - vivos[h] for h in todos}
print('web: seletores', total, '| nunca casaram', sum(len(v) for v in nunca.values()))
print('web: nunca casaram e a classe nao aparece em nenhum JS/HTML:', sorted((h, s) for h, ss in nunca.items() for s in ss if ausentes(s, web)))
css = re.sub(r'/\*.*?\*/', '', open('styles.css', encoding='utf-8').read(), flags=re.S)
pc = ''.join(a.read_text(encoding='utf-8') for a in [*pathlib.Path('.').glob('*.py'), *pathlib.Path('ui').glob('*.py'), pathlib.Path('syncup.js')])
cls = sorted(set(re.findall(r'\.(su-[\w-]+)', css)))
print('PC: classes su-* no styles.css', len(cls), '| sem nenhuma ocorrencia no Python nem no syncup.js:',
      [c for c in cls if not re.search(r'(?<![\w-])' + re.escape(c) + r'(?![\w-])', pc)])
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `web: seletores 1144 | nunca casaram 126`
  - `web: nunca casaram e a classe nao aparece em nenhum JS/HTML: [('app/stories.css', '.st-capa-vazia'), ('app/stories.css', '.st-capa.pequena')]`
  - `PC: classes su-* no styles.css 161 | sem nenhuma ocorrencia no Python nem no syncup.js: ['su-best-list', 'su-chip-label', 'su-match-h', 'su-srcs', 'su-steps']`
- **Impacto:** nenhum para o usuário; 11 linhas no `styles.css` e uma regra e meia no `stories.css` que confundem quem procura onde um estilo vive. Os outros 124 seletores que nunca casaram têm o nome da classe em algum JS: o mais provável é que sejam estados que a varredura não provocou (erro, arrastando, trio, Last.fm baixando…), mas isso **não foi conferido um a um** (§5); a busca por nome também pode achar a palavra num comentário ou texto (`grande`, `vazia`), o que subestima o código morto.
- **Solução proposta:** apagar as 5 classes do `styles.css` (11 linhas; cuidado para não levar junto o `.su-steps-home`, que está em uso, `styles.css:112-117`), a regra `.st-capa.pequena` e só o seletor `.st-capa-vazia` da lista de `stories.css:69` (o `.st-lista .st-capa` da mesma linha está em uso, `slides.js:98-99`), num PR só, junto com a regra morta do R1-05 (§5).
- **Testes necessários:** estender o teste estático de `tests/test_web.py:45` para o `stories.css` (toda classe `st-` com regra aparece no JS) e criar o equivalente para o `styles.css` contra o Python e o `syncup.js`.
- **Critério de aceitação:** as duas listas do bloco ficam vazias.

### R2-13 — No celular: 26 `:hover` sem proteção e o flash cinza do toque

- **Classificação:** Oportunidade de melhoria (conferido no código; o efeito precisa de um celular real)
- **Prioridade:** P4
- **Localização:** `site/estilo.css` (9 `:hover` fora de `@media (hover: hover)`, por exemplo `:80` e `:97`), `site/app/app.css` (9, por exemplo `:29` e `:225`), `site/app/nucleo.css` (8, por exemplo `:15`). Nenhum CSS define `-webkit-tap-highlight-color`. A contagem do bloco trata como "fora" também os `:hover` dentro de `@media (min-width: 900px)` (por exemplo `app.css:55`), que no celular não se aplicam mas valem em tablets largos. O que já está certo: entradas com 16 px (`app.css:191`, sem zoom no iOS), o player com `touch-action: pan-y` e `user-select: none` (`stories.css:11`).
- **Evidência:**

```powershell
@'
import re
for arq in ['site/estilo.css', 'site/app/app.css', 'site/app/nucleo.css']:
    t = re.sub(r'/\*.*?\*/', '', open(arq, encoding='utf-8').read(), flags=re.S)
    pilha, ini, livres, presos = [], 0, 0, 0
    for i, c in enumerate(t):
        if c == '{':
            sel = t[ini:i].strip(); pilha.append(sel); ini = i + 1
            if ':hover' in sel and not sel.startswith('@'):
                if any('hover: hover' in x for x in pilha[:-1]): presos += 1
                else: livres += 1
        elif c == '}':
            if pilha: pilha.pop()
            ini = i + 1
        elif c == ';' and not pilha: ini = i + 1
    print(arq, '- :hover dentro de (hover: hover):', presos, '| fora:', livres, '| tap-highlight:', t.count('tap-highlight'))
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `site/estilo.css - :hover dentro de (hover: hover): 4 | fora: 9 | tap-highlight: 0`
  - `site/app/app.css - :hover dentro de (hover: hover): 2 | fora: 9 | tap-highlight: 0`
  - `site/app/nucleo.css - :hover dentro de (hover: hover): 0 | fora: 8 | tap-highlight: 0`
- **Impacto:** no celular, o primeiro toque num link ou botão deixa o estado de hover preso até tocar em outro lugar, e o iOS/Android pinta um retângulo cinza por cima do toque. São os sinais mais comuns de "site dentro do navegador".
- **Solução proposta:** levar os `:hover` para dentro de `@media (hover: hover) and (pointer: fine)` (o padrão que o `estilo.css:54` e o `app.css:13` já usam) e pôr `-webkit-tap-highlight-color: transparent` no `html`, garantindo um `:active` em cada controle.
- **Testes necessários:** o mesmo bloco como teste estático (zero `:hover` fora da consulta). Conferência manual num celular.
- **Critério de aceitação:** o bloco imprime `fora: 0` nos três arquivos e `tap-highlight: 1` no `estilo.css`.

### R2-14 — App para PC: jargão técnico ("describe()") no rodapé e num rótulo

- **Classificação:** Problema comprovado (texto de interface)
- **Prioridade:** P4
- **Localização:** `ui/layout.py:870` (rodapé: "Horas e describe(): todas as execuções válidas") e `:494` (rótulo da tabela "describe() · minutos por execução").
- **Evidência (vale também para o R2-03 e para §5; a medida de rolagem lateral desta saída não vale, ver §5):**

```powershell
@'
import os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
s = socket.socket(); s.bind(('127.0.0.1', 0)); porta = s.getsockname()[1]; s.close()
app = subprocess.Popen([sys.executable, '-W', 'ignore', '-c', 'from app import executar; executar(False)'],
                       env={**os.environ, 'SYNCUP_PORTA': str(porta)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
URL = f'http://127.0.0.1:{porta}/'
for _ in range(120):
    try: urllib.request.urlopen(URL, timeout=1); break
    except Exception: time.sleep(.5)
FOCO = """() => { const e = document.activeElement; if (!e || e === document.body) return null;
  const estilo = () => { const c = getComputedStyle(e); return [c.outlineStyle, c.outlineWidth, c.outlineColor, c.boxShadow, c.backgroundColor, c.borderColor].join('|'); };
  const com = estilo(); e.blur(); const sem = estilo(); e.focus({ focusVisible: true });
  return com === sem ? (String(e.className).split(' ')[0] + ' ' + (e.getAttribute('aria-label') || '') + ' role=' + e.getAttribute('role')) : ''; }"""
quebrado = Path(tempfile.mkdtemp()) / 'quebrado.zip'; quebrado.write_bytes(b'PK\x03\x04isto nao e um zip')
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        for aba, gerar in [('Wrapped', 'Gerar meu Wrapped'), ('Dupla', 'Comparar hist')]:
            pg = b.new_page(viewport={'width': 1280, 'height': 900}); pg.goto(URL); pg.wait_for_selector('.gradio-container', timeout=60000)
            pg.get_by_role('tab', name=aba).click(); pg.wait_for_timeout(800)
            pg.locator('.gradio-container button:visible', has_text='Testar com dados').first.click(); pg.wait_for_timeout(2500)
            pg.locator('.gradio-container button:visible', has_text=gerar).first.click()
            pg.locator('.su-results:visible').first.wait_for(timeout=90000); pg.wait_for_timeout(2000)
            pg.locator('.su-results:visible').first.click(position={'x': 2, 'y': 2})
            sem = set()
            for _ in range(70):
                pg.keyboard.press('Tab'); r = pg.evaluate(FOCO)
                if r: sem.add(ascii(r))
            print(aba, '- 70 Tabs; sem mudanca visual ao focar:', sorted(sem), '| [data-testid=file] no DOM:', pg.locator('[data-testid="file"]').count(),
                  '| rolagem lateral em 360 px:', (pg.set_viewport_size({'width': 360, 'height': 800}), pg.wait_for_timeout(800), pg.evaluate('document.documentElement.scrollWidth - innerWidth'))[2])
            pg.close()
        pg = b.new_page(viewport={'width': 1280, 'height': 900}); pg.goto(URL); pg.wait_for_selector('.gradio-container', timeout=60000)
        pg.get_by_role('tab', name='Wrapped').click(); pg.wait_for_timeout(800)
        pg.locator('#su-envio-wrapped input[type=file]').set_input_files(str(quebrado)); pg.wait_for_timeout(1500)
        pg.get_by_role('button', name='Gerar meu Wrapped').click(); pg.wait_for_timeout(6000)
        print('ZIP quebrado, aviso:', [ascii(' '.join(t.split())) for t in pg.locator('.toast-body').all_inner_texts()])
        print('rodape:', ascii([t for t in pg.locator('body').inner_text().split('\n') if 'describe()' in t][:2]))
        b.close()
finally:
    app.terminate()
'@ | .venv\Scripts\python.exe -
```

  Saída: 
  - `Wrapped - 70 Tabs; sem mudanca visual ao focar: ["'su-stories Wrapped de Ana (fict\\xedcia) role=null'"] | [data-testid=file] no DOM: 0 | rolagem lateral em 360 px: 0`
  - `Dupla - 70 Tabs; sem mudanca visual ao focar: ["'su-stories Wrapped de Ana (fict\\xedcia) role=null'", "'su-stories Wrapped de Bruno (fict\\xedcio) role=null'"] | [data-testid=file] no DOM: 0 | rolagem lateral em 360 px: 0`
  - `ZIP quebrado, aviso: ["'Error \\xd7 O arquivo ZIP est\\xe1 inv\\xe1lido ou incompleto. Baixe o hist\\xf3rico novamente.'"]`
  - `rodape: ['Plays: \u226530 segundos. Horas e describe(): todas as execu\xe7\xf5es v\xe1lidas. O Ruzicka usa pesos absolutos e \xe9 sens\xedvel ao volume de escuta. Arqu\xe9tipos e tra\xe7os s\xe3o regras experimentais sobre este recorte de escuta. N\xe3o medem personalidade ou afinidade amorosa. N\xe3o s\xe3o testes psicol\xf3gicos.']`
- **Impacto:** "describe()" é o nome de um método do pandas; para quem não programa, o rodapé fica incompreensível.
- **Solução proposta:** trocar "describe()" por "o resumo estatístico (média, mediana e quartis)" no rodapé e no rótulo.
- **Testes necessários:** Python (`tests/test_smoke_ui.py`): o texto da interface não contém "describe()".
- **Critério de aceitação:** no bloco acima, a linha "rodape" fica vazia, e `ui/layout.py` não contém mais "describe()" em nenhum texto visível (o rótulo da tabela só aparece depois de uma comparação da Dupla; o teste Python cobre os dois lugares).

## 4. O que já funciona bem

**Medido pelo bloco abaixo (ou pelo bloco indicado):**

- **Sem rolagem horizontal** nas telas de **resultado** dos 4 modos em 320, 360 e 390 px (os testes atuais só cobriam a tela inicial do Wrapped e a landing, em 375 px). Inferido, não calibrado: na web o `body` usa `overflow-x: hidden` (`site/estilo.css:31`), que não impede o `scrollWidth` de crescer (no PC, o `overflow-x: clip` do contêiner impede, §5).
- **Contraste AA** no texto fora dos stories (landing, app vazio e os 4 resultados, 990 textos), em 1280 px. Limite do método: o fundo é calculado só pelas cores de fundo dos ancestrais (degradês, imagens e a cascata de cor do topo, `.app-corpo::before`, ficam de fora), e a opacidade dos ancestrais não entra.
- **Foco visível** em todas as paradas de Tab da landing (87) e do resultado da Dupla (89), em 1280 px, comparando cada elemento focado com ele mesmo sem foco. Em 390 px o problema é outro: o foco fica escondido (R2-02).
- **"Menos movimento":** nenhuma animação ainda rodando 2,5 s depois de abrir a landing, o app e os stories. Isso mostra que nada longo ou infinito continua; entradas curtas que já terminaram não aparecem nessa medida. Os testes existentes cobrem a troca direta e a chegada sem logo grande.
- **Duplo envio barrado** nos 4 modos: 1 cálculo por duplo clique (bloco do R2-06).
- **Last.fm com estados próprios no código:** "Sem conexão…", "O Last.fm pediu uma pausa…", "Nenhum scrobble nesse perfil…" (`lastfm.js:50`, `:55`, `:185`) e "Cancelar" com barra de progresso durante o download (`envio.js:69-76`).
- **ARIA na web:** abas com `role=tablist`/`tab`/`tabpanel` e setas (`resultado.js:162-165`); player com `role=region` e `aria-roledescription` (`player.js:175-176`); menu da landing com `role=dialog`, `aria-modal`, `inert` no fundo, foco no "Fechar" e Esc (`site/index.html:397-405`); link "Pular para o conteúdo". Lido no código.
- **Transparência reduzida e contraste alto** tratados em quase todo vidro (`prefers-reduced-transparency`, `prefers-contrast: more`, `@supports not`), menos o `.dock` (bloco do R2-08).
- **Pouco CSS morto na web:** de 1.144 seletores, só 2 comprovadamente sem uso (bloco do R2-12; 124 outros ficam em §5). O teste `tests/test_web.py:45` mantém o `nucleo.css` sem classe sobrando.

**Observado nesta rodada, sem bloco no relatório** (refazer antes de usar como prova; os roteiros ficaram fora do repositório):

- Gestos dos stories com toque emulado (`has_touch`): tocar à direita avança e à esquerda volta. Segurar para pausar e arrastar para trocar foram só lidos no código (`player.js:140-170`).
- Selo "Lendo neste aparelho…": visto com a CPU 20× mais lenta (CDP), o que fecha a pendência da Rodada 1.
- Last.fm: com a API respondendo por rota falsa, as três mensagens acima apareceram como `role=alert`. (A Rodada 1 deixou a rede de verdade para a Rodada 3; isto não testa resiliência, só o texto.)
- Pôster da Dupla: PNG de 1080×1920 (o canvas tem tamanho fixo, `poster.js:9`, então não depende do `devicePixelRatio`); com pessoa de 47 e artista de 83 caracteres, corta com reticências sem vazar ([`poster-dupla-nome-longo.png`](rodada-2/poster-dupla-nome-longo.png)).
- Gráficos da Dupla em 320 px: rótulos em HTML a 0,75 rem (`app.css:332`, `:352`, `:365`), com a regra de não pôr dois rótulos a menos de 15% da largura (`graficos-dupla.js:74`).
- Contraste dos stories por amostragem de pixels (texto escondido, fundo capturado, os 10% mais claros), nos 38 slides dos 4 modos, com as cores da demo e com a capa forçada para branco: nenhum texto abaixo do AA. As leituras baixas eram os números do quadro de medalhas da Batalha, cuja caixa inclui o disco da medalha (`stories.css:334`).
- App para PC com os dados fictícios do Wrapped e da Dupla: o mesmo cálculo de contraste do bloco abaixo achou 0 textos abaixo do AA.

```powershell
@'
import functools, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}'
CONTRASTE = """() => { const cv = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  const rgba = (s) => { cv.clearRect(0, 0, 1, 1); cv.fillStyle = '#000'; cv.fillStyle = s; cv.fillRect(0, 0, 1, 1); const d = cv.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const mix = (a, b) => [0, 1, 2].map((i) => a[i] * a[3] + b[i] * (1 - a[3])).concat(1);
  let ruins = 0, n = 0;
  document.querySelectorAll('body *').forEach((el) => {
    if (el.closest('.st-player, [aria-hidden=true]') || (!el.offsetParent && getComputedStyle(el).position !== 'fixed')) return;
    const txt = [...el.childNodes].filter((x) => x.nodeType === 3).map((x) => x.textContent).join('').trim(); const cs = getComputedStyle(el);
    if (!txt || cs.visibility === 'hidden' || +cs.opacity === 0 || cs.backgroundClip === 'text' || !el.getBoundingClientRect().width) return;
    const pilha = []; for (let e = el; e; e = e.parentElement) { const c = rgba(getComputedStyle(e).backgroundColor); if (c[3] > 0) { pilha.push(c); if (c[3] >= 1) break; } }
    let fundo = [0, 0, 0, 1]; for (let i = pilha.length - 1; i >= 0; i--) fundo = mix(pilha[i], fundo);
    const cor = mix(rgba(cs.color), fundo); const r = (Math.max(lum(cor), lum(fundo)) + 0.05) / (Math.min(lum(cor), lum(fundo)) + 0.05);
    const px = parseFloat(cs.fontSize), grande = px >= 24 || (px >= 18.66 && +cs.fontWeight >= 700); n++;
    if (r < (grande ? 3 : 4.5)) ruins++; });
  return n + ' textos, ' + ruins + ' abaixo do AA'; }"""
FOCO = """() => { const e = document.activeElement; if (!e || e === document.body) return null;
  const estilo = () => { const c = getComputedStyle(e); return [c.outlineStyle, c.outlineWidth, c.boxShadow, c.backgroundColor, c.borderColor].join('|'); };
  const com = estilo(); e.blur(); const sem = estilo(); e.focus({ focusVisible: true }); return com !== sem; }"""
ANIM = "() => document.getAnimations().filter(a => a.playState === 'running').length"
def nova(b, **kw):
    pg = b.new_page(**kw); pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith((URL, 'https://unpkg.com')) else r.abort()); return pg
def exemplo(pg, modo):
    pg.goto(f'{URL}/app/#{modo}'); pg.get_by_role('button', name='Ver um exemplo').click()
    pg.locator('.resultado .st-player:visible').first.wait_for(timeout=45000)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = nova(b, viewport={'width': 1280, 'height': 900}, reduced_motion='reduce')
    for nome, alvo in [('landing', '/'), ('app vazio', '/app/#wrapped'), ('wrapped', 'wrapped'), ('dupla', 'dupla'), ('batalha', 'batalha'), ('match', 'match')]:
        if alvo.startswith('/'): pg.goto(URL + alvo); pg.wait_for_timeout(1500)
        else: exemplo(pg, alvo)
        print('contraste', nome, '-', pg.evaluate(CONTRASTE))
    pg.close()
    for nome, alvo in [('landing', '/'), ('dupla', 'dupla')]:
        pg = nova(b, viewport={'width': 1280, 'height': 900})
        if alvo == '/': pg.goto(URL + '/'); pg.wait_for_timeout(1000)
        else: exemplo(pg, alvo); pg.evaluate('document.activeElement.blur(); scrollTo(0, 0)')
        r = [x for x in (pg.keyboard.press('Tab') or pg.evaluate(FOCO) for _ in range(90)) if x is not None]
        print('foco', nome, '- paradas de Tab', len(r), '| sem mudanca visual:', r.count(False))
        pg.close()
    for nome, alvo in [('landing', '/'), ('app', '/app/#wrapped'), ('stories', 'wrapped')]:
        pg = nova(b, viewport={'width': 1280, 'height': 900}, reduced_motion='reduce')
        if alvo.startswith('/'): pg.goto(URL + alvo)
        else: exemplo(pg, alvo)
        pg.wait_for_timeout(2500); print('menos movimento', nome, '- animacoes rodando:', pg.evaluate(ANIM)); pg.close()
    for modo in ['wrapped', 'dupla', 'batalha', 'match']:
        pg = nova(b, viewport={'width': 390, 'height': 844}, reduced_motion='reduce'); exemplo(pg, modo); medidas = []
        for w in (320, 360, 390):
            pg.set_viewport_size({'width': w, 'height': 800}); pg.wait_for_timeout(300)
            medidas.append(pg.evaluate('document.documentElement.scrollWidth - innerWidth'))
        print('rolagem lateral', modo, '(320/360/390 px):', medidas); pg.close()
    b.close()
'@ | .venv\Scripts\python.exe -
```

Saída: 
  - `contraste landing - 117 textos, 0 abaixo do AA`
  - `contraste app vazio - 32 textos, 0 abaixo do AA`
  - `contraste wrapped - 126 textos, 0 abaixo do AA`
  - `contraste dupla - 288 textos, 0 abaixo do AA`
  - `contraste batalha - 283 textos, 0 abaixo do AA`
  - `contraste match - 144 textos, 0 abaixo do AA`
  - `foco landing - paradas de Tab 87 | sem mudanca visual: 0`
  - `foco dupla - paradas de Tab 89 | sem mudanca visual: 0`
  - `menos movimento landing - animacoes rodando: 0`
  - `menos movimento app - animacoes rodando: 0`
  - `menos movimento stories - animacoes rodando: 0`
  - `rolagem lateral wrapped (320/360/390 px): [0, 0, 0]`
  - `rolagem lateral dupla (320/360/390 px): [0, 0, 0]`
  - `rolagem lateral batalha (320/360/390 px): [0, 0, 0]`
  - `rolagem lateral match (320/360/390 px): [0, 0, 0]`

Também valem os pontos fortes da Rodada 1 (paridade, golden master, ZIP endurecido), que esta rodada não tocou.

## 5. Necessita investigação

- **Custo real do vidro no celular (R2-08):** sem gravação do Performance do DevTools num celular de gama média, nenhum número de frames por segundo é afirmado aqui. A emulação de CPU do Chromium no desktop não mede GPU.
- **Contador dos stories com `aria-live`:** `site/app/js/stories/player.js:183` anuncia "n/N" a cada troca de slide (a cada ~10 s durante a reprodução), mas o conteúdo do slide em si não é anunciado. Precisa de teste com NVDA ou VoiceOver para saber se ajuda ou só interrompe.
- **Movimento feito por JavaScript com "menos movimento":** a medição cobriu só animações CSS e Web Animations. O relógio dos stories já tem teste (`tests/test_web.py:60`), mas as transições por `requestAnimationFrame` (por exemplo a inclinação do player em `player.js:63-78`, que já se desliga com `reduzido()`) não foram medidas.
- **Gradio `.wrap.svelte-12ioyct, [data-testid="file"]` (`styles.css:184`):** com arquivos carregados no `gr.File` (demo do Wrapped e da Dupla), nenhum elemento com `data-testid="file"` existe no DOM (bloco do R2-14). Somado ao R1-05, a regra parece toda morta no Gradio 6.31, mas só um estado foi visto (com arquivos); conferir também o `gr.File` vazio antes de apagar.
- **Título "Error" no aviso de erro do app para PC:** o erro de ZIP aparece em português ("O arquivo ZIP está inválido ou incompleto…", pendência do R1 fechada), mas com o título "Error" (bloco do R2-14), embora `falha()` já passe `title='Não deu certo'` (`ui/comum.py:50-52`) e o servidor do Gradio repasse o título. A causa não foi encontrada: pode ser o frontend do Gradio 6.31 ignorando o título ou exibindo o tipo do aviso no lugar dele.
- **Rolagem lateral no app para PC:** a medida `scrollWidth - innerWidth` dá 0 sempre, porque o `.gradio-container` usa `overflow-x: clip` (`styles.css:38`): o que passar da largura é cortado, não rolado. Precisa de outro método (procurar elementos mais largos que o contêiner).
- **Os outros 124 seletores da web que nunca casaram** (bloco do R2-12): têm o nome da classe em algum JS, o que sugere estados não provocados, mas não foram conferidos um a um.
- **Não auditados nesta rodada:** `site/app/js/opcoes.js` (painel "Opções de dados"), `ui/meus_dados.py` (painel "Meus dados" do app para PC) e a tela de Match do app para PC (`ui/match.py`).
- **App para PC no celular:** abaixo de ~600 px as abas do Gradio entram num menu de "mais abas" (`syncup.js:311`, já citado no R1-05). Sem rolagem lateral em 360 px; o resto não foi explorado, porque o app para PC é feito para o computador.
- **Alvo de toque do link "Ainda não tem o ZIP? Veja como pedir"** (`app-como-pedir`, 18 px de altura em 390 px): pelo WCAG 2.5.8 pode passar pela exceção de espaçamento; não foi medido com o círculo de 24 px.

## 6. Lista curta (fora dos 14 achados)

- Perfil do Last.fm vazio usa o mesmo alerta vermelho (`.erro`, `envio.js:81`) das falhas; é um estado vazio, não um erro, e não diz o que fazer (por exemplo, escolher "Todo o histórico").
- No app para PC, o botão "Gerar meu Wrapped" fica com ~125 px de altura porque a linha usa `equal_height=True` (`ui/layout.py:328`, `:359`, `:382`): a ação principal parece um bloco, não um botão.
- `styles.css` tem 131 `!important` (muitos para vencer o tema do Gradio, o que é esperado; vale revisar junto com o R2-10).
- A landing usa `min-height: 85vh` (`site/estilo.css:356`, `:369`); `svh` evitaria salto quando a barra do navegador some.
- `site/app/stories.css` tem um segundo `:root` no meio do arquivo (`:452`); os apelidos do rosa podem subir para o primeiro (entra no R2-11).

## 7. Plano de PRs (um item por PR, nesta ordem)

| # | PR | Achado | Toca |
|---|---|---|---|
| 1 | Wrapped: estado "histórico curto demais" e plural de "dias" | R2-01 | `wrapped.py`, `calculo.js`, `slides.js`, `stories.py`, `wrapped.js`, `ui/meu_wrapped.py`, testes + paridade, `VALIDACAO.md` |
| 2 | Foco não fica sob a barra fixa no celular | R2-02 | `site/app/app.css`, `tests/navegador/test_app.py` |
| 3 | Player do PC com papel e foco visível | R2-03 | `stories.py`, `styles.css`, teste |
| 4 | Stories da Dupla encolhem com nomes longos | R2-04 | `stories/dupla.js`, `stories/slides.js` (`useCaber`), `stories.css`, teste de navegador |
| 5 | Painel do som lê o motivo do "sem som" | R2-05 | `som.js`, `stories/palco.js`, teste de navegador |
| 6 | Botão "Cancelar" durante o cálculo | R2-06 | `worker.js`, `main.js`, `batalha-tela.js`, `match-tela.js`, `wrapped.js`, `tests/js`, teste de navegador |
| 7 | Match: linha de escala e "Como a nota é calculada" | R2-07 | `match-tela.js`, `stories/match.js` |
| 8 | Vidro: `.dock` com transparência reduzida, sem blur nos botões ocultos e nos chips do PC | R2-08 | `app.css`, `stories.css`, `styles.css` |
| 9 | Teste de paridade `nucleo.css` ↔ `styles.css` e fora as animações anuladas | R2-09 | `tests/test_web.py`, `nucleo.css` |
| 10 | Teste de paridade dos pares de tokens PC × site e escala de tamanhos de texto | R2-10 | `tests/test_web.py`, `styles.css`, `estilo.css` |
| 11 | Consolidar as sobrescritas do fim (um arquivo por PR: `stories.css`, depois `estilo.css` e `app.css`) | R2-11 | os 3 CSS |
| 12 | Apagar seletores mortos (com a regra do R1-05) | R2-12 | `styles.css`, `stories.css`, testes estáticos |
| 13 | Hover protegido e sem flash de toque | R2-13 | `estilo.css`, `app.css`, `nucleo.css` |
| 14 | Textos do PC sem "describe()" | R2-14 | `ui/layout.py`, `tests/test_smoke_ui.py` |

O PR 1 é o único que mexe em cálculo; precisa de paridade e de uma decisão sobre o piso (com dados). Quase todos dividem algum arquivo com outro: os PRs 2, 3, 4, 8, 9, 10, 11, 12 e 13 mexem em CSS em comum; 1 e 4 em `slides.js`; 1 e 3 em `stories.py`; 1 e 6 em `wrapped.js`; 6 e 7 em `match-tela.js`; 9, 10 e 12 em `tests/test_web.py`. Sair em sequência, na ordem da tabela, rebaseando cada um sobre o anterior, com o 11 por último. Só o 5 e o 14 não dividem arquivos com nenhum outro. O PR 12 pode ir junto do PR 5 do plano da Rodada 1.

## 8. Skills aplicadas

- `design:design-system` — tabela de tokens entre superfícies (R2-10) e cópia `nucleo.css` (R2-09).
- `modern-web-guidance` — guia `css` consultado: "be allergic to knowledge duplication" (R2-10, R2-09) e a distinção entre sobrescrita que especializa (aceitável) e sobrescrita que corrige (R2-11). O guia recomenda `@layer`; o R2-11 explica por que não usá-lo só em parte dos arquivos aqui (CSS sem camada, como o do Gradio, venceria).
- `animation-performance` — o `backdrop-filter` foi classificado por camada e o que precisa de gravação em aparelho real ficou marcado como tal (R2-08).
- `mobile-native` — hover preso, flash do toque, entradas a 16 px, `touch-action` do player (R2-13).
- `ui-ux-pro-max:ui-ux-pro-max` — hierarquia em 3 camadas (R2-07) e a regra "Focus Not Obscured (Minimum)" do WCAG 2.2 AA (R2-02).
- `design:ux-copy` — estrutura "o que aconteceu + por quê + o que fazer" nos estados (R2-01, R2-05, lista curta do Last.fm vazio, R2-14).
- `design:accessibility-review` e `accessibility` — contraste, foco visível, 2.4.11, 4.1.2, alvo de toque, `prefers-reduced-motion`, ARIA (R2-02, R2-03, §4).
- `agent-skills:doubt-driven-development` — revisão adversarial, em contexto limpo, deste relatório antes da entrega. Dois ciclos (o relatório inteiro, depois só as mudanças). Corrigiu, entre outras coisas, três propostas que quebrariam algo (R2-09, R2-10, R2-14), a medição de rolagem do PC e afirmações sem bloco em §4. Sem segunda opinião de outro modelo.
