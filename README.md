# Guarani Watch Bot

Revisa cada 3 horas el Guarani de Economicas-UNICEN y te manda un email
cuando aparece una materia optativa o actividad de libre eleccion nueva
que no estaba la vez anterior.

## Como funciona

`scraper.py` usa Playwright (un navegador sin interfaz) para:
1. Iniciar sesion con tu usuario y contrasena de Guarani.
2. Pararse en "Inscripcion a Materias" y, para cada "propuesta" vigilada
   (por defecto: `Actividades optativas - lgt plan 50` y
   `Actividades de libre eleccion - plan 50`), leer el listado completo.
3. Comparar ese listado contra el guardado la ultima vez (`state.json`).
4. Si hay algo nuevo, enviarte un email. Si es la primera corrida, solo
   guarda la base sin avisar (para no mandarte todo el catalogo actual
   como "nuevo").

El workflow de GitHub Actions (`.github/workflows/watch.yml`) ejecuta el
script cada 3 horas y commitea el `state.json` actualizado al repo, asi el
proximo run recuerda que ya vio.

## Puesta en marcha

### 1. Crear el repositorio

Subi esta carpeta a un repo de GitHub (puede ser privado, de hecho
conviene que lo sea ya que el workflow va a tocar tu propio repo).

```bash
cd guarani-bot
git init
git add .
git commit -m "Bot de aviso de Guarani"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/guarani-bot.git
git push -u origin main
```

### 2. Generar una contrasena de aplicacion de Gmail

Gmail no deja usar tu contrasena normal desde un script. Hay que crear una
"contrasena de aplicacion":

1. Activa la verificacion en dos pasos en tu cuenta de Google (si no la
   tenes ya): https://myaccount.google.com/security
2. Anda a https://myaccount.google.com/apppasswords
3. Creá una contraseña de aplicación (nombre "guarani-bot" por ejemplo).
   Google te da un codigo de 16 letras: eso es lo que va en
   `GMAIL_APP_PASSWORD`, no tu contrasena real de Gmail.

### 3. Cargar los "Secrets" en GitHub

En el repo: **Settings → Secrets and variables → Actions → New repository
secret**. Cargá estos cinco:

| Secret               | Valor                                              |
|----------------------|-----------------------------------------------------|
| `GUARANI_USER`       | tu usuario de Guarani                               |
| `GUARANI_PASS`       | tu contraseña de Guarani                            |
| `GMAIL_USER`         | tu direccion de Gmail (la que envia el mail)        |
| `GMAIL_APP_PASSWORD` | la contraseña de aplicacion de 16 letras del paso 2 |
| `NOTIFY_EMAIL`       | (opcional) a donde llega el aviso, si no la pones se manda a `GMAIL_USER` mismo |

Nunca pongas estos valores directamente en el codigo ni en el repo: solo
en Secrets, que GitHub encripta y no muestra en los logs.

### 4. Probarlo manualmente

En el repo: pestaña **Actions → Guarani Watch → Run workflow**. Se ejecuta
al toque, sin esperar las 3 horas. Mirá los logs: la primera vez va a
decir "sin novedades" porque esta guardando la base, aunque haya materias.
Si algo falla (login, o no encuentra el desplegable de propuestas), el
job sube una captura de pantalla (`debug-screenshots`) como artifact para
que la revisemos juntos.

### 5. Ajustar la frecuencia (opcional)

La linea `cron: "0 */3 * * *"` en `watch.yml` corre el chequeo cada 3
horas (en hora UTC). Se puede cambiar, por ejemplo a cada hora:
`"0 * * * *"`.

## Notas

- Si la facultad cambia el diseño de la pagina de Guarani, el scraper
  puede dejar de funcionar. El bot te va a avisar por email si detecta
  un error en vez de quedarse callado.
- Las "propuestas" vigiladas se pueden ajustar sin tocar el codigo,
  agregando un secret `PROPUESTAS` con los nombres exactos separados por
  `|`, por ejemplo:
  `Actividades optativas - lgt plan 50|Actividades de libre eleccion - plan 50`
