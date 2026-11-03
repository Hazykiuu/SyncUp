"""Login com Spotify (OAuth 2.0 + PKCE) e coleta dos rankings para a conciliação.

Funciona com um app próprio criado em https://developer.spotify.com/dashboard em
**modo de desenvolvimento**: até 5 usuários cadastrados na allowlist do app e o
dono precisa ter Premium (regras de fev/2026). Não usa client secret: o fluxo
PKCE é o recomendado para apps que rodam no computador do usuário.

Guardamos apenas o PERFIL (rankings, recentes, seguidos) num JSON local. O token
de acesso só existe durante a coleta e nunca é gravado em disco.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import httpx

from perfil_gosto import PERIODOS, PerfilGosto, agora_iso, salvar_perfil

URL_AUTORIZAR = 'https://accounts.spotify.com/authorize'
URL_TOKEN = 'https://accounts.spotify.com/api/token'
URL_API = 'https://api.spotify.com/v1'
ESCOPOS = 'user-top-read user-read-recently-played user-follow-read'
PORTA_PADRAO = int(os.environ.get('SYNCUP_PORTA', '7860'))
REDIRECT_PADRAO = os.environ.get(
    'SPOTIFY_REDIRECT_URI', f'http://127.0.0.1:{PORTA_PADRAO}/spotify/callback'
)
PASTA_PERFIS = Path(os.environ.get('SYNCUP_PERFIS', Path(__file__).with_name('perfis_spotify')))
VALIDADE_LOGIN_S = 600


@dataclass
class LoginPendente:
    nome: str
    client_id: str
    verificador: str
    redirect_uri: str
    criado: float


_pendentes: dict[str, LoginPendente] = {}


def _desafio_pkce(verificador: str) -> str:
    resumo = hashlib.sha256(verificador.encode('ascii')).digest()
    return base64.urlsafe_b64encode(resumo).decode('ascii').rstrip('=')


def iniciar_login(nome: str, client_id: str, redirect_uri: str = REDIRECT_PADRAO) -> str:
    """Gera a URL de autorização do Spotify e guarda o estado/verificador em memória."""
    nome, client_id = (nome or '').strip(), (client_id or '').strip()
    if not nome:
        raise ValueError('Informe o nome da pessoa que vai entrar com o Spotify.')
    if not client_id:
        raise ValueError('Informe o Client ID do seu app no Spotify Developer Dashboard.')
    agora = time.time()
    # list(): outra requisição pode alterar o dicionário durante a varredura.
    for estado in [e for e, p in list(_pendentes.items()) if agora - p.criado > VALIDADE_LOGIN_S]:
        _pendentes.pop(estado, None)
    verificador = secrets.token_urlsafe(64)[:96]
    estado = secrets.token_urlsafe(24)
    _pendentes[estado] = LoginPendente(nome, client_id, verificador, redirect_uri, agora)
    parametros = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'code_challenge_method': 'S256',
        'code_challenge': _desafio_pkce(verificador),
        'scope': ESCOPOS,
        'state': estado,
        'show_dialog': 'true',  # permite trocar de conta para cadastrar outro amigo
    }
    return f'{URL_AUTORIZAR}?{urlencode(parametros)}'


def _get(cliente: httpx.Client, caminho: str, token: str, **params) -> dict:
    resposta = cliente.get(
        f'{URL_API}{caminho}', params=params, headers={'Authorization': f'Bearer {token}'}
    )
    if resposta.status_code == 403:
        raise PermissionError(
            'O Spotify recusou o acesso (403). Confira se esta conta está na lista de usuários '
            '(User Management) do seu app e se o dono do app tem Premium.'
        )
    resposta.raise_for_status()
    return resposta.json()


def coletar_perfil(token: str, nome: str, cliente: httpx.Client | None = None) -> PerfilGosto:
    """Lê top artistas/músicas (3 períodos), últimas 50 e artistas seguidos."""
    proprio = cliente is None
    cliente = cliente or httpx.Client(timeout=20)
    try:
        top_artistas, top_musicas, generos = {}, {}, {}
        for periodo in PERIODOS:
            artistas = _get(cliente, '/me/top/artists', token, time_range=periodo, limit=50)
            top_artistas[periodo] = [a['name'] for a in artistas.get('items', []) if a.get('name')]
            for a in artistas.get('items', []):
                if a.get('genres'):
                    generos[a['name']] = list(a['genres'])
            faixas = _get(cliente, '/me/top/tracks', token, time_range=periodo, limit=50)
            top_musicas[periodo] = [
                {'musica': f['name'], 'artista': (f.get('artists') or [{}])[0].get('name', '')}
                for f in faixas.get('items', [])
                if f.get('name')
            ]
        recentes_json = _get(cliente, '/me/player/recently-played', token, limit=50)
        recentes = [
            {
                'musica': item['track']['name'],
                'artista': (item['track'].get('artists') or [{}])[0].get('name', ''),
                'tocada_em': item.get('played_at', ''),
            }
            for item in recentes_json.get('items', [])
            if item.get('track')
        ]
        seguidos: list[str] = []
        depois = None
        for _ in range(4):  # até 200 artistas seguidos
            extra = {'after': depois} if depois else {}
            pagina = _get(cliente, '/me/following', token, type='artist', limit=50, **extra)
            bloco = pagina.get('artists', {})
            seguidos += [a['name'] for a in bloco.get('items', []) if a.get('name')]
            depois = (bloco.get('cursors') or {}).get('after')
            if not depois:
                break
    finally:
        if proprio:
            cliente.close()
    perfil = PerfilGosto(
        nome=nome,
        fonte='spotify_api',
        coletado_em=agora_iso(),
        top_artistas=top_artistas,
        top_musicas=top_musicas,
        recentes=recentes,
        seguidos=seguidos,
        generos=generos,
    )
    if not any(perfil.top_artistas.values()):
        raise ValueError(
            'O Spotify não devolveu rankings para esta conta (conta nova ou com pouco uso).'
        )
    return perfil


def concluir_login(
    estado: str, codigo: str, pasta: Path = PASTA_PERFIS, cliente: httpx.Client | None = None
) -> tuple[PerfilGosto, Path]:
    """Troca o código pelo token (PKCE), coleta o perfil e salva o JSON."""
    pendente = _pendentes.pop(estado or '', None)
    if pendente is None or time.time() - pendente.criado > VALIDADE_LOGIN_S:
        raise ValueError(
            'Login expirado ou inválido. Volte ao SyncUp e clique em conectar de novo.'
        )
    proprio = cliente is None
    cliente = cliente or httpx.Client(timeout=20)
    try:
        resposta = cliente.post(
            URL_TOKEN,
            data={
                'grant_type': 'authorization_code',
                'code': codigo,
                'redirect_uri': pendente.redirect_uri,
                'client_id': pendente.client_id,
                'code_verifier': pendente.verificador,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        if resposta.status_code != 200:
            raise ValueError(
                'O Spotify não aceitou o login. Confira se a Redirect URI cadastrada no app é '
                f'exatamente {pendente.redirect_uri}'
            )
        token = resposta.json()['access_token']
        perfil = coletar_perfil(token, pendente.nome, cliente)
    finally:
        if proprio:
            cliente.close()
    return perfil, salvar_perfil(perfil, pasta)


def registrar_rotas(app, pasta: Path = PASTA_PERFIS, redirect_uri: str = REDIRECT_PADRAO) -> None:
    """Adiciona /spotify/login e /spotify/callback a um FastAPI (o que serve o Gradio)."""
    from html import escape

    from fastapi.responses import HTMLResponse, RedirectResponse

    def pagina(titulo: str, texto: str, ok: bool) -> HTMLResponse:
        cor = '#1ed760' if ok else '#ff6b6b'
        return HTMLResponse(
            f'<!doctype html><meta charset="utf-8"><title>SyncUp · Spotify</title>'
            f'<body style="background:#121212;color:#fff;font-family:Arial,sans-serif;'
            f'display:grid;place-items:center;min-height:100vh;margin:0">'
            f'<div style="max-width:520px;padding:32px;border-radius:20px;background:#181818">'
            f'<h1 style="color:{cor}">{escape(titulo)}</h1><p style="line-height:1.6">{texto}</p>'
            f'<p style="color:#b3b3b3">Pode fechar esta aba e voltar ao SyncUp.</p></div>',
            status_code=200 if ok else 400,
        )

    @app.get('/spotify/login')
    def login(nome: str = '', client_id: str = ''):
        try:
            return RedirectResponse(iniciar_login(nome, client_id, redirect_uri))
        except ValueError as erro:
            return pagina('Não foi possível conectar', escape(str(erro)), False)

    @app.get('/spotify/callback')
    def callback(code: str = '', state: str = '', error: str = ''):
        if error:
            return pagina('Login cancelado', f'O Spotify respondeu: {escape(error)}.', False)
        try:
            perfil, _ = concluir_login(state, code, pasta)
        except (ValueError, PermissionError, httpx.HTTPError) as erro:
            return pagina('Não foi possível coletar o perfil', escape(str(erro)), False)
        n_art = sum(len(v) for v in perfil.top_artistas.values())
        return pagina(
            f'Perfil de {perfil.nome} salvo!',
            f'Coletamos {n_art} posições de rankings de artistas, {len(perfil.recentes)} músicas '
            f'recentes e {len(perfil.seguidos)} artistas seguidos. No SyncUp, clique em '
            '<b>Atualizar lista</b> na aba Match.',
            True,
        )
