// Teste mínimo de áudio (Fase 1 da Etapa 4): um único <audio> desbloqueado por UM toque
// troca de src sozinho a cada trecho. Serve para validar o autoplay no Safari do iPhone.
import { html, useRef, useState } from 'preact-htm';

const TRECHO_MS = 6000;
// Músicas conhecidas para quando o histórico é fictício (o iTunes não acha "Artista fictício").
const RESERVA = [{ artista: 'Legião Urbana', faixa: 'Tempo Perdido' }, { artista: 'Tim Maia', faixa: 'Azul da Cor do Mar' }, { artista: 'Marisa Monte', faixa: 'Ainda Bem' }];

// 0,2 s de silêncio em WAV (8 kHz, 8 bits): o play() dentro do toque desbloqueia o elemento.
function silencio() {
  const n = 1600, b = new DataView(new ArrayBuffer(44 + n));
  const txt = (o, s) => [...s].forEach((c, i) => b.setUint8(o + i, c.charCodeAt(0)));
  txt(0, 'RIFF'); b.setUint32(4, 36 + n, true); txt(8, 'WAVEfmt '); b.setUint32(16, 16, true);
  b.setUint16(20, 1, true); b.setUint16(22, 1, true); b.setUint32(24, 8000, true); b.setUint32(28, 8000, true);
  b.setUint16(32, 1, true); b.setUint16(34, 8, true); txt(36, 'data'); b.setUint32(40, n, true);
  for (let i = 0; i < n; i++) b.setUint8(44 + i, 128);
  return URL.createObjectURL(new Blob([b], { type: 'audio/wav' }));
}

async function preview({ artista, faixa }) {
  const url = `https://itunes.apple.com/search?${new URLSearchParams({ term: `${artista} ${faixa}`, entity: 'song', country: 'BR', limit: '1' })}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`iTunes respondeu ${r.status}`);
  const item = (await r.json()).results?.[0];
  return item?.previewUrl ? { ...item, rotulo: `${item.artistName} · ${item.trackName}` } : null;
}

// play() rejeita com AbortError quando o src muda antes de começar: não é falha de som.
async function tocar(audio) {
  try { await audio.play(); return 'tocando'; } catch (e) { return e.name === 'AbortError' ? 'interrompido (normal)' : `bloqueado (${e.name})`; }
}

export function TesteSom({ musicas }) {
  const audio = useRef(null);
  const [log, setLog] = useState([]);
  const [ativo, setAtivo] = useState(false);
  const anotar = (linha) => setLog((l) => [...l, linha]);

  const comecar = async () => {
    const el = audio.current;
    setLog([]); setAtivo(true);
    el.src = silencio();
    const desbloqueio = tocar(el); // chamado dentro do toque, antes de qualquer await
    anotar(`Desbloqueio no toque: ${await desbloqueio}`);
    try {
      const achados = (await Promise.all(musicas.map((m) => preview(m).catch(() => null)))).filter(Boolean);
      for (const m of RESERVA) { if (achados.length >= 3) break; const p = await preview(m).catch(() => null); if (p) achados.push(p); }
      if (!achados.length) anotar('Nenhum trecho encontrado no iTunes (sem internet?).');
      for (const [i, p] of achados.slice(0, 3).entries()) {
        el.src = p.previewUrl; el.currentTime = 0;
        anotar(`Trecho ${i + 1} sem novo toque (${p.rotulo}): ${await tocar(el)}`);
        await new Promise((ok) => setTimeout(ok, TRECHO_MS));
      }
    } catch (e) { anotar(`Erro: ${e.message}`); }
    el.pause(); setAtivo(false); anotar('Fim do teste.');
  };

  return html`
    <div class="vidro teste-som">
      <h3>Teste de som <small>(validação no iPhone)</small></h3>
      <p class="nota">Toca 3 trechos de 30 s, trocando sozinho a cada 6 s depois de um único toque. Para buscar os trechos, envia o nome das músicas e o seu endereço IP para a Apple (iTunes).</p>
      <button type="button" class="btn btn-borda vidro" onClick=${comecar} disabled=${ativo}>${ativo ? 'Tocando…' : 'Tocar 3 trechos'}</button>
      <audio ref=${audio} preload="none"></audio>
      ${log.length > 0 && html`<ol class="log-som" role="status">${log.map((l) => html`<li>${l}</li>`)}</ol>`}
    </div>`;
}
