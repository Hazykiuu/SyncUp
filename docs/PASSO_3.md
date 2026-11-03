# SyncUp v0.5 — Passo 3 de 4

Entrega das **Fases 4, 5 e 6**: métricas avançadas, recursos locais, gráficos Plotly e interface Gradio 5. A implementação anterior de ingestão, filtros, fuso, diagnóstico e cache foi preservada. O Passo 4 não faz parte desta entrega.

**Arquétipos e traços descrevem este recorte de escuta. São regras experimentais: não medem personalidade ou afinidade amorosa.** Os limiares são visíveis na interface, no radar e nos cartões de perfil.

## Instalar e executar

Python 3.10 ou superior, pandas >=2.2,<3, Gradio >=5,<6, Plotly e Pillow. Nenhum módulo atual importa NumPy diretamente. Pandas, Plotly e Gradio podem ter NumPy como dependência interna.

No terminal, dentro da pasta `SyncUp` extraída:

```powershell
py -m pip install -r requirements.txt
py app.py
```

Linux/macOS: use `python` ou `python3` no lugar de `py`. O navegador abre a interface local. Para cache Parquet opcional:

```powershell
py -m pip install -r requirements-parquet.txt
```

O cache de disco continua desligado por padrão. `tzdata` é instalado no Windows para os fusos IANA. As fontes do tema e do PNG são locais; a geração do cartão não acessa a rede.

## Como usar

**Dupla:** cada painel corresponde a uma pessoa. Envie uma ou várias partes ZIP/JSON de seu Histórico Estendido do Spotify em cada painel. Todas as partes de um painel são unidas. Arquivos inteiros com SHA-256 repetido no mesmo painel são rejeitados; eventos repetidos entre partes seguem a opção de deduplicação. Não misture pessoas em um painel.

Escolha o fuso, o período, os filtros e a ponderação, e clique em **Comparar históricos**. Os botões da aba de playlist e cartão geram exportações do último resultado calculado. Depois de alterar opções, refaça a comparação para que os arquivos reflitam as novas escolhas.

**Grupo:** envie de três a seis arquivos, um por pessoa, e escreva um nome por linha na mesma ordem exibida. Nomes devem ser distintos. Para várias partes por pessoa, use a API Python abaixo. O recorte comum é a **interseção UTC de todo o grupo**, aplicada a todas as células da matriz. Sem interseção, desmarque a opção; a matriz então compara coberturas potencialmente diferentes. SHA repetido entre perfis é indicado no diagnóstico/resumo.

**Plays** são execuções ≥30 segundos; rankings, traços, métricas, coincidências e playlists usam esses plays. Horas e `describe()` incluem todas as execuções musicais válidas, mesmo as mais curtas. Correspondências de artistas/faixas usam os nomes do histórico após a limpeza, sem inferir aliases ou gêneros.

## Métricas explicáveis

A ponderação é aplicada às contagens por artista antes do cosseno, das contribuições e do Ruzicka. Participações dos gráficos, entropia, Gini e regras de arquétipos usam **contagens brutas**.

| Opção | Peso aplicado à contagem x |
|---|---|
| `bruta` (padrão compatível) | x |
| `raiz` | √x |
| `log1p` | ln(1+x), da biblioteca padrão |

- **Cosseno:** Σaᵢbᵢ/(√Σaᵢ² · √Σbᵢ²). Compara o padrão de frequências; não é porcentagem de músicas compartilhadas.
- **Contribuição do artista:** aᵢbᵢ/(|a|·|b|). A soma de todas as contribuições é o cosseno, salvo arredondamento numérico. Exclusivos contribuem zero. A interface mostra os 100 líderes em pontos percentuais; `resultado.contribuicoes` contém todos.
- **Jaccard geral / top 20:** tamanho da interseção dividido pelo tamanho da união de artistas. Não usa a ponderação.
- **Jaccard ponderado / Ruzicka:** Σmin(aᵢ,bᵢ)/Σmax(aᵢ,bᵢ), usando pesos absolutos, **sem normalizar volumes**. Por isso, pode diferir mesmo entre vetores proporcionais com cosseno 1.
- **Entropia normalizada:** −Σpᵢ·ln(pᵢ)/ln(k), com k artistas de contagem positiva. Uma categoria vale 0; distribuição uniforme com k>1 vale 1; conjunto vazio retorna `None`.
- **Gini observado:** Σ(2i−k−1)xᵢ/(kΣxᵢ), com contagens positivas ordenadas e i começando em 1. Uniformidade e uma categoria valem 0; o teto é (k−1)/k. Vazio retorna `None`.

Entropia e Gini consideram somente artistas **observados**, sem incluir todos os artistas existentes como zeros; não medem diversidade de gêneros. As métricas puras validam frequências finitas e não negativas. Cosseno ou Ruzicka com denominador zero retorna `None`; o orquestrador exige plays em todos os perfis.

## Arquétipos e traços

Todas as regras e constantes ficam em `perfis.py`; nenhuma é inferida por um modelo de personalidade.

| Dimensão | Proporção observada | Regra inclusiva |
|---|---|---|
| Favoritos | Plays dos dois artistas líderes / total de plays | ≥60%: Fiel aos favoritos; abaixo: Gosto distribuído |
| Repetição | Plays das dez faixas líderes / total de plays | ≥40%: Mestre do repeat; abaixo: Repertório variado |
| Madrugada | Plays de 00h até 05h59 no fuso selecionado / total | ≥40%: Coruja musical; abaixo: Fora da madrugada |

Top 10 tende a ser alto em amostras pequenas. As proporções são apresentadas junto aos títulos. O radar mostra as três proporções e uma linha tracejada de limiares.

## Momentos Sincronizados

Duas análises alternativas: **mesmo artista**, permitindo títulos diferentes; **mesma música e artista**, exigindo ambos iguais. A distância entre os instantes UTC deve ser **≤1 hora**, inclusive. Cruza fronteiras de hora/dia e não depende do arredondamento em blocos de uma hora. O fuso afeta a apresentação local, não o emparelhamento.

Após ordenar cronologicamente cada grupo, dois ponteiros emparelham os primeiros eventos compatíveis. Cada evento é usado no máximo uma vez **dentro de cada análise**, encontrando o máximo de pares um a um para a janela. Os dois totais não devem ser somados. A ordenação é O(n log n); o emparelhamento é O(n), sem produto cartesiano.

`total_pares` é completo; `exemplos` guarda até 200 pares na ordem de artista/música e instante. Os timestamps do Spotify são instantes registrados: coincidência de datas não comprova que as pessoas ouviram simultaneamente durante a faixa nem influência entre elas.

## Ponte Musical, playlist e cartão

**Ponte Musical:** até dez artistas líderes exclusivos de A sugeridos para B, e vice-versa. Usa contagens brutas no recorte. Ausência no arquivo não significa desinteresse, e as sugestões não são descobertas comprovadas. Os links abrem **buscas** no Spotify; não há chamada à API ou confirmação de ID oficial.

**Playlist comum:** todas as faixas presentes nos dois perfis, cruzadas por `(música, artista)`, ordenadas pela soma dos plays. Títulos homônimos de artistas diferentes não se confundem. A prévia mostra até 500 faixas; o CSV inclui todas. UTF-8 com BOM, separador `;`, contagens A/B e links de busca. Nomes que poderiam virar fórmulas em planilhas recebem um apóstrofo de proteção. Não cria uma playlist na conta Spotify.

**Cartão PNG:** Pillow, RGB, 1080×1350, nomes, métricas, ponderação, artistas comuns, recorte e aviso explícito. Fontes locais: fonte indicada → DejaVu → Windows/macOS → fallback Pillow. Textos muito longos são truncados para manter o rodapé legível. Nenhuma rede, fonte remota, IP ou identificador de arquivo entra no cartão.

Exportações usam diretórios temporários privados, sem sobrescrever outras sessões. O Gradio serve os downloads e limpa seu cache temporário após uma hora; o estado de sessão também possui limpeza de suas pastas. Dados de entrada são processados no aplicativo local; clicar num link Spotify abre o site no navegador.

## API Python

Os imports antigos continuam disponíveis:

```python
from app import carregar, comparar, metricas, criar_interface, limpar_cache
from app import ConfiguracaoCarga, EntradaPerfil, comparar_grupo
from exportacoes import exportar_playlist
from cartao import gerar_cartao

config = ConfiguracaoCarga(
    fuso_horario='America/Sao_Paulo',
    musicas_ignoradas=(),
    artistas_ignorados=(),
    deduplicar=True,
)
r = comparar(['a_2025.json', 'a_2026.json'], 'b.zip', 'Pessoa A', 'Pessoa B',
             configuracao=config, ponderacao='raiz')
print(r.metricas.cosseno)
print(r.contribuicoes.head())
print(r.momentos_musicas.total_pares)
print(r.ponte)
exportar_playlist(r, 'exportacoes/playlist.csv')
gerar_cartao(r, 'exportacoes/cartao.png')

g = comparar_grupo([
    EntradaPerfil('A', ['a_2025.json', 'a_2026.json']),
    EntradaPerfil('B', 'b.zip'),
    EntradaPerfil('C', 'c.zip'),
], configuracao=config, ponderacao='log1p')
print(g.matriz)  # Valores numéricos 0–1, diagonal 1, matriz simétrica.
```

`comparar()` retorna `ResultadoComparacao`, sem HTML ou tuplas posicionais. `comparar_grupo()` retorna `ResultadoGrupo`. Dataclasses e DataFrames mantêm os valores numéricos; formatação/sanitização ocorrem na apresentação. `ui.apresentar()`, `grafico_artistas()` e `grafico_meses()` continuam disponíveis para o notebook/benchmark anterior; a nova tela usa os gráficos avançados.

## Gráficos e acessibilidade

- **Butterfly:** A à esquerda, B à direita; sinais negativos são apenas desenho. Ambos usam participação percentual de plays.
- **Mapas hora × dia:** lado a lado, mesma escala e fuso do loader. Cada matriz representa a participação no total de plays do respectivo perfil.
- **Radar:** proporções e limiares nomeados, sem inferir personalidade.
- **Slope chart:** liga participações entre A e B de oito artistas líderes. Não é evolução temporal.
- **Matriz de grupo:** cosseno, escala fixa 0–1, valores em cada célula além das cores.

CSS externo em `styles.css`: largura total, responsividade, fontes de pelo menos 14px (texto principal 16px), botões com altura mínima 44px, foco visível e `prefers-reduced-motion`. Tema nativo `gr.themes.Base().set(...)`, usando fontes do sistema. Os pares de cores principais e o texto da matriz são testados para contraste AA (≥4,5:1). Isso não substitui uma auditoria completa de acessibilidade no navegador.

## Verificação

```powershell
py -m unittest discover -s tests -v
py tests/test_golden_master.py --escala-grande -v
```

O suite cobre as regressões anteriores, pesos e soma das contribuições, entropia/Gini, limite de 1h, DST, ausência de reutilização de eventos, limite de exemplos sem perder o total, faixas homônimas, CSV seguro, PNG/fontes sem rede, várias partes, matriz de 3/6 pessoas, janela global, gráficos e contraste. O teste HTTP real usa FastAPI/TestClient com o Gradio 5: upload múltiplo, sessão, dupla, grupo e downloads CSV/PNG.

As referências congeladas v0.4 e Passo 1 não foram modificadas. Com `ponderacao='bruta'` (padrão), as quatro métricas, rankings, horas e arquétipos anteriores permanecem iguais. Nenhuma importação direta de NumPy; sintaxe atual verificada contra Python 3.10.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `metricas.py` | Cosseno, Jaccards, contribuições, ponderação, entropia e Gini em Python puro |
| `analise.py` | Dataclasses, comparação de dupla e grupo, recorte UTC e agregações |
| `recursos.py` | Sincronização linear, Ponte Musical, playlist e links de busca |
| `dados.py` | Loader anterior, união de várias partes, diagnóstico e cache |
| `perfis.py` | Regras e constantes nomeadas de arquétipos |
| `graficos.py` | Figuras Plotly avançadas e matriz de grupo |
| `exportacoes.py` | CSV local com proteção de fórmulas |
| `cartao.py` | PNG Pillow com fontes locais e fallback |
| `styles.css` | Estilização externa responsiva e acessível |
| `ui.py` | Gradio 5, múltiplos uploads, progressos, grupo e exportações |
| `app.py` | Entrada local e reexportações compatíveis |
| `configuracao.py`, `formatacao.py` | Opções do loader e formatação pt-BR/sanitização |
| `tests/test_passo3.py`, `tests/test_ui.py` | Validação nova de cálculos, arquivos e interface |

O notebook de EDA, gerador fictício, golden masters e benchmark anterior estão incluídos. `docs/PASSO_2.md` e `benchmark/300k.*` são **registros históricos do Passo 2**, não medições desta versão com novos recursos. `medir_desempenho.py` pode medir esta versão, mas seu escopo de apresentação usa a adaptação antiga `ui.apresentar()`; não inclui as novas figuras da tela, upload nem renderização no navegador.
