"""Ingestão robusta, diagnóstico de descartes e caches em memória/Parquet."""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from importlib.util import find_spec
from multiprocessing import get_context
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Any

import pandas as pd

TETO_MS = 86_400_000  # 24 h: o maior play aceito (igual a site/app/js/historico.js)

from configuracao import ConfiguracaoCarga, normalizar_nome

try:  # Leitor JSON opcional e muito mais rápido; o padrão continua funcionando sem ele.
    import orjson as _orjson
except ImportError:  # pragma: no cover - depende do ambiente
    _orjson = None

Caminho = str | Path
FUSO_HORARIO = 'America/Sao_Paulo'
CAMPOS_SPOTIFY = (
    'ts',
    'ms_played',
    'master_metadata_track_name',
    'master_metadata_album_artist_name',
)
CHAVE_DEDUPLICACAO = ['data_utc', 'ms_played', 'musica', 'artista']
# Um histórico estendido real tem dezenas de MB; 1 GB barra ZIPs malformados ou maliciosos
# (zip bomb) antes de descompactar. O mesmo teto vale para o upload (app.py).
LIMITE_BYTES = 1024**3
MAXIMO_HISTORICOS_CACHE = 6  # Comporta o Modo Grupo completo sem reler arquivos.
VERSAO_CACHE = 'v08-uri-1'
COLUNAS_PREPARADAS = [
    'data',
    'data_utc',
    'ms_played',
    'musica',
    'artista',
    'minutos',
    'hora',
    'ano_mes',
    'dia_semana',
    'data_dia',
    # v0.7 · hábitos para o Wrapped; ausentes em exportações antigas (valores nulos).
    'pulada',
    'aleatorio',
    'offline',
    'plataforma',
    'motivo_fim',
    # v1.4 · ID da faixa no Spotify (capa exata no Wrapped web); nulo quando falta.
    'uri',
]
# Campos opcionais do Spotify → nomes internos. A plataforma guarda só a família
# (Android, Windows…), nunca o modelo do aparelho ou a versão do sistema.
CAMPOS_HABITOS = {
    'skipped': 'pulada',
    'shuffle': 'aleatorio',
    'offline': 'offline',
    'platform': 'plataforma',
    'reason_end': 'motivo_fim',
    'spotify_track_uri': 'uri',
}
CAMPOS_BOOLEANOS = ('pulada', 'aleatorio', 'offline')
ChaveArquivo = tuple[str, int, int, int, int]


@dataclass(frozen=True)
class ContadoresCarga:
    """Descartes exclusivos: a soma dos motivos mais registros finais fecha o total."""

    recebidos: int = 0
    podcasts: int = 0
    ms_invalidos: int = 0
    datas_invalidas: int = 0
    metadados_invalidos: int = 0
    various_artists_encontrados: int = 0
    various_artists_descartados: int = 0
    ignorados: int = 0
    duplicados: int = 0
    validos: int = 0


@dataclass(frozen=True)
class Historico:
    """Dados, origem e diagnóstico; campos pessoais de dispositivo não são retidos."""

    dados: pd.DataFrame
    sha256: str
    arquivo: str
    registros_antes_deduplicacao: int
    duplicados_removidos: int
    contadores: ContadoresCarga
    fuso_horario: str
    origem_cache: str


_memoria: OrderedDict[tuple[str, ConfiguracaoCarga], Historico] = OrderedDict()
_trava = RLock()


def sha256_arquivo(arquivo: Caminho) -> str:
    """Calcula SHA-256 em blocos de um megabyte."""
    resumo = hashlib.sha256()
    with Path(arquivo).open('rb') as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b''):
            resumo.update(bloco)
    return resumo.hexdigest()


def _chave_arquivo(arquivo: Caminho) -> ChaveArquivo:
    """Detecta alteração do arquivo antes de reutilizar seu hash em memória."""
    caminho = Path(arquivo).resolve()
    try:
        estado = caminho.stat()
    except OSError as erro:
        raise ValueError(
            'Não foi possível acessar o histórico. Confira o arquivo e as permissões de leitura.'
        ) from erro
    return str(caminho), estado.st_size, estado.st_mtime_ns, estado.st_ctime_ns, estado.st_ino


@lru_cache(maxsize=64)
def _hash_cache(chave: ChaveArquivo) -> str:
    """Evita rehash nas comparações repetidas da mesma versão de arquivo."""
    return sha256_arquivo(chave[0])


def sha_em_cache(arquivo: Caminho) -> str:
    """SHA-256 do arquivo, reaproveitado enquanto tamanho e datas não mudam."""
    return _hash_cache(_chave_arquivo(arquivo))


Colunas = dict[str, list[Any]]
_SEM_CAMPOS: dict[str, Any] = {}


def _ler_json(conteudo: bytes) -> Any:
    """Decodifica UTF-8 (com ou sem BOM) e usa orjson quando instalado.

    O texto é decodificado antes para que erros de codificação continuem
    distintos de JSON malformado. Valores aceitos apenas pelo módulo padrão
    (NaN, inteiros enormes) recaem no ``json`` da biblioteca padrão.
    """
    texto = conteudo.decode('utf-8-sig')
    if _orjson is not None:
        try:
            return _orjson.loads(texto)
        except _orjson.JSONDecodeError:
            pass
    return json.loads(texto)


def _entrada_ignorada(nome: str) -> bool:
    """Ignora pastas e metadados do macOS (``__MACOSX/``, ``._arquivo.json``)."""
    base = nome.rsplit('/', 1)[-1]
    return (
        nome.endswith('/')
        or nome.startswith('__MACOSX/')
        or '/__MACOSX/' in nome
        or base.startswith('._')
        or not base.lower().endswith('.json')
    )


def _novas_colunas() -> Colunas:
    """Cria as listas colunares acumuladas durante a extração."""
    return {campo: [] for campo in (*CAMPOS_SPOTIFY, 'podcast', *CAMPOS_HABITOS)}


def familia_plataforma(texto: object) -> str | None:
    """Reduz o campo ``platform`` a uma família, descartando modelo e versão do aparelho."""
    if not isinstance(texto, str) or not texto.strip() or texto == 'not_applicable':
        return None
    t = texto.casefold()
    for chaves, familia in (
        (('web_player', 'web player', 'webplayer'), 'Navegador'),
        (('android',), 'Android'),
        (('ios', 'iphone', 'ipad'), 'iOS'),
        (('windows',), 'Windows'),
        (('os x', 'osx', 'macos', 'mac os'), 'macOS'),
        (('linux',), 'Linux'),
        (('web',), 'Navegador'),
        (
            ('partner', 'cast', 'tv', 'playstation', 'xbox', 'sonos', 'alexa', 'echo', 'car'),
            'TV, console ou caixa de som',
        ),
    ):
        if any(chave in t for chave in chaves):
            return familia
    return 'Outro'


def _conferir_tamanho(total: int) -> None:
    if total > LIMITE_BYTES:
        raise ValueError(
            f'O histórico passa de {LIMITE_BYTES // 1024**3} GB descompactado. Use o histórico '
            'estendido de áudio do Spotify (ZIP ou JSON).'
        )


def _extrair_registros_impl(caminho: Path) -> Colunas:
    """Seleciona os quatro campos musicais e um indicador explícito de podcast.

    A extração é colunar: cada campo é lido em uma compreensão de lista, sem
    criar tuplas por evento. Tipos inesperados viram ``None`` e são contados
    como descartes na limpeza, exatamente como antes.
    """
    colunas = _novas_colunas()
    encontrados: set[str] = set()
    campos = set(CAMPOS_SPOTIFY)
    # O JSON cria um texto novo a cada ocorrência: guardar cada nome uma vez só baixa o pico
    # de memória (285 mil plays no navegador: 446 → 371 MB), decisivo no iOS (~350 MB).
    unicos: dict[str, str] = {}
    unico = unicos.setdefault

    def selecionar(conteudo: Any) -> None:
        """Processa listas de histórico e ignora listas auxiliares sem campos reconhecidos."""
        if not isinstance(conteudo, list):
            return
        reconhecido = any(
            isinstance(item, dict) and any(c in item for c in CAMPOS_SPOTIFY) for item in conteudo
        )
        if not reconhecido:
            return
        itens = [item if isinstance(item, dict) else _SEM_CAMPOS for item in conteudo]
        for item in itens:
            if len(encontrados) == len(campos):
                break
            encontrados.update(campos.intersection(item))
        colunas['ts'].extend(
            v if isinstance(v, str) else None for v in (item.get('ts') for item in itens)
        )
        colunas['ms_played'].extend(
            None if isinstance(v, bool) else v for v in (item.get('ms_played') for item in itens)
        )
        for campo in CAMPOS_SPOTIFY[2:]:
            colunas[campo].extend(
                unico(v, v) if isinstance(v, str) else None
                for v in (item.get(campo) for item in itens)
            )
        colunas['podcast'].extend(
            bool(
                item.get('episode_name')
                or item.get('episode_show_name')
                or item.get('spotify_episode_uri')
            )
            for item in itens
        )
        for campo in ('skipped', 'shuffle', 'offline'):
            colunas[campo].extend(
                v if isinstance(v, bool) else None for v in (item.get(campo) for item in itens)
            )
        for campo in ('platform', 'reason_end', 'spotify_track_uri'):
            colunas[campo].extend(
                unico(v, v) if isinstance(v, str) else None
                for v in (item.get(campo) for item in itens)
            )

    sufixo = caminho.suffix.lower()
    if sufixo == '.zip':
        with zipfile.ZipFile(caminho) as pacote:
            entradas = [i for i in pacote.infolist() if not _entrada_ignorada(i.filename)]
            # O zipfile para de ler no tamanho declarado: conferir o total basta.
            _conferir_tamanho(sum(i.file_size for i in entradas))
            for info in entradas:
                selecionar(_ler_json(pacote.read(info)))
    elif sufixo == '.json':
        _conferir_tamanho(caminho.stat().st_size)
        selecionar(_ler_json(caminho.read_bytes()))
    else:
        raise ValueError('Selecione um arquivo ZIP ou JSON do histórico estendido.')
    if not campos.issubset(encontrados):
        raise ValueError('Use o histórico estendido de áudio do Spotify (ZIP ou JSON).')
    return colunas


def _extrair_registros(caminho: Path) -> Colunas:
    """Traduz falhas comuns de entrada para mensagens amigáveis em português."""
    try:
        return _extrair_registros_impl(caminho)
    except json.JSONDecodeError as erro:
        raise ValueError(
            'O histórico contém um JSON inválido. Confira se o download foi concluído.'
        ) from erro
    except zipfile.BadZipFile as erro:
        raise ValueError(
            'O arquivo ZIP está inválido ou incompleto. Baixe o histórico novamente.'
        ) from erro
    except UnicodeDecodeError as erro:
        raise ValueError(
            'Não foi possível ler o texto do histórico. Use arquivos JSON em UTF-8.'
        ) from erro
    except OSError as erro:
        raise ValueError(
            'Não foi possível ler o histórico. Confira o arquivo e as permissões.'
        ) from erro


def _filtrar(dados: pd.DataFrame, manter: pd.Series) -> pd.DataFrame:
    """Evita copiar a tabela quando todos os registros já satisfazem o filtro."""
    return dados if bool(manter.all()) else dados.loc[manter].copy()


def _normalizar_indice(nomes: pd.Index) -> pd.Index:
    """Versão vetorizada de ``normalizar_nome`` (NFKC, casefold, sem pontuação/espaços)."""
    if len(nomes) == 0:
        return pd.Index([], dtype=object)
    return (
        pd.Index(nomes.astype(object))
        .str.normalize('NFKC')
        .str.casefold()
        .str.replace(r'[\W_]+', '', regex=True)
    )


def _categorias_ordenadas(coluna: pd.Series) -> pd.Series:
    """Remove níveis não observados e mantém a ordem alfabética das categorias."""
    if not isinstance(coluna.dtype, pd.CategoricalDtype):
        return coluna.astype('category')
    coluna = coluna.cat.remove_unused_categories()
    categorias = coluna.cat.categories
    if not categorias.is_monotonic_increasing:
        coluna = coluna.cat.reorder_categories(categorias.sort_values())
    return coluna


def _preparar_habitos(dados: pd.DataFrame) -> None:
    """Tipos compactos para os hábitos: booleanos anuláveis e categorias."""
    for coluna in CAMPOS_BOOLEANOS:
        dados[coluna] = dados[coluna].astype('boolean')
    plataformas = dados['plataforma'].astype('category')
    familias = {nome: familia_plataforma(nome) for nome in plataformas.cat.categories}
    dados['plataforma'] = plataformas.astype(object).map(familias)
    _tipos_habitos(dados)


def _tipos_habitos(dados: pd.DataFrame) -> None:
    """Fixa os tipos dos hábitos; usado também ao ler o Parquet (colunas vazias)."""
    for coluna in CAMPOS_BOOLEANOS:
        dados[coluna] = dados[coluna].astype('boolean')
    for coluna in ('plataforma', 'motivo_fim', 'uri'):
        dados[coluna] = dados[coluna].astype(object).astype('category')


def _limpar(
    registros: list[tuple] | Colunas, config: ConfiguracaoCarga
) -> tuple[pd.DataFrame, ContadoresCarga, int]:
    """Aplica descartes em ordem exclusiva e calcula colunas temporais uma única vez."""
    if isinstance(registros, dict):
        dados = pd.DataFrame(registros, columns=[*CAMPOS_SPOTIFY, 'podcast', *CAMPOS_HABITOS])
    else:
        # A API anterior de limpar_dados também aceitava tuplas de quatro campos.
        colunas = list(CAMPOS_SPOTIFY) + (
            ['podcast'] if registros and len(registros[0]) == 5 else []
        )
        dados = pd.DataFrame.from_records(registros, columns=colunas)
    if 'podcast' not in dados:
        dados['podcast'] = False
    for campo in CAMPOS_HABITOS:
        if campo not in dados:
            dados[campo] = None
    dados = dados.rename(
        columns={
            'master_metadata_track_name': 'musica',
            'master_metadata_album_artist_name': 'artista',
            **CAMPOS_HABITOS,
        }
    )
    contagens: dict[str, int] = {'recebidos': len(dados)}
    podcasts = dados['podcast'].fillna(False).astype(bool)
    contagens['podcasts'] = int(podcasts.sum())
    dados = _filtrar(dados, ~podcasts)
    dados['ms_played'] = pd.to_numeric(dados['ms_played'], errors='coerce')
    # Um play não passa de 24 h: acima disso é arquivo corrompido (e estouraria o int64 da sintonia).
    ms_validos = dados['ms_played'].ge(0) & dados['ms_played'].le(TETO_MS)
    contagens['ms_invalidos'] = int((~ms_validos).sum())
    dados = _filtrar(dados, ms_validos)
    datas = pd.to_datetime(dados['ts'], utc=True, format='ISO8601', errors='coerce')
    # Antes de 1970 é relógio zerado: o Spotify nem existia (e o JS calcula dias a partir de 1970).
    datas = datas.where(datas >= pd.Timestamp(0, tz='UTC'))
    contagens['datas_invalidas'] = int(datas.isna().sum())
    dados['data_utc'] = datas
    dados = _filtrar(dados, dados['data_utc'].notna())
    for coluna in ('musica', 'artista'):
        # Categorias: cada nome distinto é limpo uma única vez e filtros usam códigos inteiros.
        categoria = dados[coluna].astype('category')
        originais = categoria.cat.categories
        limpos = originais.str.strip()
        if not limpos.equals(originais):
            if limpos.is_unique:
                categoria = categoria.cat.rename_categories(limpos)
            else:  # Nomes que só diferem por espaços nas bordas viram o mesmo nome.
                categoria = categoria.astype(object).map(dict(zip(originais, limpos)))
                categoria = categoria.astype('category')
        dados[coluna] = categoria
    identificados = (
        dados['musica'].notna()
        & dados['artista'].notna()
        & dados['musica'].ne('')
        & dados['artista'].ne('')
    )
    contagens['metadados_invalidos'] = int((~identificados).sum())
    dados = _filtrar(dados, identificados)
    categorias_artistas = dados.artista.cat.categories
    normal_artistas = dict(zip(categorias_artistas, _normalizar_indice(categorias_artistas)))
    alvo_varios = normalizar_nome('Various Artists')
    varios = dados.artista.isin(
        [n for n, normal in normal_artistas.items() if normal == alvo_varios]
    )
    contagens['various_artists_encontrados'] = int(varios.sum())
    contagens['various_artists_descartados'] = (
        int(varios.sum()) if config.various_artists == 'ignorar' else 0
    )
    if config.various_artists == 'ignorar':
        dados = _filtrar(dados, ~varios)
    musicas_ignoradas = {normalizar_nome(n) for n in config.musicas_ignoradas if n.strip()}
    artistas_ignorados = {normalizar_nome(n) for n in config.artistas_ignorados if n.strip()}
    ignorados = pd.Series(False, index=dados.index)
    if musicas_ignoradas:
        categorias = dados.musica.cat.categories
        alvos = categorias[_normalizar_indice(categorias).isin(musicas_ignoradas)]
        ignorados |= dados.musica.isin(alvos)
    if artistas_ignorados:
        alvos = [n for n, normal in normal_artistas.items() if normal in artistas_ignorados]
        ignorados |= dados.artista.isin(alvos)
    contagens['ignorados'] = int(ignorados.sum())
    dados = _filtrar(dados, ~ignorados)
    antes_dedup = len(dados)
    if config.deduplicar:
        dados = deduplicar_registros(dados)
    contagens['duplicados'] = antes_dedup - len(dados)
    contagens['validos'] = len(dados)
    # UTC identifica o instante. Horário local sem fuso é calculado somente aqui.
    # O nome IANA (já validado) usa o caminho vetorizado do pandas, ~10x mais rápido que ZoneInfo.
    dados['data'] = dados.data_utc.dt.tz_convert(config.fuso_horario).dt.tz_localize(None)
    dados['hora'] = dados.data.dt.hour.astype('int8')
    dados['ano_mes'] = (dados.data.dt.year * 100 + dados.data.dt.month).astype('int32')
    dados['dia_semana'] = dados.data.dt.dayofweek.astype('int8')
    dados['data_dia'] = (dados.ano_mes * 100 + dados.data.dt.day).astype('int32')
    dados['minutos'] = dados.ms_played / 60_000
    for coluna in ('artista', 'musica'):
        dados[coluna] = _categorias_ordenadas(dados[coluna])
    _preparar_habitos(dados)
    return dados[COLUNAS_PREPARADAS], ContadoresCarga(**contagens), antes_dedup


def limpar_dados(
    registros: list[tuple], configuracao: ConfiguracaoCarga | None = None
) -> pd.DataFrame:
    """Limpa tuplas de quatro/cinco campos com as opções informadas."""
    preparados = []
    for registro in registros:
        ts, ms, musica, artista = registro[:4]
        podcast = bool(registro[4]) if len(registro) == 5 else False
        preparados.append(
            (
                ts if isinstance(ts, str) else None,
                None if isinstance(ms, bool) else ms,
                musica if isinstance(musica, str) else None,
                artista if isinstance(artista, str) else None,
                podcast,
            )
        )
    return _limpar(preparados, configuracao or ConfiguracaoCarga())[0]


def deduplicar_registros(dados: pd.DataFrame) -> pd.DataFrame:
    """Deduplica pelo instante UTC; não confunde horários repetidos por horário de verão."""
    chave = (
        CHAVE_DEDUPLICACAO if 'data_utc' in dados else ['data', 'ms_played', 'musica', 'artista']
    )
    return dados.drop_duplicates(subset=chave, keep='first').copy()


def _arquivos_cache(sha: str, config: ConfiguracaoCarga) -> tuple[Path, Path, str]:
    """Combina SHA-256 original, versão de esquema e opções de conteúdo."""
    opcoes = {'versao': VERSAO_CACHE, 'opcoes': config.opcoes_dados()}
    identidade = hashlib.sha256(
        json.dumps(opcoes, sort_keys=True, ensure_ascii=False).encode('utf-8')
    ).hexdigest()
    base = Path(config.diretorio_cache).resolve() / f'{sha}-{identidade}'
    return base.with_suffix('.parquet'), base.with_suffix('.json'), identidade


def _ler_cache(sha: str, config: ConfiguracaoCarga) -> tuple[Historico | None, bool]:
    """Recupera Parquet validado; cache ausente/corrompido será reconstruído."""
    parquet, manifesto, identidade = _arquivos_cache(sha, config)
    existe = parquet.exists() or manifesto.exists()
    if not (parquet.is_file() and manifesto.is_file()):
        return None, existe
    try:
        meta = json.loads(manifesto.read_text(encoding='utf-8'))
        if (
            meta['sha256'] != sha
            or meta['identidade'] != identidade
            or meta['versao'] != VERSAO_CACHE
        ):
            return None, True
        if sha256_arquivo(parquet) != meta['parquet_sha256']:
            return None, True
        dados = pd.read_parquet(parquet, engine='pyarrow')
        if all(c in dados for c in CAMPOS_HABITOS.values()):
            _tipos_habitos(dados)
        contadores = ContadoresCarga(**meta['contadores'])
        motivos = (
            'podcasts',
            'ms_invalidos',
            'datas_invalidas',
            'metadados_invalidos',
            'various_artists_descartados',
            'ignorados',
            'duplicados',
        )
        if any(
            not isinstance(v, int) or isinstance(v, bool) or v < 0
            for v in asdict(contadores).values()
        ):
            return None, True
        if contadores.recebidos != contadores.validos + sum(
            getattr(contadores, c) for c in motivos
        ):
            return None, True
        if meta['antes_dedup'] != contadores.validos + contadores.duplicados:
            return None, True
        if list(dados.columns) != COLUNAS_PREPARADAS or len(dados) != contadores.validos:
            return None, True
        if any(str(dados[c].dtype) != 'category' for c in ('musica', 'artista')):
            return None, True
        return Historico(
            dados,
            sha,
            '',
            meta['antes_dedup'],
            contadores.duplicados,
            contadores,
            config.fuso_horario,
            'Parquet em disco',
        ), False
    except (OSError, ValueError, KeyError, TypeError):
        return None, True


def _gravar_cache(historico: Historico, config: ConfiguracaoCarga) -> str:
    """Grava arquivos temporários e publica cada arquivo por substituição atômica."""
    parquet, manifesto, identidade = _arquivos_cache(historico.sha256, config)
    temporarios: list[Path] = []
    try:
        parquet.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=parquet.parent, suffix='.parquet', delete=False) as arquivo:
            temp_parquet = Path(arquivo.name)
        temporarios.append(temp_parquet)
        historico.dados.to_parquet(temp_parquet, engine='pyarrow', index=True)
        meta = {
            'versao': VERSAO_CACHE,
            'sha256': historico.sha256,
            'identidade': identidade,
            'parquet_sha256': sha256_arquivo(temp_parquet),
            'contadores': asdict(historico.contadores),
            'antes_dedup': historico.registros_antes_deduplicacao,
        }
        with NamedTemporaryFile(
            dir=parquet.parent, suffix='.json', mode='w', encoding='utf-8', delete=False
        ) as arquivo:
            temp_manifesto = Path(arquivo.name)
            temporarios.append(temp_manifesto)
            json.dump(meta, arquivo, ensure_ascii=False)
        os.replace(temp_parquet, parquet)
        os.replace(temp_manifesto, manifesto)
        return 'gravado em Parquet'
    except (OSError, ValueError):
        return 'não foi possível gravar o cache; análise mantida. Confira a pasta e as permissões'
    finally:
        for caminho in temporarios:
            caminho.unlink(missing_ok=True)


def carregar_historico(
    arquivo: Caminho,
    *,
    deduplicar: bool | None = None,
    configuracao: ConfiguracaoCarga | None = None,
) -> Historico:
    """Carrega dados e retorna uma cópia; opções e conteúdo invalidam ambos os caches."""
    config = configuracao or ConfiguracaoCarga()
    if deduplicar is not None:
        config = replace(config, deduplicar=deduplicar)
    if config.usar_cache_disco and find_spec('pyarrow') is None:
        raise ValueError(
            'Para ativar o cache Parquet, instale: pip install -r requirements-parquet.txt'
        )
    caminho = Path(arquivo).resolve()
    sha = _hash_cache(_chave_arquivo(caminho))
    chave = (sha, config)
    with _trava:
        if chave in _memoria:
            _memoria.move_to_end(chave)
            original = replace(_memoria[chave], origem_cache='Memória da sessão')
            return replace(original, dados=original.dados.copy(), arquivo=caminho.name)
    # Leitura fora da trava: sessões e arquivos diferentes não esperam uns pelos outros.
    original, corrompido = _ler_cache(sha, config) if config.usar_cache_disco else (None, False)
    if original is None:
        dados, contadores, antes_dedup = _limpar(_extrair_registros(caminho), config)
        original = Historico(
            dados,
            sha,
            '',
            antes_dedup,
            contadores.duplicados,
            contadores,
            config.fuso_horario,
            'Arquivo original',
        )
        if config.usar_cache_disco:
            status = _gravar_cache(original, config)
            prefixo = 'cache inválido reconstruído; ' if corrompido else ''
            original = replace(original, origem_cache=f'Arquivo original; {prefixo}{status}')
    with _trava:
        # Se outra thread leu o mesmo arquivo antes, todos usam a versão já guardada.
        original = _memoria.setdefault(chave, original)
        _memoria.move_to_end(chave)
        while len(_memoria) > MAXIMO_HISTORICOS_CACHE:
            _memoria.popitem(last=False)
    return replace(original, dados=original.dados.copy(), arquivo=caminho.name)


def carregar(
    arquivo: Caminho,
    *,
    deduplicar: bool | None = None,
    configuracao: ConfiguracaoCarga | None = None,
) -> pd.DataFrame:
    """Preserva o retorno DataFrame e acrescenta opções explícitas de ingestão."""
    return carregar_historico(arquivo, deduplicar=deduplicar, configuracao=configuracao).dados


def limpar_cache() -> None:
    """Limpa memória e hashes; mantém o cache opcional em disco."""
    with _trava:
        _memoria.clear()
        _hash_cache.cache_clear()


_processos: ProcessPoolExecutor | None = None
_paralelo_habilitado = False
MINIMO_BYTES_PARALELO = 2 * 1024 * 1024


def habilitar_leitura_paralela(ativo: bool = True) -> None:
    """Liga a leitura paralela em processos (a interface liga; a API Python não).

    Processos ``spawn`` reimportam o módulo principal; por isso só programas
    protegidos por ``if __name__ == '__main__':`` (como ``app.py``) devem ligar.
    """
    global _paralelo_habilitado
    _paralelo_habilitado = ativo
    if ativo:
        # Aquece os processos em segundo plano: a primeira comparação não paga a importação.
        executor = _executor(2)
        if executor is not None:
            try:
                for _ in range(executor._max_workers):
                    executor.submit(_aquecer)
            except Exception:  # noqa: BLE001 - aquecimento é opcional.
                pass


def _aquecer() -> None:
    """Tarefa vazia: força a criação do processo e a importação do pandas."""


def _preparar_bruto(
    caminho: str, config: ConfiguracaoCarga
) -> tuple[pd.DataFrame, ContadoresCarga, int]:
    """Trabalho de um processo auxiliar: extrai e limpa um único arquivo."""
    return _limpar(_extrair_registros(Path(caminho)), config)


def _executor(trabalhos: int) -> ProcessPoolExecutor | None:
    """Pool persistente (spawn) para ler vários arquivos grandes em paralelo.

    ``SYNCUP_PROCESSOS=0`` desativa; ``SYNCUP_PROCESSOS=n`` limita a n processos.
    """
    global _processos
    limite = os.environ.get('SYNCUP_PROCESSOS', '').strip()
    maximo = int(limite) if limite.isdigit() else min(4, os.cpu_count() or 1)
    if maximo < 2 or trabalhos < 2:
        return None
    if _processos is None:
        _processos = ProcessPoolExecutor(max_workers=maximo, mp_context=get_context('spawn'))
    return _processos


def precarregar(arquivos: list[Caminho], configuracao: ConfiguracaoCarga | None = None) -> int:
    """Lê em paralelo os arquivos grandes que ainda não estão no cache em memória.

    É apenas uma otimização: qualquer falha (arquivo inválido, processo
    indisponível) é ignorada aqui e reaparece, com a mensagem amigável de
    sempre, na leitura sequencial de ``carregar_historico``. Devolve quantos
    arquivos foram preparados em paralelo.
    """
    config = configuracao or ConfiguracaoCarga()
    if not _paralelo_habilitado or config.usar_cache_disco:
        return 0
    pendentes: dict[str, Path] = {}
    total = 0
    try:
        for arquivo in arquivos:
            caminho = Path(arquivo).resolve()
            chave = _chave_arquivo(caminho)
            sha = _hash_cache(chave)
            with _trava:
                if (sha, config) in _memoria or sha in pendentes:
                    continue
            pendentes[sha] = caminho
            total += chave[1]
    except (ValueError, OSError):
        return 0
    minimo = int(os.environ.get('SYNCUP_PARALELO_MIN_BYTES', MINIMO_BYTES_PARALELO))
    executor = _executor(len(pendentes)) if total >= minimo else None
    if executor is None:
        return 0
    try:
        futuros = {
            sha: executor.submit(_preparar_bruto, str(c), config) for sha, c in pendentes.items()
        }
    except Exception:  # noqa: BLE001 - pool indisponível: segue sequencial.
        return 0
    prontos = 0
    for sha, futuro in futuros.items():
        try:
            dados, contadores, antes_dedup = futuro.result()
        except Exception:  # noqa: BLE001 - o caminho sequencial reporta o erro real.
            continue
        historico = Historico(
            dados,
            sha,
            '',
            antes_dedup,
            contadores.duplicados,
            contadores,
            config.fuso_horario,
            'Arquivo original (leitura paralela)',
        )
        with _trava:
            _memoria[(sha, config)] = historico
            while len(_memoria) > MAXIMO_HISTORICOS_CACHE:
                _memoria.popitem(last=False)
        prontos += 1
    return prontos


def carregar_historicos(
    arquivos: Caminho | list[Caminho] | tuple[Caminho, ...],
    *,
    configuracao: ConfiguracaoCarga | None = None,
) -> Historico:
    """Une partes de um perfil, somando diagnósticos e preservando categorias.

    Arquivos inteiros com SHA idêntico são rejeitados, evitando dupla contagem
    acidental. Eventos repetidos entre partes seguem a opção de deduplicação.
    O hash combinado considera os conteúdos e a ordem, não os nomes dos arquivos.
    """
    config = configuracao or ConfiguracaoCarga()
    caminhos = [arquivos] if isinstance(arquivos, (str, Path)) else list(arquivos)
    if not caminhos:
        raise ValueError('Selecione pelo menos um ZIP ou JSON por perfil.')
    historicos = [carregar_historico(caminho, configuracao=config) for caminho in caminhos]
    if len(historicos) == 1:
        return historicos[0]
    if len({h.sha256 for h in historicos}) != len(historicos):
        raise ValueError(
            'O mesmo conteúdo foi selecionado mais de uma vez neste perfil. Remova o arquivo duplicado.'
        )
    dados = pd.concat([h.dados for h in historicos], ignore_index=True)
    antes = sum(h.registros_antes_deduplicacao for h in historicos)
    extras = 0
    if config.deduplicar:
        tamanho = len(dados)
        dados = dados.drop_duplicates(CHAVE_DEDUPLICACAO).reset_index(drop=True)
        extras = tamanho - len(dados)
    for coluna in ('artista', 'musica', 'plataforma', 'motivo_fim', 'uri'):
        dados[coluna] = dados[coluna].astype('category')
    somas = {
        campo: sum(getattr(h.contadores, campo) for h in historicos)
        for campo in ContadoresCarga.__dataclass_fields__
    }
    somas['duplicados'] += extras
    somas['validos'] -= extras
    resumo = hashlib.sha256(
        ('SyncUp-partes-v1:' + ':'.join(h.sha256 for h in historicos)).encode()
    ).hexdigest()
    return Historico(
        dados,
        resumo,
        ' + '.join(h.arquivo for h in historicos),
        antes,
        somas['duplicados'],
        ContadoresCarga(**somas),
        config.fuso_horario,
        'Partes unidas: ' + '; '.join(h.origem_cache for h in historicos),
    )
