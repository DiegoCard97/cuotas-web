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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            cuadro TEXT DEFAULT 'SCOUT',
            activo BOOLEAN DEFAULT TRUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cuotas (
            mes TEXT PRIMARY KEY,
            monto INTEGER NOT NULL
        )
    """)

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

    cur.execute("""
        SELECT id, nombre, cuadro
        FROM personas
        WHERE activo = TRUE
        ORDER BY cuadro, nombre
    """)
    personas = cur.fetchall()

    cur.execute("SELECT persona_id, mes FROM pagos")
    pagos_por_persona = {}
    for persona_id, mes in cur.fetchall():
        pagos_por_persona.setdefault(persona_id, set()).add(mes)

    cuadros = {"MANADA": [], "SCOUT": [], "RAIDER": [], "ROVER": []}

    for pid, nombre, cuadro in personas:
        estado = {mes: mes in pagos_por_persona.get(pid, set()) for mes in MESES}
        cuadros.setdefault(cuadro, []).append({
            "id": pid,
            "nombre": nombre,
            "cuadro": cuadro,
            "meses": estado
        })

    cur.execute("""
        SELECT pagos.id, personas.nombre, pagos.mes, pagos.monto
        FROM pagos
        JOIN personas ON pagos.persona_id = personas.id
        ORDER BY pagos.fecha DESC
    """)
    pagos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("panel.html", cuadros=cuadros, meses=MESES, pagos=pagos)

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
                INSERT INTO personas (nombre, cuadro, activo)
                VALUES (%s, %s, TRUE)
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

@app.route("/personas/editar/<int:persona_id>", methods=["GET", "POST"])
def editar_persona(persona_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
            UPDATE personas
            SET nombre = %s, cuadro = %s
            WHERE id = %s
        """, (request.form["nombre"], request.form["cuadro"], persona_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/personas")

    cur.execute("""
        SELECT id, nombre, cuadro
        FROM personas
        WHERE id = %s
    """, (persona_id,))
    persona = cur.fetchone()

    cur.close()
    conn.close()
    return render_template("persona_editar.html", persona=persona)

@app.route("/personas/desactivar/<int:persona_id>")
def desactivar_persona(persona_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE personas SET activo = FALSE WHERE id = %s", (persona_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/personas")

@app.route("/personas/reactivar/<int:persona_id>")
def reactivar_persona(persona_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE personas SET activo = TRUE WHERE id = %s", (persona_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/personas")

# ======================
# PAGOS
# ======================

@app.route("/pago", methods=["GET", "POST"])
def pago():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, nombre FROM personas WHERE activo = TRUE ORDER BY nombre")
    personas = cur.fetchall()

    cur.execute("SELECT mes, monto FROM cuotas ORDER BY mes")
    cuotas = cur.fetchall()

    if request.method == "POST":
        cur.execute("SELECT monto FROM cuotas WHERE mes = %s", (request.form["mes"],))
        cuota = cur.fetchone()

        cur.execute("""
            INSERT INTO pagos (persona_id, mes, monto, fecha)
            VALUES (%s, %s, %s, %s)
        """, (
            int(request.form["persona"]),
            request.form["mes"],
            cuota[0],
            datetime.now().strftime("%Y-%m-%d")
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/panel")

    cur.close()
    conn.close()
    return render_template("pago.html", personas=personas, cuotas=cuotas)

# ======================
# ADMINISTRAR PAGOS
# ======================

@app.route("/pagos")
def administrar_pagos():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT pagos.id, personas.nombre, pagos.mes, pagos.monto, pagos.fecha
        FROM pagos
        JOIN personas ON pagos.persona_id = personas.id
        ORDER BY pagos.fecha DESC
    """)
    pagos = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("pagos.html", pagos=pagos)

@app.route("/pagos/borrar/<int:pago_id>")
def borrar_pago(pago_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pagos WHERE id = %s", (pago_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/pagos")

# ======================
# RECIBO PDF
# ======================

@app.route("/recibo/<int:pago_id>")
def recibo(pago_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT personas.nombre, pagos.mes, pagos.monto, pagos.fecha
        FROM pagos
        JOIN personas ON pagos.persona_id = personas.id
        WHERE pagos.id = %s
    """, (pago_id,))
    pago = cur.fetchone()

    cur.close()
    conn.close()

    if not pago:
        return "Pago no encontrado"

    pdf = generar_recibo(*pago)
    return send_file(pdf, as_attachment=True,
                     download_name=f"recibo_{pago[0]}_{pago[1]}.pdf",
                     mimetype="application/pdf")

# ======================
# CUOTAS
# ======================

@app.route("/cuotas", methods=["GET", "POST"])
def cuotas():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
            UPDATE cuotas
            SET monto = %s
            WHERE mes = %s
        """, (int(request.form["monto"]), request.form["mes"]))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/cuotas")

    cur.execute("SELECT mes, monto FROM cuotas ORDER BY mes")
    cuotas = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("cuotas.html", cuotas=cuotas)
