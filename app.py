from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "algo-secreto"

# Usuarios de prueba
USUARIOS = {
    "admin": "1234",
    "Tesorero": "cuotas2025",
    "Secretaria": "scout"
}
PERSONAS = {
    1: "Juan Perez",
    2: "Maria Gomez",
    3: "Carlos Lopez"
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


# ======================
# FUNCIONES
# ======================

def calcular_saldo(persona_id):
    total_pagado = sum(
        p["monto"] for p in PAGOS if p["persona"] == persona_id
    )

    total_debido = 0
    for mes, valor in CUOTAS.items():
        total_debido += valor

    return total_debido - total_pagado

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

    datos = []
    for pid, nombre in PERSONAS.items():
        saldo = calcular_saldo(pid)
        datos.append({
            "nombre": nombre,
            "saldo": saldo
        })

    return render_template("panel.html", datos=datos)

@app.route("/pago", methods=["GET", "POST"])
def pago():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        persona_id = int(request.form["persona"])
        mes = request.form["mes"]
        monto = int(request.form["monto"])

        PAGOS.append({
            "persona": persona_id,
            "mes": mes,
            "monto": monto
        })

        return redirect("/panel")

    return render_template("pago.html", personas=PERSONAS)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()






