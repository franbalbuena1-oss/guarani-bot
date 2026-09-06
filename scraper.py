"""
Bot que revisa el Guarani de Economicas-UNICEN y avisa por email cuando
aparece una materia optativa o actividad de libre eleccion nueva.

Credenciales y config vienen SIEMPRE por variables de entorno (GitHub Secrets
en el workflow), nunca hardcodeadas aca.
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://guarani.unicen.edu.ar/autogestion/economicas"
CURSADA_URL = f"{BASE}/cursada"
STATE_PATH = Path(__file__).parent / "state.json"

# Las propuestas a vigilar. Se pueden sobreescribir con la variable de
# entorno PROPUESTAS separando por "|", por si cambian de plan/orientacion.
DEFAULT_PROPUESTAS = [
    "Actividades optativas - lgt plan 50",
    "Actividades de libre eleccion - plan 50",
]
PROPUESTAS = os.environ.get("PROPUESTAS", "|".join(DEFAULT_PROPUESTAS)).split("|")

GUARANI_USER = os.environ["GUARANI_USER"].strip()
GUARANI_PASS = os.environ["GUARANI_PASS"].strip()
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


def login(page):
    response = page.goto(CURSADA_URL)
    print(f"GET {CURSADA_URL} -> status {response.status if response else '?'}", flush=True)
    page.wait_for_selector("#usuario", timeout=15000)
    page.fill("#usuario", GUARANI_USER)
    page.fill("#password", GUARANI_PASS)

    with page.expect_navigation(wait_until="networkidle", timeout=20000):
        page.click("#login")

    print(f"URL despues del submit: {page.url}", flush=True)

    body_text = page.locator("body").inner_text()
    for linea in body_text.splitlines():
        linea = linea.strip()
        if linea and any(
            palabra in linea.lower()
            for palabra in ["incorrect", "error", "invalid", "bloque", "captcha", "intento"]
        ):
            print(f"Texto sospechoso en la pagina: {linea}", flush=True)

    if page.locator("#lista_materias").count() == 0 and page.locator("#usuario").count() > 0:
        page.screenshot(path="debug_login.png", full_page=True)
        raise RuntimeError(
            "No se pudo iniciar sesion en Guarani (usuario/contrasena "
            "incorrectos o el sitio cambio). Ver debug_login.png"
        )


def select_propuesta(page, nombre):
    toggle = page.locator(".dropdown-toggle").filter(has_text="plan 50")
    if toggle.count() == 0:
        toggle = page.locator("button, a").filter(has_text="plan 50")
    toggle.first.click()

    link = page.get_by_role("link", name=nombre, exact=True)
    if link.count() == 0:
        link = page.get_by_text(nombre, exact=True)
    link.first.click()

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(700)


def scrape_lista_materias(page):
    page.wait_for_selector("#js-listado-materias", timeout=15000)
    items = page.locator("#js-listado-materias ul.nav-list li a")
    result = {}
    for i in range(items.count()):
        a = items.nth(i)
        href = a.get_attribute("href") or ""
        title = a.get_attribute("title") or a.inner_text().strip()
        key = href.rstrip("/").split("/")[-1] or title
        result[key] = title
    return result


def main():
    state = load_state()
    current_by_propuesta = {}
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            login(page)
        except Exception as e:
            print(f"ERROR al iniciar sesion: {e}", flush=True)
            browser.close()
            send_email(
                "[Guarani Bot] Error al iniciar sesion",
                f"El bot no pudo iniciar sesion en Guarani.\n\nDetalle: {e}",
            )
            sys.exit(1)

        for propuesta in PROPUESTAS:
            try:
                select_propuesta(page, propuesta)
                current_by_propuesta[propuesta] = scrape_lista_materias(page)
            except Exception as e:
                print(f"ERROR revisando '{propuesta}': {e}", flush=True)
                safe_name = "".join(c if c.isalnum() else "_" for c in propuesta)
                page.screenshot(path=f"debug_{safe_name}.png")
                errors.append(f"- {propuesta}: {e}")

        browser.close()

    new_by_propuesta = {}
    for propuesta, current in current_by_propuesta.items():
        previous = state.get(propuesta)
        if previous is not None:
            new_keys = set(current) - set(previous)
            if new_keys:
                new_by_propuesta[propuesta] = {k: current[k] for k in new_keys}
        state[propuesta] = current

    save_state(state)

    if new_by_propuesta:
        lines = []
        for propuesta, items in new_by_propuesta.items():
            lines.append(f"\n{propuesta}:")
            for title in items.values():
                lines.append(f"  - {title}")
        body = "Se publicaron nuevas materias/actividades en Guarani:\n" + "\n".join(lines)
        send_email("[Guarani Bot] Nueva oferta disponible", body)
        print(body)
    else:
        print("Sin novedades.")

    if errors:
        send_email(
            "[Guarani Bot] Error revisando algunas propuestas",
            "No se pudo revisar:\n" + "\n".join(errors),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
