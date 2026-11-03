"""Ingestão de históricos, limpeza, deduplicação opcional e cache local."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import hashlib
import json
import re
import zipfile
import pandas as pd

Caminho = str | Path
FUSO_HORARIO = 'America/Sao_Paulo'
CAMPOS_SPOTIFY = (
    'ts', 'ms_played', 'master_metadata_track_name', 'master_metadata_album_artist_name',
)
CHAVE_DEDUPLICACAO = ['data', 'ms_played', 'musica', 'artista']
MUSICAS_EXCLUIDAS_NORMALIZADAS = frozenset({'falsaesperança'})
MAXIMO_HISTORICOS_CACHE = 4
ChaveArquivo = tuple[str, int, int, int, int]


@dataclass(frozen=True)
class Historico:
    """Dados preparados e informações de origem, sem metadados de dispositivo."""
    dados: pd.DataFrame
    sha256: str
    arquivo: str
    registros_antes_deduplicacao: int
    duplicados_removidos: int


def sha256_arquivo(arquivo: Caminho) -> str:
    """Calcula SHA-256 em blocos, sem carregar o arquivo inteiro na memória."""
    resumo = hashlib.sha256()
    with Path(arquivo).open('rb') as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b''):
            resumo.update(bloco)
    return resumo.hexdigest()


def _chave_arquivo(arquivo: Caminho) -> ChaveArquivo:
    """Identifica caminho e atributos usados para invalidar o cache da sessão."""
    caminho = Path(arquivo).resolve()
    estado = caminho.stat()
    return str(caminho), estado.st_size, estado.st_mtime_ns, estado.st_ctime_ns, estado.st_ino


def _extrair_registros(caminho: Path) -> list[tuple[Any, Any, Any, Any]]:
    """Lê ZIP/JSON e seleciona os quatro campos necessários à análise."""
    registros: list[tuple[Any, Any, Any, Any]] = []
    encontrados: set[str] = set()

    def selecionar(conteudo: Any) -> None:
        """Ignora metadados auxiliares que não são listas de execuções."""
        if not isinstance(conteudo, list):
            return
        for item in conteudo:
            if isinstance(item, dict) and 'ms_played' in item:
                if len(encontrados) < len(CAMPOS_SPOTIFY):
                    encontrados.update(set(CAMPOS_SPOTIFY).intersection(item))
                registros.append((item.get('ts'), item.get('ms_played'),
                                  item.get('master_metadata_track_name'),
                                  item.get('master_metadata_album_artist_name')))

    if caminho.suffix.lower() == '.zip':
        with zipfile.ZipFile(caminho) as pacote:
            for nome in pacote.namelist():
                if nome.lower().endswith('.json'):
                    selecionar(json.loads(pacote.read(nome).decode('utf-8-sig')))
    elif caminho.suffix.lower() == '.json':
        selecionar(json.loads(caminho.read_text(encoding='utf-8-sig')))
    else:
        raise ValueError('Selecione um arquivo ZIP ou JSON do histórico estendido.')
    if not set(CAMPOS_SPOTIFY).issubset(encontrados):
        raise ValueError('Use o histórico estendido de áudio do Spotify (ZIP ou JSON).')
    return registros


def limpar_dados(registros: list[tuple[Any, Any, Any, Any]]) -> pd.DataFrame:
    """Valida datas, tempos e nomes; remove podcasts e a exclusão solicitada."""
    dados = pd.DataFrame.from_records(registros, columns=CAMPOS_SPOTIFY)
    dados = dados.rename(columns={
        'master_metadata_track_name': 'musica', 'master_metadata_album_artist_name': 'artista',
    })
    dados['data'] = pd.to_datetime(dados['ts'], utc=True, errors='coerce').dt.tz_convert(FUSO_HORARIO)
    dados['ms_played'] = pd.to_numeric(dados['ms_played'], errors='coerce')
    dados = dados[['data', 'ms_played', 'musica', 'artista']].dropna()
    dados = dados[(dados['ms_played'] >= 0) & (dados['ms_played'] < float('inf'))].copy()
    for coluna in ('musica', 'artista'):
        nomes = {nome: nome.strip() if isinstance(nome, str) else None
                 for nome in dados[coluna].unique()}
        dados[coluna] = dados[coluna].map(nomes)
    # Nomes que não são texto ou ficam vazios não identificam uma música.
    dados = dados.dropna(subset=['musica', 'artista'])
    dados = dados[(dados['musica'] != '') & (dados['artista'] != '')].copy()
    excluidas = {nome for nome in dados['musica'].unique()
                 if re.sub(r'[^\w]', '', nome.casefold()) in MUSICAS_EXCLUIDAS_NORMALIZADAS}
    dados = dados[~dados['musica'].isin(excluidas)].copy()
    dados['minutos'] = dados['ms_played'] / 60000
    return dados


def deduplicar_registros(dados: pd.DataFrame) -> pd.DataFrame:
    """Mantém o primeiro registro por data, duração, música e artista.

    Esta regra básica não remove plays da mesma faixa em horários distintos.
    É opcional: duas execuções com os mesmos quatro campos são indistinguíveis.
    """
    return dados.drop_duplicates(subset=CHAVE_DEDUPLICACAO, keep='first').copy()


@lru_cache(maxsize=MAXIMO_HISTORICOS_CACHE)
def _historico_cache(chave: ChaveArquivo, deduplicar: bool) -> Historico:
    """Prepara um histórico; o objeto armazenado nunca é exposto diretamente."""
    caminho = Path(chave[0])
    dados = limpar_dados(_extrair_registros(caminho))
    quantidade = len(dados)
    if deduplicar:
        dados = deduplicar_registros(dados)
    return Historico(dados, sha256_arquivo(caminho), caminho.name, quantidade, quantidade - len(dados))


def carregar_historico(arquivo: Caminho, *, deduplicar: bool = False) -> Historico:
    """Retorna uma cópia do histórico; deduplicação é desativada por compatibilidade."""
    original = _historico_cache(_chave_arquivo(arquivo), deduplicar)
    return Historico(original.dados.copy(), original.sha256, original.arquivo,
                     original.registros_antes_deduplicacao, original.duplicados_removidos)


def carregar(arquivo: Caminho, *, deduplicar: bool = False) -> pd.DataFrame:
    """Preserva a API v0.4: devolve a tabela preparada do histórico."""
    return carregar_historico(arquivo, deduplicar=deduplicar).dados


def limpar_cache() -> None:
    """Libera todos os históricos mantidos na memória da sessão."""
    _historico_cache.cache_clear()
