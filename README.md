# Guarani Watch Bot

Revisa cada 10 minutos la cartelera publica de Optativas y ALE de
Economicas-UNICEN y te manda un email cuando aparece una oferta nueva
que no estaba la vez anterior.

Fuente: https://econ.unicen.edu.ar/alumnos/ale/ofertas-ale-y-optativas
(pagina publica, no requiere usuario ni contraseña de Guarani).

## Como funciona

`scraper.py`:
1. Pide esa pagina publica con un simple `requests.get`.
2. Extrae cada tarjeta de oferta (codigo, titulo, tipo: Optativa o ALE).
3. Compara ese listado contra el guardado la ultima vez (`state.json`).
4. Si hay algo nuevo, te manda un email. Si es la primera corrida, solo
   guarda la base sin avisar (para no mandarte todo el catalogo actual
   como "nuevo").

El workflow de GitHub Actions (`.github/workflows/watch.yml`) ejecuta el
script cada 10 minutos y commitea el `state.json` actualizado al repo.

Como es una pagina publica, no hace falta Playwright ni un navegador: el
chequeo es liviano (unos segundos) y no depende de tu usuario/contraseña
de Guarani ni de que tu PC este prendida.

## Puesta en marcha

### 1. Generar una contrasena de aplicacion de Gmail

Gmail no deja usar tu contrasena normal desde un script. Hay que crear una
"contrasena de aplicacion":

1. Activa la verificacion en dos pasos en tu cuenta de Google (si no la
   tenes ya): https://myaccount.google.com/security
2. Anda a https://myaccount.google.com/apppasswords
3. Creá una contraseña de aplicación (nombre "guarani-bot" por ejemplo).
   Google te da un codigo de 16 letras: eso es lo que va en
   `GMAIL_APP_PASSWORD`, no tu contrasena real de Gmail.

### 2. Cargar los Secrets en GitHub

En el repo: **Settings → Secrets and variables → Actions → New repository
secret**. Cargá estos tres:

| Secret               | Valor                                              |
|----------------------|-----------------------------------------------------|
| `GMAIL_USER`         | tu direccion de Gmail (la que envia el mail)        |
| `GMAIL_APP_PASSWORD` | la contraseña de aplicacion de 16 letras del paso 1 |
| `NOTIFY_EMAIL`       | (opcional) a donde llega el aviso, si no la pones se manda a `GMAIL_USER` mismo |

### 3. Probarlo manualmente

En el repo: pestaña **Actions → Guarani Watch → Run workflow**. La
primera vez va a decir "Primera corrida: guardando base sin avisar",
aunque haya ofertas. A partir de la segunda corrida, si aparece algo
nuevo, te llega el email.

### 4. Ajustar la frecuencia (opcional)

La linea `cron: "*/10 * * * *"` en `watch.yml` corre el chequeo cada 10
minutos. Se puede cambiar, por ejemplo a cada 30 minutos: `"*/30 * * * *"`.

## Notas

- Si la facultad cambia el diseño de esa pagina, el scraper puede dejar
  de encontrar las tarjetas y el workflow va a fallar (revisá los logs
  de Actions). Al ser HTML simple sin JavaScript pesado, es poco
  probable que cambie seguido.
- Este bot **no** usa tu usuario ni contraseña de Guarani: solo lee la
  pagina publica de la facultad.
