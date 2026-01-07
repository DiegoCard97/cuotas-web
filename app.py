from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# ======================
# CONFIG
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
    "Secretaria": "scout"
}

# ======================
# BASE DE DATOS
# ======================

def init_db():
    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            persona_id INTEGER,
            mes TEXT,
            monto INTEGER,
            fecha TEXT,
            FOREIGN KEY (persona_id) REFERENCES personas(id)
        )
    """)

    conn.commit()
    conn.close()

def cargar_cuotas_iniciales():
    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    for mes in MESES:
        cur.execute(
            "INSERT OR IGNORE INTO cuotas (mes, monto) VALUES (?, ?)",
            (mes, 5000 if mes < "2026-07" else 6000)
        )

    conn.commit()
    conn.close()

init_db()
cargar_cuotas_iniciales()

# ======================
# UTILIDADES
# ======================

def generar_recibo(nombre, mes, monto):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    c.setFont("Helvetica", 12)
    c.drawString(50, 800, "RECIBO DE PAGO")
    c.drawString(50, 760, f"Nombre: {nombre}")
    c.drawString(50, 730, f"Mes: {mes}")
    c.drawString(50, 700, f"Monto: ${monto}")
    c.drawString(50, 670, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ======================
# RUTAS
# ======================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if USUARIOS.get(request.form["usuario"]) == request.form["password"]:
            session["user"] = request.form["usuario"]
            return redirect("/panel")
    return render_template("login.html")

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    cur.execute("SELECT id, nombre FROM personas")
    personas = cur.fetchall()

    datos = []
    for pid, nombre in personas:
        cur.execute("SELECT mes FROM pagos WHERE persona_id = ?", (pid,))
        pagos = {row[0] for row in cur.fetchall()}

        datos.append({
            "id": pid,
            "nombre": nombre,
            "meses": {mes: mes in pagos for mes in MESES}
        })

    cur.execute("""
        SELECT pagos.id, personas.nombre, pagos.mes, pagos.monto
        FROM pagos
        JOIN personas ON personas.id = pagos.persona_id
        ORDER BY pagos.fecha DESC
    """)
    pagos = cur.fetchall()

    conn.close()

    return render_template(
        "panel.html",
        datos=datos,
        meses=MESES,
        pagos=pagos
    )

@app.route("/pago", methods=["GET", "POST"])
def pago():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    cur.execute("SELECT id, nombre FROM personas")
    personas = cur.fetchall()

    cur.execute("SELECT mes, monto FROM cuotas")
    cuotas = cur.fetchall()

    if request.method == "POST":
        persona_id = request.form["persona"]
        mes = request.form["mes"]

        cur.execute("SELECT monto FROM cuotas WHERE mes = ?", (mes,))
        monto = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO pagos (persona_id, mes, monto, fecha)
            VALUES (?, ?, ?, ?)
        """, (persona_id, mes, monto, datetime.now().strftime("%Y-%m-%d")))

        conn.commit()
        conn.close()
        return redirect("/panel")

    conn.close()
    return render_template("pago.html", personas=personas, cuotas=cuotas)

@app.route("/recibo/<int:pago_id>")
def recibo(pago_id):
    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT personas.nombre, pagos.mes, pagos.monto
        FROM pagos
        JOIN personas ON personas.id = pagos.persona_id
        WHERE pagos.id = ?
    """, (pago_id,))
    fila = cur.fetchone()
    conn.close()

    if not fila:
        return "Recibo no encontrado"

    pdf = generar_recibo(*fila)
    return send_file(pdf, as_attachment=True,
                     download_name="recibo.pdf",
                     mimetype="application/pdf")

@app.route("/persona", methods=["GET", "POST"])
def persona():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        conn = sqlite3.connect("cuotas.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO personas (nombre) VALUES (?)", (request.form["nombre"],))
        conn.commit()
        conn.close()
        return redirect("/panel")

    return render_template("persona.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

















