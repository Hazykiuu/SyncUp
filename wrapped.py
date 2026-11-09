"""Wrapped da vida toda: estatísticas de todo o histórico enviado de uma pessoa.

Usa todos os eventos válidos para horas e hábitos, e plays de pelo menos 30 s
para rankings, descobertas e horários (mesma regra do restante do SyncUp).
Nenhum dado sai do computador; nenhuma chamada de rede é feita.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from arquetipos import PerfilArquetipos, classificar
from configuracao import ConfiguracaoCarga
from dados import Caminho, carregar_historicos

TEMPO_MINIMO_PLAY_MS = 30_000
DIAS_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
PERIODOS = (
    ('Madrugada', 0, 6),
    ('Manhã', 6, 12),
    ('Tarde', 12, 18),
    ('Noite', 18, 24),
)
MINIMO_CONHECIDOS = 0.5  # Fração mínima de eventos com o campo preenchido.


@dataclass(frozen=True)
class ItemRanking:
    """Artista ou música em um ranking, com plays e horas."""

    nome: str
    plays: int
    horas: float = 0.0
    artista: str = ''
    uri: str | None = None  # ID da faixa no Spotify (só músicas): capa exata no app web


@dataclass(frozen=True)
class ResumoAno:
    """Um ano do histórico: volume, líderes e descobertas."""

    ano: int
    horas: float
    plays: int
    top_artistas: list[ItemRanking]
    top_musica: ItemRanking | None
    novos_artistas: int


@dataclass(frozen=True)
class Wrapped:
    """Tudo o que os slides do Wrapped precisam, já calculado."""

    nome: str
    inicio: pd.Timestamp
    fim: pd.Timestamp
    dias_periodo: int
    dias_com_musica: int
    horas: float
    plays: int
    quantidade_artistas: int
    quantidade_musicas: int
    artista_vida: ItemRanking
    descoberta_artista_vida: pd.Timestamp
    participacao_artista_vida: float
    top_artistas: list[ItemRanking]
    top_musicas: list[ItemRanking]
    primeira_musica: ItemRanking
    primeira_data: pd.Timestamp
    anos: list[ResumoAno]
    dia_recorde: pd.Timestamp
    horas_dia_recorde: float
    artista_dia_recorde: str
    repeticao_dia: ItemRanking
    data_repeticao_dia: pd.Timestamp
    sequencia: int
    inicio_sequencia: pd.Timestamp
    fim_sequencia: pd.Timestamp
    plays_por_hora: list[int]
    pico_hora: int
    dia_semana_favorito: str
    periodos: dict[str, float]
    fiel: ItemRanking
    anos_fiel: int
    habitos: dict[str, float | None]
    plataformas: list[tuple[str, float]]
    medidas: dict[str, float | None]
    arquetipos: PerfilArquetipos
    fuso_horario: str = 'America/Sao_Paulo'
    avisos: list[str] = field(default_factory=list)
    fiel_anos: list[int] = field(default_factory=list)  # anos em que o fiel esteve no top 5


def mes_ano(data: pd.Timestamp) -> str:
    """Formata como 'mar/2021'."""
    return f'{MESES[data.month - 1]}/{data.year}'


def data_br(data: pd.Timestamp) -> str:
    """Formata como '24/03/2025'."""
    return f'{data:%d/%m/%Y}'


def _ranking_artistas(plays: pd.DataFrame, limite: int) -> list[ItemRanking]:
    """Top artistas por plays (desempate alfabético), com horas totais."""
    agrupado = plays.groupby('artista', observed=True).agg(
        plays=('ms_played', 'size'), ms=('ms_played', 'sum')
    )
    agrupado.index = agrupado.index.astype(object)
    agrupado = agrupado.reset_index().sort_values(
        ['plays', 'artista'], ascending=[False, True], kind='stable'
    )
    return [
        ItemRanking(str(a), int(p), float(ms) / 3_600_000)
        for a, p, ms in agrupado.head(limite).itertuples(index=False, name=None)
    ]


def _ranking_musicas(plays: pd.DataFrame, limite: int) -> list[ItemRanking]:
    """Top músicas por plays, identificadas por (música, artista)."""
    contagem = plays.groupby(['musica', 'artista'], observed=True).size().rename('plays')
    tabela = contagem.reset_index()
    tabela[['musica', 'artista']] = tabela[['musica', 'artista']].astype(object)
    tabela = tabela.sort_values(
        ['plays', 'musica', 'artista'], ascending=[False, True, True], kind='stable'
    )
    return [
        ItemRanking(str(m), int(p), artista=str(a))
        for m, a, p in tabela.head(limite).itertuples(index=False, name=None)
    ]


def _maior_sequencia(dias: pd.Series) -> tuple[int, pd.Timestamp, pd.Timestamp]:
    """Maior sequência de dias consecutivos com pelo menos uma reprodução."""
    unicos = pd.Series(dias.drop_duplicates().sort_values().to_numpy())
    quebras = unicos.diff().dt.days.ne(1).cumsum()
    tamanhos = quebras.value_counts()
    grupo = tamanhos.idxmax()
    trecho = unicos[quebras == grupo]
    return int(tamanhos.max()), trecho.iloc[0], trecho.iloc[-1]


def _fracao(serie: pd.Series) -> float | None:
    """Média de um booleano anulável quando o campo é conhecido na maioria dos eventos."""
    if len(serie) == 0 or serie.notna().mean() < MINIMO_CONHECIDOS:
        return None
    return float(serie.dropna().astype(bool).mean())


def calcular_wrapped(dados: pd.DataFrame, nome: str, fuso_horario: str = '') -> Wrapped:
    """Calcula o Wrapped a partir de ``Historico.dados`` (todas as colunas preparadas)."""
    if dados.empty:
        raise ValueError('O histórico não contém músicas válidas para montar o Wrapped.')
    plays = dados[dados.ms_played >= TEMPO_MINIMO_PLAY_MS]
    if plays.empty:
        raise ValueError('O histórico não tem reproduções de pelo menos 30 segundos.')
    nome = (nome or '').strip() or 'Você'
    avisos: list[str] = []
    datas = dados['data']
    inicio, fim = datas.min(), datas.max()
    dias = datas.dt.normalize()
    total_plays = len(plays)

    top_artistas = _ranking_artistas(plays, 5)
    top_musicas = _ranking_musicas(plays, 5)
    artista_vida = top_artistas[0]
    contagem_artistas = plays['artista'].value_counts()
    contagem_artistas = contagem_artistas[contagem_artistas > 0]
    primeira_vez = plays.groupby('artista', observed=True)['data'].min()
    primeira_vez.index = primeira_vez.index.astype(object)

    primeiro = plays.iloc[plays['data_utc'].argmin()]

    # Anos: volume, líderes e descobertas.
    anos_plays = plays['data'].dt.year
    anos_todos = datas.dt.year
    horas_ano = dados['minutos'].groupby(anos_todos, observed=True).sum() / 60
    plays_ano = anos_plays.value_counts()
    por_ano_artista = (
        plays.assign(ano=anos_plays)
        .groupby(['ano', 'artista'], observed=True)
        .size()
        .rename('plays')
        .reset_index()
    )
    por_ano_artista['artista'] = por_ano_artista['artista'].astype(object)
    por_ano_artista = por_ano_artista.sort_values(
        ['ano', 'plays', 'artista'], ascending=[True, False, True], kind='stable'
    )
    top5_ano = por_ano_artista.groupby('ano', observed=True).head(5)
    novos = primeira_vez.dt.year.value_counts()
    musicas_ano = (
        plays.assign(ano=anos_plays)
        .groupby(['ano', 'musica', 'artista'], observed=True)
        .size()
        .rename('plays')
        .reset_index()
    )
    musicas_ano[['musica', 'artista']] = musicas_ano[['musica', 'artista']].astype(object)
    musicas_ano = musicas_ano.sort_values(
        ['ano', 'plays', 'musica'], ascending=[True, False, True], kind='stable'
    ).drop_duplicates('ano')
    lider_musica = {
        int(a): ItemRanking(str(m), int(p), artista=str(art))
        for a, m, art, p in musicas_ano.itertuples(index=False, name=None)
    }
    anos: list[ResumoAno] = []
    for ano in sorted(int(a) for a in horas_ano.index):
        lideres = top5_ano[top5_ano['ano'] == ano].head(3)
        anos.append(
            ResumoAno(
                ano=ano,
                horas=float(horas_ano.get(ano, 0.0)),
                plays=int(plays_ano.get(ano, 0)),
                top_artistas=[
                    ItemRanking(str(a), int(p))
                    for a, p in zip(lideres['artista'], lideres['plays'])
                ],
                top_musica=lider_musica.get(ano),
                novos_artistas=int(novos.get(ano, 0)),
            )
        )

    # Fidelidade: quem mais vezes esteve no top 5 anual.
    anos_no_top = top5_ano.groupby('artista', observed=True).size()
    plays_total_artista = top5_ano.groupby('artista', observed=True)['plays'].sum()
    fidelidade = (
        pd.DataFrame({'anos': anos_no_top, 'plays': plays_total_artista})
        .reset_index()
        .sort_values(['anos', 'plays', 'artista'], ascending=[False, False, True], kind='stable')
    )
    fiel_nome, fiel_anos, fiel_plays = fidelidade.iloc[0][['artista', 'anos', 'plays']]
    anos_do_fiel = sorted(int(a) for a in top5_ano.loc[top5_ano['artista'] == fiel_nome, 'ano'])

    # Dia recorde e maior repetição de uma música em um único dia.
    horas_dia = dados['minutos'].groupby(dias, observed=True).sum() / 60
    dia_recorde = horas_dia.idxmax()
    plays_dia = plays[plays['data'].dt.normalize() == dia_recorde]
    artista_dia = str(plays_dia['artista'].value_counts().idxmax()) if len(plays_dia) else ''
    repeticoes = (
        plays.assign(dia=plays['data'].dt.normalize())
        .groupby(['dia', 'musica', 'artista'], observed=True)
        .size()
    )
    dia_rep, musica_rep, artista_rep = repeticoes.idxmax()

    sequencia, inicio_seq, fim_seq = _maior_sequencia(dias)

    # Relógio e calendário.
    horas_plays = plays['hora'].astype(int)
    por_hora = horas_plays.value_counts().reindex(range(24), fill_value=0)
    periodos = {
        nome_periodo: float(horas_plays.between(ini, fim_p - 1).mean())
        for nome_periodo, ini, fim_p in PERIODOS
    }
    semana = plays['dia_semana'].value_counts()
    fim_de_semana = float(plays['dia_semana'].ge(5).mean())

    # Hábitos (podem faltar em exportações antigas).
    pulos = _fracao(dados['pulada'])
    motivos = dados['motivo_fim']
    motivos_conhecidos = motivos.notna().mean() >= MINIMO_CONHECIDOS
    if pulos is None and motivos_conhecidos:
        pulos = float(motivos.dropna().eq('fwdbtn').mean())
    fim_natural = float(motivos.dropna().eq('trackdone').mean()) if motivos_conhecidos else None
    aleatorio = _fracao(dados['aleatorio'])
    offline = _fracao(dados['offline'])
    plataformas_validas = dados['plataforma'].dropna()
    plataformas = [
        (str(nome_p), float(v))
        for nome_p, v in plataformas_validas.value_counts(normalize=True).head(4).items()
        if v > 0
    ]
    if pulos is None and aleatorio is None:
        avisos.append('Este histórico não traz pulos/aleatório; esses hábitos foram omitidos.')

    top10_musicas = plays.groupby(['musica', 'artista'], observed=True).size().nlargest(10).sum()
    medidas: dict[str, float | None] = {
        'top1': artista_vida.plays / total_plays,
        'descobertas': len(contagem_artistas) / total_plays,
        'madrugada': periodos['Madrugada'],
        'manha': periodos['Manhã'],
        'noite': periodos['Noite'],
        'fim_de_semana': fim_de_semana,
        'pulos': pulos,
        'aleatorio': aleatorio,
        'fim_natural': fim_natural,
        'sequencia': float(sequencia),
        'repeticao': float(top10_musicas) / total_plays,
        'offline': offline,
    }
    wrapped = Wrapped(
        nome=nome,
        inicio=inicio,
        fim=fim,
        dias_periodo=int((fim.normalize() - inicio.normalize()).days) + 1,
        dias_com_musica=int(dias.nunique()),
        horas=float(dados['minutos'].sum() / 60),
        plays=total_plays,
        quantidade_artistas=int(len(contagem_artistas)),
        quantidade_musicas=int(plays.groupby(['musica', 'artista'], observed=True).ngroups),
        artista_vida=artista_vida,
        descoberta_artista_vida=primeira_vez[artista_vida.nome],
        participacao_artista_vida=artista_vida.plays / total_plays,
        top_artistas=top_artistas,
        top_musicas=top_musicas,
        primeira_musica=ItemRanking(str(primeiro['musica']), 1, artista=str(primeiro['artista'])),
        primeira_data=primeiro['data'],
        anos=anos,
        dia_recorde=dia_recorde,
        horas_dia_recorde=float(horas_dia.max()),
        artista_dia_recorde=artista_dia,
        repeticao_dia=ItemRanking(str(musica_rep), int(repeticoes.max()), artista=str(artista_rep)),
        data_repeticao_dia=dia_rep,
        sequencia=sequencia,
        inicio_sequencia=inicio_seq,
        fim_sequencia=fim_seq,
        plays_por_hora=[int(x) for x in por_hora.tolist()],
        pico_hora=int(por_hora.idxmax()),
        dia_semana_favorito=DIAS_SEMANA[int(semana.idxmax())],
        periodos=periodos,
        fiel=ItemRanking(str(fiel_nome), int(fiel_plays)),
        anos_fiel=int(fiel_anos),
        fiel_anos=anos_do_fiel,
        habitos={
            'pulos': pulos,
            'aleatorio': aleatorio,
            'offline': offline,
            'fim_natural': fim_natural,
        },
        plataformas=plataformas,
        medidas=medidas,
        arquetipos=classificar(medidas),
        fuso_horario=fuso_horario,
        avisos=avisos,
    )
    return _com_uris(wrapped, plays)


def _com_uris(w: Wrapped, plays: pd.DataFrame) -> Wrapped:
    """Põe nas músicas do Wrapped o ID do Spotify mais tocado de cada par (música, artista)."""
    if 'uri' not in plays:
        return w
    musicas = [w.primeira_musica, w.repeticao_dia, *w.top_musicas]
    musicas += [a.top_musica for a in w.anos if a.top_musica]
    base = plays.loc[
        plays['musica'].isin({m.nome for m in musicas}) & plays['uri'].notna(),
        ['musica', 'artista', 'uri'],
    ]
    melhor: dict[tuple[str, str], str] = {}
    for (musica, artista, uri), _ in base.astype(object).value_counts().items():
        melhor.setdefault((musica, artista), uri)  # value_counts vem do mais tocado ao menos

    def com(item: ItemRanking) -> ItemRanking:
        uri = melhor.get((item.nome, item.artista))
        return replace(item, uri=str(uri)) if uri else item

    return replace(
        w,
        primeira_musica=com(w.primeira_musica),
        repeticao_dia=com(w.repeticao_dia),
        top_musicas=[com(m) for m in w.top_musicas],
        anos=[replace(a, top_musica=com(a.top_musica)) if a.top_musica else a for a in w.anos],
    )


def wrapped_de_arquivos(
    arquivos: Caminho | list[Caminho],
    nome: str,
    configuracao: ConfiguracaoCarga | None = None,
) -> Wrapped:
    """Carrega uma ou várias partes do histórico de uma pessoa e calcula o Wrapped."""
    config = configuracao or ConfiguracaoCarga(musicas_ignoradas=())
    historico = carregar_historicos(arquivos, configuracao=config)
    return calcular_wrapped(historico.dados, nome, config.fuso_horario)
