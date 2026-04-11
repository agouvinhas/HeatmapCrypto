# Alerta de Bitcoin no WhatsApp 🚀📉

Monitora o BTC/BRL no Mercado Bitcoin e te manda mensagem no WhatsApp com humor,
toda vez que a variação superar o threshold configurado.

---

## 1. Configurar o CallMeBot (WhatsApp gratuito)

O CallMeBot permite enviar mensagens no seu próprio WhatsApp via API, sem custo.

1. Adicione o número **+34 644 60 49 48** nos seus contatos (nome sugerido: "CallMeBot")
2. Envie a seguinte mensagem para esse contato no WhatsApp:
   ```
   I allow callmebot to send me messages
   ```
3. Em alguns segundos você receberá uma mensagem com seu **API Key** (ex: `123456`)
4. Guarde esse key — você vai precisar no próximo passo

---

## 2. Editar o config.json

Abra o arquivo `config.json` e preencha:

```json
{
  "whatsapp": {
    "phone": "+5511987654321",        ← seu número com DDI e DDD
    "callmebot_api_key": "123456"     ← API key recebido no WhatsApp
  },
  "thresholds": {
    "3h":  2.0,    ← alerta se variar ≥ 2% nas últimas 3h
    "6h":  3.5,    ← alerta se variar ≥ 3.5% nas últimas 6h
    "12h": 5.0,
    "24h": 8.0
  },
  "cooldown_horas": {
    "3h":  1.0,    ← mínimo 1h entre alertas do período de 3h
    "6h":  2.0,
    "12h": 4.0,
    "24h": 6.0
  }
}
```

---

## 3. Testar

```bash
python3 btc_alert.py --test
```

Você deve receber uma mensagem de confirmação no WhatsApp com o preço atual.

---

## 4. Agendar com cron (verificar a cada 5 minutos)

Abra o crontab:
```bash
crontab -e
```

Adicione a linha (substitua o caminho pelo seu):
```
*/5 * * * * /usr/bin/python3 /Users/agouvinhas/Claud_test/btc_alert.py >> /Users/agouvinhas/Claud_test/btc_alert.log 2>&1
```

Para verificar se está agendado:
```bash
crontab -l
```

Para ver o log:
```bash
tail -f /Users/agouvinhas/Claud_test/btc_alert.log
```

---

## Exemplos de mensagens que você vai receber

**Alta grande (+8% em 24h):**
> 🚀🚀🚀 DECOLA! Bitcoin disparou +8.4% em 24h! Hora de ligar pro seu cunhado que disse que era golpe!
> 💰 Preço atual: R$ 365.000,00
> 📊 Variação 24h: +8.42%
> ⏰ 09/04/2026 14:23

**Queda moderada (-4.5% em 6h):**
> 📉 Turbulência! Bitcoin caiu 4.5% em 6h. Buy the dip? Você decide, eu só informo.
> 💰 Preço atual: R$ 338.000,00
> 📊 Variação 6h: -4.52%
> ⏰ 09/04/2026 09:11

---

## Ajustes finos

| Parâmetro | O que faz |
|---|---|
| `thresholds` | Sensibilidade dos alertas — aumente para só alertar em movimentos grandes |
| `cooldown_horas` | Evita spam — diminua se quiser alertas mais frequentes |
| `janela_historico_minutos` | Aumente (ex: 20) se houver erros ao buscar preço histórico |

---

## Arquivos

| Arquivo | Descrição |
|---|---|
| `btc_alert.py` | Script principal |
| `config.json` | Suas configurações |
| `.alert_state.json` | Controle de cooldown (auto-gerado) |
| `btc_alert.log` | Log do cron (auto-gerado) |
