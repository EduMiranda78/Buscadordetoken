# dashboard.py
from flask import Flask, render_template, jsonify
import json
import os
import logging

app = Flask(__name__)

def carregar_historico():
    if not os.path.exists("historico.json"):
        return []
    try:
        with open("historico.json", "r") as f:
            conteudo = f.read().strip()
            if not conteudo:
                return []
            return json.loads(conteudo)
    except Exception as e:
        logging.warning(f"Erro ao carregar histórico: {e}")
        return []

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/stats")
def stats():
    hist = carregar_historico()
    if not hist:
        return jsonify({
            "total_trades": 0,
            "win_rate": 0,
            "profit_total_usdt": 0,
            "avg_profit_per_trade": 0,
            "trades": []
        })

    total_trades = len(hist)
    wins = [t for t in hist if t["lucro_pct"] > 0]
    win_rate = len(wins) / total_trades * 100 if total_trades else 0
    profit_total = sum(t["lucro_usdt"] for t in hist)
    avg_profit = profit_total / total_trades if total_trades else 0

    return jsonify({
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "profit_total_usdt": round(profit_total, 2),
        "avg_profit_per_trade": round(avg_profit, 2),
        "trades": hist
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
