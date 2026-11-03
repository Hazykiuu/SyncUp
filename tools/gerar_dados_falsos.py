"""Gera ZIPs fictícios e reproduzíveis no formato de histórico estendido Spotify."""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random
from typing import Any


@dataclass(frozen=True)
class Configuracao:
    """Parâmetros do histórico; nenhum dado de pessoa real é utilizado."""

    linhas: int = 300_000
    artistas: int = 3_000
    seed: int = 42
    tamanho_bloco: int = 25_000
    proporcao_podcasts: float = 0.05
    proporcao_various_artists: float = 0.01
    proporcao_duplicados: float = 0.002
    expoente_cauda: float = 1.1

    def validar(self) -> None:
        """Verifica limites e espaço para os exemplos obrigatórios."""
        if self.artistas < 1 or self.linhas < self.artistas + 2 or self.tamanho_bloco < 1:
            raise ValueError('Use artistas ≥1, linhas ≥artistas+2 e tamanho_bloco ≥1.')
        if not 0 < self.expoente_cauda <= 3:
            raise ValueError('O expoente da cauda deve estar entre zero e três.')
        proporcoes = (
            self.proporcao_podcasts,
            self.proporcao_various_artists,
            self.proporcao_duplicados,
        )
        if any(not 0 <= valor <= 1 for valor in proporcoes) or sum(proporcoes) > 1:
            raise ValueError('As proporções devem estar entre zero e um e somar no máximo um.')


def _gravar_json(pacote: zipfile.ZipFile, nome: str, conteudo: Any) -> None:
    """Fixa metadados para reproduzir os mesmos bytes no mesmo ambiente."""
    info = zipfile.ZipInfo(nome, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    pacote.writestr(
        info, json.dumps(conteudo, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    )


def gerar_zip(destino: str | Path, configuracao: Configuracao | None = None) -> Path:
    """Gera exatamente linhas eventos em blocos, garantindo artistas e casos especiais.

    As primeiras linhas contêm todos os artistas, um podcast e Various Artists.
    Depois usa distribuição de cauda longa. Duplicados copiam integralmente o
    evento anterior; plays normais têm horários distintos. A seed altera os
    favoritos e todos os campos sorteados.
    """
    config = configuracao or Configuracao()
    config.validar()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    rng = Random(config.seed)
    artistas = [f'Artista fictício {n:04d}' for n in range(1, config.artistas + 1)]
    favoritos = artistas.copy()
    rng.shuffle(favoritos)
    acumulados: list[float] = []
    total = 0.0
    for posicao in range(config.artistas):
        total += (posicao + 1) ** (-config.expoente_cauda)
        acumulados.append(total)
    inicio = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bloco: list[dict[str, Any]] = []
    anterior: dict[str, Any] | None = None
    numero_bloco = 0
    contagens = {'podcasts': 0, 'various_artists': 0, 'duplicados': 0}
    with zipfile.ZipFile(destino, 'w') as pacote:
        for indice in range(config.linhas):
            sorteio = rng.random()
            duplicado = indice >= config.artistas + 2 and sorteio < config.proporcao_duplicados
            if duplicado and anterior is not None:
                evento = anterior.copy()
                contagens['duplicados'] += 1
            else:
                limite_podcast = config.proporcao_duplicados + config.proporcao_podcasts
                limite_various = limite_podcast + config.proporcao_various_artists
                podcast = indice == config.artistas or (
                    indice >= config.artistas + 2 and sorteio < limite_podcast
                )
                various = indice == config.artistas + 1 or (
                    indice >= config.artistas + 2 and not podcast and sorteio < limite_various
                )
                artista = (
                    artistas[indice]
                    if indice < config.artistas
                    else rng.choices(favoritos, cum_weights=acumulados, k=1)[0]
                )
                if various:
                    artista = 'Various Artists'
                faixa = rng.randint(1, 20)
                pulado = rng.random() < 0.15
                instante = inicio + timedelta(minutes=indice * 10, seconds=rng.randint(0, 59))
                evento = {
                    'ts': instante.isoformat(timespec='seconds').replace('+00:00', 'Z'),
                    'username': f'usuario_ficticio_{config.seed}',
                    'platform': rng.choice(['android', 'windows', 'web_player']),
                    'ms_played': rng.randint(0, 29_999) if pulado else rng.randint(30_000, 360_000),
                    'conn_country': 'BR',
                    'ip_addr': f'192.0.2.{rng.randint(1, 254)}',
                    'master_metadata_track_name': None
                    if podcast
                    else f'Faixa {faixa:02d} · {artista}',
                    'master_metadata_album_artist_name': None if podcast else artista,
                    'master_metadata_album_album_name': None
                    if podcast
                    else f'Álbum fictício {faixa // 5}',
                    'spotify_track_uri': None
                    if podcast
                    else f'spotify:track:ficticio_{artista[-4:]}_{faixa:02d}',
                    'episode_name': f'Episódio fictício {indice % 40}' if podcast else None,
                    'episode_show_name': 'Podcast fictício SyncUp' if podcast else None,
                    'spotify_episode_uri': f'spotify:episode:ficticio_{indice}'
                    if podcast
                    else None,
                    'reason_start': 'clickrow',
                    'reason_end': 'fwdbtn' if pulado else 'trackdone',
                    'shuffle': rng.choice([True, False]),
                    'skipped': pulado,
                    'offline': False,
                    'offline_timestamp': 0,
                    'incognito_mode': False,
                }
            contagens['podcasts'] += int(evento['episode_name'] is not None)
            contagens['various_artists'] += int(
                evento['master_metadata_album_artist_name'] == 'Various Artists'
            )
            anterior = evento
            bloco.append(evento)
            if len(bloco) >= config.tamanho_bloco or indice == config.linhas - 1:
                _gravar_json(
                    pacote,
                    f'Spotify Extended Streaming History/Streaming_History_Audio_{numero_bloco:03d}.json',
                    bloco,
                )
                bloco.clear()
                numero_bloco += 1
        _gravar_json(
            pacote,
            'DADOS_FICTICIOS.json',
            {
                'aviso': 'Dados totalmente fictícios.',
                'configuracao': asdict(config),
                'contagens': contagens,
            },
        )
    return destino


def main() -> None:
    """Gera um histórico com parâmetros escolhidos pelo terminal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destino', nargs='?', default='dados_falsos.zip')
    parser.add_argument('--linhas', type=int, default=300_000)
    parser.add_argument('--artistas', type=int, default=3_000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--tamanho-bloco', type=int, default=25_000)
    parser.add_argument('--podcasts', type=float, default=0.05)
    parser.add_argument('--various-artists', type=float, default=0.01)
    parser.add_argument('--duplicados', type=float, default=0.002)
    parser.add_argument('--expoente-cauda', type=float, default=1.1)
    args = parser.parse_args()
    config = Configuracao(
        args.linhas,
        args.artistas,
        args.seed,
        args.tamanho_bloco,
        args.podcasts,
        args.various_artists,
        args.duplicados,
        args.expoente_cauda,
    )
    try:
        destino = gerar_zip(args.destino, config)
    except ValueError as erro:
        parser.error(str(erro))
    print(f'Gerado: {destino} · {config.linhas:,} eventos · seed {config.seed}')


if __name__ == '__main__':
    main()
