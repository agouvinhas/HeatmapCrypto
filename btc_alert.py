#!/usr/bin/env python3
"""
Alerta de preço do Bitcoin em R$ — Mercado Bitcoin → WhatsApp
Verifica variação nas últimas 3h, 6h, 12h e 24h e envia mensagem via CallMeBot.
"""

import json
import os
import random
import ssl
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError

# Contexto SSL que funciona no macOS mesmo sem certificados configurados
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

# ─── Caminhos ────────────────────────────────────────────────────────────────
DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIR, "config.json")
STATE_FILE  = os.path.join(DIR, ".alert_state.json")

PERIODOS = ["3h", "6h", "12h", "24h"]
HORAS    = {"3h": 3, "6h": 6, "12h": 12, "24h": 24}

# ─── Utilitários ─────────────────────────────────────────────────────────────

def carregar_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def carregar_estado():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_estado(estado):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)

def http_get_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "btc-alert/1.0"})
    with urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
        return json.loads(resp.read().decode())

# ─── Mercado Bitcoin API ──────────────────────────────────────────────────────

def preco_atual():
    """Retorna o último preço do BTC em R$."""
    data = http_get_json("https://www.mercadobitcoin.net/api/BTC/ticker/")
    return float(data["ticker"]["last"])

def preco_ha_n_horas(horas, janela_minutos=10):
    """
    Busca o preço negociado aproximadamente N horas atrás usando a API de trades.
    Tenta janelas crescentes até encontrar uma negociação.
    """
    alvo = datetime.now() - timedelta(hours=horas)
    tentativas = [janela_minutos, janela_minutos * 3, janela_minutos * 6, 60]

    for janela in tentativas:
        from_ts = int((alvo - timedelta(minutes=janela // 2)).timestamp())
        to_ts   = int((alvo + timedelta(minutes=janela // 2)).timestamp())
        url = f"https://www.mercadobitcoin.net/api/BTC/trades/{from_ts}/{to_ts}/"
        try:
            trades = http_get_json(url)
            if trades:
                # Pega o trade mais próximo do alvo
                alvo_ts = alvo.timestamp()
                mais_proximo = min(trades, key=lambda t: abs(t["date"] - alvo_ts))
                return float(mais_proximo["price"])
        except Exception:
            pass
        time.sleep(0.3)

    # Fallback: se não encontrou nada, usa o open do ticker (válido para 24h)
    if horas >= 20:
        data = http_get_json("https://www.mercadobitcoin.net/api/BTC/ticker/")
        return float(data["ticker"]["open"])

    return None

# ─── Mensagens bem-humoradas ──────────────────────────────────────────────────

MSGS_ALTA_ENORME = [
    "🚀🚀🚀 DECOLA! Bitcoin disparou *+{var:.1f}%* em {h}! Hora de ligar pro seu cunhado que disse que era golpe!",
    "🤑 CARAMBA! *+{var:.1f}%* em {h}! Satoshi tá sorrindo lá do além!",
    "🔥🔥 MOONSHOT! *+{var:.1f}%* em {h}! Seus vizinhos não sabem ainda... mas logo vão perguntar o que é Bitcoin.",
    "🚀 Houston, temos LUCRO! *+{var:.1f}%* em {h}! HODL, rei. HODL.",
]

MSGS_ALTA_GRANDE = [
    "📈 Eita, lasqueira! Bitcoin subiu *+{var:.1f}%* em {h}! Tá esquentando essa brasa!",
    "😎 *+{var:.1f}%* em {h}h de pura glória! O portfólio agradece.",
    "🔥 Subida firme de *+{var:.1f}%* em {h}! Isso que é aquecimento global que presta.",
    "📈 Bitcoin acordou animado hoje: *+{var:.1f}%* em {h}. Bom dia pra você também!",
]

MSGS_ALTA_PEQUENA = [
    "😊 Bitcoin dando uma subidinha gostosa de *+{var:.1f}%* em {h}. Devagar e sempre!",
    "📈 *+{var:.1f}%* em {h}. Nada dramático, mas o Bitcoin tá bem, obrigado por perguntar.",
    "🙂 Alta modesta de *+{var:.1f}%* em {h}. Cada Satoshi conta!",
    "☕ *+{var:.1f}%* em {h}. Tomou café? O Bitcoin também.",
]

MSGS_QUEDA_ENORME = [
    "💀 MAYDAY! Bitcoin despencou *{var:.1f}%* em {h}! Cilada, Bino? Ou buy the dip? 👀",
    "📉 S.O.S! *{var:.1f}%* em {h}! Segura o coração e o hardware wallet!",
    "🩸 Vermelhão total: *{var:.1f}%* em {h}. Mas ei... fraco não faz bull run!",
    "😱 *{var:.1f}%* em {h}! Isso dói, mas lembra: quem vendeu na baixa anterior também tá arrependido.",
]

MSGS_QUEDA_GRANDE = [
    "😬 Turbulência! Bitcoin caiu *{var:.1f}%* em {h}. Buy the dip? Você decide, eu só informo.",
    "📉 *{var:.1f}%* em {h}. Ai ai... mas já vimos coisa pior. Respira.",
    "🎢 *{var:.1f}%* em {h}. A montanha-russa do Bitcoin pediu desconto temporário.",
    "📉 Queda de *{var:.1f}%* em {h}. Isso é promoção disfarçada ou fim do mundo? Difícil saber.",
]

MSGS_QUEDA_PEQUENA = [
    "😅 Escorregou um pouco: *{var:.1f}%* em {h}. Um chocolate resolve.",
    "📉 *{var:.1f}%* em {h}. O Bitcoin tá de ressaca, mas isso passa.",
    "🙈 *{var:.1f}%* em {h}. Nem olha pro portfólio por uns minutos, tá?",
    "😌 Leve recuo de *{var:.1f}%* em {h}. Até o Bitcoin precisa de uma pausa.",
]

def escolher_mensagem(variacao: float, periodo: str) -> str:
    """Seleciona template com base na direção e intensidade da variação."""
    abs_var = abs(variacao)
    horas_str = periodo  # ex: "3h"

    if variacao > 0:
        if abs_var >= 8:
            pool = MSGS_ALTA_ENORME
        elif abs_var >= 4:
            pool = MSGS_ALTA_GRANDE
        else:
            pool = MSGS_ALTA_PEQUENA
        sinal = "+"
    else:
        if abs_var >= 8:
            pool = MSGS_QUEDA_ENORME
        elif abs_var >= 4:
            pool = MSGS_QUEDA_GRANDE
        else:
            pool = MSGS_QUEDA_PEQUENA
        sinal = "-"

    template = random.choice(pool)
    return template.format(var=abs_var, h=horas_str, sinal=sinal)

# ─── WhatsApp via CallMeBot ───────────────────────────────────────────────────

def formatar_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def enviar_whatsapp(phone: str, api_key: str, mensagem: str) -> bool:
    encoded = quote(mensagem)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded}&apikey={api_key}"
    try:
        req = Request(url, headers={"User-Agent": "btc-alert/1.0"})
        with urlopen(req, timeout=15, context=SSL_CTX) as resp:
            body = resp.read().decode()
            return "Message queued" in body or resp.status == 200
    except Exception as e:
        print(f"[ERRO] WhatsApp: {e}", file=sys.stderr)
        return False

def montar_mensagem(humor: str, preco: float, variacao: float, periodo: str) -> str:
    preco_fmt = formatar_brl(preco)
    sinal = "+" if variacao >= 0 else ""
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    return (
        f"{humor}\n\n"
        f"💰 Preço atual: *{preco_fmt}*\n"
        f"📊 Variação {periodo}: *{sinal}{variacao:.2f}%*\n"
        f"⏰ {ts}"
    )

# ─── Lógica principal ─────────────────────────────────────────────────────────

def em_cooldown(estado: dict, periodo: str, cooldown_horas: float) -> bool:
    ultimo = estado.get(periodo)
    if not ultimo:
        return False
    delta = datetime.now() - datetime.fromisoformat(ultimo)
    return delta.total_seconds() < cooldown_horas * 3600

def verificar_alertas():
    cfg = carregar_config()
    estado = carregar_estado()
    janela = cfg.get("janela_historico_minutos", 10)

    phone   = cfg["whatsapp"]["phone"]
    api_key = cfg["whatsapp"]["callmebot_api_key"]

    if phone == "+5511999999999" or api_key == "SEU_API_KEY_AQUI":
        print("[AVISO] Configure phone e callmebot_api_key no config.json antes de usar!")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Buscando preço atual...")
    try:
        preco_now = preco_atual()
    except Exception as e:
        print(f"[ERRO] Falha ao buscar preço atual: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  → Preço atual: {formatar_brl(preco_now)}")

    alertas_enviados = []

    for periodo in PERIODOS:
        horas       = HORAS[periodo]
        threshold   = cfg["thresholds"][periodo]
        cooldown_h  = cfg["cooldown_horas"][periodo]

        if em_cooldown(estado, periodo, cooldown_h):
            print(f"  [{periodo}] Em cooldown, pulando.")
            continue

        print(f"  [{periodo}] Buscando preço de {horas}h atrás...")
        try:
            preco_passado = preco_ha_n_horas(horas, janela)
        except Exception as e:
            print(f"  [{periodo}] ERRO: {e}", file=sys.stderr)
            continue

        if preco_passado is None:
            print(f"  [{periodo}] Sem dados históricos disponíveis.")
            continue

        variacao = ((preco_now - preco_passado) / preco_passado) * 100
        print(f"  [{periodo}] Preço há {horas}h: {formatar_brl(preco_passado)} → variação: {variacao:+.2f}%")

        if abs(variacao) >= threshold:
            print(f"  [{periodo}] ⚡ Threshold {threshold}% atingido! Enviando alerta...")
            humor = escolher_mensagem(variacao, periodo)
            msg   = montar_mensagem(humor, preco_now, variacao, periodo)

            sucesso = enviar_whatsapp(phone, api_key, msg)
            if sucesso:
                print(f"  [{periodo}] ✓ Mensagem enviada!")
                estado[periodo] = datetime.now().isoformat()
                salvar_estado(estado)
                alertas_enviados.append(periodo)
                time.sleep(2)  # pausa entre mensagens
            else:
                print(f"  [{periodo}] ✗ Falha no envio.")
        else:
            print(f"  [{periodo}] Variação {variacao:+.2f}% abaixo do threshold {threshold}%. Sem alerta.")

    if not alertas_enviados:
        print("Nenhum alerta disparado nesta verificação.")
    else:
        print(f"Alertas enviados: {', '.join(alertas_enviados)}")

# ─── Modo de teste ────────────────────────────────────────────────────────────

def testar_mensagem():
    """Envia uma mensagem de teste para confirmar que o WhatsApp está configurado."""
    cfg = carregar_config()
    phone   = cfg["whatsapp"]["phone"]
    api_key = cfg["whatsapp"]["callmebot_api_key"]

    preco_now = preco_atual()
    msg = (
        f"✅ *Alerta de Bitcoin configurado com sucesso!*\n\n"
        f"💰 Preço atual do BTC: *{formatar_brl(preco_now)}*\n"
        f"🎯 Thresholds configurados:\n"
        + "\n".join(f"  • {p}: ≥{cfg['thresholds'][p]}%" for p in PERIODOS)
        + f"\n\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    print("Enviando mensagem de teste...")
    sucesso = enviar_whatsapp(phone, api_key, msg)
    print("✓ Mensagem enviada!" if sucesso else "✗ Falha no envio. Verifique phone e api_key.")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        testar_mensagem()
    else:
        verificar_alertas()
