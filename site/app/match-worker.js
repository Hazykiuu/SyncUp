// Motor do Match no navegador: lê os ZIPs uma pessoa por vez (guarda só o perfil, poucos KB) e lê os convites.
//   {tipo: 'match', arquivos: [[File, ...], ...], nomes, convites: texto, opcoes} → {ok, dados: {r, fontes, fora}}
//   {tipo: 'convite', arquivos: [File, ...], nome, opcoes} → {ok, dados: código}
// Durante a leitura: {etapa}. Erro: {ok: false, erro}.
import { gerarConvite, lerConvite, separarConvites } from './js/convite.js';
import { lerHistorico } from './js/historico.js';
import { conciliar, MAXIMO_PESSOAS, perfilDeHistorico } from './js/match.js';

async function perfil(lista, nome, opcoes) {
  const partes = [];
  for (const f of lista) partes.push({ nome: f.name, bytes: new Uint8Array(await f.arrayBuffer()) });
  return perfilDeHistorico(await lerHistorico(partes, opcoes), nome);
}

self.onmessage = async ({ data: { tipo, arquivos, nomes, nome, convites, opcoes } }) => {
  try {
    if (tipo === 'convite') {
      self.postMessage({ etapa: `Lendo o histórico de ${nome}…` });
      self.postMessage({ ok: true, dados: await gerarConvite(await perfil(arquivos, nome, opcoes)) });
      return;
    }
    const perfis = [], fontes = {}, fora = [];
    for (let i = 0; i < arquivos.length; i++) {
      self.postMessage({ etapa: `Lendo o histórico de ${nomes[i]} (${i + 1} de ${arquivos.length})…` });
      perfis.push(await perfil(arquivos[i], nomes[i], opcoes));
      fontes[nomes[i]] = 'Histórico ZIP';
    }
    const codigos = separarConvites(convites);
    for (let k = 0; k < codigos.length; k++) {
      try {
        const p = await lerConvite(codigos[k]);
        perfis.push(p);
        fontes[p.nome] = 'Convite';
      } catch (e) { fora.push(`Convite ${k + 1}: ${e.message}`); } // um código cortado não derruba os outros
    }
    const vistos = perfis.map((p) => p.nome.trim().toLocaleLowerCase('pt-BR'));
    if (new Set(vistos).size < vistos.length) throw new Error('Cada pessoa precisa de um nome diferente (confira os nomes dos convites).');
    if (perfis.length < 2) throw new Error(`O Match precisa de pelo menos duas pessoas.${fora.length ? ` ${fora.join(' · ')}` : ''}`);
    if (perfis.length > MAXIMO_PESSOAS) throw new Error(`Use no máximo ${MAXIMO_PESSOAS} pessoas no Match.`);
    self.postMessage({ etapa: 'Comparando todos com todos…' });
    self.postMessage({ ok: true, dados: { r: conciliar(perfis), fontes, fora } });
  } catch (e) {
    const nosso = e?.constructor === Error && e.message;
    self.postMessage({ ok: false, erro: nosso || 'Algo deu errado ao processar os arquivos. Confira se são ZIPs do Histórico Estendido.' });
  }
};
