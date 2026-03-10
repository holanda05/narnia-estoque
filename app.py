from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "casafood"

DB_NAME = "casafood.db"


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            quantidade_minima INTEGER NOT NULL DEFAULT 1,
            categoria TEXT NOT NULL,
            observacao TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            categoria TEXT NOT NULL,
            observacao TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS codigos (
            codigo TEXT PRIMARY KEY,
            nome TEXT
        )
    """)

    # cria usuário padrão
    cur.execute("SELECT * FROM usuarios WHERE usuario=?", ("admin",))
    user = cur.fetchone()

    if not user:
        cur.execute(
            "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)",
            ("admin", "1234")
        )

    conn.commit()
    conn.close()


@app.route("/buscar_barcode/<codigo>")
def buscar_barcode(codigo):
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json"
        r = requests.get(url, timeout=5)
        data = r.json()

        if data["status"] == 1:
            produto = data["product"]
            nome = produto.get("product_name", codigo)
        else:
            nome = codigo
    except:
        nome = codigo

    return {"nome": nome}


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        senha = request.form["senha"].strip()

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            (usuario, senha)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = usuario
            return redirect("/estoque")

        flash("Usuário ou senha inválidos.")

    return render_template("login.html")


@app.route("/estoque")
def estoque():
    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM estoque ORDER BY categoria, nome")

    itens = cur.fetchall()
    conn.close()

    geladeira = [i for i in itens if i["categoria"] == "Geladeira"]
    freezer = [i for i in itens if i["categoria"] == "Freezer"]
    despensa = [i for i in itens if i["categoria"] == "Despensa"]

    return render_template(
        "estoque.html",
        geladeira=geladeira,
        freezer=freezer,
        despensa=despensa
    )


@app.route("/compras")
def compras():
    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM compras ORDER BY nome")
    itens = cur.fetchall()

    conn.close()

    return render_template("compras.html", itens=itens)


@app.route("/add", methods=["POST"])
def add():
    if "user" not in session:
        return redirect("/")

    nome = request.form["nome"].strip()
    quantidade = request.form["quantidade"].strip()
    categoria = request.form["categoria"].strip()

    if not nome or not quantidade:
        flash("Preencha nome e quantidade.")
        return redirect("/estoque")

    quantidade = int(quantidade)

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO estoque (nome, quantidade, categoria)
        VALUES (?, ?, ?)
    """, (nome, quantidade, categoria))

    conn.commit()
    conn.close()

    flash("Item adicionado com sucesso.")
    return redirect("/estoque")


@app.route("/menos/<int:id>")
def menos(id):
    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nome, quantidade, categoria
        FROM estoque
        WHERE id=?
    """, (id,))
    item = cur.fetchone()

    if not item:
        conn.close()
        return redirect("/estoque")

    nova_qtd = item["quantidade"] - 1

    if nova_qtd <= 0:
        cur.execute("DELETE FROM estoque WHERE id=?", (id,))
        nova_qtd = 0
    else:
        cur.execute("UPDATE estoque SET quantidade=? WHERE id=?", (nova_qtd, id))

    # envia para lista de compras automaticamente
    if nova_qtd <= 1:

        cur.execute("SELECT id FROM compras WHERE nome=?", (item["nome"],))
        existe = cur.fetchone()

        if not existe:
            cur.execute("""
                INSERT INTO compras (nome, quantidade, categoria)
                VALUES (?, ?, ?)
            """, (item["nome"], 1, item["categoria"]))

    conn.commit()
    conn.close()

    return redirect("/estoque")


@app.route("/mais/<int:id>")
def mais(id):
    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE estoque SET quantidade = quantidade + 1 WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/estoque")


@app.route("/delete/<int:id>")
def delete(id):
    if "user" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()

    cur.execute("DELETE FROM estoque WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("Item removido.")
    return redirect("/estoque")


@app.route("/comprado/<int:id>", methods=["POST"])
def comprado(id):

    if "user" not in session:
        return redirect("/")

    quantidade = request.form.get("quantidade", "").strip()

    if not quantidade:
        quantidade = "1"

    quantidade = int(quantidade)

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT nome, categoria FROM compras WHERE id=?", (id,))
    item = cur.fetchone()

    if item:

        cur.execute("SELECT id FROM estoque WHERE nome=?", (item["nome"],))
        existe = cur.fetchone()

        if existe:

            cur.execute("""
                UPDATE estoque
                SET quantidade = quantidade + ?
                WHERE id=?
            """, (quantidade, existe["id"]))

        else:

            cur.execute("""
                INSERT INTO estoque (nome, quantidade, categoria)
                VALUES (?, ?, ?)
            """, (item["nome"], quantidade, item["categoria"]))

        cur.execute("DELETE FROM compras WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("Item voltou para o estoque.")
    return redirect("/compras")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/buscar_produto/<codigo>")
def buscar_produto(codigo):

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT nome FROM codigos WHERE codigo=?", (codigo,))
    item = cur.fetchone()

    conn.close()

    if item:
        return {"nome": item["nome"]}

    return {"nome": None}


@app.route("/salvar_codigo", methods=["POST"])
def salvar_codigo():

    codigo = request.json["codigo"]
    nome = request.json["nome"]

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO codigos (codigo,nome) VALUES (?,?)",
        (codigo, nome)
    )

    conn.commit()
    conn.close()

    return {"ok": True}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
