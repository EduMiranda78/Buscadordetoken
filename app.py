#!/usr/bin/env python3
# app.py – Scanner de tokens novos em futures + monitor de lucro + registro de trades

import os
import json
import time
import logging
import requests
import ccxt
from dotenv import load_dotenv

# ================== CONFIG ==================
TIMEFRAME_NOVO = "15m"
MAX_CANDLES_NOVO = 64
TIMEFRAME_MOMENTUM = "1h"

MIN_VOLUME_USDT = 50_000
MIN_PRECO_PUMP = 1.50
MIN_MOMENTUM_1H_PCT = 5.0

ALVO_LUCRO_PCT = 50.0
CHECK_INTERVAL = 60

POSICOES_FILE = "posicoes.json"
ALERTADOS_FILE = "alertados.json"
HISTORICO_FILE = "historico.json"
# ===========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not all([BINANCE_API_KEY, BINANCE_SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    raise RuntimeError("Variáveis obrigatórias não encontradas no .env")


# ================== UTILS ==================

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logging.error(f"Erro ao enviar Telegram: {e}")


def carregar_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            conteudo = f.read().strip()
            if not conteudo:
                return {}
            return json.loads(conteudo)
    except Exception as e:
        logging.warning(f"Erro ao carregar {path}: {e}")
        return {}


def salvar_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Erro ao salvar {path}: {e}")


def carregar_historico():
    if not os.path.exists(HISTORICO_FILE):
        return []
    try:
        with open(HISTORICO_FILE, "r") as f:
            conteudo = f.read().strip()
            if not conteudo:
                return []
            return json.loads(conteudo)
    except Exception as e:
        logging.warning(f"Erro ao carregar histórico: {e}")
        return []


def salvar_historico(historico):
    try:
        with open(HISTORICO_FILE, "w") as f:
            json.dump(historico, f, indent=2)
    except Exception as e:
        logging.error(f"Erro ao salvar histórico: {e}")


def registrar_trade_no_historico(par, info, preco_saida, motivo="take_profit"):
    historico = carregar_historico()

    # Calcula lucro percentual
    lucro_pct = ((preco_saida - info["preco_entrada"]) / info["preco_entrada"]) * 100
    # Quantidade pode vir da posição; fallback para 1 se não tiver
    quantidade = info.get("quantidade", 1)
    lucro_usdt = (lucro_pct / 100) * (info["preco_entrada"] * quantidade)

    trade = {
        "id": f"{par.replace('/', '-')}-{int(info['adicionado_em'])}",
        "par": par,
        "lado": info.get("lado", "long"),
        "entrada_preco": info["preco_entrada"],
        "saida_preco": preco_saida,
        "quantidade": quantidade,
        "entrada_ts": int(info["adicionado_em"]),
        "saida_ts": int(time.time()),
        "duracao_seg": int(time.time() - info["adicionado_em"]),
        "lucro_usdt": round(lucro_usdt, 4),
        "lucro_pct": round(lucro_pct, 2),
        "alvo_atingido": motivo == "take_profit",
        "motivo_saida": motivo
    }

    historico.append(trade)
    salvar_historico(historico)
    logging.info(f"Trade registrado: {par} | +{lucro_pct:.2f}%")

    # Opcional: avisar no Telegram
    msg = (
        f"✅ <b>Trade Fechado</b>\n"
        f"Par: {par}\n"
        f"Lucro: {'+' if lucro_pct > 0 else ''}{lucro_pct:.2f}% (${lucro_usdt:.2f})\n"
        f"Motivo: {motivo}"
    )
    enviar_telegram(msg)


# ================== EXCHANGE ==================

def criar_exchange():
    exchange = ccxt.binance({
        "apiKey": BINANCE_API_KEY,
        "secret": BINANCE_SECRET_KEY,
        "options": {"defaultType": "future"},
        "enableRateLimit": True,
    })
    exchange.load_markets()
    return exchange


def obter_pares_futures_usdt(exchange):
    return [
        symbol for symbol, market in exchange.markets.items()
        if market.get("quote") == "USDT"
        and market.get("type") == "future"
        and market.get("linear") is True
        and market.get("active") is True
    ]


# ================== DADOS DE MERCADO ==================

def get_candle_count(exchange, par, timeframe, limit):
    try:
        candles = exchange.fetch_ohlcv(par, timeframe, limit=limit)
        return len(candles)
    except:
        return 0


def get_ticker(exchange, par):
    try:
        return exchange.fetch_ticker(par)
    except:
        return None


def get_momentum_1h(exchange, par):
    try:
        candles = exchange.fetch_ohlcv(par, TIMEFRAME_MOMENTUM, limit=2)
        if len(candles) < 2:
            return 0.0
        prev = candles[-2][4]
        curr = candles[-1][4]
        return ((curr - prev) / prev) * 100
    except:
        return 0.0


# ================== POSIÇÕES REAIS DA BINANCE ==================

def obter_posicoes_abertas_binance(exchange):
    try:
        positions = exchange.fetch_positions()
        abertas = {}
        for pos in positions:
            contracts = float(pos.get("contracts", 0))
            if contracts != 0:
                symbol = pos["symbol"]
                entry_price = float(pos.get("entryPrice", 0))
                side = pos.get("side", "long")
                abertas[symbol] = {
                    "preco_entrada": entry_price,
                    "lado": side,
                    "quantidade": contracts,
                    "ativo": True
                }
        return abertas
    except Exception as e:
        logging.error(f"Erro ao buscar posições abertas: {e}")
        return {}


# ================== LÓGICA PRINCIPAL ==================

def eh_token_novo(exchange, par):
    count = get_candle_count(exchange, par, TIMEFRAME_NOVO, MAX_CANDLES_NOVO + 5)
    return 0 < count <= MAX_CANDLES_NOVO


def detectar_pumps(exchange, pares, alertados):
    encontrados = []

    for par in pares:
        if par in alertados:
            continue

        if not eh_token_novo(exchange, par):
            continue

        ticker = get_ticker(exchange, par)
        if not ticker:
            continue

        preco = float(ticker.get("last") or 0)
        volume = float(ticker.get("quoteVolume") or 0)

        if preco < MIN_PRECO_PUMP:
            continue

        if volume < MIN_VOLUME_USDT:
            continue

        momentum = get_momentum_1h(exchange, par)
        if momentum < MIN_MOMENTUM_1H_PCT:
            continue

        base = par.replace("/", "")
        link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{base}.P"

        encontrados.append({
            "par": par,
            "preco": preco,
            "volume": volume,
            "momentum": momentum,
            "link": link
        })

    return encontrados


def monitorar_posicoes(exchange):
    posicoes_local = carregar_json(POSICOES_FILE)
    alterado = False

    posicoes_binance = obter_posicoes_abertas_binance(exchange)

    # Detectar novas posições
    for par, info_binance in posicoes_binance.items():
        if par not in posicoes_local:
            preco_entrada = info_binance["preco_entrada"]
            alvo_preco = preco_entrada * (1 + ALVO_LUCRO_PCT / 100)

            posicoes_local[par] = {
                "preco_entrada": preco_entrada,
                "alvo_preco": alvo_preco,
                "lado": info_binance["lado"],
                "quantidade": info_binance["quantidade"],
                "ativo": True,
                "adicionado_em": time.time()
            }
            alterado = True
            logging.info(f"Nova posição detectada: {par} @ ${preco_entrada:.4f}")

    # Monitorar fechamentos e alvos
    for par, info in list(posicoes_local.items()):
        if not info.get("ativo", False):
            continue

        if par not in posicoes_binance:
            # Fechada manualmente ou por stop loss
            ticker = get_ticker(exchange, par)
            if ticker:
                preco_saida = float(ticker["last"])
                registrar_trade_no_historico(par, info, preco_saida, motivo="manual_or_sl")
            posicoes_local[par]["ativo"] = False
            alterado = True
            continue

        # Verificar alvo
        ticker = get_ticker(exchange, par)
        if not ticker:
            continue

        preco_atual = float(ticker.get("last") or 0)
        alvo = info.get("alvo_preco", 0)

        if preco_atual >= alvo and alvo > 0:
            registrar_trade_no_historico(par, info, preco_atual, motivo="take_profit")
            posicoes_local[par]["ativo"] = False
            alterado = True

    if alterado:
        salvar_json(POSICOES_FILE, posicoes_local)


# ================== LOOP ==================

def main():
    exchange = criar_exchange()
    pares = obter_pares_futures_usdt(exchange)

    logging.info("Sistema iniciado – scanner + monitor de posições + registro de trades")

    while True:
        try:
            alertados = carregar_json(ALERTADOS_FILE)
            monitorar_posicoes(exchange)
            pumps = detectar_pumps(exchange, pares, alertados)

            for p in pumps:
                msg = (
                    f"🔥 <b>PUMP EM TOKEN NOVO</b>\n"
                    f"Par: <b>{p['par']}</b>\n"
                    f"Preço: ${p['preco']:.4f}\n"
                    f"Volume: ${p['volume']:,.0f}\n"
                    f"Momentum 1h: +{p['momentum']:.1f}%\n"
                    f"Gráfico: {p['link']}"
                )
                enviar_telegram(msg)
                logging.info(f"Alerta enviado para {p['par']}")

                alertados[p["par"]] = {"detectado_em": time.time()}

            if pumps:
                salvar_json(ALERTADOS_FILE, alertados)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Encerrado pelo usuário")
            break
        except Exception as e:
            logging.error(f"Erro no loop: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
