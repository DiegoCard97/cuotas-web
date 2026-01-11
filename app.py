from flask import Flask, render_template, request, redirect, session, send_file
import os
import psycopg2
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ======================
# CONFIGURACIÓN
# ======================

app = Flask(__name__)
app.secret_key = "algo-secreto"

MESES = [
    "2026-01", "2026-02", "2026-03", "2026-04",
    "2026-05", "2026-06", "2026-07", "2026-08",
    "2026-09", "2026-10", "2026-11", "2026-12"
]

USUARIOS = {
    "admin": "1234",
    "Tesorero": "cuotas2025",
    "Secretaria": "scout",
    "Jenni": "LobaTenaz"
}

# ======================
# BASE DE DATOS
# ======================

def get_db_connection():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        sslmode="require"
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Personas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL
        )
    """)

    cur.execute("""
        ALTER TABLE personas
        ADD COLUMN IF NOT EXISTS cuadro TEXT DEFAULT 'SCOUT'
    """)

    cur.execute("""
        ALTER TABLE personas
        ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE
    """)

    # Cuotas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cuotas (
            mes TEXT PRIMARY KEY,
            monto INTEGER NOT NULL
        )
    """)

    # Pagos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            persona_id INTEGER NOT NULL,
            mes TEXT NOT NULL,
            monto INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            UNIQUE(persona_id, mes),
            FOREIGN KEY (persona_id) REFERENCES personas(id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

def cargar_cuotas_iniciales():
    conn = get_db_connection()
    cur = conn.cursor()

    cuotas = [
        ("2026-01", 5000), ("2026-02", 5000), ("2026-03", 5000),
        ("2026-04", 5000), ("2026-05", 5000), ("2026-06", 5000),
        ("2026-07", 6000), ("2026-08", 6000), ("2026-09", 6000),
        ("2026-10", 6000), ("2026-11", 6000), ("2026-12", 6000),
    ]

    for mes, monto in cuotas:
        cur.execute("""
            INSERT INTO cuotas (mes, monto)
            VALUES (%s, %s)
            ON CONFLICT (mes) DO NOTHING
        """, (mes, monto))

    conn.commit()
    cur.close()
    conn.close()

# ======================
# PDF
# ======================

def generar_recibo(nombre, mes, monto, fecha):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    _, alto = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, alto - 50, "RECIBO DE PAGO")

    c.setFont("Helvetica", 12)
    c.drawString(50, alto - 100, f"Nombre: {nombre}")
    c.drawString(50, alto - 130, f"Mes abonado: {mes}")
    c.drawString(50, alto - 160, f"Monto: ${monto}")
    c.drawString(50, alto - 190, f"Fecha de pago: {fecha}")

    c.drawString(50, alto - 260, "Firma: ___________________________")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

init_db()
cargar_cuotas_iniciales()

# ======================
# LOGIN
# ======================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["usuario"]
        password = request.form["password"]

        if user in USUARIOS and USUARIOS[user] == password:
            session["user"] = user
            return redirect("/panel")

        return render_template("login.html", error="Usuario o clave incorrectos")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ======================
# PANEL
# ======================

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    # Personas activas con su cuadro
    cur.execute("""
        SELECT id, nombre, cuadro
        FROM personas
        WHERE activo = TRUE
        ORDER BY cuadro, nombre
    """)
    personas = cur.fetchall()

    # Pagos registrados
    cur.execute("""
        SELECT persona_id, mes
        FROM pagos
    """)
    pagos_por_persona = {}
    for persona_id, mes in cur.fetchall():
        pagos_por_persona.setdefault(persona_id, set()).add(mes)

    # Estructura por cuadro
    panel_por_cuadro = {
        "MANADA": [],
        "SCOUT": [],
        "RAIDER": [],
        "ROVER": []
    }

    for pid, nombre, cuadro in personas:
        estado_meses = {}
        for mes in MESES:
            estado_meses[mes] = mes in pagos_por_persona.get(pid, set())

        persona_data = {
            "id": pid,
            "nombre": nombre,
            "meses": estado_meses
        }

        # Por las dudas, si viene algo raro en BD
        if cuadro not in panel_por_cuadro:
            cuadro = "SCOUT"

        panel_por_cuadro[cuadro].append(persona_data)

    cur.close()
    conn.close()

    return render_template(
        "panel.html",
        panel=panel_por_cuadro,
        meses=MESES
    )

# ======================
# PERSONAS
# ======================

@app.route("/personas", methods=["GET", "POST"])
def personas():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        cuadro = request.form.get("cuadro", "SCOUT")

        if nombre:
            cur.execute("""
                INSERT INTO personas (nombre, activo, cuadro)
                VALUES (%s, TRUE, %s)
            """, (nombre, cuadro))
            conn.commit()

        cur.close()
        conn.close()
        return redirect("/personas")

    cur.execute("""
        SELECT id, nombre, cuadro, activo
        FROM personas
        ORDER BY cuadro, nombre
    """)
    personas = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("personas.html", personas=personas)












































