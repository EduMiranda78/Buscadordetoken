#!/usr/bin/env python3
# app_novalista.py – Monitor de novos listings no USD-M Futures da Binance (versão robusta)

import os
import time
import json
import logging
import socket
import requests
from datetime import datetime, timezone
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

# ================= CONFIG =================
CHECK_INTERVAL = 120          # segundos
MAX_HORAS_LISTAGEM = 16       # janela de novidade
CACHE_FILE = "novos_listados.json"
REQUEST_TIMEOUT = 30          # aumentado
MAX_RETRIES = 3
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("Telegram não configurado no .env")


# ================= UTIL =================

def internet_disponivel(host="8.8.8.8", port=53, timeout=5):
    """Verifica se há conexão básica com a internet."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def criar_sessao_http():
    """Cria uma sessão HTTP com retry automático."""
    sessao = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=2,  # 2s, 4s, 8s...
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    sessao.mount("http://", adapter)
    sessao.mount("https://", adapter)
    return sessao


def enviar_telegram(msg):
    # 🔥 CORRIGIDO: removido espaço após "bot"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        sessao = criar_sessao_http()
        sessao.post(url, data=payload, timeout=20)
    except Exception as e:
        logging.error(f"Erro ao enviar Telegram: {e}")


def carregar_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            conteudo = f.read().strip()
            if not conteudo:
                return {}
            return json.loads(conteudo)
    except Exception as e:
        logging.warning(f"Erro ao carregar cache: {e}")
        return {}


def salvar_cache(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Erro ao salvar cache: {e}")


# ================= BINANCE =================

def buscar_exchange_info():
    # 🔥 CORRIGIDO: URL SEM ESPAÇOS
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    sessao = criar_sessao_http()
    r = sessao.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def filtrar_novos_listings(exchange_info, horas_max):
    agora = datetime.now(timezone.utc)
    novos = []

    for symbol in exchange_info.get("symbols", []):
        if symbol.get("contractType") != "PERPETUAL":
            continue
        if symbol.get("quoteAsset") != "USDT":
            continue

        onboard_ms = symbol.get("onboardDate")
        if not onboard_ms:
            continue

        onboard_dt = datetime.fromtimestamp(onboard_ms / 1000, tz=timezone.utc)
        diff_horas = (agora - onboard_dt).total_seconds() / 3600

        if 0 <= diff_horas <= horas_max:
            novos.append({
                "symbol": symbol["symbol"],
                "onboard": onboard_dt.isoformat(),
                "idade_horas": round(diff_horas, 2)
            })

    return novos


# ================= LOOP =================

def main():
    logging.info("Monitor de novos listings USD-M iniciado")

    while True:
        try:
            if not internet_disponivel():
                logging.warning("Sem conexão com a internet. Aguardando...")
                time.sleep(60)
                continue

            cache = carregar_cache()
            exchange_info = buscar_exchange_info()
            novos = filtrar_novos_listings(exchange_info, MAX_HORAS_LISTAGEM)

            for item in novos:
                sym = item["symbol"]
                if sym in cache:
                    continue

                # 🔥 CORRIGIDO: link do TradingView sem espaço
                tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{sym}.P"

                msg = (
                    f"🆕 <b>NOVO LISTING NO FUTURES USD-M</b>\n"
                    f"Par: <b>{sym}</b>\n"
                    f"Idade: {item['idade_horas']} horas\n"
                    f"Onboard: {item['onboard']}\n"
                    f"{tv_link}"
                )

                enviar_telegram(msg)
                logging.info(f"Novo listing detectado: {sym}")

                cache[sym] = {
                    "onboard": item["onboard"],
                    "detectado_em": datetime.now(timezone.utc).isoformat()
                }

            if novos:
                salvar_cache(cache)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Encerrado pelo usuário")
            break
        except requests.exceptions.Timeout:
            logging.error("Timeout na requisição à Binance. Tentando novamente...")
            time.sleep(30)
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Erro de conexão: {e}. Verifique rede ou bloqueio.")
            time.sleep(60)
        except Exception as e:
            logging.error(f"Erro inesperado no loop: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
