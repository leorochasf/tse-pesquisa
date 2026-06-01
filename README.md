# Ferramenta TSE

Consulta automatizada de eleitos, suplentes e mandatos municipais a partir dos
dados abertos do TSE — sem automação de navegador.

## Pré-requisitos

```
Python 3.11+
pip install -r requirements.txt
```

## Fluxo de uso

### 1. Importar dados

```bash
python cli.py ingest --anos 2024
# Para múltiplos anos:
python cli.py ingest --anos 2016 2020 2024
```

Baixa `consulta_cand_AAAA.zip` do TSE, extrai apenas GO e popula `tse_core/dados/tse.sqlite`.
O download é cacheado localmente (pasta `cache/`); reimportar o mesmo ano é idempotente.

### 2. Listar candidatos

```bash
python cli.py listar --municipio "Inaciolândia" --cargo vereador --ano 2024
python cli.py listar --municipio "Goiânia" --cargo prefeito --ano 2024 --excel resultado.xlsx
```

### 3. Rastrear pessoa entre eleições

```bash
python cli.py rastrear --nome "FULANO DE TAL" --municipio "Inaciolândia" --cargo vereador
```

Retorna linha do tempo de mandatos (início/fim) e flag de reeleição.

## Estrutura do projeto

```
FerramentaTSE/
├─ tse_core/          # Motor de consulta (reusado pela skill /tse)
│  ├─ db.py          # Schema SQLite
│  ├─ ingest.py      # Download e importação dos CSVs
│  ├─ consulta.py    # listar() e rastrear()
│  ├─ mandato.py     # Inferência de mandatos
│  └─ dados/
│     ├─ cargos.py   # Mapa código↔nome de cargo
│     └─ tse.sqlite  # Base local (gerada via ingest; não versionada)
├─ cli.py            # Interface de linha de comando
├─ docs/             # Plano de viabilidade e etapas de implementação
└─ requirements.txt
```

## Estado das etapas

| Etapa | Status | Descrição |
|-------|--------|-----------|
| 0 | ✅ | Scaffolding e schema SQLite |
| 1 | pendente | Ingest do CSV oficial do TSE |
| 2 | pendente | Consulta "listar" (núcleo) |
| 3 | pendente | CLI listar + exportação Excel/CSV |
| 4 | pendente | Rastrear pessoa + inferência de mandato |
| 5 | pendente | Skill /tse no AssessorIA |

## Fonte dos dados

TSE Dados Abertos — `consulta_cand`:
`https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_AAAA.zip`
