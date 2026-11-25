# Auditoria SyncUp — Rodada 1: integridade de dados

| | |
|---|---|
| **Commit auditado** | `origin/main` = `6743e598f6044b5adb8b1ca0922760762925f706` (merge do PR #43, v1.27). Mesma árvore (`1b738a3`) de `c524991` (branch `v1.27`), conferida com `git rev-parse "<commit>^{tree}"`. A `main` local estava desatualizada (`fbb9391`) e não foi usada. |
| **Data** | 2026-11-24 |
| **Ambiente** | Windows 11, PowerShell, Python 3.12.10 (`.venv`), pytest 8.3.5, pandas 2.2.3, Gradio 6.31.0, Playwright/Chromium, Node 26.13 (o CI usa Node 22 e Python 3.10/3.12) |
| **Escopo** | SYNC-001 a SYNC-011 e o P1 da rodada. Só relatório: nenhum arquivo do app foi alterado. |
| **Dados** | Todos fictícios ("Ana", "Banda A", arquivos gerados na hora numa pasta temporária). Nenhum histórico real foi usado. |

## 1. Linha de base dos testes (antes de qualquer diagnóstico)

| Comando | Resultado | Tempo |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` | **295 passaram, 3 pulados, 17 desmarcados** (`-m 'not navegador'` do `pyproject.toml:17`). Pulados: `pyarrow`/Parquet opcionais (`test_licencas.py:36`, `test_passo2.py:231` e `:262`) | ~97 s (outra rodada: ~69 s; varia com a máquina) |
| `node --test tests/js` (forma do prompt) | **105 passaram**, 0 falharam | 1,6 s |
| `node --test tests/js/*.test.mjs` (forma do CI) | **105 passaram**, 0 falharam | 1,5 s |
| `.venv\Scripts\python.exe -m pytest -m navegador -q -p no:cacheprovider` | **17 passaram** (Playwright/Chromium) | 28 s |

Nenhuma falha, nem só de ambiente (Node 26 local × 22 no CI). Avisos: `StarletteDeprecationWarning` do `fastapi.testclient` e o aviso esperado de "sem sintonia" em `test_listenbrainz.py`.

> **Como rodar as evidências:** cada bloco `powershell` roda da raiz do repositório, colado inteiro no PowerShell (Windows PowerShell 5.1). Os textos não-ASCII estão escritos como `\u…` de propósito: o 5.1 pode mandar o here-string para o programa em ASCII. Todos os blocos foram rodados assim nesta auditoria e as saídas abaixo são as obtidas.

## 2. Status das hipóteses

| ID | Status | Resumo | Achado |
|---|---|---|---|
| SYNC-001 | **Confirmado** | Sem validação de `p`/`k`. Python e JS divergem nos inválidos (`p=0`: erro × `NaN`; `k=2.5`: erro × número). Os chamadores só usam o padrão. | R1-04 |
| SYNC-002 / 007 | **Parcialmente confirmado** | Perfil vazio **já é recusado** com mensagem nos dois motores (ver R1-01). O que sobra é o perfil cujos nomes somem no `normalizar_nome`: aí `None` vira `0.0` "Mundos diferentes", entra nos pares e na média. Com 5 pessoas, a média cai de 34 para 17. A Dupla já distingue (`analise.py:332`). | R1-01 |
| SYNC-003 | **Parcialmente confirmado** | 3 de 22 strings divergem, todas em formatos que Spotify/Last.fm não produzem (`+24:00`, ISO básico, offset só com hora). Offsets incomuns, sem fuso e datas impossíveis batem. | R1-09 |
| SYNC-004 | **Confirmado** | Limitação intencional. 64 MB por JSON só no navegador (Python aceita), 50 MB por pessoa no envio web, 1 GB nos dois. A mensagem dos 64 MB orienta errado. | R1-07 |
| SYNC-005 | **Confirmado** | Faixas calibradas com 4 históricos (`conciliacao.py:28`). Um perfil com **1 artista** tira "Sintonia rara" (58,9), sem nenhum aviso de amostra. | R1-02 |
| SYNC-006 | **Parcialmente confirmado** | `ß`, ligaduras e invisíveis batem. Divergem `ı`, o sigma final grego e o Cherokee. `web/ponte.py` não normaliza nomes (o caminho do prompt não se aplica). | R1-08 |
| SYNC-008 | **Falso positivo** | 6.787 instantes em 11 transições reais de DST (São Paulo 2008–2019, Lisboa 1992–2023; o script confere que cada janela tem mesmo uma troca de deslocamento): 0 divergências entre `relogio()` e `tz_convert`. | evidência em §3.1 |
| SYNC-009 | **Parcialmente confirmado** | Artista malformado recusa o convite inteiro, com mensagem. **Música** malformada é descartada em silêncio (1 de 5 lidas), em Python e JS. | R1-10 |
| SYNC-010 | **Parcialmente confirmado** | Gravação atômica (temporário + `replace`) e recuperação de JSON corrompido: **ok**. Tipos internos, versão e tamanho: **não validados**, e um número no cache faz o `conciliar` levantar `TypeError`. | R1-03 |
| SYNC-011 | **Confirmado** | 53 `.gradio-container` em 40 linhas e 1 classe Svelte com hash, que **já está morta** no Gradio 6.31 instalado. Nenhum teste cobre os seletores internos. | R1-05 |

Correção de caminho do prompt: o `rbo` em JS fica em `site/app/js/dupla.js:61`, não em `calculo.js`.

## 3. P1 da rodada — veredito

| Item do P1 | Veredito | Como foi verificado |
|---|---|---|
| 0% × comparação indisponível: **cálculo** | Falha no Match (R1-01). Ok na Dupla (`analise.py:332`). | Python e JS rodados (blocos do R1-01). |
| 0% × indisponível: **tela** | Falha: `match-tela.js:35` mostra `0%` + "Mundos diferentes". | Lido no código. O valor vem do cálculo rodado acima. |
| 0% × indisponível: **emparelhamento** | Falha: entra nos pares, no trio e na média. | Rodado com 4 e 5 pessoas, nos dois motores. |
| Erro na entrada do **ZIP do Spotify** (web) | **Ok**: ZIP quebrado, entrada > 64 MB e JSON que não é histórico mostram `role="alert"` com mensagem própria. A dos 64 MB orienta errado (R1-07). A lógica já é testada (`tests/js/historico.test.mjs:96-108`); falta o teste de interface (R1-06). | Observado no Chromium (bloco do R1-06). |
| Carregamento e cancelamento (web) | Estados `vazio` / `lendo` / `pronto` / `erro` e cancelamento por `AbortError` existem (`envio.js:20-28`, `:92-150`). O caminho feliz está coberto por `test_app.py:39`, e o cancelamento do Worker por `tests/js` ("cancelar: rejeita a pendente com AbortError"). O selo "Lendo neste aparelho…" **não foi observado** na tela. | Código + testes existentes. |
| Erro no **Last.fm** (web) | Perfil privado: **ok**, coberto por `tests/navegador/test_lastfm.py:102` (passou na linha de base). Rede fora, lenta e limite de taxa: **não verificado** (Rodada 3). | Teste existente. |
| Entrada no **app para PC** (Gradio) | **Não verificado**: o app para PC não foi aberto. Pelo código, os erros de leitura viram `gr.Error` em português via `falha()` (`ui/comum.py:50`, `ui/meu_wrapped.py:51`). | Só código → "Necessita investigação". |

**Resumo do P1:**
- O 0% × indisponível **falha no Match** (R1-01).
- O feedback de **erro** funciona na web.
- O feedback de **carregamento** e a entrada do app para PC ficaram **sem verificação visual** (§6).

### 3.1 Evidência do falso positivo (SYNC-008)

```powershell
@'
import json, subprocess
import pandas as pd
NODE = ("import {relogio} from './site/app/js/historico.js'; const f = relogio(process.argv[1]); let s = '';"
        "process.stdin.on('data', d => s += d).on('end', () => console.log(JSON.stringify(JSON.parse(s).map(f))));")
casos = {'America/Sao_Paulo': ['2008-10-19', '2016-10-16', '2017-02-19', '2017-10-15', '2018-02-18', '2018-11-04', '2019-02-17'],
         'Europe/Lisbon': ['1992-03-29', '1996-10-27', '2023-03-26', '2023-10-29']}
total = divergentes = trocas = 0
for fuso, dias in casos.items():
    for dia in dias:
        inicio = pd.Timestamp(dia, tz='UTC') - pd.Timedelta(days=1)
        inst = [inicio + pd.Timedelta(minutes=7 * i) for i in range(617)]  # 3 dias, de 7 em 7 min
        ms = [t.value // 10**6 for t in inst]
        py = [t.tz_convert(fuso).tz_localize(None).value // 10**6 for t in inst]
        trocas += len({p - m for p, m in zip(py, ms)}) > 1  # a janela tem mesmo uma troca de deslocamento
        js = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE, fuso], input=json.dumps(ms),
                                       capture_output=True, text=True, check=True).stdout)
        total += len(ms); divergentes += sum(a != b for a, b in zip(py, js))
print('janelas com troca', trocas, 'de 11; instantes', total, 'divergentes', divergentes)
'@ | .venv\Scripts\python.exe -W ignore -
```

Saída: `janelas com troca 11 de 11; instantes 6787 divergentes 0`.

Nota: uma primeira versão deste roteiro usava 3 dias sem troca de horário (São Paulo 2019-11-03, Lisboa 1992-09-27 e 1996-03-31). A revisão adversarial apontou isso, e a conferência `trocas` foi acrescentada para evitar o mesmo erro.

## 4. Achados (ordem de impacto)

### R1-01 — Match: comparação sem dados aparece como 0% e entra no emparelhamento

- **Classificação:** Problema comprovado
- **Prioridade:** P1, porque é o P1 que o escopo da rodada define. Pela frequência no uso real, o gatilho é raro (ver abaixo); o R1-02 tem mais exposição.
- **Localização:**
  - Python: `conciliacao.py:96-97` (`pontuacao = round((valor or 0.0) * 100, 1)`), `:123` (`jaccard(...) or 0.0`), `:187-192` (matriz → `emparelhamento_otimo`), `:207` (média).
  - JS: `site/app/js/match.js:110-111`, `:122`, `:187`, `:195`.
  - UI web: `site/app/js/match-tela.js:35` (`pct(l.pontuacao)` + nível) e `:76` (média).
  - Contraste: a Dupla não mostra 0% nesse caso; ela interrompe a análise com uma mensagem própria (`analise.py:332-333`). Não é um estado "indisponível" por par (a Dupla não tem emparelhamento), mas mostra a intenção de não fingir um zero.
- **Gatilho (estreito):** perfis **vazios** já são recusados antes do Match: `perfil_gosto.py:73`, `convite.py:93`, `match.js:31-34` (histórico sem plays) e `convite.js:71`. Só chega ao 0% um perfil com rankings cujos nomes viram texto vazio no `normalizar_nome`: nomes só de pontuação ou emoji, como a banda "!!!". No caso real, isso é raro.
- **Evidência:**

```powershell
@'
from perfil_gosto import PerfilGosto
from conciliacao import comparar_perfis, conciliar
def P(nome, arts):
    return PerfilGosto.de_dict({'nome': nome, 'top_artistas': {p: arts for p in ('short_term', 'medium_term', 'long_term')}})
ana = P('Ana', ['Banda A', 'Banda B', 'Banda C'])
bia = P('Bia', ['Banda X', 'Banda Y', 'Banda Z'])
cris = P('Cris', ['Banda A', 'Banda X', 'Banda Q'])
duda = P('Duda', ['!!!', '\U0001F3B5'])  # aceito, mas nenhum nome sobrevive ao normalizar_nome
eli = P('Eli', ['Banda B', 'Banda Y', 'Banda R'])
eva = P('Eva', ['Banda A'])
for x, y in [(ana, duda), (ana, bia), (ana, eva)]:
    c = comparar_perfis(x, y); print(f'{x.nome} x {y.nome}:', c.pontuacao, c.nivel)
print('4 pessoas:', conciliar([ana, bia, cris, duda]).pares)
r = conciliar([ana, bia, cris, duda, eli]); print('5 pessoas:', r.pares, 'media', r.pontuacao_media_pares)
r = conciliar([ana, bia, cris, eli]); print('sem Duda:', r.pares, 'media', r.pontuacao_media_pares)
'@ | .venv\Scripts\python.exe -
```

```powershell
@'
import { compararPerfis, conciliar } from './site/app/js/match.js';
const P = (nome, a) => ({ nome, top_artistas: { short_term: a, medium_term: a, long_term: a }, top_musicas: {} });
const ana = P('Ana', ['Banda A', 'Banda B', 'Banda C']), bia = P('Bia', ['Banda X', 'Banda Y', 'Banda Z']);
const cris = P('Cris', ['Banda A', 'Banda X', 'Banda Q']), duda = P('Duda', ['!!!', '\u{1F3B5}']);
const eli = P('Eli', ['Banda B', 'Banda Y', 'Banda R']), eva = P('Eva', ['Banda A']);
for (const [x, y] of [[ana, duda], [ana, bia], [ana, eva]]) { const c = compararPerfis(x, y); console.log(`${x.nome} x ${y.nome}:`, c.pontuacao, c.nivel); }
console.log('4 pessoas:', JSON.stringify(conciliar([ana, bia, cris, duda]).pares));
const r = conciliar([ana, bia, cris, duda, eli]); console.log('5 pessoas:', JSON.stringify(r.pares), 'media', r.pontuacao_media_pares);
'@ | node --input-type=module -
```

  Saída (Python; o JS dá os mesmos números):
  - `Ana x Duda: 0.0 Mundos diferentes`
  - `Ana x Bia: 0.0 Mundos diferentes` (zero real, mesma tela)
  - `Ana x Eva: 58.9 Sintonia rara` (ver R1-02)
  - `4 pessoas: [('Ana', 'Cris'), ('Bia', 'Duda')]`
  - `5 pessoas: [('Ana', 'Cris'), ('Bia', 'Duda', 'Eli')] media 17.0`
  - `sem Duda: [('Ana', 'Cris'), ('Bia', 'Eli')] media 34.0`
- **Impacto:** quem não tem dados comparáveis aparece como "Mundos diferentes", vira par ou entra num trio, e puxa a média do grupo para baixo (neste exemplo, de 34 para 17). O usuário lê como falta de afinidade algo que é falta de dado.
- **Solução proposta:** seguir o padrão que já existe para o ListenBrainz ("Ficaram de fora do Match", `ui/match.py:127`): a pessoa cujo `vetor_artistas` fica vazio sai do Match antes da matriz, com aviso. Como defesa, `comparar_perfis`/`compararPerfis` passam a devolver `pontuacao=None` com o nível "Comparação indisponível", em vez de `0`.
- **Testes necessários:**
  - Python (`tests/test_match.py`) e JS (`tests/js/match.test.mjs`): um perfil com nomes só de pontuação fica de fora com aviso, em grupo par e em grupo ímpar.
  - Paridade (`tests/test_paridade_match.py`): mesmo grupo, mesma lista de excluídos e mesmos pares.
- **Critério de aceitação:** nos dois blocos, Duda não aparece em `pares` e a média com Duda é igual à de `sem Duda` (34.0).

### R1-02 — Match: faixa "Sintonia rara" com amostra mínima e sem aviso de tamanho

- **Classificação:** Problema comprovado
- **Prioridade:** P2
- **Localização:** `conciliacao.py:28-37` (faixas e o comentário "calibradas com 4 históricos reais"), `site/app/js/match.js:14-21`, `match-tela.js:35`.
- **Evidência:** nos blocos do R1-01, `Ana x Eva: 58.9 Sintonia rara`. Eva tem **um** artista no ranking. Não há contagem de artistas válidos nem aviso de amostra em `match-tela.js` ou em `ui/match.py`.
- **Impacto:** a faixa mais alta ("compartilhar playlists é garantia") sai de um único artista em comum. É um score sem base nos dados, o que o escopo da auditoria pede para evitar.
- **Solução proposta:** calcular o tamanho efetivo (artistas válidos de cada lado) junto com a pontuação. Abaixo de um mínimo, mostrar "amostra pequena" e não usar as duas faixas de cima. O mínimo deve ser decidido com dados e documentado em `VALIDACAO.md`; esta auditoria não propõe um número. Se a calibração e a conferência usaram os mesmos 4 históricos ainda está em aberto (§5).
- **Testes necessários:** Python e JS (perfil com 1 artista não recebe "Sintonia rara"), mais paridade do campo novo.
- **Critério de aceitação:** `Ana x Eva` mostra o aviso de amostra pequena nas duas superfícies, e `VALIDACAO.md` registra o mínimo e de onde ele veio.

### R1-03 — Cache de gêneros aceita tipos errados: letras viram gêneros e um número derruba o Match

- **Classificação:** Problema comprovado
- **Prioridade:** P3 (o gatilho é o arquivo editado ou corrompido de um jeito que ainda é JSON válido)
- **Localização:** `generos.py:67-72` (`_ler_disco` só confere se é `dict`), `:79-80` (devolve o valor como está), `:176-180` (`vetor_generos` itera o valor), `ui/match.py:185` (só traduz `ValueError`).
- **Evidência:**

```powershell
@'
import json, os, tempfile
from generos import ConsultaMusicBrainz, preencher_generos, vetor_generos
from perfil_gosto import PerfilGosto
from conciliacao import conciliar
cam = os.path.join(tempfile.mkdtemp(), 'generos.json')
with open(cam, 'w', encoding='utf-8') as f: json.dump({'bandaa': 'rock', 'bandab': 5}, f)
c = ConsultaMusicBrainz(cache=cam)
g = [preencher_generos(PerfilGosto.de_dict({'nome': n, 'top_artistas': {'short_term': [n.replace('Pessoa', 'Banda')]}}), c)
     for n in ('Pessoa A', 'Pessoa B')]
print('Banda A:', g[0].generos, vetor_generos(g[0]))
try: conciliar(g)
except Exception as e: print('conciliar ->', type(e).__name__, e)
with open(cam, 'w', encoding='utf-8') as f: f.write('{corrompido')
print('JSON corrompido ->', ConsultaMusicBrainz(cache=cam)._cache)
'@ | .venv\Scripts\python.exe -
```

  Saída:
  - `Banda A: {'Banda A': 'rock'} {'r': 0.15, 'o': 0.15, 'c': 0.15, 'k': 0.15}`
  - `conciliar -> TypeError 'int' object is not iterable`
  - `JSON corrompido -> {}`
- **Impacto:** o estilo do Match sai com "gêneros" de uma letra só. Com um número no cache, o `conciliar` falha. Como o erro não é `ValueError`, não passa pela mensagem em português de `falha()`; o que aparece na tela não foi verificado (§5).
- **Solução proposta:** em `_ler_disco`, manter só as entradas `str → list[str]`. Gravar `{"versao": N, "artistas": {...}}` e tratar uma versão desconhecida como cache vazio, e cortar o arquivo num número máximo de entradas. A gravação atômica atual fica como está.
- **Testes necessários:** Python (`tests/test_generos.py`): valor `str`, `int`, lista com não-`str`, versão futura e arquivo acima do teto. Sem paridade (o cache só existe no app para PC).
- **Critério de aceitação:** no bloco acima, as duas pessoas ficam sem gêneros, o `conciliar` termina sem erro, e um teste novo cobre cada caso.

### R1-04 — RBO sem validação de parâmetros, com Python e JS divergindo nos inválidos

- **Classificação:** Risco potencial (hoje os dois chamadores, `analise.py:329` e `dupla.js:415`, usam `p=0.9` e `k=50`)
- **Prioridade:** P3
- **Localização:** `metricas.py:61-83`, `site/app/js/dupla.js:61-73`. Os testes atuais (`tests/test_metricas.py:152-164`, `tests/js/rbo.test.mjs:7-15`) só cobrem entradas válidas.
- **Evidência:**

```powershell
@'
from metricas import rbo
a, b = ['x', 'y', 'z'], ['y', 'x', 'w']
for p in [0, 1, -0.1, 1.5, float('nan')]:
    try: print('p', p, rbo(a, b, p=p))
    except Exception as e: print('p', p, type(e).__name__)
for k in [-1, True, 2.5]:
    try: print('k', k, rbo(a, b, k=k))
    except Exception as e: print('k', k, type(e).__name__)
print('duplicada', rbo(['x', 'x', 'x'], ['x', 'y', 'z']))
'@ | .venv\Scripts\python.exe -
```

```powershell
@'
import { rbo } from './site/app/js/dupla.js';
const a = ['x', 'y', 'z'], b = ['y', 'x', 'w'];
for (const p of [0, 1, -0.1, 1.5, NaN]) console.log('p', p, rbo(a, b, p));
for (const k of [-1, true, 2.5]) console.log('k', k, rbo(a, b, 0.9, k));
console.log('duplicada', rbo(['x', 'x', 'x'], ['x', 'y', 'z']));
'@ | node --input-type=module -
```

  | Entrada | Python | JS |
  |---|---|---|
  | `p=0` | `ZeroDivisionError` | `NaN` |
  | `p=1` | `0.667` (o RBO não é definido em `p=1`) | `0.667` |
  | `p=-0.1` / `p=1.5` | `-0.103` / `0.75` | igual |
  | `p=NaN` | `nan` | `NaN` |
  | `k=-1` | `0.0`, por laço vazio (deveria ser inválido; vazio dá `None`) | `0` |
  | `k=True` | aceito como `k=1` (`bool` passa por `int`); aqui `0.0` é o valor correto para k=1 | `0` |
  | `k=2.5` | `TypeError` | `0.7047…` |
  | lista com repetição | `1.0` para `['x','x','x']` × `['x','y','z']` | `1` |
- **Impacto:** nenhum hoje para o usuário. Uma mudança futura (opção de profundidade ou peso) passaria valores sem sentido e quebraria a paridade sem nenhum teste avisar.
- **Solução proposta:** validar na entrada das duas funções: `0 < p < 1` finito; `k` inteiro ≥ 1, recusando `bool`; e listas sem repetição. Usar o mesmo erro (`ValueError` / `RangeError`) e a mesma mensagem.
- **Testes necessários:** Python e JS com a mesma tabela de inválidos, mais invariantes (simetria `rbo(a,b)==rbo(b,a)`, identidade = 1, resultado em [0,1]).
- **Critério de aceitação:** a tabela acima vira erro nos dois lados, e os testes de paridade existentes continuam passando.

### R1-05 — CSS e JS dependem de classes internas do Gradio, e uma já está morta

- **Classificação:** Risco potencial (fragilidade num upgrade do Gradio). A parte já comprovada é pequena: a metade `.wrap.svelte-12ioyct` da regra em `styles.css:184` não casa com nada no Gradio 6.31.
- **Prioridade:** P3 (amortecido pelo pin `gradio==6.31.0` em `requirements.txt:3`)
- **Localização:**
  - `styles.css:184` (`.wrap.svelte-12ioyct`).
  - 53 ocorrências de `.gradio-container` em 40 linhas de `styles.css`, além de `.tab-wrapper` (7), `.tab-container` (6), `.label-wrap` (2), `.wrap` e `.block` (1 cada) e `[data-testid="file"]` (2).
  - `syncup.js:311` (`[aria-label="More tabs"]`, texto interno do Gradio).
  - `ui/layout.py`: nenhuma dependência.
- **Evidência:**

```powershell
(Select-String -Path styles.css -Pattern 'gradio-container' -AllMatches).Matches.Count
(Select-String -Path styles.css -Pattern 'svelte-[a-z0-9]+' -AllMatches).Matches.Value
$t = Get-ChildItem .venv\Lib\site-packages\gradio\templates -Recurse -File -Include *.js,*.css
"svelte-12ioyct: " + ($t | Select-String -SimpleMatch 'svelte-12ioyct' -List).Count
"tab-wrapper: " + ($t | Select-String -SimpleMatch 'tab-wrapper' -List).Count
```

  Saída: `53` · `svelte-12ioyct` · `svelte-12ioyct: 0` · `tab-wrapper: 3`. O bundle do Gradio 6.31 tem 211 classes `svelte-*` diferentes, e essa não está entre elas. Os testes de navegador (`tests/navegador/`) cobrem só o site, não o app para PC.
- **Impacto:** hoje, só a metade `.wrap.svelte-12ioyct` da regra deixa de valer; a outra metade, `[data-testid="file"]`, não foi confirmada no bundle (§5). Num upgrade do Gradio, abas, acordeões e o rótulo "Mais abas" podem perder o estilo ou a tradução sem que nenhum teste falhe.
- **Solução proposta:** apagar a regra morta. Criar um teste estático que confira se cada seletor interno usado em `styles.css`/`syncup.js` (lista curta, mantida no teste) existe no bundle do Gradio instalado. Onde der, trocar por `elem_classes`/`elem_id` próprios.
- **Testes necessários:** Python (`tests/test_smoke_ui.py` ou um novo): seletores internos encontrados em `gradio/templates`. Sem JS.
- **Critério de aceitação:** `svelte-` não aparece mais em `styles.css`, e o teste novo falha se um seletor da lista sumir do Gradio.

### R1-06 — Os estados de erro da entrada web não têm teste de interface

- **Classificação:** Oportunidade de melhoria
- **Prioridade:** P3 (parte do P1 "feedback de carregamento e erro")
- **Localização:** `site/app/js/envio.js:92-150` (estados e `role="alert"`). A **lógica** já é testada em `tests/js/historico.test.mjs:96-108` (ZIP inválido ou mentiroso, entrada > 64 MB, JSON que não é histórico). Na interface só há `tests/navegador/test_app.py:39` (caminho feliz) e `tests/navegador/test_lastfm.py:102` (perfil privado).
- **Evidência:** o comportamento está **correto**. Este roteiro gera 3 arquivos fictícios, serve `site/` e lê o alerta no Chromium:

```powershell
@'
import functools, json, re, tempfile, threading, zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
d = Path(tempfile.mkdtemp())
(d / 'quebrado.zip').write_bytes(b'PK\x03\x04isto nao e um zip')
(d / 'outro.json').write_text('[{"x": 1}]')
reg = [{'ts': '2023-12-30T03:00:00Z', 'ms_played': 200000, 'master_metadata_track_name': 'Faixa Ficticia', 'master_metadata_album_artist_name': 'Banda Ficticia'}]
with zipfile.ZipFile(d / 'grande.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('Streaming_History_Audio_2023.json', json.dumps(reg) + ' ' * (65 * 2**20))
class Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory='site'))
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch()
    for nome in ['quebrado.zip', 'grande.zip', 'outro.json']:
        pg = b.new_page(); pg.goto(f'http://127.0.0.1:{srv.server_port}/app/#wrapped')
        tela = pg.get_by_role('region', name=re.compile('Seu hist.rico'))
        tela.locator('input[type=file]').first.set_input_files(str(d / nome))
        alerta = tela.get_by_role('alert').first; alerta.wait_for(timeout=15000)
        print(nome, '-> alert:', ascii(alerta.inner_text()))
        pg.close()
    b.close()
'@ | .venv\Scripts\python.exe -
```

  Saída (acentos escapados pelo `ascii()`):
  - `quebrado.zip -> alert: 'O arquivo ZIP est\xe1 inv\xe1lido ou incompleto. Baixe o hist\xf3rico novamente.'`
  - `grande.zip -> alert: 'Um arquivo dentro do ZIP passa de 64 MB descompactado, grande demais para o navegador. Use o hist\xf3rico estendido de \xe1udio do Spotify.'`
  - `outro.json -> alert: 'Use o hist\xf3rico estendido de \xe1udio do Spotify (ZIP ou JSON).'`

  Nenhum desses casos está nos 17 testes de navegador.
- **Impacto:** nenhum hoje. Uma regressão só na tela (por exemplo, o alerta não aparecer) passaria pelo CI.
- **Solução proposta:** levar esses 3 casos para `tests/navegador/test_app.py`, com os arquivos gerados no `tmp_path`, conferindo o `role=alert` e o selo "Lendo neste aparelho…" antes do erro.
- **Testes necessários:** Playwright (`-m navegador`).
- **Critério de aceitação:** 3 testes novos, verdes no job `navegador` do CI.

### R1-07 — Limites de tamanho diferentes entre PC e navegador, e a mensagem dos 64 MB orienta errado

- **Classificação:** Limitação conhecida (documentada em `historico.js:5-6` como `shortcut`)
- **Prioridade:** P4
- **Localização:**

  | Limite | PC (Python) | Navegador (JS) |
  |---|---|---|
  | Total descompactado | 1 GB (`dados.py:40`, `:205-210`; upload no `app.py:52`) | 1 GB (`historico.js:4`, `:95`, `:99`) |
  | Por JSON dentro do ZIP | sem limite | 64 MB (`historico.js:7`, `:96`) |
  | Arquivos enviados por pessoa | — | 50 MB comprimidos (`envio.js:12`, `:54`, `:107`) |
- **Evidência:**

```powershell
@'
import json, os, subprocess, tempfile, zipfile
from dados import carregar
reg = [{'ts': '2023-12-30T03:00:00Z', 'ms_played': 200000, 'master_metadata_track_name': 'Faixa Ficticia',
        'master_metadata_album_artist_name': 'Banda Ficticia', 'spotify_track_uri': 'spotify:track:x'}]
cam = os.path.join(tempfile.mkdtemp(), 'grande.zip')
with zipfile.ZipFile(cam, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('Spotify Extended Streaming History/Streaming_History_Audio_2023.json', json.dumps(reg) + ' ' * (65 * 2**20))
print('ZIP', os.path.getsize(cam), 'bytes; Python carregou', len(carregar(cam)), 'linha(s)')
NODE = ("import {lerHistorico} from './site/app/js/historico.js'; import fs from 'node:fs';"
        "try { await lerHistorico([{ nome: 'grande.zip', bytes: new Uint8Array(fs.readFileSync(process.argv[1])) }]); console.log('JS carregou'); }"
        "catch (e) { console.log('JS recusou:', e.message); }")
print(subprocess.run(['node', '--input-type=module', '-e', NODE, cam], capture_output=True, text=True, encoding='utf-8').stdout.strip())
'@ | .venv\Scripts\python.exe -X utf8 -
```

  Saída: `ZIP 66632 bytes; Python carregou 1 linha(s)` · `JS recusou: Um arquivo dentro do ZIP passa de 64 MB descompactado, grande demais para o navegador. Use o histórico estendido de áudio do Spotify.` No Chromium, a mesma frase aparece no `role="alert"` (bloco do R1-06).
- **Impacto:** o mesmo arquivo funciona no PC e falha no navegador. A frase manda "usar o histórico estendido" para quem já está usando. Na prática é raro: o maior JSON real do Spotify tem ~15 MB, segundo o comentário do código.
- **Solução proposta:** trocar a mensagem `entrada` por uma que diga o que fazer de verdade, por exemplo "Um arquivo dentro do ZIP é grande demais para abrir no navegador (passa de 64 MB). Use o app para PC.", e documentar os três limites lado a lado no README ou no `VALIDACAO.md`. Não igualar os limites: o do navegador protege o iOS.
- **Testes necessários:** JS: atualizar a asserção que já existe em `tests/js/historico.test.mjs:101` (hoje ela casa com o texto atual). Sem paridade (é um limite próprio do navegador).
- **Critério de aceitação:** a mensagem nova não sugere o histórico estendido, e a tabela de limites está documentada.

### R1-08 — Normalização de nomes: `ı`, sigma final e Cherokee divergem entre Python e JS

- **Classificação:** Problema comprovado
- **Prioridade:** P4
- **Localização:** `configuracao.py:21` (`casefold()` + `[\W_]+`), `site/app/js/historico.js:106` (`toUpperCase().toLowerCase()` + `[^\p{L}\p{N}]+`), usado também em `dupla.js:182` e `match.js:68,73`. O único caso testado é `ß` (`tests/js/historico.test.mjs:115`).
- **Evidência:** o mesmo bloco testa as 22 datas do R1-09.

```powershell
@'
import json, subprocess
import pandas as pd
from configuracao import normalizar_nome
NODE = "import {normalizarNome, instanteUtc} from './site/app/js/historico.js'; let s=''; process.stdin.on('data', d => s += d).on('end', () => { const [n, t] = JSON.parse(s); console.log(JSON.stringify([n.map(normalizarNome), t.map(x => { const v = instanteUtc(x); return Number.isNaN(v) ? null : v; })])); });"
nomes = ['Stra\u00dfe', '\u0131stanbul', '\ufb01nal', 'Bey\u200bonc\u00e9', '\u03a3\u038a\u03a3\u03a5\u03a6\u039f\u03a3', '\u13a0']
datas = ['2023-12-30T03:00:00Z', '2023-12-30T03:00:00+05:45', '2023-12-30T03:00:00-03:30', '2023-12-30T03:00:00+0545',
         '2023-12-30T03:00:00', '2023-12-30 03:00', '2023-12-30', '2023-02-30T03:00:00Z', '2023-02-29T03:00:00Z',
         '2024-02-29T03:00:00Z', '2023-12-30T24:00:00Z', '2023-12-30T23:59:60Z', '2023-12-30T03:00:00.123456789Z',
         '2023-12-30T03:00:00+14:00', '2023-12-30T03:00:00+23:59', '2023-12-30T03:00:00+24:00', '2023-12-30T03:00:00z',
         '2023-12-30T03:00Z', '20231230T030000Z', '2023-12-30T03:00:00+05', '1969-12-31T23:59:59Z', '  2023-12-30T03:00:00Z  ']
js_n, js_t = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE], input=json.dumps([nomes, datas]),
                                       capture_output=True, text=True, encoding='utf-8', check=True).stdout)
for x, j in zip(nomes, js_n):
    py = normalizar_nome(x); print('OK  ' if py == j else 'DIFF', ascii(x), 'py', ascii(py), 'js', ascii(j))
for x, j in zip(datas, js_t):
    d = pd.to_datetime(pd.Series([x]), utc=True, format='ISO8601', errors='coerce')[0]
    py = None if pd.isna(d) else d.value // 10**6
    print('OK  ' if py == j else 'DIFF', repr(x), 'py', py, 'js', j)
'@ | .venv\Scripts\python.exe -
```

  Nomes: `Straße`, `ﬁnal` e `Bey​oncé` (com espaço de largura zero) dão **OK**. Divergem:
  - `ıstanbul`: Python mantém `ı`, JS vira `istanbul`. No Python, "ıstanbul" e "Istanbul" ficam como artistas diferentes; no JS, viram o mesmo.
  - `ΣΊΣΥΦΟΣ`: Python `σίσυφοσ`, JS `σίσυφος` (sigma final).
  - `Ꭰ`: Python mantém a maiúscula do Cherokee, JS vira a minúscula. Muda a ordem de desempate, que é feita pela chave.
- **Impacto:** raro. Para artistas turcos ou gregos com grafias variadas, o PC e o navegador podem juntar ou separar nomes de forma diferente e dar números diferentes na Dupla e no Match.
- **Solução proposta:** igualar o JS ao `casefold` nesses casos (mapear `ı→i`, `ς→σ` e o Cherokee para maiúscula depois do `toLowerCase`) ou o Python ao JS. A escolha fica para o PR, com os mesmos casos nos dois lados.
- **Testes necessários:** paridade com a tabela de nomes em `tests/js/historico.test.mjs` e `tests/test_dados.py`, com os mesmos valores esperados.
- **Critério de aceitação:** as 6 linhas de nomes do bloco dão `OK`.

### R1-09 — Parser de datas: 3 formatos raros divergem entre Python e JS

- **Classificação:** Problema comprovado
- **Prioridade:** P4 (nenhum desses formatos aparece no Spotify, que usa `…Z`, nem no Last.fm)
- **Localização:** `site/app/js/historico.js:126-144` (regex `ISO` e `instanteUtc`) × `dados.py:390` (`pd.to_datetime(..., utc=True, format='ISO8601', errors='coerce')`). Datas antes de 1970 são descartadas depois, nos dois lados (`dados.py:392`, `historico.js:232`).
- **Evidência:** o bloco do R1-08, 22 strings. 19 dão `OK`, entre elas: `+05:45`, `-03:30`, `+0545`, sem fuso, só a data, `30/02`, `29/02` de ano não bissexto, `24:00`, `23:59:60`, nanossegundos, `+14:00`, `z` minúsculo (recusado nos dois) e espaços nas pontas. Divergem:
  - `'2023-12-30T03:00:00+24:00'`: Python `None`, JS `1703818800000`.
  - `'20231230T030000Z'` (ISO básico): Python `1703905200000`, JS `None`.
  - `'2023-12-30T03:00:00+05'` (offset só com hora): Python `1703887200000`, JS `None`.

  Ressalva: o pandas foi chamado elemento por elemento. No `dados.py`, ele lê a coluna inteira de uma vez.
- **Impacto:** nenhum com as fontes atuais. Um JSON montado à mão perderia linhas diferentes no PC e no navegador, aparecendo como "datas inválidas".
- **Solução proposta:** documentar o subconjunto aceito (o do JS) e fazer o Python recusar o que fica de fora, ou aceitar os dois formatos no JS. A paridade é o que importa.
- **Testes necessários:** a mesma tabela de 22 strings em `tests/js/historico.test.mjs` e `tests/test_dados.py`, com o mesmo resultado esperado.
- **Critério de aceitação:** as 22 linhas de datas do bloco dão `OK`.

### R1-10 — Convite descarta músicas malformadas sem avisar

- **Classificação:** Problema comprovado
- **Prioridade:** P4 (só acontece com um convite alterado à mão, porque o app sempre gera o formato certo)
- **Localização:** `convite.py:85` (`if isinstance(m, list) and len(m) == 2`), `site/app/js/convite.js:67` (`.filter(...)`).
- **Evidência:**

```powershell
$c = @'
import json, zlib, base64
from convite import PREFIXO
d = {'n': 'Teste', 'a': {'short_term': ['Banda A']}, 'm': {'short_term': [['Faixa 1', 'Banda A'], 'lixo', [1], ['a', 'b', 'c'], {'x': 1}]}}
print(PREFIXO + base64.urlsafe_b64encode(zlib.compress(json.dumps(d).encode())).decode().rstrip('='))
'@ | .venv\Scripts\python.exe -
"from convite import ler_convite; p = ler_convite('$c'); print('Python: musicas lidas', len(p.top_musicas['short_term']), 'de 5')" | .venv\Scripts\python.exe -
"import { lerConvite } from './site/app/js/convite.js'; const p = await lerConvite('$c'); console.log('JS: musicas lidas', p.top_musicas.short_term.length, 'de 5');" | node --input-type=module -
```

  Saída: `Python: musicas lidas 1 de 5` · `JS: musicas lidas 1 de 5`. Um artista que não seja texto, por outro lado, recusa o convite inteiro ("O convite está incompleto ou foi alterado…").
- **Impacto:** quase nenhum hoje. O tratamento é incoerente: artista malformado recusa o convite, música malformada some.
- **Solução proposta:** tratar a música malformada como o artista (recusar com a mesma mensagem), já que o convite é sempre gerado pelo app e qualquer forma errada indica alteração.
- **Testes necessários:** `tests/test_convite.py` e `tests/js/convite.test.mjs` com o mesmo código malformado, e a mesma mensagem nos dois.
- **Critério de aceitação:** o bloco acima recusa o convite nos dois lados.

## 5. O que já funciona bem

- **Suítes verdes e rápidas:** 295 testes Python, 105 JS e 17 de navegador, sem falhas no Windows.
- **Paridade de verdade:**
  - `tests/test_paridade_{dupla,match,wrapped}.py` rodam o motor JS no Node e comparam número a número.
  - Os blocos do R1-01 deram valores idênticos nos dois motores, inclusive o arredondamento (`arredondar1` reproduz o `round` do Python).
  - O RBO com entradas válidas bate até o último dígito.
- **Golden master** (`tests/golden/`, `test_golden_master.py`).
- **Fuso horário exato:** o `relogio()` com cache por dia e por hora bateu com o pandas nos 6.787 instantes em torno de 11 transições de DST (§3.1).
- **ZIP endurecido no navegador** (`historico.js:51-76`): a descompressão para no tamanho declarado ("cabeçalho mentiroso"), recusa senha e métodos raros e confere o total de 1 GB antes de abrir.
- **Datas impossíveis** (30/02, 24:00, 23:59:60) e anteriores a 1970 são recusadas igualmente nos dois motores.
- **Entradas vazias barradas cedo:** perfil sem ranking, convite sem artistas e histórico sem plays são recusados com mensagem, nos dois motores.
- **Cache de gêneros:** gravação atômica com mescla entre sessões (`generos.py:114-133`), falha de rede fora do cache e recuperação de JSON corrompido.
- **Convite:** limites de tamanho do código e do JSON descompactado e mensagens claras para código cortado. Python e JS se comportam igual.
- **A Dupla não finge um zero:** com dados insuficientes, recusa com mensagem própria (`analise.py:332`). O R1-01 é dar ao Match um tratamento equivalente.
- **Entrada web:** estados visíveis, erros anunciados (`role="alert"`) e cancelamento de leitura.

## 6. Necessita investigação

- **App para PC:** não foi aberto nesta rodada. Faltam ver:
  - o que a tela mostra quando o `TypeError` do R1-03 escapa (`ui/match.py:185` só traduz `ValueError`);
  - os erros de entrada do ZIP no Gradio (pelo código, `gr.Error` em português via `falha()`).
- **`[data-testid="file"]` no Gradio 6.31** (`styles.css:184`, segunda metade da regra): uma busca estática no bundle não encontrou o atributo com o valor `file`, que pode ser montado em tempo de execução. Conferir no app aberto antes de apagar a regra inteira.
- **Selo "Lendo neste aparelho…"** (`envio.js:134`): existe no código, mas não foi observado na tela (a leitura dos arquivos de teste é rápida demais).
- **Calibração × validação do Match:** `conciliacao.py:28` diz que as faixas foram calibradas com 4 históricos reais. `VALIDACAO.md:73` registra o Match conferido no Chromium com 4 históricos reais, o que é uma checagem de interface e não uma validação das faixas. Não está documentado se houve dados separados para validar. Fica para o item 5 da Rodada 3.
- **Last.fm fora do ar, lento ou com limite de taxa:** não reproduzido (precisa simular a rede). Fica para o item 4 da Rodada 3.

## 7. Lista curta (fora dos 10 achados)

- `rbo` com listas repetidas dá 1,0 (`['x','x','x']` × `['x','y','z']`). Os rankings atuais não têm repetição; entra na validação do R1-04.
- `jaccard_artistas` também colapsa `None → 0` (`conciliacao.py:123`, `match.js:122`); entra no R1-01.
- O prompt aponta `site/app/js/calculo.js` para o RBO, mas ele está em `dupla.js:61`.
- `StarletteDeprecationWarning` no `fastapi.testclient` (aviso de dependência, sem efeito hoje).
- Busca por skills externas (`npx skills find "python javascript parity"`, `"data validation audit"`): nada que cubra uma lacuna das skills já instaladas.

## 8. Plano de PRs (um item por PR, nesta ordem)

| # | PR | Achado | Toca |
|---|---|---|---|
| 1 | Match: pessoa sem dados comparáveis sai com aviso; `pontuacao=None` como defesa | R1-01 | `conciliacao.py`, `match.js`, `match-tela.js`, `ui/match.py`, testes + paridade |
| 2 | Match: aviso de amostra pequena e mínimo documentado | R1-02 | idem + `VALIDACAO.md` |
| 3 | Cache de gêneros: tipos, versão e teto | R1-03 | `generos.py`, `tests/test_generos.py` |
| 4 | RBO: validação igual nos dois motores | R1-04 | `metricas.py`, `dupla.js`, `test_metricas.py`, `rbo.test.mjs` |
| 5 | Gradio: apagar a regra morta (depois de conferir §6) e testar os seletores internos | R1-05 | `styles.css`, teste novo |
| 6 | Testes de navegador para os erros da entrada | R1-06 | `tests/navegador/test_app.py` |
| 7 | Mensagem dos 64 MB e tabela de limites | R1-07 | `historico.js`, README/`VALIDACAO.md` |
| 8 | Normalização Unicode igual nos dois motores | R1-08 | `configuracao.py` ou `historico.js`, testes |
| 9 | Datas: mesmo subconjunto ISO nos dois motores | R1-09 | `historico.js` ou `dados.py`, testes |
| 10 | Convite: música malformada recusa o convite | R1-10 | `convite.py`, `convite.js`, testes |

Os PRs 1 e 2 mexem nos mesmos arquivos e devem sair em sequência. Os PRs 3 a 10 são independentes entre si.
