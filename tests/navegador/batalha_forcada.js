// Worker de teste da Batalha: os testes de navegador o servem no lugar de app/batalha-worker.js (page.route),
// para forçar quais temas viram story sem nada novo na interface de produção. O teste põe antes deste código
// `const FORCAR = { modo, chaves }`:
//   modo 'real': lê os arquivos como o Worker de verdade e troca as 10 sorteadas pelas `chaves`;
//   modo 'sintetico': ignora os arquivos e usa números de pior caso (6 dígitos, 0, porcentagens abaixo de 1,
//   dois vencedores empatados em parte dos temas, selo e "Dedinho nervoso"); `valores` ({ chave: [...] }) troca
//   os números de um tema (capturas com números plausíveis).
// Medalhas, campeão, título e resenha são refeitos sobre as rodadas forçadas.
import {
  alertaPaciencia, campeoes, decididoNoDetalhe, destaqueRodada, medalhas, montarBatalha, numerosDoLutador, resenha, rodadas, tituloCampeao,
} from './js/batalha.js';
import { numerosDoGrupo } from './js/batalha-medidas.js';
import { TEMAS } from './js/batalha-temas.js';
import { lerHistorico } from './js/historico.js';

async function ler(lista, opcoes) {
  const partes = [];
  for (const f of lista) partes.push({ nome: f.name, bytes: new Uint8Array(await f.arrayBuffer()) });
  return lerHistorico(partes, opcoes);
}

function valores(t, n) {
  if (FORCAR.valores?.[t.chave]) return FORCAR.valores[t.chave].slice(0, n);
  let v;
  if (t.chave === 'plays') v = [128450, 96210, 40330, 5120, 870, 120];
  else if (t.escala === 100) v = [64.2, 31.5, 6, 1.2, 0.4, 0];
  else if (t.escala === 24) v = [23.9, 18.2, 9.5, 3.1, 0.6, 0.1];
  else v = t.casas ? [128450.5, 96210.2, 40330.7, 5120.1, 87.3, 0] : [128450, 96210, 40330, 5120, 87, 0];
  v = v.slice(0, n);
  if (TEMAS.indexOf(t) % 4 === 1) v[1] = v[0]; // dois vencedores empatados
  return v;
}

function sinteticos(nomes) {
  return nomes.map((nome, k) => ({
    nome,
    numeros: Object.fromEntries(TEMAS.map((t) => [t.chave, valores(t, nomes.length)[k]])),
    contagens: new Map([['Artista em comum', 10 + k], [`Só de ${k + 1}`, 5]]),
  }));
}

self.onmessage = async ({ data: { fase, arquivos, nomes, opcoes, janela, semente } }) => {
  try {
    if (fase === 1) {
      const faixas = [];
      for (const lista of arquivos) {
        if (FORCAR.modo === 'sintetico') { faixas.push([0, 1]); continue; }
        const c = await ler(lista, opcoes);
        faixas.push([Math.min(...c.utc), Math.max(...c.utc)]);
      }
      self.postMessage({ ok: true, faixas });
      return;
    }
    let lutadores;
    if (FORCAR.modo === 'sintetico') lutadores = sinteticos(nomes);
    else {
      lutadores = [];
      for (let i = 0; i < arquivos.length; i++) {
        const c = await ler(arquivos[i], opcoes);
        lutadores.push({ nome: nomes[i], ...numerosDoLutador(c, nomes[i], opcoes.fuso || 'America/Sao_Paulo', janela) });
      }
      const grupo = numerosDoGrupo(lutadores);
      lutadores = lutadores.map((l, i) => ({ ...l, numeros: { ...l.numeros, ...grupo[i] } }));
    }
    const b = montarBatalha(lutadores, { semente });
    const dentro = new Map(rodadas(lutadores).dentro.map((r) => [r.chave, r]));
    const faltam = FORCAR.chaves.filter((k) => !dentro.has(k));
    if (faltam.length) throw new Error(`Temas forçados fora: ${faltam.join(', ')}`);
    b.rodadas = FORCAR.chaves.map((k) => dentro.get(k)).map((r) => ({ ...r, destaque: destaqueRodada(r), alerta: alertaPaciencia(r, nomes) }));
    b.temas = FORCAR.chaves;
    const m = medalhas(b.rodadas);
    b.lutadores = b.lutadores.map((l, i) => ({ ...l, medalhas: m[i] }));
    b.campeoes = campeoes(m);
    b.titulo = tituloCampeao(b);
    b.detalhe = decididoNoDetalhe(b);
    b.resenha = resenha(b, nomes);
    b.trilha = null; // sem som: nada vai ao iTunes
    self.postMessage({ ok: true, dados: b });
  } catch (e) {
    self.postMessage({ ok: false, erro: e.message });
  }
};
