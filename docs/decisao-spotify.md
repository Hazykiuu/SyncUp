# Decisão: sem login com Spotify (OAuth PKCE) na v1.14

- **Data:** 16/11/2026
- **Situação:** decidido; reavaliar se as regras do Spotify mudarem.

## Contexto

O app no navegador lê o Histórico Estendido que a pessoa baixa do Spotify (ZIP). A pergunta era se valia acrescentar login com a conta do Spotify, por OAuth 2.0 Authorization Code com PKCE, que é o fluxo indicado para um app sem servidor. Com ele, daria para, por exemplo, salvar a playlist comum da Dupla direto no Spotify.

## O que a documentação oficial dizia em 16/11/2026

Estas regras podem mudar; confira as fontes antes de reabrir a decisão.

- **PKCE:**
  - Autorização em `GET https://accounts.spotify.com/authorize`, com `response_type=code`, `code_challenge_method=S256` e `state`.
  - Troca do código em `POST https://accounts.spotify.com/api/token` (form-urlencoded), sem client secret.
  - Fonte: [Authorization Code with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow).
- **Tokens:**
  - O access token vale 1 hora.
  - O refresh token vale 6 meses a partir da autorização; renovar o access token não estende esse prazo.
  - O refresh pode devolver um refresh token novo.
  - Fonte: [Refreshing tokens](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens).
- **Development Mode** (vale para todo app novo):
  - Até 5 usuários autenticados, cadastrados um a um no painel. Quem não estiver na lista recebe 403.
  - O dono do app precisa ter Spotify Premium.
  - A cota estendida (uso público) só é concedida a organizações, com pelo menos 250 mil usuários ativos por mês. Pessoas físicas não podem pedir.
  - Fontes: [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) e [guia de migração de fevereiro de 2026](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide).
- **Redirect URI:**
  - HTTPS obrigatório e idêntico ao cadastrado; um endereço do GitHub Pages serve.
  - `localhost` não é aceito; `127.0.0.1` é.
  - Fonte: [Redirect URIs](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).
- **Playlists:**
  - `POST /v1/me/playlists` cria a playlist.
  - `POST /v1/playlists/{id}/items` adiciona até 100 itens por chamada.
  - As rotas antigas `/users/{id}/playlists` e `/tracks` saíram.
  - Fontes: [Create Playlist](https://developer.spotify.com/documentation/web-api/reference/create-playlist) e [Add Items to Playlist](https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist).
- **Histórico:** a Web API não entrega o histórico completo. `recently-played` devolve no máximo 50 faixas e `top` é um ranking. O ZIP continua sendo a única fonte do SyncUp.
- **Não confirmado nas páginas lidas:**
  - se as pessoas que entram no app também precisam de Premium (a documentação não diz);
  - o texto do anúncio de 06/02/2026 no blog (a página não abriu).

## Decisão

Não implementar o login. Num site público, ele funcionaria só para o dono e mais 4 contas cadastradas à mão. Isso daria a impressão de um recurso para todos, mas que falha com 403 para quase todo mundo, e o SyncUp não pode pedir a cota estendida.

## Consequências

- **O app continua sem conta e sem servidor.** O histórico não sai do aparelho.
- **A playlist comum continua em CSV** (botão "Playlist comum · CSV" da Dupla).
- **As capas continuam vindo do oEmbed público do Spotify.** Ele é usado só para capas de faixas, nunca para perfis de pessoas, e não precisa de login.
