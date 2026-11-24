"""Gera notebook/SyncUp_CRISP-DM.ipynb (projeto acadêmico, 6 fases do CRISP-DM).

O notebook é autocontido (Pandas, NumPy, Seaborn, Matplotlib) para rodar no
Colab sem instalar o app. É salvo SEM saídas: gráficos e tabelas com dados
reais não entram no repositório público. Uso:

    python tools/gerar_notebook.py
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

DESTINO = Path(__file__).resolve().parents[1] / 'notebook' / 'SyncUp_CRISP-DM.ipynb'
CELULAS: list = []


def md(texto: str) -> None:
    CELULAS.append(nbf.v4.new_markdown_cell(texto.strip()))


def code(texto: str) -> None:
    CELULAS.append(nbf.v4.new_code_cell(texto.strip()))


md(r"""
# 🎧 SyncUp — Projeto de Dados com CRISP-DM

**Ciência de Dados I · UCL** · Carlos Henrique

**Pergunta do projeto:** *Usando o histórico real do Spotify de um grupo de amigos, quem combina musicalmente com quem — em quê, em quanto — e o que cada um pode recomendar ao outro?*

| Fase do CRISP-DM | Neste notebook | No app SyncUp |
|---|---|---|
| 1. Entendimento do Negócio | pergunta, critérios de sucesso e hipótese | — |
| 2. Entendimento dos Dados | leitura dos ZIPs, qualidade, **`describe()`** e gráficos **Seaborn** | `dados.py` |
| 3. Preparação dos Dados | limpeza, fuso, plays ≥ 30 s, período comum | `dados.py`, `configuracao.py` |
| 4. Modelagem | **Jaccard** (conjuntos), **cosseno** (vetores), matriz e **duplas ótimas** | `metricas.py`, `conciliacao.py` |
| 5. Avaliação | interpretação, conclusões e limitações | `VALIDACAO.md`, testes |
| 6. Implantação | recomendações + app/site | `app.py`, `ui/`, site |

Ferramentas: **Pandas** e **Seaborn** (base da disciplina), NumPy e Matplotlib.
""")

md(r"""
## ⚙️ Configuração

Rode as células em ordem (**Ambiente de execução → Executar tudo**). Use **um ZIP do Histórico Estendido por pessoa** (2 a 8 pessoas).

- Se os ZIPs já estiverem na pasta do notebook, ajuste o dicionário `PESSOAS` abaixo.
- Se não estiverem, no Colab abre uma janela para **escolher os ZIPs** de uma vez; o nome de cada pessoa vem do nome do arquivo (`carlos_historico.zip` → *Carlos*).
""")

code(r"""
# Pessoa → arquivo ZIP do Histórico Estendido do Spotify
PESSOAS = {
    'Carlos': 'carlos_historico.zip',
    'Japa': 'japa_historico.zip',
}

import itertools, json, os, zipfile
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style='whitegrid', palette='Set2')
pd.set_option('display.float_format', lambda x: f'{x:,.2f}')

if not all(os.path.exists(f) for f in PESSOAS.values()):
    from google.colab import files  # só existe no Colab
    print('Selecione os ZIPs (um por pessoa, pode marcar vários):')
    enviados = files.upload()
    PESSOAS = {os.path.basename(n).split('_')[0].split('.')[0].capitalize(): n for n in enviados}

NOMES = list(PESSOAS)
CORES = dict(zip(NOMES, sns.color_palette('Set2', len(NOMES))))
print('Pessoas:', ', '.join(f'{n} ({a})' for n, a in PESSOAS.items()))
""")

# ---------------- Fase 1
md(r"""
# 1️⃣ Entendimento do Negócio

**Contexto.** O Spotify faz o *Blend* entre duas pessoas, mas não mostra **como** chega no resultado nem diz, num grupo, **quem combina com quem**. O SyncUp responde isso com os dados reais e de forma explicável.

**Perguntas**
1. Como cada pessoa ouve música? (quanto, quando, quem)
2. Quanto os gostos se parecem — em **quais artistas** e **com que intensidade**?
3. Num grupo, quais **duplas** combinam mais, e o que cada um pode **recomendar** ao outro?

**Critérios de sucesso.** Similaridades explicáveis (Jaccard e cosseno), apoiadas por estatísticas descritivas e gráficos; uma divisão do grupo em duplas justificada pelos dados; recomendações para cada dupla.

**Hipótese inicial.** Amigos têm *alguns* artistas em comum, mas gostos ainda bem diferentes: a similaridade deve ser baixa ou média, nunca perto de 100%.
""")

# ---------------- Fase 2
md(r"""
# 2️⃣ Entendimento dos Dados

O Spotify entrega o histórico como vários JSONs dentro de um ZIP. **Cada linha é uma reprodução** (uma vez que uma música tocou).
""")

code(r"""
def carregar_historico(caminho_zip, nome):
    # Lê todos os JSONs de áudio do ZIP e devolve um DataFrame
    registros = []
    with zipfile.ZipFile(caminho_zip) as z:
        for arquivo in z.namelist():
            base = arquivo.rsplit('/', 1)[-1]
            if arquivo.endswith('.json') and 'Audio' in arquivo and not base.startswith('._'):
                registros += json.loads(z.read(arquivo))
    df = pd.DataFrame(registros)
    df['pessoa'] = nome
    return df

bruto = pd.concat([carregar_historico(a, n) for n, a in PESSOAS.items()], ignore_index=True)
print(f'Reproduções: {len(bruto):,} · colunas: {len(bruto.columns)}')
bruto.groupby('pessoa').size().rename('reproduções')
""")

code(r"""
colunas = ['ts', 'ms_played', 'master_metadata_track_name',
           'master_metadata_album_artist_name', 'skipped', 'shuffle', 'pessoa']
bruto[colunas].head()
""")

md(r"""
### Dicionário dos dados (colunas usadas)

| Coluna | Significado |
|---|---|
| `ts` | data e hora em que a reprodução terminou (UTC) |
| `ms_played` | quanto tempo tocou, em milissegundos |
| `master_metadata_track_name` | música (vazio = podcast/vídeo) |
| `master_metadata_album_artist_name` | artista |
| `skipped` | se a faixa foi pulada |
| `shuffle` | se estava no modo aleatório |

### Qualidade: valores ausentes
""")

code(r"""
bruto[colunas].isna().sum().rename('valores vazios')
""")

md(r"""
### EDA com `describe()` — tempo de cada reprodução

O `describe()` resume uma coluna numérica: **count** (quantidade), **mean** (média), **std** (desvio padrão), **min**, **25%** (1º quartil), **50%** (mediana), **75%** (3º quartil) e **max**.
""")

code(r"""
bruto['minutos'] = bruto['ms_played'] / 60000
bruto.groupby('pessoa')['minutos'].describe()
""")

code(r"""
d = bruto.groupby('pessoa')['minutos'].describe()
for p in d.index:
    print(f"{p}: {d.loc[p,'count']:,.0f} reproduções; média {d.loc[p,'mean']:.2f} min, mediana {d.loc[p,'50%']:.2f} min "
          f"(desvio padrão {d.loc[p,'std']:.2f}).")
    print(f"   25% duram menos de {d.loc[p,'25%']*60:.0f} s → faixas puladas logo no começo; "
          f"o máximo ({d.loc[p,'max']:.0f} min) é um outlier.")
print('\nLeitura: há muitas reproduções curtíssimas (pulos). Na Preparação só contamos plays de 30 s ou mais.')
""")

code(r"""
fig, ax = plt.subplots(1, 2, figsize=(14, 4.5))
curtas = bruto[bruto['minutos'] <= 8]
sns.histplot(data=curtas, x='minutos', hue='pessoa', bins=48, palette=CORES, element='step', ax=ax[0])
ax[0].axvline(0.5, color='red', ls='--')
ax[0].set_title('Distribuição do tempo tocado (até 8 min)\nlinha vermelha = 30 segundos')
sns.boxplot(data=curtas, x='pessoa', y='minutos', hue='pessoa', palette=CORES, ax=ax[1], legend=False)
ax[1].set_title('Boxplot: mediana e quartis do tempo tocado')
plt.tight_layout(); plt.show()
""")

md(r"""
**Leitura:** há um pico perto de **0 minuto** (pulos) e outro em **2–4 minutos** (músicas ouvidas inteiras). Isso justifica a regra do Spotify de contar um *play* só a partir de **30 segundos**.
""")

# ---------------- Fase 3
md(r"""
# 3️⃣ Preparação dos Dados

1. **Remover podcasts/vídeos** → não têm artista musical.
2. **Converter `ts`** para o fuso de **São Paulo** → horários reais.
3. **Criar colunas** `hora`, `dia_semana`, `ano`, `mes`.
4. **Manter só plays ≥ 30 s** → regra do Spotify.
5. **Usar só o período comum a todos** → comparação justa.
""")

code(r"""
df = bruto.dropna(subset=['master_metadata_track_name', 'master_metadata_album_artist_name']).copy()
df = df.rename(columns={'master_metadata_track_name': 'musica',
                        'master_metadata_album_artist_name': 'artista'})
df['data'] = pd.to_datetime(df['ts'], utc=True).dt.tz_convert('America/Sao_Paulo')
df['hora'] = df['data'].dt.hour
df['dia_semana'] = df['data'].dt.dayofweek          # 0 = segunda ... 6 = domingo
df['ano'] = df['data'].dt.year
df['mes'] = df['data'].dt.strftime('%Y-%m')

plays = df[df['ms_played'] >= 30000].copy()
inicio = plays.groupby('pessoa')['data'].min().max()
fim = plays.groupby('pessoa')['data'].max().min()
plays = plays[(plays['data'] >= inicio) & (plays['data'] <= fim)]

print(f'Reproduções: {len(bruto):,} → músicas: {len(df):,} → plays ≥30s no período comum: {len(plays):,}')
print(f'Período comum: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}')
plays.groupby('pessoa').agg(plays=('musica', 'size'), horas=('minutos', lambda m: m.sum() / 60),
                            artistas=('artista', 'nunique'), musicas=('musica', 'nunique'))
""")

md(r"""
### `describe()` — quantas músicas cada pessoa ouve por dia
""")

code(r"""
por_dia = plays.groupby(['pessoa', plays['data'].dt.date]).size().rename('plays_no_dia').reset_index()
d = por_dia.groupby('pessoa')['plays_no_dia'].describe()
for p in d.index:
    print(f"{p}: num dia típico (mediana) ouve {d.loc[p,'50%']:.0f} músicas; metade dos dias fica entre "
          f"{d.loc[p,'25%']:.0f} e {d.loc[p,'75%']:.0f}; recorde de {d.loc[p,'max']:.0f}.")
d
""")

md(r"""
### `describe()` — plays por artista (a "cauda longa")
""")

code(r"""
por_artista = plays.groupby(['pessoa', 'artista']).size().rename('plays').reset_index()
d = por_artista.groupby('pessoa')['plays'].describe()
for p in d.index:
    print(f"{p}: {d.loc[p,'count']:.0f} artistas; mediana de {d.loc[p,'50%']:.0f} play(s) por artista, "
          f"média {d.loc[p,'mean']:.1f}, máximo {d.loc[p,'max']:.0f}.")
print('\nLeitura: a maioria dos artistas foi ouvida pouquíssimas vezes e poucos favoritos concentram muitos plays.')
print('Isso pesa na Modelagem: o Jaccard sofre com a cauda longa e o cosseno bruto é dominado pelos favoritos.')
d
""")

md(r"""
### Visualizações exploratórias (Seaborn)
""")

code(r"""
colunas_graf = min(len(NOMES), 2)
linhas_graf = -(-len(NOMES) // colunas_graf)
fig, ax = plt.subplots(linhas_graf, colunas_graf, figsize=(15, 5 * linhas_graf), squeeze=False)
for i, p in enumerate(NOMES):
    eixo = ax[i // colunas_graf][i % colunas_graf]
    top = por_artista[por_artista['pessoa'] == p].nlargest(10, 'plays')
    sns.barplot(data=top, y='artista', x='plays', color=CORES[p], ax=eixo)
    eixo.set_title(f'Top 10 artistas — {p}'); eixo.set_ylabel('')
for j in range(len(NOMES), linhas_graf * colunas_graf):
    ax[j // colunas_graf][j % colunas_graf].axis('off')
plt.tight_layout(); plt.show()
""")

code(r"""
dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
sns.set_style('white')
fig, ax = plt.subplots(linhas_graf, colunas_graf, figsize=(16, 4.2 * linhas_graf), squeeze=False)
for i, p in enumerate(NOMES):
    eixo = ax[i // colunas_graf][i % colunas_graf]
    tabela = plays[plays['pessoa'] == p].pivot_table(index='dia_semana', columns='hora', values='musica',
                                                     aggfunc='size', fill_value=0)
    sns.heatmap(tabela / tabela.values.sum() * 100, cmap='Greens', ax=eixo, cbar_kws={'label': '% dos plays'})
    eixo.set_yticklabels(dias, rotation=0); eixo.set_title(f'Quando {p} ouve música (dia × hora)')
for j in range(len(NOMES), linhas_graf * colunas_graf):
    ax[j // colunas_graf][j % colunas_graf].axis('off')
plt.tight_layout(); plt.show()
sns.set_style('whitegrid')
""")

code(r"""
mensal = plays.groupby(['pessoa', 'mes'])['minutos'].sum().div(60).rename('horas').reset_index().sort_values('mes')
plt.figure(figsize=(15, 4.2))
sns.lineplot(data=mensal, x='mes', y='horas', hue='pessoa', palette=CORES, marker='o')
plt.xticks(sorted(mensal['mes'].unique())[::6], rotation=45)
plt.title('Horas ouvidas por mês'); plt.xlabel(''); plt.tight_layout(); plt.show()
""")

# ---------------- Fase 4
md(r"""
# 4️⃣ Modelagem

Duas técnicas vistas em aula:

**Jaccard (conjuntos)** — só presença/ausência de artistas: $J(A,B) = \frac{|A \cap B|}{|A \cup B|}$

**Cosseno (vetores)** — cada artista é uma posição do vetor e o valor é o número de plays: $\cos\theta = \frac{A \cdot B}{\lVert A\rVert\,\lVert B\rVert}$

Usamos também o cosseno com $\log(1 + \text{plays})$, que reduz o peso exagerado dos favoritos (um artista com 2.000 plays não deve valer 100× um com 20).
""")

code(r"""
contagem = por_artista.pivot_table(index='artista', columns='pessoa', values='plays', fill_value=0).astype(int)

def jaccard(A, B):
    return len(A & B) / len(A | B)

def cosseno(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

conjuntos = {p: set(contagem.index[contagem[p] > 0]) for p in NOMES}
linhas = []
for a, b in itertools.combinations(NOMES, 2):
    va, vb = contagem[a].values, contagem[b].values
    linhas.append({
        'dupla': f'{a} × {b}',
        'artistas em comum': len(conjuntos[a] & conjuntos[b]),
        'Jaccard': jaccard(conjuntos[a], conjuntos[b]) * 100,
        'Cosseno (plays)': cosseno(va, vb) * 100,
        'Cosseno log': cosseno(np.log1p(va), np.log1p(vb)) * 100,
    })
resultados = pd.DataFrame(linhas).set_index('dupla').sort_values('Cosseno log', ascending=False)
resultados
""")

code(r"""
longo = resultados.drop(columns='artistas em comum').reset_index().melt(id_vars='dupla', var_name='métrica', value_name='%')
plt.figure(figsize=(11, 0.9 * len(resultados) + 2.5))
sns.barplot(data=longo, y='dupla', x='%', hue='métrica', palette='crest')
plt.title('Similaridade por dupla e por métrica (%)'); plt.ylabel(''); plt.xlim(0, 100)
plt.tight_layout(); plt.show()
""")

md(r"""
### Matriz de todos com todos e duplas ótimas (o "Match" do app)

Com 3 ou mais pessoas, montamos a **matriz de similaridade** (cosseno log) e escolhemos a divisão em duplas que deixa o **grupo inteiro** mais satisfeito: a que **maximiza a soma** das similaridades. Isso nem sempre junta o par mais parecido — às vezes separá-lo evita que alguém fique com um par quase sem nada em comum. Com número ímpar, quem sobra entra na dupla em que combina melhor (trio).
""")

code(r"""
matriz = pd.DataFrame(100.0, index=NOMES, columns=NOMES)
for a, b in itertools.combinations(NOMES, 2):
    matriz.loc[a, b] = matriz.loc[b, a] = resultados.loc[f'{a} × {b}', 'Cosseno log']

plt.figure(figsize=(1.6 * len(NOMES) + 3, 1.3 * len(NOMES) + 2))
sns.set_style('white')
sns.heatmap(matriz.mask(np.eye(len(NOMES), dtype=bool)), annot=True, fmt='.1f', cmap='Greens', cbar_kws={'label': 'cosseno log (%)'})
plt.title('Similaridade de todos com todos (%)'); plt.tight_layout(); plt.show()
sns.set_style('whitegrid')

def duplas_otimas(nomes):
    # Testa todas as divisões em duplas (rápido até 8 pessoas) e fica com a de maior soma
    melhor, melhor_total = None, -1
    for ordem in itertools.permutations(nomes):
        if ordem[0] != nomes[0]:
            break
        pares = [tuple(sorted(ordem[i:i + 2])) for i in range(0, len(ordem) - 1, 2)]
        total = sum(matriz.loc[x, y] for x, y in pares)
        if total > melhor_total:
            melhor, melhor_total = pares, total
    if len(nomes) % 2:  # quem sobrou vira trio na dupla em que combina melhor
        sobra = [n for n in nomes if all(n not in p for p in melhor)][0]
        i = max(range(len(melhor)), key=lambda k: sum(matriz.loc[sobra, x] for x in melhor[k]))
        melhor[i] = melhor[i] + (sobra,)
    return melhor

if len(NOMES) >= 3:
    grupos = duplas_otimas(NOMES)
    for g in grupos:
        media = np.mean([matriz.loc[x, y] for x, y in itertools.combinations(g, 2)])
        print(f"🎧 {' + '.join(g)}: {media:.1f}%")
    mais_parecidos = max(itertools.combinations(NOMES, 2), key=lambda p: matriz.loc[p[0], p[1]])
    a, b = mais_parecidos
    print(f"\nPar mais parecido: {a} × {b} ({matriz.loc[a, b]:.1f}%)")
else:
    grupos = [tuple(NOMES)]
    print('Com 2 pessoas, a dupla é única. Adicione mais ZIPs para ver o Match do grupo.')
""")

md(r"""
### Quais artistas mais aproximam cada dupla?

No cosseno, cada artista contribui com $\frac{a_i \cdot b_i}{\lVert A\rVert \lVert B\rVert}$; a soma das contribuições é o cosseno.
""")

code(r"""
def contribuicoes(a, b, n=8):
    la, lb = np.log1p(contagem[a].values), np.log1p(contagem[b].values)
    c = pd.Series(la * lb / (np.linalg.norm(la) * np.linalg.norm(lb)) * 100, index=contagem.index)
    return c[c > 0].nlargest(n)

pares_mostrados = [p for g in grupos for p in itertools.combinations(g, 2)][:4]
fig, ax = plt.subplots(1, len(pares_mostrados), figsize=(7 * len(pares_mostrados), 4.5), squeeze=False)
for eixo, (a, b) in zip(ax[0], pares_mostrados):
    top = contribuicoes(a, b).rename('contribuição').reset_index()
    sns.barplot(data=top, y='artista', x='contribuição', color='#1DB954', ax=eixo)
    eixo.set_title(f'O que aproxima {a} e {b} (p.p.)'); eixo.set_ylabel('')
plt.tight_layout(); plt.show()
""")

# ---------------- Fase 5
md(r"""
# 5️⃣ Avaliação

Os números respondem às perguntas do negócio?
""")

code(r"""
melhor = resultados.index[0]
r = resultados.loc[melhor]
print(f"1) A dupla mais parecida é {melhor}: Jaccard {r['Jaccard']:.1f}%, cosseno {r['Cosseno (plays)']:.1f}%, "
      f"cosseno log {r['Cosseno log']:.1f}% ({int(r['artistas em comum'])} artistas em comum).")
if len(resultados) > 1:
    print(f"2) Em todas as duplas, o Jaccard fica entre {resultados['Jaccard'].min():.1f}% e {resultados['Jaccard'].max():.1f}%: "
          'cada pessoa ouve muita coisa que as outras nunca ouviram (cauda longa).')
    print(f"3) O cosseno log fica entre {resultados['Cosseno log'].min():.1f}% e {resultados['Cosseno log'].max():.1f}%: "
          'os artistas compartilhados costumam ser muito ouvidos pelos dois.')
else:
    print(f"2) O Jaccard ({r['Jaccard']:.1f}%) é bem menor que o cosseno log ({r['Cosseno log']:.1f}%): poucos artistas em comum,"
          ' mas os compartilhados são muito ouvidos pelos dois.')
if len(NOMES) >= 3:
    print(f"4) Divisão ótima do grupo: {' | '.join(' + '.join(g) for g in grupos)}.")
print('Hipótese confirmada: há base em comum, mas nenhuma dupla passa perto de 100%.')
""")

md(r"""
**Conclusões**
- **Jaccard** mede *quantos* artistas são compartilhados; **cosseno** mede *o quanto o padrão de escuta* se parece. Os dois juntos dão uma visão completa.
- A EDA com `describe()` explica os números baixos: a **cauda longa** (mediana de poucos plays por artista) derruba o Jaccard, e poucos **favoritos** dominam o cosseno bruto — por isso o log.
- Num grupo, a **melhor divisão** maximiza a soma das similaridades, não só o par mais parecido.

**Limitações**
- O histórico mostra o que **tocou**, não o que a pessoa **gosta** (músicas de fundo, playlists de terceiros).
- Variações de nomes ("feat.", grafias) não são unificadas aqui.
- Poucas pessoas: os limiares de "alta" ou "baixa" compatibilidade são calibrados nesta amostra.
""")

# ---------------- Fase 6
md(r"""
# 6️⃣ Implantação

**Recomendação por similaridade** (mesma ideia do *Projeto 01* da aula): numa dupla, recomendamos a cada um o que o outro ouve muito e ele ainda não ouviu.
""")

code(r"""
def recomendar(de, para, n=8):
    candidatos = contagem[(contagem[de] > 0) & (contagem[para] == 0)][de]
    return candidatos.nlargest(n).rename(f'plays de {de}').reset_index()

for g in grupos:
    for de, para in itertools.permutations(g, 2):
        print(f'🎧 {de} pode apresentar a {para}:')
        display(recomendar(de, para))
""")

md(r"""
### O produto: SyncUp

Toda esta análise virou o **SyncUp**, de código aberto:

- **No navegador** (sem instalar): <https://hazykiuu.github.io/SyncUp/app/> — Dupla, Wrapped, Batalha e **Match** (2 a 16 pessoas, duplas ótimas, como na Modelagem acima).
- **App para PC** (`python app.py`): também o Grupo e fontes extras do Match (ListenBrainz e convite por código). A conciliação fica em `conciliacao.py`, com rankings ponderados para comparar fontes diferentes de forma justa.
- O login direto com o Spotify foi avaliado e descartado: a API limita apps novos a 5 contas e não entrega o histórico completo (`docs/decisao-spotify.md`).
- Testes automáticos (`pytest`) conferem as métricas, a conciliação e a privacidade a cada mudança.

**Próximos passos:** usar gêneros musicais, unificar nomes de artistas e comparar grupos maiores.
""")


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb['cells'] = CELULAS
    nb['metadata'] = {
        'colab': {'provenance': []},
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'},
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, DESTINO)
    print(f'{DESTINO} ({len(CELULAS)} células)')


if __name__ == '__main__':
    main()
