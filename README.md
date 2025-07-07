# Documentação do Projeto: Analisador de Jogos de Xadrez com Stockfish

## Descrição

Este projeto consiste em um script Python que analisa múltiplos arquivos de partidas de xadrez no formato PGN utilizando o motor de xadrez Stockfish. O objetivo é identificar lances críticos nas partidas — jogadas que causam grandes variações na avaliação da posição — e gerar relatórios detalhados com essas análises, facilitando o estudo e aprimoramento dos jogadores.

---

## Funcionalidades Principais

- Carregamento e análise de múltiplos arquivos PGN de um diretório.
- Avaliação das posições antes e depois de cada lance usando Stockfish.
- Detecção automática de lances críticos baseados em um limiar configurável.
- Geração de relatórios:
    - JSON com dados estruturados dos lances críticos.
    - Relatório HTML visualmente formatado.
    - Arquivo de texto com prompts para análise via ChatGPT.
- Sistema de logs para acompanhar o andamento e erros durante a análise.
- Suporte a parâmetros via linha de comando para personalização.

---

## Requisitos

- Python 3.x
- Bibliotecas Python:
    - `chess`
    - `stockfish`
    - `python-chess`
- Motor Stockfish instalado no sistema e acessível via linha de comando.

Instalação das bibliotecas Python:

```
pip install chess stockfish python-chess
```

Stockfish pode ser baixado em:

https://stockfishchess.org/download/

---

## Uso

Executar o script via linha de comando:

```python
python chess_analyzer.py <diretório_com_arquivos_pgn> [opções]
```

### Opções

| Opção | Descrição | Padrão |
| --- | --- | --- |
| `--stockfish` | Caminho para o executável do Stockfish | `"stockfish"` |
| `--depth` | Profundidade da análise feita pelo Stockfish | 15 |
| `--threshold` | Limiar (em pontos) para considerar um lance como crítico | 2.0 |
| `--no-html` | Não gera o relatório em HTML | (não usado) |
| `--no-prompts` | Não gera o arquivo de prompts para ChatGPT | (não usado) |
| `--output-dir` | Diretório onde os relatórios serão salvos | `"./output"`  |

### Exemplo

```python
python chess_analyzer.py ./pgn_files --stockfish /usr/local/bin/stockfish --depth 20 --threshold 3.0 --output-dir ./resultados
```

## Saída gerada

No diretório de saída especificado, serão criados os seguintes arquivos:

- `chess_analysis.json`: Dados estruturados dos lances críticos detectados.
- `chess_analysis_report.html`: Relatório visual detalhado (exceto se `-no-html` for usado).
- `chess_analysis_prompts.txt`: Prompts para análise dos lances com ChatGPT (exceto se `-no-prompts` for usado).
- `chess_analyzer.log`: Arquivo de log com informações da execução.

---

## Estrutura Interna

- `ChessAnalyzer`: Classe principal responsável pela análise, carregamento dos arquivos PGN, interação com o Stockfish, detecção dos lances críticos e geração dos relatórios.
- `CriticalMove`: Dataclass que armazena informações detalhadas sobre cada lance crítico encontrado.
- Função `main()`: Lida com argumentos da linha de comando, inicializa o analisador, executa a análise e gera os relatórios.

---

## Como Funciona a Análise

1. Para cada arquivo PGN no diretório informado, carrega todas as partidas.
2. Para cada partida:
    - Avalia a posição inicial.
    - Percorre todos os lances da linha principal.
    - Avalia a posição após cada lance.
    - Calcula a diferença (delta) entre as avaliações antes e depois do lance.
    - Se o delta for maior ou igual ao limiar, o lance é marcado como crítico.
    - Obtém o melhor lance para a posição anterior para comparação.
    - Armazena informações e comentários sobre o lance crítico.
3. Ao final, gera os relatórios com base em todos os lances críticos detectados.

---

## Logs

O script gera logs detalhados no arquivo `chess_analyzer.log` e na saída padrão, facilitando a depuração e acompanhamento do progresso.

---
