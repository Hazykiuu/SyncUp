"""Perfil pelo ListenBrainz: fonte aberta, sem login, sem limite de pessoas.

O ListenBrainz (MetaBrainz, código aberto) guarda os "listens" de quem conecta o
Spotify (ou outro player) a uma conta gratuita. As estatísticas são públicas, então
basta o nome de usuário: nada de Client ID, lista de usuários ou token.

Os períodos da API são mapeados para os mesmos rankings do Spotify:
``month`` → ~4 semanas, ``half_yearly`` → ~6 meses, ``year`` → ~1 ano.
As estatísticas são recalculadas pelo ListenBrainz uma vez por dia; um período sem
dados volta 204 e vira um ranking vazio.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
import pandas as pd

from generos import USER_AGENT
from perfil_gosto import TAMANHO_RANKING, PerfilGosto, agora_iso

URL_API = 'https://api.listenbrainz.org/1'
PERIODOS_API = {'short_term': 'month', 'medium_term': 'half_yearly', 'long_term': 'year'}
# Nomes de usuário do ListenBrainz/MusicBrainz: letras, números e poucos símbolos.
USUARIO_VALIDO = re.compile(r'^[\w.\- ]{1,64}$')


LISTENS_POR_CHAMADA = 1000  # máximo que a API entrega por chamada
LIMITE_ESCUTAS = 5000  # 5 chamadas por pessoa: meses de escuta sem travar um Match grande
ESPERA_MAXIMA_S = 10  # a cota do ListenBrainz é de 30 chamadas a cada 10 s
TENTATIVAS_429 = 3  # quem leva 429 tenta de novo antes de desistir


def _espera(resposta: httpx.Response, padrao: int) -> int:
    """Segundos que o servidor pede (Reset-In ou Retry-After), com teto; senão o padrão."""
    for cabecalho in ('X-RateLimit-Reset-In', 'Retry-After'):
        valor = resposta.headers.get(cabecalho, '')
        if valor.isdigit():
            return min(int(valor), ESPERA_MAXIMA_S)
    return padrao


def _get(cliente: httpx.Client, caminho: str, **params) -> dict:
    for tentativa in range(TENTATIVAS_429):
        resposta = cliente.get(f'{URL_API}{caminho}', params=params)
        if resposta.status_code != 429:
            break
        if tentativa < TENTATIVAS_429 - 1:
            time.sleep(_espera(resposta, 2**tentativa))  # sem cabeçalho: 1 s, depois 2 s
    else:
        raise ValueError('O ListenBrainz está ocupado agora. Tente de novo em instantes.')
    if resposta.headers.get('X-RateLimit-Remaining') == '0':
        # Cota acabou: espera ela voltar antes da próxima chamada, em vez de levar um 429.
        time.sleep(_espera(resposta, 1))
    if resposta.status_code == 404:
        raise ValueError(
            'Usuário não encontrado no ListenBrainz. Confira o nome (é o do perfil público).'
        )
    if resposta.status_code == 204:
        return {}
    resposta.raise_for_status()
    return resposta.json().get('payload') or {}


def _base(usuario: str) -> str:
    """Caminho do usuário na API, validado antes de ir à rede."""
    if not USUARIO_VALIDO.match(usuario):
        raise ValueError(f'Nome de usuário do ListenBrainz inválido: {usuario[:64]!r}.')
    return f'/user/{quote(usuario, safe="")}'


def coletar_escutas_listenbrainz(
    usuario: str,
    fuso: str,
    cliente: httpx.Client | None = None,
    limite: int = LIMITE_ESCUTAS,
) -> pd.DataFrame:
    """Os ``limite`` listens mais recentes no formato do histórico, para a sintonia.

    O ListenBrainz guarda o início do play (``listened_at``) e a duração da
    faixa; o fim é início + duração. Listens sem duração ficam de fora.
    """
    base = _base((usuario or '').strip())
    proprio = cliente is None
    cliente = cliente or httpx.Client(timeout=10, headers={'User-Agent': USER_AGENT})
    linhas: list[tuple[str, str, int, int]] = []  # artista, música, início (s), duração (ms)
    max_ts = None
    try:
        for _ in range(-(-limite // LISTENS_POR_CHAMADA)):
            params = {'count': LISTENS_POR_CHAMADA, **({'max_ts': max_ts} if max_ts else {})}
            listens = _get(cliente, f'{base}/listens', **params).get('listens', [])
            for item in listens:
                meta = item.get('track_metadata') or {}
                extra = meta.get('additional_info') or {}
                creditos = (meta.get('mbid_mapping') or {}).get('artists') or [{}]
                # O artista principal bate com o do ZIP ("Röyksopp", não "Röyksopp feat. …").
                artista = creditos[0].get('artist_credit_name') or meta.get('artist_name')
                duracao = extra.get('duration_ms') or 1000 * (extra.get('duration') or 0)
                inicio = item.get('listened_at')
                if artista and meta.get('track_name') and isinstance(inicio, int) and duracao:
                    linhas.append((str(artista), str(meta['track_name']), inicio, int(duracao)))
            if len(listens) < LISTENS_POR_CHAMADA:
                break
            max_ts = min(int(i['listened_at']) for i in listens if i.get('listened_at'))
    finally:
        if proprio:
            cliente.close()
    tabela = pd.DataFrame(linhas[:limite], columns=['artista', 'musica', 'inicio', 'ms_played'])
    # shortcut: supõe o play inteiro (o ListenBrainz não guarda pulos); usar ms_played
    # real se a API passar a enviar quanto tocou.
    data_utc = pd.to_datetime(tabela.inicio, unit='s', utc=True) + pd.to_timedelta(
        tabela.ms_played, unit='ms'
    )
    return tabela.drop(columns='inicio').assign(
        data_utc=data_utc, data=data_utc.dt.tz_convert(fuso).dt.tz_localize(None)
    )


def coletar_perfil_listenbrainz(
    usuario: str, nome: str | None = None, cliente: httpx.Client | None = None
) -> PerfilGosto:
    """Top artistas e músicas nos três períodos e os últimos 50 listens."""
    usuario = (usuario or '').strip()
    base = _base(usuario)
    proprio = cliente is None
    # 7 chamadas por pessoa: 10 s cada limita a espera num serviço lento.
    cliente = cliente or httpx.Client(timeout=10, headers={'User-Agent': USER_AGENT})
    try:
        top_artistas, top_musicas = {}, {}
        for periodo, faixa in PERIODOS_API.items():
            artistas = _get(cliente, f'/stats{base}/artists', range=faixa, count=TAMANHO_RANKING)
            top_artistas[periodo] = [
                a['artist_name'] for a in artistas.get('artists', []) if a.get('artist_name')
            ]
            gravacoes = _get(
                cliente, f'/stats{base}/recordings', range=faixa, count=TAMANHO_RANKING
            )
            top_musicas[periodo] = [
                {'musica': g['track_name'], 'artista': g.get('artist_name', '')}
                for g in gravacoes.get('recordings', [])
                if g.get('track_name')
            ]
        listens = _get(cliente, f'{base}/listens', count=50).get('listens', [])
    finally:
        if proprio:
            cliente.close()
    recentes = [
        {
            'musica': str(item.get('track_metadata', {}).get('track_name', '')),
            'artista': str(item.get('track_metadata', {}).get('artist_name', '')),
            'tocada_em': datetime.fromtimestamp(int(item['listened_at']), timezone.utc).isoformat(),
        }
        for item in listens
        if item.get('listened_at') and item.get('track_metadata', {}).get('track_name')
    ]
    perfil = PerfilGosto(
        nome=(nome or usuario).strip(),
        fonte='listenbrainz',
        coletado_em=agora_iso(),
        top_artistas=top_artistas,
        top_musicas=top_musicas,
        recentes=recentes,
    )
    if not any(top_artistas.values()):
        raise ValueError(
            f'O ListenBrainz ainda não tem estatísticas de {usuario}. Elas são calculadas uma vez '
            'por dia depois que a conta recebe os primeiros listens.'
        )
    return perfil
