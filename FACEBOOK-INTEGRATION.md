# Integracao Facebook no site

O site ja esta preparado para mostrar publicacoes automaticas na homepage a partir do ficheiro `facebook-feed.json`.

## O que falta para ativar

No GitHub, neste repositorio, cria estes dois secrets:

- `FACEBOOK_PAGE_ID`
- `FACEBOOK_PAGE_ACCESS_TOKEN`

## Como funciona

1. A GitHub Action `.github/workflows/update-facebook-feed.yml` corre de 6 em 6 horas ou manualmente.
2. A action chama a API Graph do Facebook.
3. O resultado e guardado em `facebook-feed.json`.
4. A homepage le esse ficheiro e mostra as publicacoes na secao "Ultimas publicacoes trazidas automaticamente da pagina".

## Notas importantes

- O token nao deve ficar no HTML nem em JavaScript do browser.
- O ideal e usar uma pagina Facebook real tua, com permissao valida para ler publicacoes.
- Se mudares a pagina, atualiza tambem o URL usado em `index.html` e no `facebook-feed.json`.
