from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "casafood"

def get_db():
    return sqlite3.connect("casafood.db")


@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            (usuario,senha)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["usuario"] = usuario
            return redirect("/estoque")

    return render_template("login.html")


@app.route("/estoque")
def estoque():

    if "usuario" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM estoque")
    itens = cur.fetchall()

    conn.close()

    return render_template("estoque.html", itens=itens)


@app.route("/add", methods=["POST"])
def add():

    if "usuario" not in session:
        return redirect("/")

    nome = request.form["nome"]
    quantidade = request.form["quantidade"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO estoque (nome,quantidade) VALUES (?,?)",
        (nome,quantidade)
    )

    conn.commit()
    conn.close()

    return redirect("/estoque")


@app.route("/delete/<int:id>")
def delete(id):

    if "usuario" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM estoque WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/estoque")


@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
