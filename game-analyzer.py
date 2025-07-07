#!/usr/bin/env python3
"""
Analisador de Jogos de Xadrez com Stockfish
==========================================

Este script analisa múltiplos arquivos PGN usando Stockfish para detectar
lances críticos e gerar relatórios detalhados.

Requisitos:
- pip install chess stockfish python-chess
- Stockfish engine instalado no sistema

"""

import chess
import chess.pgn
import chess.engine
import os
import json
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime


@dataclass
class CriticalMove:
    """Classe para armazenar informações sobre um lance crítico"""
    game_id: str
    move_number: int
    move: str
    side: str
    eval_before: float
    eval_after: float
    delta: float
    position_fen: str
    best_move: Optional[str] = None
    comment: str = ""


class ChessAnalyzer:
    """Classe principal para análise de jogos de xadrez"""
    
    def __init__(self, stockfish_path: str = "stockfish", depth: int = 15, 
                 critical_threshold: float = 2.0):
        """
        Inicializa o analisador

        Args:
            stockfish_path: Caminho para o executável do Stockfish
            depth: Profundidade de análise
            critical_threshold: Limite para considerar um lance como crítico
        """
        self.stockfish_path = stockfish_path
        self.depth = depth
        self.critical_threshold = critical_threshold
        self.engine = None
        self.setup_logging()
        
    def setup_logging(self):
        """Configura o sistema de logs"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('chess_analyzer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_engine(self):
        """Inicia o engine Stockfish"""
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
            self.logger.info(f"Engine Stockfish iniciado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao iniciar Stockfish: {e}")
            raise
    
    def stop_engine(self):
        """Para o engine Stockfish"""
        if self.engine:
            self.engine.quit()
            self.logger.info("Engine Stockfish parado")
    
    def evaluate_position(self, board: chess.Board) -> float:
        """
        Avalia uma posição usando Stockfish
        
        Args:
            board: Posição do tabuleiro
            
        Returns:
            Avaliação em centipawns (perspectiva das brancas)
        """
        try:
            info = self.engine.analyse(board, chess.engine.Limit(depth=self.depth))
            score = info["score"]
            
            # Converte para centipawns
            if score.is_mate():
                # Mate em X lances
                mate_value = score.mate()
                return 1000 + mate_value if mate_value > 0 else -1000 - mate_value
            else:
                return score.white().score() / 100.0
                
        except Exception as e:
            self.logger.error(f"Erro ao avaliar posição: {e}")
            return 0.0
    
    def get_best_move(self, board: chess.Board) -> Optional[str]:
        """
        Obtém o melhor lance para uma posição
        
        Args:
            board: Posição do tabuleiro
            
        Returns:
            Melhor lance em notação algébrica
        """
        try:
            result = self.engine.play(board, chess.engine.Limit(depth=self.depth))
            return board.san(result.move)
        except Exception as e:
            self.logger.error(f"Erro ao obter melhor lance: {e}")
            return None
    
    def analyze_game(self, game: chess.pgn.Game, game_id: str) -> List[CriticalMove]:
        """
        Analisa um jogo completo e identifica lances críticos
        
        Args:
            game: Jogo em formato PGN
            game_id: Identificador único do jogo
            
        Returns:
            Lista de lances críticos encontrados
        """
        critical_moves = []
        board = game.board()
        previous_eval = 0.0
        move_number = 0
        
        self.logger.info(f"Analisando jogo {game_id}")
        
        # Avalia posição inicial
        if not board.is_game_over():
            previous_eval = self.evaluate_position(board)
        
        for move in game.mainline_moves():
            move_number += 1
            
            # Faz o lance
            move_san = board.san(move)
            board.push(move)
            
            # Avalia nova posição
            if not board.is_game_over():
                current_eval = self.evaluate_position(board)
                
                # Calcula delta (mudança de avaliação)
                delta = abs(current_eval - previous_eval)
                
                # Verifica se é um lance crítico
                if delta >= self.critical_threshold:
                    # Obtém o melhor lance para a posição anterior
                    board.pop()  # Volta à posição anterior
                    best_move = self.get_best_move(board)
                    board.push(move)  # Refaz o lance
                    
                    critical_move = CriticalMove(
                        game_id=game_id,
                        move_number=move_number,
                        move=move_san,
                        side="Brancas" if board.turn == chess.BLACK else "Pretas",
                        eval_before=previous_eval,
                        eval_after=current_eval,
                        delta=delta,
                        position_fen=board.fen(),
                        best_move=best_move,
                        comment=self._generate_move_comment(previous_eval, current_eval, delta)
                    )
                    
                    critical_moves.append(critical_move)
                    self.logger.info(f"Lance crítico detectado: {move_san} (Δ={delta:.2f})")
                
                previous_eval = current_eval
            
            # Progresso a cada 10 lances
            if move_number % 10 == 0:
                self.logger.info(f"Analisado lance {move_number}")
        
        return critical_moves
    
    def _generate_move_comment(self, eval_before: float, eval_after: float, delta: float) -> str:
        """
        Gera um comentário descritivo para um lance crítico
        
        Args:
            eval_before: Avaliação antes do lance
            eval_after: Avaliação após o lance
            delta: Mudança de avaliação
            
        Returns:
            Comentário descritivo
        """
        if eval_after > eval_before:
            if delta >= 5.0:
                return "Lance excelente! Melhora significativamente a posição"
            elif delta >= 3.0:
                return "Bom lance tático que aumenta a vantagem"
            else:
                return "Lance que melhora ligeiramente a posição"
        else:
            if delta >= 5.0:
                return "Erro grave! Lance que compromete seriamente a posição"
            elif delta >= 3.0:
                return "Erro tático importante"
            else:
                return "Imprecisão que piora a posição"
    
    def load_pgn_files(self, directory: str) -> List[Tuple[chess.pgn.Game, str]]:
        """
        Carrega todos os arquivos PGN de um diretório
        
        Args:
            directory: Caminho para o diretório com arquivos PGN
            
        Returns:
            Lista de tuplas (jogo, id_do_jogo)
        """
        games = []
        pgn_files = list(Path(directory).glob("*.pgn"))
        
        self.logger.info(f"Encontrados {len(pgn_files)} arquivos PGN")
        
        for pgn_file in pgn_files:
            try:
                with open(pgn_file, 'r', encoding='utf-8') as f:
                    game_count = 0
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        
                        game_count += 1
                        game_id = f"{pgn_file.stem}_{game_count}"
                        games.append((game, game_id))
                        
                self.logger.info(f"Carregados {game_count} jogos de {pgn_file.name}")
                
            except Exception as e:
                self.logger.error(f"Erro ao carregar {pgn_file}: {e}")
        
        return games
    
    def analyze_multiple_games(self, directory: str) -> List[CriticalMove]:
        """
        Analisa múltiplos jogos de um diretório
        
        Args:
            directory: Caminho para o diretório com arquivos PGN
            
        Returns:
            Lista de todos os lances críticos encontrados
        """
        all_critical_moves = []
        games = self.load_pgn_files(directory)
        
        self.logger.info(f"Iniciando análise de {len(games)} jogos")
        
        for i, (game, game_id) in enumerate(games, 1):
            self.logger.info(f"Analisando jogo {i}/{len(games)}: {game_id}")
            
            try:
                critical_moves = self.analyze_game(game, game_id)
                all_critical_moves.extend(critical_moves)
                
                self.logger.info(f"Jogo {game_id}: {len(critical_moves)} lances críticos encontrados")
                
            except Exception as e:
                self.logger.error(f"Erro ao analisar jogo {game_id}: {e}")
        
        return all_critical_moves
    
    def generate_report(self, critical_moves: List[CriticalMove], output_file: str = "chess_analysis_report.html"):
        """
        Gera relatório HTML com os lances críticos
        
        Args:
            critical_moves: Lista de lances críticos
            output_file: Nome do arquivo de saída
        """
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Relatório de Análise de Xadrez</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 8px; }}
                .stats {{ background-color: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .critical-move {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; }}
                .critical-move.error {{ border-left: 5px solid #e74c3c; }}
                .critical-move.good {{ border-left: 5px solid #27ae60; }}
                .move-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }}
                .fen {{ font-family: monospace; font-size: 12px; background-color: #f8f9fa; padding: 5px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Relatório de Análise de Xadrez</h1>
                <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
            
            <div class="stats">
                <h2>📈 Estatísticas</h2>
                <ul>
                    <li><strong>Total de lances críticos:</strong> {len(critical_moves)}</li>
                    <li><strong>Limiar de criticidade:</strong> {self.critical_threshold} pontos</li>
                    <li><strong>Profundidade de análise:</strong> {self.depth} lances</li>
                </ul>
            </div>
            
            <div class="moves-section">
                <h2>🎯 Lances Críticos Detectados</h2>
        """
        
        for move in sorted(critical_moves, key=lambda x: x.delta, reverse=True):
            move_class = "good" if move.eval_after > move.eval_before else "error"
            
            html_content += f"""
                <div class="critical-move {move_class}">
                    <h3>🎲 {move.move} - {move.side} (Lance {move.move_number})</h3>
                    <div class="move-info">
                        <div><strong>Jogo:</strong> {move.game_id}</div>
                        <div><strong>Mudança:</strong> {move.delta:.2f} pontos</div>
                        <div><strong>Avaliação anterior:</strong> {move.eval_before:.2f}</div>
                        <div><strong>Avaliação posterior:</strong> {move.eval_after:.2f}</div>
                    </div>
                    <p><strong>Comentário:</strong> {move.comment}</p>
                    {f'<p><strong>Melhor lance:</strong> {move.best_move}</p>' if move.best_move else ''}
                    <div class="fen">
                        <strong>FEN:</strong> {move.position_fen}
                    </div>
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Relatório HTML gerado: {output_file}")
    
    def generate_chatgpt_prompts(self, critical_moves: List[CriticalMove], 
                                output_file: str = "chatgpt_prompts.txt"):
        """
        Gera prompts descritivos para análise no ChatGPT
        
        Args:
            critical_moves: Lista de lances críticos
            output_file: Nome do arquivo de saída
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Prompts para Análise de Xadrez no ChatGPT\n")
            f.write("=" * 50 + "\n\n")
            
            for i, move in enumerate(sorted(critical_moves, key=lambda x: x.delta, reverse=True)[:10], 1):
                f.write(f"## Prompt {i}: {move.move} - {move.side}\n")
                f.write(f"**Jogo:** {move.game_id} | **Lance:** {move.move_number}\n")
                f.write(f"**Mudança de avaliação:** {move.delta:.2f} pontos\n\n")
                
                f.write("### Prompt para ChatGPT:\n")
                f.write(f"""
Analise esta posição de xadrez onde foi jogado o lance {move.move} pelas {move.side.lower()}:

🎯 **Contexto:**
- Lance número: {move.move_number}
- Avaliação antes: {move.eval_before:.2f}
- Avaliação depois: {move.eval_after:.2f}
- Mudança: {move.delta:.2f} pontos
- Melhor lance sugerido: {move.best_move or 'N/A'}

📋 **Posição FEN:**
{move.position_fen}

🤔 **Perguntas para análise:**
1. Por que este lance foi crítico?
2. Quais eram as alternativas melhores?
3. Que padrão tático/estratégico está envolvido?
4. Como a posição mudou após este lance?
5. Que lições podemos aprender?

Por favor, forneça uma análise detalhada desta posição.
""")
                f.write("\n" + "="*80 + "\n\n")
        
        self.logger.info(f"Prompts para ChatGPT gerados: {output_file}")
    
    def save_json_report(self, critical_moves: List[CriticalMove], 
                        output_file: str = "critical_moves.json"):
        """
        Salva os resultados em formato JSON
        
        Args:
            critical_moves: Lista de lances críticos
            output_file: Nome do arquivo de saída
        """
        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "threshold": self.critical_threshold,
                "depth": self.depth,
                "total_moves": len(critical_moves)
            },
            "critical_moves": [
                {
                    "game_id": move.game_id,
                    "move_number": move.move_number,
                    "move": move.move,
                    "side": move.side,
                    "eval_before": move.eval_before,
                    "eval_after": move.eval_after,
                    "delta": move.delta,
                    "position_fen": move.position_fen,
                    "best_move": move.best_move,
                    "comment": move.comment
                }
                for move in critical_moves
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Dados salvos em JSON: {output_file}")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Analisador de Jogos de Xadrez com Stockfish")
    parser.add_argument("directory", help="Diretório contendo arquivos PGN")
    parser.add_argument("--stockfish", default="stockfish", help="Caminho para Stockfish")
    parser.add_argument("--depth", type=int, default=15, help="Profundidade de análise")
    parser.add_argument("--threshold", type=float, default=2.0, help="Limiar para lances críticos")
    parser.add_argument("--no-html", action="store_true", help="Não gerar relatório HTML")
    parser.add_argument("--no-prompts", action="store_true", help="Não gerar prompts ChatGPT")
    parser.add_argument("--output-dir", default="./output", help="Diretório de saída")
    
    args = parser.parse_args()
    
    # Cria diretório de saída
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Inicializa o analisador
    analyzer = ChessAnalyzer(
        stockfish_path=args.stockfish,
        depth=args.depth,
        critical_threshold=args.threshold
    )
    
    try:
        # Inicia o engine
        analyzer.start_engine()
        
        # Analisa os jogos
        critical_moves = analyzer.analyze_multiple_games(args.directory)
        
        if not critical_moves:
            print("❌ Nenhum lance crítico encontrado!")
            return
        
        print(f"✅ {len(critical_moves)} lances críticos detectados!")
        
        # Gera relatórios
        output_base = os.path.join(args.output_dir, "chess_analysis")
        
        # JSON (sempre gerado)
        analyzer.save_json_report(critical_moves, f"{output_base}.json")
        
        # HTML
        if not args.no_html:
            analyzer.generate_report(critical_moves, f"{output_base}_report.html")
        
        # Prompts ChatGPT
        if not args.no_prompts:
            analyzer.generate_chatgpt_prompts(critical_moves, f"{output_base}_prompts.txt")
        
        print(f"📊 Relatórios salvos em: {args.output_dir}")
        
    except Exception as e:
        print(f"❌ Erro durante análise: {e}")
    finally:
        # Para o engine
        analyzer.stop_engine()


if __name__ == "__main__":
    main()
