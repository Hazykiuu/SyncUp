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
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from generos import USER_AGENT
from perfil_gosto import TAMANHO_RANKING, PerfilGosto, agora_iso

URL_API = 'https://api.listenbrainz.org/1'
PERIODOS_API = {'short_term': 'month', 'medium_term': 'half_yearly', 'long_term': 'year'}
# Nomes de usuário do ListenBrainz/MusicBrainz: letras, números e poucos símbolos.
USUARIO_VALIDO = re.compile(r'^[\w.\- ]{1,64}$')


def _get(cliente: httpx.Client, caminho: str, **params) -> dict:
    resposta = cliente.get(f'{URL_API}{caminho}', params=params)
    if resposta.status_code == 404:
        raise ValueError(
            'Usuário não encontrado no ListenBrainz. Confira o nome (é o do perfil público).'
        )
    if resposta.status_code == 204:
        return {}
    if resposta.status_code == 429:
        raise ValueError('O ListenBrainz está ocupado agora. Tente de novo em instantes.')
    resposta.raise_for_status()
    return resposta.json().get('payload') or {}


def coletar_perfil_listenbrainz(
    usuario: str, nome: str | None = None, cliente: httpx.Client | None = None
) -> PerfilGosto:
    """Top artistas e músicas nos três períodos e os últimos 50 listens."""
    usuario = (usuario or '').strip()
    if not USUARIO_VALIDO.match(usuario):
        raise ValueError(f'Nome de usuário do ListenBrainz inválido: {usuario[:64]!r}.')
    base = f'/user/{quote(usuario, safe="")}'
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
