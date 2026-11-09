// Wrapped da vida toda a partir das colunas de historico.js, com as regras de wrapped.py,
// arquetipos.py e ponte._trilha. Devolve o mesmo JSON (`dados`, `trilha`) que a ponte do Python.
// Sem DOM: roda no Worker do Wrapped e no Node (teste de paridade com o Python).
import { fmtNum, fmtPct } from './stories/logica.js';

const TEMPO_MINIMO_PLAY_MS = 30_000;
const HORA = 3_600_000, DIA = 24 * HORA;
const DIAS_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'];
const PERIODOS = [['Madrugada', 0, 6], ['Manhã', 6, 12], ['Tarde', 12, 18], ['Noite', 18, 24]];
const MINIMO_CONHECIDOS = 0.5; // fração mínima de eventos com o campo preenchido

// Ordem de texto do Python (ponto de código); o `<` do JS compara UTF-16 e erra com emoji.
export function compararTexto(a, b) {
  if (a === b) return 0;
  for (let i = 0; i < a.length && i < b.length; i++) {
    const x = a.codePointAt(i), y = b.codePointAt(i);
    if (x !== y) return x < y ? -1 : 1;
    if (x > 0xffff) i++;
  }
  return a.length - b.length;
}

// Datas como o pandas escreve um Timestamp sem fuso: "2021-03-24T13:45:12" (frações com 6 casas).
const iso = (ms) => {
  const s = new Date(ms).toISOString();
  return ms % 1000 ? `${s.slice(0, 23)}000` : s.slice(0, 19);
};
const item = (nome, plays, horas = 0, artista = '', uri = null) => ({ nome, plays, horas, artista, uri });
const somar = (mapa, chave, valor = 1) => mapa.set(chave, (mapa.get(chave) || 0) + valor);
const DIAS_CHAVE = 100_000; // chave (par, dia) das repetições: dia < 100 mil (até o ano 2243)
const SEP = '\u0000'; // separa música e artista nas chaves compostas

/* ---------- Arquétipos (arquetipos.py) ---------- */
export const AVISO_ARQUETIPOS = 'Arquétipos são regras sobre hábitos de escuta neste histórico. Não medem personalidade nem afinidade entre pessoas.';
// [chave, nome, ícone, medida, limiar, frase, formato, teto]
export const REGRAS = [
  ['devoto', 'Devoto(a)', '💚', 'top1', 0.10, 'Um único artista ocupa {valor} de tudo o que você ouviu.', 'pct', 0.20],
  ['explorador', 'Explorador(a)', '🧭', 'descobertas', 0.06, 'A cada 100 plays, você encontrou {valor} artistas diferentes.', 'por100', 0.12],
  ['coruja', 'Coruja', '🦉', 'madrugada', 0.15, '{valor} dos seus plays foram entre 0h e 5h59.', 'pct', 0.35],
  ['madrugador', 'Madrugador(a)', '🌅', 'manha', 0.28, '{valor} dos seus plays foram de manhã, entre 6h e 11h59.', 'pct', 0.45],
  ['noturno', 'Trilha da noite', '🌙', 'noite', 0.40, '{valor} dos seus plays foram entre 18h e 23h59.', 'pct', 0.60],
  ['fim_de_semana', 'Fim de semana sonoro', '🎉', 'fim_de_semana', 0.34, '{valor} dos seus plays caíram no sábado ou no domingo.', 'pct', 0.50],
  ['pulador', 'Dedo no próximo', '⏭️', 'pulos', 0.35, 'Você pulou {valor} das faixas que começou.', 'pct', 0.60],
  ['aleatorio', 'Rei/Rainha do aleatório', '🔀', 'aleatorio', 0.60, '{valor} das suas reproduções estavam no modo aleatório.', 'pct', 1.0],
  ['album', 'Do começo ao fim', '💿', 'fim_natural', 0.65, '{valor} das faixas tocaram até o fim, sem pular.', 'pct', 0.85],
  ['maratonista', 'Maratonista', '🔥', 'sequencia', 180, 'Você ouviu música por {valor} dias seguidos.', 'dias', 1000],
  ['repeat', 'Modo repeat', '🔁', 'repeticao', 0.08, 'Suas 10 músicas favoritas somam {valor} de todos os plays.', 'pct', 0.20],
  ['offline', 'Sem sinal, com som', '✈️', 'offline', 0.20, '{valor} das reproduções aconteceram offline.', 'pct', 0.60],
].map(([chave, nome, icone, medida, limiar, frase, formato, teto]) => ({ chave, nome, icone, medida, limiar, frase, formato, teto }));
const EQUILIBRADO = { chave: 'equilibrado', nome: 'Ouvinte equilibrado(a)', icone: '⚖️', frase: 'Nenhum hábito domina: você distribui a escuta entre horários, artistas e modos.' };

export function formatarValor(valor, formato) {
  if (formato === 'pct') return fmtPct(valor, 1);
  if (formato === 'por100') return fmtNum(valor * 100, 1);
  return fmtNum(valor);
}

export function classificar(medidas) {
  const avaliados = [];
  for (const r of REGRAS) {
    const valor = medidas[r.medida];
    if (valor == null) continue;
    let forca = r.limiar ? valor / r.limiar : 0;
    if (r.chave === 'album' && (medidas.aleatorio || 0) >= 0.5) forca = Math.min(forca, 0.99); // fim no aleatório não é "álbum"
    const intensidade = forca >= 1 ? Math.min(1, (valor - r.limiar) / Math.max(r.teto - r.limiar, 1e-9)) : forca - 1;
    avaliados.push({ chave: r.chave, nome: r.nome, icone: r.icone, valor, limiar: r.limiar, forca, explicacao: r.frase.replace('{valor}', formatarValor(valor, r.formato)), intensidade });
  }
  avaliados.sort((a, b) => b.intensidade - a.intensidade || compararTexto(a.chave, b.chave));
  const atingidos = avaliados.filter((a) => a.forca >= 1);
  const quase = avaliados.filter((a) => a.forca >= 0.8 && a.forca < 1).slice(0, 2);
  const principal = atingidos[0] ?? { chave: EQUILIBRADO.chave, nome: EQUILIBRADO.nome, icone: EQUILIBRADO.icone, valor: 0, limiar: 1, forca: 1, explicacao: EQUILIBRADO.frase, intensidade: 0 };
  return { principal, secundarios: atingidos.slice(1, 3), avaliados, quase };
}

/* ---------- Wrapped (wrapped.calcular_wrapped) ---------- */
// Média de um booleano anulável quando o campo é conhecido na maioria dos eventos.
function fracao(coluna) {
  let conhecidos = 0, sim = 0;
  for (const v of coluna) if (v !== null) { conhecidos++; if (v) sim++; }
  return coluna.length && conhecidos / coluna.length >= MINIMO_CONHECIDOS ? sim / conhecidos : null;
}

// Maior valor de um Map; empate fica com quem veio antes na iteração (a ordem do pandas em cada caso).
function maiorDe(mapa) {
  let melhor, max = -Infinity;
  for (const [k, v] of mapa) if (v > max) { melhor = k; max = v; }
  return [melhor, max];
}
const ordenado = (mapa) => new Map([...mapa].sort(([a], [b]) => (typeof a === 'number' ? a - b : compararTexto(a, b))));

/** `c`: colunas de lerHistorico. Devolve o JSON `dados` da ponte (todos os campos do Wrapped). */
export function calcularWrapped(c, nome, fuso = '') {
  const n = c.utc.length;
  if (!n) throw new Error('O histórico não contém músicas válidas para montar o Wrapped.');
  const plays = [];
  for (let i = 0; i < n; i++) if (c.ms[i] >= TEMPO_MINIMO_PLAY_MS) plays.push(i);
  if (!plays.length) throw new Error('O histórico não tem reproduções de pelo menos 30 segundos.');
  nome = (nome || '').trim() || 'Você';
  const total = plays.length;
  const anoDoDia = new Map();
  const ano = (d) => anoDoDia.get(d) ?? (anoDoDia.set(d, new Date(d * DIA).getUTCFullYear()), anoDoDia.get(d));
  const diaDe = (i) => Math.floor(c.local[i] / DIA);

  // Todos os eventos válidos: período, horas, dias e hábitos.
  let inicio = Infinity, fim = -Infinity, minutos = 0;
  const minutosDia = new Map(), minutosAno = new Map();
  for (let i = 0; i < n; i++) {
    const l = c.local[i], d = Math.floor(l / DIA), m = c.ms[i] / 60000;
    if (l < inicio) inicio = l;
    if (l > fim) fim = l;
    minutos += m;
    somar(minutosDia, d, m);
    somar(minutosAno, ano(d), m);
  }

  // Plays de 30 s ou mais: rankings, descobertas, relógio e calendário.
  // Cada par (música, artista) vira um número uma vez só: chaves de texto por play custavam caro.
  const artistas = new Map(); // artista → { plays, ms, primeira }
  const pares = new Map(), musicas = []; // música → artista → índice em `musicas` ({ musica, artista, plays })
  const parDe = (m, art) => {
    let porArtista = pares.get(m);
    if (!porArtista) pares.set(m, (porArtista = new Map()));
    let id = porArtista.get(art);
    if (id === undefined) { id = musicas.length; porArtista.set(art, id); musicas.push({ musica: m, artista: art, plays: 0 }); }
    return id;
  };
  const porAnoArtista = new Map(), porAnoMusica = new Map(), repeticoes = new Map(), playsAno = new Map();
  const porHora = new Array(24).fill(0), semana = new Map(), periodos = PERIODOS.map(() => 0);
  let primeiro = plays[0], fimDeSemana = 0;
  for (const i of plays) {
    const l = c.local[i], d = Math.floor(l / DIA), a = ano(d), hora = Math.floor((l - d * DIA) / HORA), dow = (((d + 3) % 7) + 7) % 7;
    const art = c.artista[i], id = parDe(c.musica[i], art);
    const reg = artistas.get(art);
    if (reg) { reg.plays++; reg.ms += c.ms[i]; if (l < reg.primeira) reg.primeira = l; } else artistas.set(art, { plays: 1, ms: c.ms[i], primeira: l });
    musicas[id].plays++;
    if (!porAnoArtista.has(a)) { porAnoArtista.set(a, new Map()); porAnoMusica.set(a, new Map()); }
    somar(porAnoArtista.get(a), art);
    somar(porAnoMusica.get(a), id);
    somar(repeticoes, id * DIAS_CHAVE + d);
    somar(playsAno, a);
    porHora[hora]++;
    somar(semana, dow);
    PERIODOS.forEach(([, ini, fimP], k) => { if (hora >= ini && hora < fimP) periodos[k]++; });
    if (dow >= 5) fimDeSemana++;
    if (c.utc[i] < c.utc[primeiro]) primeiro = i;
  }

  const rankingArtistas = [...artistas].sort(([a, x], [b, y]) => y.plays - x.plays || compararTexto(a, b));
  const topArtistas = rankingArtistas.slice(0, 5).map(([a, r]) => item(a, r.plays, r.ms / HORA));
  const porMusica = (x, y) => y.plays - x.plays || compararTexto(x.musica, y.musica) || compararTexto(x.artista, y.artista);
  const rankingMusicas = [...musicas].sort(porMusica);
  const topMusicas = rankingMusicas.slice(0, 10).map((m) => item(m.musica, m.plays, 0, m.artista));
  const artistaVida = topArtistas[0];

  // Anos: volume, líderes (top 5 por ano) e descobertas.
  const top5Ano = new Map(), liderMusica = new Map(), novos = new Map();
  for (const [a, mapa] of porAnoArtista) {
    top5Ano.set(a, [...mapa].sort(([x, p], [y, q]) => q - p || compararTexto(x, y)).slice(0, 5));
    let lider = null; // uma passada basta: só o primeiro do ano interessa
    for (const [id, p] of porAnoMusica.get(a)) {
      const cand = { ...musicas[id], plays: p };
      if (!lider || porMusica(cand, lider) < 0) lider = cand;
    }
    liderMusica.set(a, item(lider.musica, lider.plays, 0, lider.artista));
  }
  for (const r of artistas.values()) somar(novos, ano(Math.floor(r.primeira / DIA)));
  const anos = [...minutosAno.keys()].sort((x, y) => x - y).map((a) => ({
    ano: a,
    horas: minutosAno.get(a) / 60,
    plays: playsAno.get(a) || 0,
    top_artistas: (top5Ano.get(a) || []).slice(0, 3).map(([art, p]) => item(art, p)),
    top_musica: liderMusica.get(a) || null,
    novos_artistas: novos.get(a) || 0,
  }));

  // Fidelidade: quem mais vezes esteve no top 5 anual (desempate: plays nesses anos, nome).
  const fidelidade = new Map();
  for (const [a, lista] of top5Ano) for (const [art, p] of lista) {
    const f = fidelidade.get(art) ?? { anos: [], plays: 0 };
    f.anos.push(a); f.plays += p;
    fidelidade.set(art, f);
  }
  const [fielNome, fiel] = [...fidelidade].sort(([x, f], [y, g]) => g.anos.length - f.anos.length || g.plays - f.plays || compararTexto(x, y))[0];

  // Dia recorde (o mais antigo no empate) e maior repetição de uma música num dia.
  const [diaRecorde, minutosRecorde] = maiorDe(ordenado(minutosDia));
  const artistasDoDia = new Map();
  for (const i of plays) if (diaDe(i) === diaRecorde) somar(artistasDoDia, c.artista[i]);
  const artistaDia = artistasDoDia.size ? maiorDe(ordenado(artistasDoDia))[0] : ''; // empate: ordem alfabética
  let rep = null;
  for (const [k, p] of repeticoes) {
    if (rep && p < rep.p) continue;
    const { musica: m, artista: a } = musicas[Math.floor(k / DIAS_CHAVE)], cand = { d: k % DIAS_CHAVE, m, a, p };
    if (!rep || p > rep.p || (cand.d - rep.d || compararTexto(m, rep.m) || compararTexto(a, rep.a)) < 0) rep = cand;
  }

  // Maior sequência de dias seguidos (empate: a mais antiga).
  const dias = [...minutosDia.keys()].sort((x, y) => x - y);
  let seq = { tamanho: 0 };
  for (let j = 0, ini = 0; j < dias.length; j++) {
    if (j > 0 && dias[j] - dias[j - 1] !== 1) ini = j;
    if (j - ini + 1 > seq.tamanho) seq = { tamanho: j - ini + 1, inicio: dias[ini], fim: dias[j] };
  }

  // Hábitos (podem faltar em exportações antigas).
  let pulos = fracao(c.pulada);
  let motivosConhecidos = 0, fwd = 0, trackdone = 0;
  for (const m of c.motivo) if (m !== null) { motivosConhecidos++; if (m === 'fwdbtn') fwd++; else if (m === 'trackdone') trackdone++; }
  const conhecidos = motivosConhecidos / n >= MINIMO_CONHECIDOS;
  if (pulos === null && conhecidos) pulos = fwd / motivosConhecidos;
  const fimNatural = conhecidos ? trackdone / motivosConhecidos : null;
  const aleatorio = fracao(c.aleatorio), offline = fracao(c.offline);
  const contagemPlataformas = new Map();
  let comPlataforma = 0;
  for (const p of c.plataforma) if (p !== null) { somar(contagemPlataformas, p); comPlataforma++; }
  const plataformas = [...contagemPlataformas].sort(([a, x], [b, y]) => y - x || compararTexto(a, b)).slice(0, 4).map(([p, v]) => [p, v / comPlataforma]);
  const avisos = pulos === null && aleatorio === null ? ['Este histórico não traz pulos/aleatório; esses hábitos foram omitidos.'] : [];

  const fracoes = Object.fromEntries(PERIODOS.map(([nomeP], k) => [nomeP, periodos[k] / total]));
  const top10 = rankingMusicas.slice(0, 10).reduce((s, m) => s + m.plays, 0);
  const medidas = {
    top1: artistaVida.plays / total,
    descobertas: artistas.size / total,
    madrugada: fracoes.Madrugada,
    manha: fracoes['Manhã'],
    noite: fracoes.Noite,
    fim_de_semana: fimDeSemana / total,
    pulos,
    aleatorio,
    fim_natural: fimNatural,
    sequencia: seq.tamanho,
    repeticao: top10 / total,
    offline,
  };
  const [diaSemana] = maiorDe(ordenado(semana)); // empate: o primeiro da semana
  const dados = {
    nome,
    inicio: iso(inicio),
    fim: iso(fim),
    dias_periodo: Math.floor(fim / DIA) - Math.floor(inicio / DIA) + 1,
    dias_com_musica: minutosDia.size,
    horas: minutos / 60,
    plays: total,
    quantidade_artistas: artistas.size,
    quantidade_musicas: musicas.length,
    artista_vida: artistaVida,
    descoberta_artista_vida: iso(artistas.get(artistaVida.nome).primeira),
    participacao_artista_vida: artistaVida.plays / total,
    top_artistas: topArtistas,
    top_musicas: topMusicas,
    primeira_musica: item(c.musica[primeiro], 1, 0, c.artista[primeiro]),
    primeira_data: iso(c.local[primeiro]),
    anos,
    dia_recorde: iso(diaRecorde * DIA),
    horas_dia_recorde: minutosRecorde / 60,
    artista_dia_recorde: artistaDia,
    repeticao_dia: item(rep.m, rep.p, 0, rep.a),
    data_repeticao_dia: iso(rep.d * DIA),
    sequencia: seq.tamanho,
    inicio_sequencia: iso(seq.inicio * DIA),
    fim_sequencia: iso(seq.fim * DIA),
    plays_por_hora: porHora,
    pico_hora: porHora.indexOf(Math.max(...porHora)),
    dia_semana_favorito: DIAS_SEMANA[diaSemana],
    periodos: fracoes,
    fiel: item(fielNome, fiel.plays),
    anos_fiel: fiel.anos.length,
    habitos: { pulos, aleatorio, offline, fim_natural: fimNatural },
    plataformas,
    medidas,
    arquetipos: classificar(medidas),
    fuso_horario: fuso,
    avisos,
    fiel_anos: fiel.anos.sort((x, y) => x - y),
  };
  comUris(dados, c, plays);
  return dados;
}

// Põe nas músicas do Wrapped o ID do Spotify mais tocado de cada par (música, artista).
function comUris(d, c, plays) {
  const itens = [d.primeira_musica, d.repeticao_dia, ...d.top_musicas, ...d.anos.map((a) => a.top_musica).filter(Boolean)];
  const nomes = new Set(itens.map((m) => m.nome));
  const contagem = new Map(); // música␀artista → Map uri → plays
  for (const i of plays) {
    if (c.uri[i] === null || !nomes.has(c.musica[i])) continue;
    const chave = c.musica[i] + SEP + c.artista[i];
    if (!contagem.has(chave)) contagem.set(chave, new Map());
    somar(contagem.get(chave), c.uri[i]);
  }
  for (const m of itens) {
    const uris = contagem.get(m.nome + SEP + m.artista);
    if (!uris) continue;
    const [uri] = maiorDe(ordenado(uris)); // empate: o menor ID (ordem do groupby do pandas)
    if (uri) m.uri = uri;
  }
}

/* ---------- Trilha dos stories (ponte._trilha) ---------- */
// Candidatas de música de cada slide, em ordem de preferência. {faixa, artista} é uma música certa;
// {artista} pede as mais famosas do artista. O JS só busca algo se a pessoa pedir som.
export function trilha(d) {
  const musica = (m) => (m && m.artista ? { faixa: m.nome, artista: m.artista } : null);
  const artista = (nomeA) => (nomeA ? { artista: nomeA } : null);
  const lista = (...candidatas) => candidatas.filter(Boolean);
  const tops = d.top_musicas.map(musica);
  const ultimo = d.anos.at(-1) ?? null;
  const slides = {
    intro: lista(ultimo ? musica(ultimo.top_musica) : null, ...tops),
    primeira: lista(musica(d.primeira_musica)),
    artista: lista(artista(d.artista_vida.nome)),
    top_artistas: lista(...d.top_artistas.slice(1, 3).map((a) => artista(a.nome))),
    top_musicas: lista(...tops),
    anos: lista(d.anos.length ? musica(d.anos[0].top_musica) : null),
    descobertas: lista(ultimo && ultimo.top_artistas.length ? artista(ultimo.top_artistas[0].nome) : null),
    recorde: lista(musica(d.repeticao_dia), artista(d.artista_dia_recorde)),
    fiel: lista(artista(d.fiel.nome)),
  };
  return {
    slides: Object.fromEntries(Object.entries(slides).filter(([, candidatas]) => candidatas.length)),
    // Acabaram as mais ouvidas? Seguem as mais famosas dos top artistas, sem repetir.
    fila: [...tops.slice(0, 10).filter(Boolean), ...lista(...d.top_artistas.slice(0, 5).map((a) => artista(a.nome)))],
  };
}
