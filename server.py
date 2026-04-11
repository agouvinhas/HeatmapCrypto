#!/usr/bin/env python3
"""
BTC Alert — Dashboard + Scheduler
Roda localmente ou no Railway (variáveis de ambiente substituem config.json).
"""

import json
import logging
import os
import ssl
import subprocess
import sys
from datetime import datetime
from functools import wraps
from urllib.request import urlopen, Request

from flask import Flask, jsonify, render_template, request, Response
from apscheduler.schedulers.background import BackgroundScheduler

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIR, "config.json")
STATE_FILE  = os.path.join(DIR, ".alert_state.json")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

# ─── SSL ──────────────────────────────────────────────────────────────────────

def _ssl_ctx():
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

SSL_CTX = _ssl_ctx()

# ─── Config (arquivo local ou variáveis de ambiente do Railway) ───────────────

def ler_config():
    cfg = json.load(open(CONFIG_FILE, encoding="utf-8")) if os.path.exists(CONFIG_FILE) else {}

    # Variáveis de ambiente sobrescrevem o arquivo (útil no Railway)
    cfg.setdefault("whatsapp", {})
    cfg["whatsapp"]["phone"]            = os.environ.get("PHONE",            cfg["whatsapp"].get("phone", ""))
    cfg["whatsapp"]["callmebot_api_key"] = os.environ.get("CALLMEBOT_API_KEY", cfg["whatsapp"].get("callmebot_api_key", ""))

    cfg.setdefault("thresholds",    {"3h": 2.0, "6h": 3.5, "12h": 5.0, "24h": 8.0})
    cfg.setdefault("cooldown_horas",{"3h": 1.0, "6h": 2.0, "12h": 4.0, "24h": 6.0})
    cfg.setdefault("janela_historico_minutos", 10)
    return cfg

def salvar_config(data):
    cfg = ler_config()
    cfg["whatsapp"]["phone"]             = data["phone"]
    cfg["whatsapp"]["callmebot_api_key"] = data["callmebot_api_key"]
    cfg["thresholds"]                    = {p: float(data[f"threshold_{p}"]) for p in ["3h","6h","12h","24h"]}
    cfg["cooldown_horas"]                = {p: float(data[f"cooldown_{p}"])   for p in ["3h","6h","12h","24h"]}
    cfg["janela_historico_minutos"]      = int(data.get("janela_historico_minutos", 10))
    json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def ler_estado():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE, encoding="utf-8"))
    return {}

# ─── Auth básica ──────────────────────────────────────────────────────────────

def _check_auth(username, password):
    expected_user = os.environ.get("DASHBOARD_USER", "admin")
    expected_pass = os.environ.get("DASHBOARD_PASSWORD", "")
    if not expected_pass:          # sem senha configurada → acesso livre (local)
        return True
    return username == expected_user and password == expected_pass

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not _check_auth(auth.username if auth else "", auth.password if auth else ""):
            return Response("Login necessário", 401, {"WWW-Authenticate": 'Basic realm="BTC Alert"'})
        return f(*args, **kwargs)
    return decorated

# ─── Preço ────────────────────────────────────────────────────────────────────

def preco_btc():
    req = Request("https://www.mercadobitcoin.net/api/BTC/ticker/",
                  headers={"User-Agent": "btc-alert/1.0"})
    with urlopen(req, timeout=8, context=SSL_CTX) as resp:
        t = json.loads(resp.read())["ticker"]
    return {k: float(t[k]) for k in ("last", "high", "low", "open", "vol")}

# ─── Scheduler (substitui o cron do Mac) ─────────────────────────────────────

def run_check():
    log.info("Scheduler: verificando alertas...")
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(DIR, "btc_alert.py")],
            capture_output=True, text=True, timeout=60
        )
        for line in (result.stdout + result.stderr).splitlines():
            log.info("  " + line)
    except Exception as e:
        log.error(f"Scheduler erro: {e}")

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_check, "interval", minutes=5, id="btc_check")
scheduler.start()
log.info("Scheduler iniciado — verificando a cada 5 minutos.")

# ─── Rotas ────────────────────────────────────────────────────────────────────

@app.get("/")
@requires_auth
def index():
    return render_template("index.html")

@app.get("/api/config")
@requires_auth
def get_config():
    cfg = ler_config()
    return jsonify({
        "phone":             cfg["whatsapp"]["phone"],
        "callmebot_api_key": cfg["whatsapp"]["callmebot_api_key"],
        "thresholds":        cfg["thresholds"],
        "cooldown_horas":    cfg["cooldown_horas"],
        "janela_historico_minutos": cfg.get("janela_historico_minutos", 10),
    })

@app.post("/api/config")
@requires_auth
def post_config():
    salvar_config(request.get_json(force=True))
    return jsonify({"ok": True})

@app.get("/api/price")
@requires_auth
def get_price():
    try:
        return jsonify({"ok": True, "data": preco_btc()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

@app.get("/api/state")
@requires_auth
def get_state():
    return jsonify(ler_estado())

@app.post("/api/test")
@requires_auth
def post_test():
    try:
        r = subprocess.run([sys.executable, os.path.join(DIR, "btc_alert.py"), "--test"],
                           capture_output=True, text=True, timeout=20)
        return jsonify({"ok": r.returncode == 0, "output": r.stdout + r.stderr})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/check")
@requires_auth
def post_check():
    try:
        r = subprocess.run([sys.executable, os.path.join(DIR, "btc_alert.py")],
                           capture_output=True, text=True, timeout=30)
        return jsonify({"ok": r.returncode == 0, "output": r.stdout + r.stderr})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.delete("/api/state/<periodo>")
@requires_auth
def delete_state(periodo):
    estado = ler_estado()
    estado.pop(periodo, None)
    json.dump(estado, open(STATE_FILE, "w"), indent=2)
    return jsonify({"ok": True})

@app.get("/api/scheduler")
@requires_auth
def get_scheduler():
    job = scheduler.get_job("btc_check")
    return jsonify({
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None
    })

# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Dashboard em http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
