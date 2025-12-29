from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "clave_secreta_simple"

# Usuarios de prueba
USUARIOS = {
    "admin": "1234",
    "juan": "abcd",
    "ana": "9999"
}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario in USUARIOS and USUARIOS[usuario] == password:
            session["usuario"] = usuario
            return redirect("/panel")
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")

@app.route("/panel")
def panel():
    if "usuario" not in session:
        return redirect("/")
    return render_template("panel.html", usuario=session["usuario"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()
