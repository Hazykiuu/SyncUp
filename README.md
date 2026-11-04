# SyncUp v0.9

Comparador local do **Histórico Estendido do Spotify**: duas pessoas ou grupos de 3–6 perfis, com rankings, similaridades, arquétipos explicáveis, gráficos interativos, playlist CSV e cartão PNG. Projeto acadêmico organizado pelo CRISP-DM e **open source** ([licença MIT](LICENSE)).

**Aviso metodológico:** métricas e traços descrevem o recorte de escuta. Não medem personalidade ou afinidade amorosa. Uma similaridade de 100% não identifica o dono do histórico.

## Executar

Use **Python 3.10 a 3.14 (64 bits)**. As dependências fixadas escolhem automaticamente versões com binários prontos para a sua versão do Python (pandas 2.3.3 e PyArrow 26 no 3.13/3.14), então a instalação não precisa de compilador. Python 3.12 continua sendo a referência. Na pasta extraída `SyncUp`, crie um ambiente virtual:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv312\Scripts\python.exe app.py
```

Em Linux/macOS: `python3.12 -m venv .venv`, `source .venv/bin/activate`, e os comandos `python -m pip install -r requirements.txt` e `python app.py`. No Windows, os comandos acima usam diretamente o interpretador do ambiente e não precisam ativar scripts do PowerShell. As dependências diretas têm versões fixadas, incluindo Gradio 5.50.0 e pandas 2.2.3; as transitivas são resolvidas pelo pip conforme o Python/plataforma. Não há import direto de NumPy nas métricas.

**Dupla:** cada painel representa uma pessoa; seus vários ZIPs/JSONs são unidos. **Grupo:** a tela recebe um arquivo por pessoa e um nome por linha, na ordem dos arquivos. Várias partes por pessoa no grupo estão disponíveis na API `EntradaPerfil`. Fuso padrão: `America/Sao_Paulo`. Filtros, deduplicação e ponderação são configuráveis. Campos como IP/dispositivo não são retidos.

Cache Parquet é opcional e fica desligado por padrão:

```bash
python -m pip install -r requirements-parquet.txt
```

## Arquitetura e API

| Módulo | Responsabilidade |
|---|---|
| `dados.py`, `configuracao.py` | ZIP/JSON, validação, descartes, fuso, categorias, múltiplas partes e cache SHA-256 |
| `metricas.py`, `perfis.py` | Cosseno/Jaccards, contribuições, diversidade e regras nomeadas de arquétipos |
| `analise.py`, `recursos.py` | Resultados em dataclasses, recorte UTC, dupla/grupo, coincidências e descobertas sugeridas |
| `graficos.py`, `ui.py`, `styles.css` | Plotly e Gradio 5 no tema Spotify, apresentação responsiva com contraste/foco |
| `perfil_gosto.py`, `conciliacao.py`, `spotify_api.py` | Perfil unificado (ZIP e API), conciliação em pares ótimos e login OAuth/PKCE |
| `wrapped.py`, `arquetipos.py`, `stories.py` | Wrapped da vida toda, regras de arquétipos e slides em stories |
| `componentes.py`, `syncup.js` | Blocos HTML animados (Blend, Wrapped, listas tipo playlist, corrida de artistas) e o script de animações |
| `exportacoes.py`, `cartao.py` | CSV protegido para planilhas e PNG local em Pillow |
| `generos.py`, `festa.py` | Estilo musical (Spotify/MusicBrainz) e playlist da festa em CSV/XSPF |
| `listenbrainz.py` | Perfil pelo ListenBrainz (fonte aberta, sem login) |
| `formatacao.py`, `app.py` | Formatação/sanitização pt-BR, entrada local e reexportações compatíveis |

```python
from app import ConfiguracaoCarga, comparar

r = comparar('a.zip', 'b.zip', 'Pessoa A', 'Pessoa B',
             configuracao=ConfiguracaoCarga(musicas_ignoradas=()),
             ponderacao='raiz')
print(r.metricas.cosseno)
print(r.diagnostico)
```

Os imports `carregar`, `comparar`, `metricas`, `criar_interface` e `limpar_cache` permanecem em `app.py`. **Mudança de contrato:** `comparar()` devolve `ResultadoComparacao`, com campos nomeados; não devolve a tupla de 12 saídas da v0.4. `metricas()` mantém a tupla `(cosseno, jaccard)`.

## Estilo, playlist da festa e stories do Match (v0.9)

- **Estilo musical** (`generos.py`): além dos artistas, cada dupla ganha uma compatibilidade de **gêneros**. Ela ajuda quando os artistas não batem mas o estilo bate. O peso de cada artista é dividido entre os gêneros dele, e gêneros compostos ("brazilian rock") também contam, com meio peso, para as palavras que os formam. Assim as tags do Spotify e do MusicBrainz se aproximam. É uma aproximação: o emparelhamento continua só pelos artistas.
- **De onde vêm os gêneros**: o ZIP não traz gêneros, e a API do Spotify também não os envia para apps em modo de desenvolvimento (a lista vem vazia; foi conferido com um login real). Marque *Comparar também o estilo* para buscá-los no [MusicBrainz](https://musicbrainz.org) (base aberta, dados CC0). Só nomes de artistas são enviados, 1 por segundo, e as respostas ficam em `.syncup_cache/generos_musicbrainz.json`. Na primeira vez leva até ~25 s por pessoa. A busca vale para todos os perfis, de ZIP ou de login. Se o Spotify enviar gêneros (apps com acesso estendido), eles são usados e não são buscados de novo.
- **Playlist da festa** (`festa.py`): até 30 músicas que cobrem o gosto de todo o grupo. A escolha maximiza Σ √cobertura, o que dá prioridade a quem ainda tem pouco. Cada faixa diz para quem foi escolhida. Baixe em CSV ou em **XSPF**, o formato aberto de playlist da Xiph, que abre no VLC e em outros players livres.
- **Stories do Match** revelam as duplas e o trio. A aba *Para postar* gera o **story PNG** (1080×1920) de uma dupla, localmente. As duplas aparecem como pôsteres 4:5: um print da tela já serve de post.
- **ListenBrainz, sem limite de pessoas** (`listenbrainz.py`): o [ListenBrainz](https://listenbrainz.org) é um projeto aberto da MetaBrainz. Cada amigo cria uma conta grátis, conecta o Spotify uma vez em *Settings → Music services* e informa só o **nome de usuário** no Match. Não precisa de Client ID nem da lista de usuários do Spotify. As estatísticas (top artistas e músicas do mês, do semestre e do ano) são públicas e recalculadas uma vez por dia; uma conta nova leva até um dia para ter rankings.
- **Em sintonia** (aba Dupla): mostra quando os dois ouviam **a mesma música ao mesmo tempo**. O Spotify registra o fim de cada play (`ts`) e quanto tocou (`ms_played`), então o intervalo é `[fim − duração, fim]`. Os intervalos dos dois são cruzados por faixa, e uma sobreposição de pelo menos 30 s conta como um momento juntos. A aba traz minutos juntos, a primeira vez, a música de vocês, o momento mais longo, a hora e o dia favoritos, a linha do tempo mês a mês, stories e o story PNG. A comparação antiga, com até 1 h de distância, ficou em "Quase juntos".

## Match entre amigos e login com Spotify (v0.8)

Aba **Match**: junte várias pessoas — por **histórico ZIP** (sem limite) e/ou **login com Spotify** (até 5) — e o SyncUp:

1. compara **todos com todos** (matriz de compatibilidade);
2. forma as **duplas que maximizam a compatibilidade total do grupo** (emparelhamento ótimo; com número ímpar, a pessoa restante entra no par onde combina melhor, formando um trio);
3. explica cada dupla pelos **artistas em comum** e sugere o que cada um pode **apresentar ao outro**;
4. mostra o **ranking individual** (com quem cada pessoa mais combina).

**Comparação justa entre fontes** (`perfil_gosto.py`): a API só entrega favoritos — top 50 artistas e músicas em ~4 semanas, ~6 meses e ~1 ano. Por isso o ZIP é convertido para os mesmos rankings, nas mesmas janelas (contadas a partir do fim do histórico). A compatibilidade (`conciliacao.py`) é o cosseno entre vetores de artistas ponderados pela posição no ranking (1º lugar = 1, 50º = 0,02) e pelo período (1 ano 1,0 · 6 meses 0,8 · 4 semanas 0,6), com reforço de 0,5 para artistas das músicas favoritas. Faixas: ≥25 Sintonia rara · ≥10 Alta · ≥5 Boa · ≥1 Baixa · <1 Mundos diferentes — calibradas com 4 históricos reais, em que rankings de top 50 raramente passam de 15% de sobreposição.

### Configurar o login do Spotify (uma vez)

Regras atuais do Spotify para projetos pessoais (modo de desenvolvimento, fev/2026): **o dono do app precisa de Premium** e **no máximo 5 usuários** cadastrados. Para liberar mais gente, o Spotify exige uma empresa com 250 mil usuários ativos por mês — por isso o ZIP continua sendo a fonte sem limite.

1. Em <https://developer.spotify.com/dashboard>, crie um app (marque **Web API**).
2. Em **Redirect URIs**, cadastre exatamente `http://127.0.0.1:7860/spotify/callback` (o Spotify não aceita `localhost`).
3. Em **User Management**, adicione nome e e-mail do Spotify de cada amigo (até 5).
4. Copie o **Client ID** (não é preciso o secret: o login usa PKCE).
5. Rode `python app.py`, abra a aba **Match**, cole o Client ID, digite o nome da pessoa e clique em **Conectar com Spotify**. Cada amigo autoriza na conta dele; o perfil vai para `perfis_spotify/<nome>.json`.

Variáveis opcionais: `SPOTIFY_CLIENT_ID` (preenche o campo), `SYNCUP_PORTA` (padrão 7860; mude também a Redirect URI) e `SYNCUP_PERFIS` (pasta dos perfis). Guardamos só rankings, últimas 50 músicas e artistas seguidos — **o token nunca é gravado**. No Colab, o login não funciona (a Redirect URI precisa ser `127.0.0.1`), mas o Match com ZIPs funciona normalmente.

```python
from conciliacao import conciliar
from perfil_gosto import carregar_perfil, perfil_de_historico
from dados import carregar_historicos

ana = perfil_de_historico(carregar_historicos('ana.zip').dados, 'Ana')
bia = carregar_perfil('perfis_spotify/Bia.json')
r = conciliar([ana, bia])
print(r.pares, r.par('Ana', 'Bia').artistas_comuns[:5])
```

## Wrapped da vida toda e arquétipos (v0.7)

Aba **Meu Wrapped**: envie o Histórico Estendido de uma pessoa (todas as partes) e veja a vida inteira no Spotify em **stories 9:16** animados — clique à direita para avançar, à esquerda para voltar, espaço pausa, setas navegam:

abertura com horas totais · primeira música · artista da vida · top 5 artistas e músicas · ano a ano · descobertas por ano · dia mais musical e a música mais repetida num dia · relógio musical (24 h) · maior sequência de dias seguidos · fidelidade ao top 5 · hábitos (aleatório, pulos, ouvidas até o fim, offline, aparelhos) · **arquétipo** · resumo final. O resumo pode ser baixado como PNG 1080×1920.

Na **Dupla**, cada pessoa ganha o arquétipo da vida toda no cartão de identidade e a aba *Explorar → Wrapped da vida toda* mostra os dois players lado a lado. No **Grupo**, cada cartão mostra o arquétipo.

**Arquétipos** (`arquetipos.py`): 12 regras com limiares nomeados — Devoto(a), Explorador(a), Coruja, Madrugador(a), Trilha da noite, Fim de semana sonoro, Dedo no próximo, Rei/Rainha do aleatório, Do começo ao fim, Maratonista, Modo repeat e Sem sinal, com som. A *intensidade* (quanto a pessoa passa do limiar, rumo a um "teto") escolhe o principal; os dois seguintes viram secundários e regras a ≥80% do limiar aparecem como "quase". A aba mostra todas as regras com valor e limiar. Sem regra atingida: *Ouvinte equilibrado(a)*. Descrevem hábitos do histórico, não personalidade.

**Novos campos lidos** (`dados.py`): `skipped`, `shuffle`, `offline`, `reason_end` e `platform`. Da plataforma só fica a família (Android, iOS, Windows, macOS, Linux, Navegador, TV/console/caixa de som) — modelo e versão do aparelho são descartados na leitura. Exportações antigas sem esses campos continuam funcionando; os hábitos ausentes são omitidos.

**Filtro de músicas:** a interface agora começa com a lista de músicas ignoradas vazia (o nome antigo aparece como exemplo). A API Python mantém o padrão anterior em `ConfiguracaoCarga`; `wrapped_de_arquivos()` usa lista vazia por padrão.

```python
from wrapped import wrapped_de_arquivos
w = wrapped_de_arquivos('meu_historico.zip', 'Carlos')
print(w.artista_vida.nome, w.horas, w.arquetipos.principal.nome)
```

## Interface (v0.6)

Tema escuro inspirado no Spotify, com animações em todos os pontos onde fazem sentido:

- **Botões** em formato pílula com zoom no hover, compressão no clique e onda (*ripple*); o botão principal pulsa suavemente.
- **Blend**: avatares que se encontram, anel de similaridade que se preenche e números com contagem animada.
- **Gráficos**: barras crescem a partir do eixo, linhas são desenhadas, mapas de calor são revelados da esquerda para a direita e o radar expande do centro. Ao trocar de aba, a animação toca de novo.
- **Corrida dos artistas**: ranking acumulado mês a mês, com player (play/pausa e linha do tempo arrastável).
- **Rankings** como listas de playlist: ao passar o mouse, o número vira ▶ e o link abre a busca no Spotify.
- Botão **Testar com dados fictícios** para ver tudo sem enviar históricos reais.

Todas as animações são desligadas quando o sistema pede movimento reduzido (`prefers-reduced-motion`). Sem JavaScript, os valores finais continuam visíveis. A fonte Figtree (OFL) vem embutida no projeto, em `fontes/`: funciona offline e não faz requisições ao Google Fonts.

**Leitura paralela:** pela interface, arquivos grandes de pessoas diferentes são lidos em processos paralelos (até 4). `SYNCUP_PROCESSOS=0` desativa; a API Python continua sequencial, a menos que chame `dados.habilitar_leitura_paralela()` dentro de `if __name__ == '__main__':`.

## Testes e qualidade

```bash
python -m pip install -r requirements-dev.txt -r requirements-parquet.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python tests/test_golden_master.py --escala-grande -v
```

No Windows, substitua `python` por `.\.venv312\Scripts\python.exe` nos comandos desta seção. Execute um comando por vez e prossiga somente se o anterior terminar sem erro. Um bloqueio Ruff com `WinError 4551` é uma política do Windows: não impede por si só o aplicativo ou pytest, mas exige uma liberação autorizada para executar o Ruff.

Novos testes pytest: `test_metricas.py`, `test_dados.py`, `test_analise.py`, `test_smoke_ui.py`, `test_notebook.py` `test_v06.py` (correções e recursos da v0.6) `test_wrapped.py` (Wrapped e arquétipos da v0.7) `test_match.py` (conciliação e login com a API simulada), `test_generos.py` (estilo e MusicBrainz simulado), `test_festa.py` (playlist da festa, stories e cartão do Match) e `test_licencas.py` (licenças abertas). Fixtures usam somente dados fictícios e isolam o cache. A suíte também descobre os testes de regressão/recursos anteriores em unittest, incluindo o fluxo HTTP real do Gradio. Parquet é testado quando instalado; sem a dependência, seus testes específicos são pulados.

Ruff usa Python 3.10 como alvo, 100 colunas, imports ordenados e formatação uniforme. `tests/fixtures/` fica excluído: seu código congelado e seus hashes devem permanecer intactos. Golden masters existentes são lidos pelos testes, nunca atualizados automaticamente. Rankings são ordenados por contagem decrescente e nome crescente (música, depois artista, para faixas). A regressão preserva contagens e todos os itens acima do empate na última posição; valida o desempate e o corte contra contagens independentes dos eventos. Assim, não depende da ordem indefinida do quicksort antigo. Use `python -m ruff format .` para formatar alterações futuras.

## Notebook CRISP-DM

Abra `SyncUp.ipynb` num editor de notebooks, com o kernel do ambiente acima, na pasta do projeto. Ele contém as seis fases: entendimento do negócio/dados, preparação, modelagem, avaliação e implantação. Usa Pandas/Seaborn no EDA e importa os cálculos dos módulos da aplicação.

O padrão gera **dados fictícios** e mantém a interface desligada durante a execução automática. Para analisar dados próprios, edite a primeira célula e os caminhos da segunda célula de código. Para verificar todas as células sem servidor Jupyter:

```bash
python tools/verificar_notebook.py
```

O verificador roda o código real em IPython e em uma cópia temporária, sem abrir portas de rede ou Gradio; não testa o protocolo de kernel nem a interface gráfica do Jupyter. O notebook distribuído não contém saídas, históricos ou resultados pessoais.

## Benchmarks

```bash
python tools/gerar_dados_falsos.py perfil_a.zip --seed 41
python tools/gerar_dados_falsos.py perfil_b.zip --seed 97
python medir_desempenho.py perfil_a.zip perfil_b.zip --repeticoes 3 --parquet --somente-nucleo --saida benchmark/meu_pc
```

Gera cerca de 300 mil eventos por perfil e relatórios JSON/CSV/Markdown com tempos brutos e medianas. A referência padrão é o Passo 1 congelado; `--antes outra/pasta` seleciona outra referência. Mede cache frio do aplicativo, memória quente e Parquet preparado. Imports, upload, rede, escrita inicial do Parquet e renderização no navegador ficam fora da medição. Não esvazia o cache do sistema operacional.

A v0.5 calcula recursos adicionais: a diferença de tempo para a referência também reflete esse trabalho novo. Sem `--somente-nucleo`, a apresentação medida é a adaptação antiga `ui.apresentar()`, e não todos os gráficos da tela atual. `benchmark/300k.*` e `docs/PASSO_2.md` são registros históricos; não são medições da entrega final.

## Código aberto

O SyncUp é distribuído sob a [licença MIT](LICENSE) e só usa código e recursos abertos:

| Dependência | Licença |
|---|---|
| Gradio | Apache-2.0 |
| FastAPI | MIT |
| httpx | BSD-3-Clause |
| pandas | BSD-3-Clause |
| Plotly | MIT |
| Pillow | MIT-CMU |
| seaborn | BSD-3-Clause |
| matplotlib | PSF |
| orjson | Apache-2.0 / MIT |
| pytest, Ruff | MIT |
| Fonte Figtree (`fontes/`) | SIL OFL 1.1 ([`fontes/OFL.txt`](fontes/OFL.txt)) |
| MusicBrainz (gêneros, opcional) | dados CC0, servidor open source |
| ListenBrainz (perfis, opcional) | servidor open source (MetaBrainz) |

`tests/test_licencas.py` confere a licença declarada de cada pacote em `requirements*.txt`. Uma dependência nova sem licença aberta faz a suíte falhar.

**Contribuir:** abra uma *issue* ou um *pull request*. Antes, rode `python -m pytest -q`, `python -m ruff check .` e `python -m ruff format --check .`. O `.gitattributes` mantém tudo em LF, também no Windows. Nunca envie históricos reais nem perfis de `perfis_spotify/`: são dados pessoais, e o `.gitignore` já os exclui.

## Rumo à 2.0

Ideia para uma versão futura: **descobrir pessoas com gosto parecido** e conversar com elas dentro do app. Isso muda a natureza do projeto, de local para conectado, e exige:

- um servidor que guarde perfis, com **consentimento explícito**, opção de apagar e cuidado com a **LGPD** (hábitos de escuta são dados pessoais);
- descoberta por perfil resumido (rankings e gêneros), nunca pelo histórico bruto;
- moderação e bloqueio entre usuários;
- para o chat, um protocolo aberto como o **[Matrix](https://matrix.org)**, em vez de um chat próprio. Ele já resolve criptografia, federação e clientes livres, e mantém o projeto 100% aberto.

## Limitações e interpretação

- Plays/rankings/traços usam execuções ≥30s; horas e `describe()` incluem todas as execuções válidas. O recorte comum usa UTC; no grupo, a mesma janela global é aplicada a toda a matriz.
- Ponderações: x, √x e ln(1+x). Cosseno compara padrões; Ruzicka usa pesos absolutos e responde ao volume. Contribuições somam o cosseno, com tolerância de ponto flutuante. Entropia/Gini usam contagens brutas entre artistas observados, sem inferir gêneros.
- Arquétipos: top 2 artistas ≥60%, top 10 faixas ≥40%, madrugada 00h–05h59 ≥40%. Regras em `perfis.py`, visíveis na tela; amostras pequenas podem inflar o top 10.
- Coincidências temporais usam distância inclusiva ≤1h e pares sem reutilização por análise. Totais de artista e música são alternativas, não somáveis; não comprovam influência nem simultaneidade durante a faixa.
- Ponte Musical sugere artistas ausentes no recorte do destino; ausência não prova desinteresse. Links são **buscas** Spotify. O CSV não cria uma playlist na conta; o PNG é gerado sem rede.
- Nomes/aliases não são reconciliados automaticamente. Cobertura temporal não garante completude dos dados. Similaridade não é recomendação validada com usuários reais.

Veja `CHANGELOG.md` para as alterações e `VALIDACAO.md` para as verificações desta entrega. `docs/PASSO_3.md` preserva o guia detalhado da etapa anterior.
