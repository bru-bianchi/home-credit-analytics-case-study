## Visão geral da pasta data

- `data/raw/`: arquivos originais recebidos da fonte, mantidos intocados.
- `data/warehouse/`: arquivo DuckDB local com as camadas analíticas do projeto.

Para informações detalhadas, consulte `docs/data.md`

Dentro do `warehouse`, a organização prevista é:

- `raw`: tabelas carregadas diretamente dos arquivos de origem;
- `bronze`: padronizações técnicas iniciais;
- `silver`: transformações e enriquecimentos intermediários;
- `gold`: tabelas finais para consumo analítico;
- `metadados`: registro das execuções de ingestão e seus status.