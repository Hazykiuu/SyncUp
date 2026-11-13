# SyncUp v0.5 — Passo 2 de 4

Esta entrega cobre as correções de bugs (Fase 2) e performance (Fase 3). Python 3.10+, pandas >=2.2,<3; sem import direto de NumPy. Os imports `carregar`, `comparar`, `metricas`, `criar_interface` e `limpar_cache` continuam disponíveis em `app.py`. O retorno é `ResultadoComparacao`.

## Instalar e abrir

Dentro da pasta extraída:

```powershell
py -m pip install -r requirements.txt
py app.py
```

Para habilitar também o cache Parquet:

```powershell
py -m pip install -r requirements-parquet.txt
```

A interface tem a seção **Filtros, horário e cache**, com seletor de fuso IANA, músicas/artistas ignorados (um nome por linha), tratamento de Various Artists e cache em disco opcional. Nomes com vírgula, como Dream, Ivory, permanecem inteiros.

## Configurar pelo código

```python
from app import ConfiguracaoCarga, comparar, carregar, limpar_cache

opcoes = ConfiguracaoCarga(
    fuso_horario='America/Sao_Paulo',
    musicas_ignoradas=(),           # Desativa a preferência musical anterior.
    artistas_ignorados=('Artista a ignorar',),
    various_artists='manter',      # Ou 'ignorar'. Não infere intérpretes reais.
    deduplicar=False,
    usar_cache_disco=True,
    diretorio_cache='.syncup_cache',
)
resultado = comparar('perfil_a.zip', 'perfil_b.zip', 'A', 'B', configuracao=opcoes)
print(resultado.metricas.cosseno)
print(resultado.diagnostico)
```

A preferência anterior de música ignorada agora fica em `MUSICAS_IGNORADAS_PADRAO`, em `configuracao.py`, e aparece como texto editável na interface. Não há condição especial dessa música no loader. Os nomes são comparados após normalizar caixa, espaços, pontuação e forma Unicode; acentos são preservados. `deduplicar=True/False` passado diretamente continua funcionando e sobrescreve a opção da configuração.

## Correções

- `formatacao.py`: `fmt_num(1234.56, 2)` → `1.234,56`; `fmt_pct(0.1234)` → `12,3%`; `fmt_horas(1234.5)` → `1.234,5 h`, sem depender do locale do computador.
- HTML e Markdown têm escapes específicos. Nomes como `*NSYNC`, pipes, underscores e tags não alteram a apresentação. Nomes originais permanecem nos dados do núcleo; o escape ocorre somente ao apresentar.
- Listas de conexões usam `itertools.islice`, limitadas a vinte itens; não cortam nomes ou sequências de escape no meio.
- Datas usam `pd.to_datetime(..., utc=True, format='ISO8601', errors='coerce')`. Variantes com frações, offsets e sufixo Z são aceitas; datas inválidas são contadas.
- Podcasts são identificados pelos campos de episódio. Durações negativas, não numéricas, booleanas ou não finitas são descartadas e contadas.
- Fuso IANA validado antes da leitura; padrão America/Sao_Paulo. Arquétipos, horas locais, meses e dias usam o mesmo fuso selecionado.
- Various Artists pode ser mantido como artista agregado ou ignorado. O Diagnóstico informa quantos eventos dessa categoria foram encontrados/descartados.

A aba **Diagnóstico** inclui total recebido, podcasts, duração inválida, data inválida, identificação inválida, ignorados pelos filtros, Various Artists, duplicados e total válido antes do recorte. Motivos de descarte são exclusivos e aplicados nesta ordem: podcast → duração → data → identificação → Various Artists → filtros → duplicados. Um evento com vários problemas pertence ao primeiro motivo aplicável; a soma dos descartes mais válidos fecha o total recebido.

## Datas e categorias

O loader mantém `data_utc` como instante UTC e calcula `data` local **sem fuso** uma única vez. Também prepara colunas inteiras:

| Coluna | Significado |
|---|---|
| `hora` | Hora local, 0–23. |
| `ano_mes` | Ano/mês local, inteiro YYYYMM. |
| `dia_semana` | Segunda = 0, domingo = 6. |
| `data_dia` | Dia local, inteiro YYYYMMDD. |

`artista` e `musica` viram `category` depois da limpeza. Todo `groupby` da implementação atual usa `observed=True`, para não inventar artistas/faixas ausentes no recorte nem expandir combinações de categorias. Rankings de saída têm nomes como texto e contagens numéricas; a interface formata as pequenas tabelas em pt-BR.

Intervalos comuns e deduplicação usam **instantes UTC**, preservando duas execuções distintas que caem na mesma hora local durante a volta do horário de verão. Os horários locais não são usados para identificar eventos. Deduplicação permanece opcional, desativada por padrão, pela chave instante/duração/música/artista.

O orquestrador reutiliza colunas temporais e totais dos plays. Conexões e exclusivos usam operações vetorizadas de índices e pesos, sem consultar Series em uma lambda por artista. Arquétipos reutilizam agregações de pandas, sem criar grandes dicionários de faixas. Filtros que mantêm todas as linhas evitam cópias desnecessárias.

## Caches

A memória mantém até quatro históricos preparados, identificados pelo SHA-256 original e pelas opções. Caminho/tamanho/mtime/ctime/inode invalidam o hash em memória quando o arquivo muda. Arquivos renomeados com os mesmos bytes reutilizam dados, mas mostram seus nomes atuais no Diagnóstico. Funções públicas devolvem cópias para proteger o cache.

O cache opcional em `.syncup_cache/` usa Parquet + manifesto JSON. A chave combina **SHA-256 original + versão de esquema + filtros/fuso/Various Artists/deduplicação**. Assim, opções diferentes não reutilizam resultados incorretos. A leitura valida hash do Parquet, esquema, categorias e contadores. Cache corrompido é reconstruído a partir do original; problema de escrita mantém a análise e informa o status no Diagnóstico. Arquivos temporários são publicados por substituição atômica.

`limpar_cache()` limpa memória e hashes; **não apaga o disco**. O cache em disco fica desativado por padrão. Se PyArrow estiver ausente, a mensagem explica a instalação da dependência opcional. JSONs auxiliares e campos pessoais de dispositivo/IP não são guardados na tabela preparada.

## Medir antes/depois

> Registro histórico da v0.5. O `medir_desempenho.py` e a cópia congelada `tests/fixtures/v05_passo1/` saíram na auditoria da 1.9; os resultados medidos continuam em `benchmark/300k.*`.

A cópia congelada do Passo 1 está em `tests/fixtures/v05_passo1/` e é a referência padrão do benchmark. Gere os dois históricos fictícios:

```powershell
py tools/gerar_dados_falsos.py perfil_a.zip --seed 41
py tools/gerar_dados_falsos.py perfil_b.zip --seed 97
py medir_desempenho.py perfil_a.zip perfil_b.zip --repeticoes 3 --parquet --saida benchmark/meu_pc
```

O script gera **JSON com tempos brutos**, **CSV com separador ponto e vírgula** e **tabela Markdown**. Use `--somente-nucleo` para medir sem construir apresentação, `--historicos-completos` para mudar o recorte, ou `--antes outra/pasta` para usar outra referência contendo app.py.

Cada versão roda em processo separado. Imports e um aquecimento inicial ficam fora da medição; a ordem antes/depois alterna por rodada. São reportadas medianas de:

1. **Frio de dados:** memória do aplicativo vazia, cache de disco desligado. Não esvazia o cache do sistema operacional.
2. **Quente em memória:** mesmos arquivos e opções já preparados.
3. **Quente em Parquet:** Parquet preparado antes da medida, memória/hashes limpos, releitura do original para SHA e do Parquet no tempo medido.

O benchmark usa pasta temporária privada para Parquet e não remove caches do usuário. Exclui abertura, upload, rede, renderização no navegador e primeira escrita do Parquet. O escopo padrão inclui núcleo e construção da apresentação Python. Não compare estes tempos diretamente com medições que incluem upload ou usam outro escopo.

A medição desta entrega, com 300 mil eventos em cada perfil, está em `benchmark/300k.json`, `.csv` e `.md`. Resultados são específicos do ambiente registrado e podem variar no seu computador.

## Testes e linha de base

```powershell
py -m unittest discover -s tests -v
py tests/test_golden_master.py --escala-grande -v
```

Os testes de Parquet são pulados quando a dependência opcional não está instalada. Para executar todos, instale `requirements-parquet.txt`.

As referências originais da v0.4 continuam intactas em `tests/golden/`. A regressão agora compara dados de rankings, estatísticas e gráficos com essa referência e as quatro métricas/perfis com a cópia numérica do Passo 1. Formatação, descrição do fuso e colunas novas de Diagnóstico mudaram intencionalmente na Fase 2; não se exige igualdade byte a byte dessas apresentações antigas.

As novas verificações cobrem ISO misto, contabilidade de descartes, filtros editáveis, Various Artists, fusos, hora repetida por horário de verão, ausência de categorias fantasmas, escapes, truncamento e invalidade/reutilização dos caches. As cópias históricas em `tests/fixtures/` permanecem como eram e não são a implementação atual.

## Arquivos principais

| Arquivo | Responsabilidade |
|---|---|
| `configuracao.py` | Fuso, filtros, política de coletâneas e opções dos caches. |
| `formatacao.py` | Números pt-BR, escape HTML/Markdown e listas limitadas. |
| `dados.py` | Ingestão, limpeza, contadores, colunas temporais, categorias e caches. |
| `analise.py` | Orquestração estruturada, recorte UTC e agregações observadas. |
| `perfis.py` | Constantes e regras de arquétipos reutilizando proporções agregadas. |
| `ui.py` | Interface com seletores e apresentação sanitizada/formatada. |
| `medir_desempenho.py` | Workers isolados, medianas e relatórios comparativos. |
| `metricas.py` | Cosseno/Jaccards em Python puro, preservados. |

Seaborn e Matplotlib continuam no notebook de EDA. Nenhuma fase futura foi implementada nesta entrega.

## Resultado medido nesta entrega

Medianas de três rodadas, 300 mil eventos por perfil, núcleo e construção da apresentação no Python:

| Cenário | Antes (s) | Depois (s) | Redução |
|---|---:|---:|---:|
| Cache de dados frio | 5,272 | 5,839 | -10,8% |
| Cache em memória quente | 0,459 | 0,236 | 48,5% |
| Cache Parquet quente | — | 0,294 | — |

- Frio significa caches de dados do aplicativo vazios; não esvazia cache do sistema operacional.
- Quente em memória reutiliza dados preparados; quente Parquet limpa a memória e relê disco.
- Não inclui importações, abertura, upload, rede, renderização no navegador ou escrita inicial do Parquet.

A primeira leitura ficou 10,8% mais lenta com a validação adicional e preparação de categorias/colunas. A comparação em memória ficou 48,5% mais rápida; o Parquet já preparado permitiu releitura em 0,294 s. A dependência opcional não elimina o custo da primeira leitura e gravação.

Validação final: 26 testes aprovados, regressão de 300 mil eventos por perfil aprovada nos dois modos, e fluxo da interface conferido com novo fuso, escapes, Diagnóstico e cache em disco.
