from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

# ======================
# CONFIGURACIÓN
# ======================

app = Flask(__name__)
app.secret_key = "algo-secreto"

DB_NAME = "cuotas.db"

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

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
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
            persona_id INTEGER NOT NULL,
            mes TEXT NOT NULL,
            monto INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            UNIQUE(persona_id, mes),
            FOREIGN KEY (persona_id) REFERENCES personas(id)
        )
    """)

    conn.commit()
    conn.close()

def cargar_cuotas_iniciales():
    conn = get_db()
    cur = conn.cursor()

    cuotas = [
        ("2026-01", 5000), ("2026-02", 5000), ("2026-03", 5000),
        ("2026-04", 5000), ("2026-05", 5000), ("2026-06", 5000),
        ("2026-07", 6000), ("2026-08", 6000), ("2026-09", 6000),
        ("2026-10", 6000), ("2026-11", 6000), ("2026-12", 6000),
    ]

    for mes, monto in cuotas:
        cur.execute(
            "INSERT OR IGNORE INTO cuotas (mes, monto) VALUES (?, ?)",
            (mes, monto)
        )

    conn.commit()
    conn.close()
def generar_recibo(nombre, mes, monto, fecha):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4

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
        user = request.form.get("usuario")
        password = request.form.get("password")

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
# PANEL PRINCIPAL
# ======================

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # Personas
    cur.execute("SELECT id, nombre FROM personas")
    personas = cur.fetchall()

    # Pagos
    cur.execute("""
    SELECT 
        pagos.id,
        personas.nombre,
        pagos.mes,
        pagos.monto
    FROM pagos
    JOIN personas ON pagos.persona_id = personas.id
    ORDER BY pagos.fecha DESC
""")
pagos = cur.fetchall()

    pagos_por_persona = {}
    for pid, mes in pagos:
        pagos_por_persona.setdefault(pid, set()).add(mes)

    datos = []
    for pid, nombre in personas:
        estado = {}
        for mes in MESES:
            estado[mes] = mes in pagos_por_persona.get(pid, set())

        datos.append({
            "id": pid,
            "nombre": nombre,
            "meses": estado
        })

    pagos = [
    {
        "id": 1,
        "nombre": "Juan Pérez",
        "mes": "2026-01",
        "monto": 5000
    }
]

    conn.close()

    return render_template(
        "panel.html",
        datos=datos,
        meses=MESES,
        pagos=pagos
    )

# ======================
# PERSONAS
# ======================

@app.route("/persona", methods=["GET", "POST"])
def persona():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        nombre = request.form["nombre"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO personas (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()

        return redirect("/panel")

    return render_template("persona.html")

# ======================
# REGISTRAR PAGO
# ======================

@app.route("/pago", methods=["GET", "POST"])
def pago():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, nombre FROM personas")
    personas = cur.fetchall()

    cur.execute("SELECT mes, monto FROM cuotas ORDER BY mes")
    cuotas = cur.fetchall()

    if request.method == "POST":
        persona_id = int(request.form["persona"])
        mes = request.form["mes"]

        cur.execute("SELECT monto FROM cuotas WHERE mes = ?", (mes,))
        cuota = cur.fetchone()

        if not cuota:
            conn.close()
            return "Ese mes no tiene cuota definida"

        try:
            cur.execute("""
                INSERT INTO pagos (persona_id, mes, monto, fecha)
                VALUES (?, ?, ?, ?)
            """, (
                persona_id,
                mes,
                cuota[0],
                datetime.now().strftime("%Y-%m-%d")
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Ese mes ya está pago"

        conn.close()
        return redirect("/panel")

    conn.close()
    return render_template(
        "pago.html",
        personas=personas,
        cuotas=cuotas
    )
    
@app.route("/recibo/<int:pago_id>")
def recibo(pago_id):
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("cuotas.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT personas.nombre, pagos.mes, pagos.monto
        FROM pagos
        JOIN personas ON pagos.persona_id = personas.id
        WHERE pagos.id = ?
    """, (pago_id,))

    pago = cur.fetchone()
    conn.close()

    if not pago:
        return "Pago no encontrado"

    nombre, mes, monto = pago

    pdf = generar_recibo(nombre, mes, monto)

    return send_file(
        pdf,
        as_attachment=True,
        download_name=f"recibo_{nombre}_{mes}.pdf",
        mimetype="application/pdf"
    )
# ======================
# MAIN
# ======================

if __name__ == "__main__":
    app.run(debug=True)












