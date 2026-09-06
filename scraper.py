"""
Bot que revisa la cartelera publica de Optativas y ALE de Economicas-UNICEN
y avisa por email cuando aparece una oferta nueva.

Esta pagina es publica (no requiere login), asi que no hace falta ninguna
credencial de Guarani: https://econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas
"""

import json
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas"
STATE_PATH = Path(__file__).parent / "state.json"

GMAIL_USER = os.environ["GMAIL_USER"].strip()
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].strip().replace(" ", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", GMAIL_USER).strip()


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_USER, [NOTIFY_EMAIL], msg.as_string())


def scrape_ofertas():
    resp = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; guarani-watch-bot/1.0)"},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = soup.select("#views-bootstrap-ofertas-ale-y-optativas-page-1 > li")
    ofertas = {}
    for li in items:
        header = li.select_one(".card-header")
        if not header:
            continue
        codigo = header.select_one("h3")
        titulo = header.select_one("h2")
        categoria = header.select_one(".badge")
        codigo = codigo.get_text(strip=True) if codigo else None
        titulo = titulo.get_text(strip=True) if titulo else ""
        categoria = categoria.get_text(strip=True) if categoria else ""
        if not codigo:
            continue
        ofertas[codigo] = f"{codigo} - {titulo} ({categoria})"
    return ofertas


def main():
    state = load_state()
    previous = state.get("ofertas")

    current = scrape_ofertas()
    print(f"Ofertas encontradas: {len(current)}", flush=True)

    if previous is not None:
        new_keys = set(current) - set(previous)
        if new_keys:
            lines = [current[k] for k in new_keys]
            body = "Nuevas ofertas de ALE / Optativas:\n\n" + "\n".join(f"- {l}" for l in lines)
            body += f"\n\nVer la pagina completa: {URL}"
            send_email("[Guarani Bot] Nueva oferta disponible", body)
            print(body, flush=True)
        else:
            print("Sin novedades.", flush=True)
    else:
        print("Primera corrida: guardando base sin avisar.", flush=True)

    state["ofertas"] = current
    save_state(state)


if __name__ == "__main__":
    main()
