# Câmara da Lapa em Dados

Site: https://pedrosolb.github.io/olho-na-camara-lapa/

Painel cidadão com presença, votações nominais e proposições dos vereadores da Câmara Municipal da Lapa-PR.
Fonte: API pública do SAPL (https://sapl.lapa.pr.leg.br/api/), dados sob licença CC BY-SA 4.0.

## Arquivos
- `coletar_dados.py`: lê a API do SAPL e gera `data.json`.
- `index.src.html`: modelo da página (visual e lógica).
- `montar_pagina.py`: junta modelo + dados e gera `docs/index.html` (página completa).
- `.github/workflows/atualizar.yml`: atualiza os dados todo dia no GitHub.

## Como publicar (GitHub Pages, grátis)
1. Crie um repositório público no GitHub e envie esta pasta.
2. Em Settings > Pages, escolha a branch `main` e a pasta `/docs`.
3. Em Actions, rode "Atualizar dados da Câmara" uma vez para testar.

## Rodar no computador
    pip install requests
    python coletar_dados.py
    python montar_pagina.py
