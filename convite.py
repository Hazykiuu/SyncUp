"""Convite por código: o perfil de gosto vira um texto curto para mandar a um amigo.

Cada pessoa gera o código no próprio computador (a partir do ZIP ou de um perfil
salvo do Spotify) e manda por mensagem. Quem recebe cola o código no Match. Não há
servidor, conta nem limite de pessoas.

Só os rankings viajam: top artistas e top músicas nos três períodos. Ficam de fora
o histórico, as músicas recentes (com horário), os artistas seguidos e os gêneros.

Formato: ``SYNCUP1.`` + base64url(zlib(JSON compacto)). O código vem de fora, então
tudo é conferido antes de virar perfil: tamanho do texto, tamanho descompactado,
estrutura, tipos e tamanho de cada nome.
"""

from __future__ import annotations

import base64
import binascii
import json
import zlib

from perfil_gosto import PERIODOS, TAMANHO_RANKING, PerfilGosto, agora_iso

PREFIXO = 'SYNCUP1.'
MAXIMO_CODIGO = 20_000  # caracteres: um código real tem ~3 mil
MAXIMO_JSON = 100_000  # bytes depois de descompactar: barra "zip bomb" no código
MAXIMO_NOME = 60
MAXIMO_TEXTO = 200  # nome de artista ou de música


def gerar_convite(perfil: PerfilGosto) -> str:
    """Código de convite com os rankings do perfil."""
    dados = {
        'n': perfil.nome.strip()[:MAXIMO_NOME],
        'a': {p: perfil.top_artistas.get(p, [])[:TAMANHO_RANKING] for p in PERIODOS},
        'm': {
            p: [
                [m['musica'], m['artista']] for m in perfil.top_musicas.get(p, [])[:TAMANHO_RANKING]
            ]
            for p in PERIODOS
        },
    }
    texto = json.dumps(dados, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return PREFIXO + base64.urlsafe_b64encode(zlib.compress(texto, 9)).decode('ascii').rstrip('=')


def _texto(valor: object, limite: int = MAXIMO_TEXTO) -> str:
    if not isinstance(valor, str) or not valor.strip() or len(valor) > limite:
        raise ValueError
    return valor.strip()


def _lista(valor: object) -> list:
    if not isinstance(valor, list) or len(valor) > TAMANHO_RANKING:
        raise ValueError
    return valor


def ler_convite(codigo: str) -> PerfilGosto:
    """Perfil de um código de convite; ``ValueError`` com mensagem em português se inválido."""
    codigo = ''.join((codigo or '').split())  # tolera quebras de linha do aplicativo de mensagem
    if not codigo.startswith(PREFIXO):
        raise ValueError('Isso não parece um convite do SyncUp (ele começa com "SYNCUP1.").')
    if len(codigo) > MAXIMO_CODIGO:
        raise ValueError('O convite é grande demais. Peça para a pessoa gerar de novo.')
    corpo = codigo[len(PREFIXO) :]
    try:
        bruto = base64.urlsafe_b64decode(corpo + '=' * (-len(corpo) % 4))
        descompactar = zlib.decompressobj()
        texto = descompactar.decompress(bruto, MAXIMO_JSON)
        if descompactar.unconsumed_tail or not descompactar.eof:
            raise ValueError
        dados = json.loads(texto.decode('utf-8'))
        if not isinstance(dados, dict):
            raise ValueError
        nome = _texto(dados.get('n'), MAXIMO_NOME)
        artistas, musicas = dados.get('a'), dados.get('m')
        if not isinstance(artistas, dict) or not isinstance(musicas, dict):
            raise ValueError
        top_artistas = {p: [_texto(a) for a in _lista(artistas.get(p, []))] for p in PERIODOS}
        top_musicas = {
            p: [
                {'musica': _texto(m[0]), 'artista': _texto(m[1])}
                for m in _lista(musicas.get(p, []))
                if isinstance(m, list) and len(m) == 2
            ]
            for p in PERIODOS
        }
    except (ValueError, TypeError, binascii.Error, zlib.error, UnicodeDecodeError) as erro:
        raise ValueError(
            'O convite está incompleto ou foi alterado. Copie o código inteiro de novo.'
        ) from erro
    if not any(top_artistas.values()):
        raise ValueError(f'O convite de {nome} não tem nenhum ranking de artistas.')
    return PerfilGosto(nome, 'convite', agora_iso(), top_artistas, top_musicas)


def separar_convites(texto: str) -> list[str]:
    """Os códigos colados numa caixa: um por linha, ou quebrados pelo aplicativo de mensagem.

    Um pedaço que não começa com o prefixo é a continuação do código anterior.
    """
    codigos: list[str] = []
    for pedaco in (texto or '').split():
        if pedaco.startswith(PREFIXO) or not codigos:
            codigos.append(pedaco)
        else:
            codigos[-1] += pedaco
    return codigos
