from flask import Flask, render_template, request, redirect, session
import sqlite3
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from flask import send_file

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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT UNIQUE NOT NULL,
            monto INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = "algo-secreto"

init_db()

# Usuarios de prueba
USUARIOS = {
    "admin": "1234",
    "Tesorero": "cuotas2025",
    "Secretaria": "scout"
}


CUOTAS = {
    "2026-01": 4000,
    "2026-07": 5000
}

PAGOS = [
    {"persona": 1, "mes": "2026-01", "monto": 4000},
    {"persona": 1, "mes": "2026-02", "monto": 4000},
    {"persona": 2, "mes": "2026-01", "monto": 4000},
]

MESES = [
    "2026-01", "2026-02", "2026-03", "2026-04",
    "2026-05", "2026-06", "2026-07", "2026-08",
    "2026-09", "2026-10", "2026-11", "2026-12"
]
# ======================
# FUNCIONES
# ======================

def obtener_personas():
    conn = sqlite3.connect("cuotas.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, nombre FROM personas")
    personas = cur.fetchall()

    conn.close()
    return personas

def calcular_saldo(persona_id):
    total_pagado = sum(
        p["monto"] for p in PAGOS if p["persona"] == persona_id
    )

    total_debido = 0
    for mes, valor in CUOTAS.items():
        total_debido += valor

    return total_debido - total_pagado

def generar_recibo(nombre, mes, monto):
    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4

    c.setFont("Helvetica", 12)

    c.drawString(50, alto - 50, "RECIBO DE PAGO")
    c.line(50, alto - 55, 400, alto - 55)

    c.drawString(50, alto - 100, f"Nombre: {nombre}")
    c.drawString(50, alto - 130, f"Mes abonado: {mes}")
    c.drawString(50, alto - 160, f"Monto: ${monto}")
    c.drawString(50, alto - 190, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")

    c.drawString(50, alto - 250, "Firma: ___________________________")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer

def cargar_cuotas_base():
    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    for mes in MESES:
        cur.execute(
            "INSERT OR IGNORE INTO cuotas (mes, monto) VALUES (?, ?)",
            (mes, 4000)
        )

    conn.commit()
    conn.close()

def cargar_cuotas_base():
    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    for mes in MESES:
        cur.execute(
            "INSERT OR IGNORE INTO cuotas (mes, monto) VALUES (?, ?)",
            (mes, 4000)
        )

    conn.commit()
    conn.close()

init_db()
cargar_cuotas_base()
# ======================
# RUTAS
# ======================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print("LLEGO POST")
        print(request.form)

        user = request.form.get("usuario")
        password = request.form.get("password")

        if user in USUARIOS and USUARIOS[user] == password:
            session["user"] = user
            return redirect("/panel")
        else:
            return render_template("login.html", error="Usuario o clave incorrectos")

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
        cur.execute(
            "SELECT mes FROM pagos WHERE persona_id = ?",
            (pid,)
        )
        pagos_persona = [row[0] for row in cur.fetchall()]

        estado_meses = {}
        for mes in MESES:
            estado_meses[mes] = mes in pagos_persona

        datos.append({
            "id": pid,
            "nombre": nombre,
            "meses": estado_meses
        })

    cur.execute("""
        SELECT persona_id, mes, monto
        FROM pagos
        ORDER BY persona_id, mes
    """)
    pagos = cur.fetchall()

    conn.close()

    return render_template(
        "panel.html",
        datos=datos,
        meses=MESES,
        pagos=pagos
    )

    return render_template(
        "panel.html",
        datos=datos,
        meses=MESES
    )
    
@app.route("/pago", methods=["GET", "POST"])
def pago():
    personas = obtener_personas()

    if request.method == "POST":
        persona_id = int(request.form["persona"])
        mes = request.form["mes"]
        monto = CUOTAS.get(mes)

        if monto is None:
            return "Ese mes no tiene cuota definida"

        registrar_pago(persona_id, mes, monto)
        return redirect("/panel")

    return render_template(
        "pago.html",
        personas=personas,
        meses=MESES
    )

@app.route("/recibo/<int:pago_id>")
def recibo(pago_id):
    if pago_id < 0 or pago_id >= len(PAGOS):
        return "Pago no encontrado"

    pago = PAGOS[pago_id]

    nombre = PERSONAS[pago["persona"]]
    mes = pago["mes"]
    monto = pago["monto"]

    pdf = generar_recibo(nombre, mes, monto)

    return send_file(
        pdf,
        as_attachment=True,
        download_name=f"recibo_{nombre}_{mes}.pdf",
        mimetype="application/pdf"
    )

@app.route("/persona", methods=["GET", "POST"])
def persona():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        nombre = request.form["nombre"]

        conn = sqlite3.connect("cuotas.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO personas (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()

        return redirect("/panel")

    return render_template("persona.html")

@app.route("/pagar/<int:persona_id>/<mes>")
def pagar(persona_id, mes):
    if "user" not in session:
        return redirect("/")

    # 1. Verificar que el mes tenga cuota
    if mes not in CUOTAS:
        return "Ese mes no tiene cuota definida"

    monto = CUOTAS[mes]

    # 2. Evitar pagar dos veces el mismo mes
    for p in PAGOS:
        if p["persona"] == persona_id and p["mes"] == mes:
            return "Ese mes ya está pago"

    # 3. Registrar el pago
    PAGOS.append({
        "persona": persona_id,
        "mes": mes,
        "monto": monto
    })

    # 4. Volver al panel
    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()


















