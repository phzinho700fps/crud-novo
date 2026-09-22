from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "batcomputer-development-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"


# ================================================================
# CONEXÃO COM O BANCO
# ================================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ================================================================
# INICIALIZAÇÃO DO BANCO
# ================================================================

def init_db():
    conn = get_db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS criminosos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            codinome TEXT NOT NULL,
            nivel_perigo INTEGER NOT NULL CHECK(nivel_perigo BETWEEN 1 AND 10),
            status TEXT NOT NULL,
            ultima_localizacao TEXT,
            descricao TEXT,
            foto TEXT
        );

        CREATE TABLE IF NOT EXISTS ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            local TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL,
            criminoso_id INTEGER,
            FOREIGN KEY (criminoso_id)
                REFERENCES criminosos(id)
                ON DELETE SET NULL
        );
    """)

    # ============================================================
    # MIGRAÇÃO DO BANCO EXISTENTE
    # ============================================================
    # Se o database.db já existia antes da coluna "foto",
    # CREATE TABLE IF NOT EXISTS não adicionaria a coluna.
    # Por isso fazemos esta verificação.

    colunas = conn.execute(
        "PRAGMA table_info(criminosos)"
    ).fetchall()

    nomes_colunas = [coluna["name"] for coluna in colunas]

    if "foto" not in nomes_colunas:
        conn.execute(
            "ALTER TABLE criminosos ADD COLUMN foto TEXT"
        )

    # ============================================================
    # FOTOS PADRÃO DOS CRIMINOSOS EXISTENTES
    # ============================================================

    fotos = {
        "Charada": "charada.jpg",
        "Pinguim": "pinguim.jpg",
        "Duas-Caras": "duas-caras.jpg",
        "Espantalho": "espantalho.jpg",
        "Coringa": "coringa.jpg"
    }

    for codinome, foto in fotos.items():
        conn.execute(
            """
            UPDATE criminosos
            SET foto = ?
            WHERE codinome = ?
              AND (foto IS NULL OR foto = '')
            """,
            (foto, codinome)
        )

    # ============================================================
    # DADOS INICIAIS
    # ============================================================

    if conn.execute(
        "SELECT COUNT(*) FROM criminosos"
    ).fetchone()[0] == 0:

        criminosos = [
            (
                "Edward Nygma",
                "Charada",
                8,
                "Procurado",
                "Gotham Central",
                "Especialista em enigmas, crimes intelectuais e desafios direcionados ao Batman.",
                "charada.jpg"
            ),
            (
                "Oswald Cobblepot",
                "Pinguim",
                7,
                "Sob investigação",
                "Iceberg Lounge",
                "Figura conhecida do submundo de Gotham e proprietário do Iceberg Lounge.",
                "pinguim.jpg"
            ),
            (
                "Harvey Dent",
                "Duas-Caras",
                9,
                "Procurado",
                "Desconhecida",
                "Ex-promotor de Gotham envolvido com crimes organizados e decisões baseadas em sua moeda.",
                "duas-caras.jpg"
            ),
            (
                "Jonathan Crane",
                "Espantalho",
                9,
                "Procurado",
                "Arkham",
                "Pesquisador obcecado pelo medo e responsável por experimentos com toxinas.",
                "espantalho.jpg"
            ),
            (
                "Jack Napier",
                "Coringa",
                10,
                "Alta prioridade",
                "Desconhecida",
                "Criminoso extremamente perigoso, associado a ataques caóticos em Gotham.",
                "coringa.jpg"
            )
        ]

        conn.executemany(
            """
            INSERT INTO criminosos
            (
                nome,
                codinome,
                nivel_perigo,
                status,
                ultima_localizacao,
                descricao,
                foto
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            criminosos
        )

        ocorrencias = [
            (
                "Roubo ao Gotham National Bank",
                "Uma sequência de enigmas foi encontrada no local após o roubo.",
                "Gotham National Bank",
                "2026-09-20",
                "Em investigação",
                1
            ),
            (
                "Movimentação no Iceberg Lounge",
                "Informantes relataram uma reunião entre membros do submundo.",
                "Iceberg Lounge",
                "2026-09-21",
                "Monitoramento",
                2
            ),
            (
                "Ataque com toxina do medo",
                "Agentes encontraram resíduos químicos associados a experimentos ilegais.",
                "Crime Alley",
                "2026-09-22",
                "Ativa",
                4
            )
        ]

        conn.executemany(
            """
            INSERT INTO ocorrencias
            (
                titulo,
                descricao,
                local,
                data,
                status,
                criminoso_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ocorrencias
        )

    conn.commit()
    conn.close()


# ================================================================
# ANO ATUAL
# ================================================================

@app.context_processor
def inject_year():
    from datetime import datetime

    return {
        "current_year": datetime.now().year
    }


# ================================================================
# DASHBOARD
# ================================================================

@app.route("/")
def index():

    conn = get_db()

    stats = {
        "criminosos": conn.execute(
            "SELECT COUNT(*) FROM criminosos"
        ).fetchone()[0],

        "procurados": conn.execute(
            """
            SELECT COUNT(*)
            FROM criminosos
            WHERE status IN ('Procurado', 'Alta prioridade')
            """
        ).fetchone()[0],

        "casos_ativos": conn.execute(
            """
            SELECT COUNT(*)
            FROM ocorrencias
            WHERE status NOT IN ('Encerrada', 'Resolvida')
            """
        ).fetchone()[0],

        "casos_encerrados": conn.execute(
            """
            SELECT COUNT(*)
            FROM ocorrencias
            WHERE status IN ('Encerrada', 'Resolvida')
            """
        ).fetchone()[0]
    }

    recentes = conn.execute(
        """
        SELECT o.*, c.codinome
        FROM ocorrencias o
        LEFT JOIN criminosos c
            ON c.id = o.criminoso_id
        ORDER BY o.id DESC
        LIMIT 5
        """
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        stats=stats,
        recentes=recentes
    )


# ================================================================
# LISTA DE CRIMINOSOS
# ================================================================

@app.route("/criminosos")
def criminosos():

    busca = request.args.get("busca", "").strip()

    conn = get_db()

    if busca:

        lista = conn.execute(
            """
            SELECT *
            FROM criminosos
            WHERE nome LIKE ?
               OR codinome LIKE ?
               OR status LIKE ?
            ORDER BY nivel_perigo DESC, id DESC
            """,
            (
                f"%{busca}%",
                f"%{busca}%",
                f"%{busca}%"
            )
        ).fetchall()

    else:

        lista = conn.execute(
            """
            SELECT *
            FROM criminosos
            ORDER BY nivel_perigo DESC, id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "criminosos.html",
        criminosos=lista,
        busca=busca
    )


# ================================================================
# DETALHES DO CRIMINOSO
# ================================================================

@app.route("/criminoso/<int:criminoso_id>")
def criminoso(criminoso_id):

    conn = get_db()

    registro = conn.execute(
        """
        SELECT *
        FROM criminosos
        WHERE id = ?
        """,
        (criminoso_id,)
    ).fetchone()

    if registro is None:

        conn.close()

        flash(
            "Arquivo não encontrado no Batcomputador.",
            "error"
        )

        return redirect(url_for("criminosos"))

    ocorrencias = conn.execute(
        """
        SELECT *
        FROM ocorrencias
        WHERE criminoso_id = ?
        ORDER BY id DESC
        """,
        (criminoso_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "criminoso.html",
        criminoso=registro,
        ocorrencias=ocorrencias
    )


# ================================================================
# ADICIONAR CRIMINOSO
# ================================================================

@app.route(
    "/criminoso/adicionar",
    methods=["GET", "POST"]
)
def adicionar_criminoso():

    if request.method == "POST":

        dados = (
            request.form["nome"].strip(),
            request.form["codinome"].strip(),
            int(request.form["nivel_perigo"]),
            request.form["status"].strip(),
            request.form["ultima_localizacao"].strip(),
            request.form["descricao"].strip(),
            request.form.get("foto", "").strip()
        )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO criminosos
            (
                nome,
                codinome,
                nivel_perigo,
                status,
                ultima_localizacao,
                descricao,
                foto
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            dados
        )

        conn.commit()
        conn.close()

        flash(
            "Novo arquivo criminal registrado.",
            "success"
        )

        return redirect(url_for("criminosos"))

    return render_template(
        "form_criminoso.html",
        modo="adicionar",
        criminoso=None
    )


# ================================================================
# EDITAR CRIMINOSO
# ================================================================

@app.route(
    "/criminoso/<int:criminoso_id>/editar",
    methods=["GET", "POST"]
)
def editar_criminoso(criminoso_id):

    conn = get_db()

    registro = conn.execute(
        """
        SELECT *
        FROM criminosos
        WHERE id = ?
        """,
        (criminoso_id,)
    ).fetchone()

    if registro is None:

        conn.close()

        flash(
            "Arquivo não encontrado.",
            "error"
        )

        return redirect(url_for("criminosos"))

    if request.method == "POST":

        dados = (
            request.form["nome"].strip(),
            request.form["codinome"].strip(),
            int(request.form["nivel_perigo"]),
            request.form["status"].strip(),
            request.form["ultima_localizacao"].strip(),
            request.form["descricao"].strip(),
            request.form.get("foto", "").strip(),
            criminoso_id
        )

        conn.execute(
            """
            UPDATE criminosos
            SET
                nome = ?,
                codinome = ?,
                nivel_perigo = ?,
                status = ?,
                ultima_localizacao = ?,
                descricao = ?,
                foto = ?
            WHERE id = ?
            """,
            dados
        )

        conn.commit()
        conn.close()

        flash(
            "Arquivo atualizado no Batcomputador.",
            "success"
        )

        return redirect(
            url_for(
                "criminoso",
                criminoso_id=criminoso_id
            )
        )

    conn.close()

    return render_template(
        "form_criminoso.html",
        modo="editar",
        criminoso=registro
    )


# ================================================================
# EXCLUIR CRIMINOSO
# ================================================================

@app.post(
    "/criminoso/<int:criminoso_id>/excluir"
)
def excluir_criminoso(criminoso_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM criminosos WHERE id = ?",
        (criminoso_id,)
    )

    conn.commit()
    conn.close()

    flash(
        "Arquivo removido do banco de dados.",
        "success"
    )

    return redirect(url_for("criminosos"))


# ================================================================
# LISTA DE OCORRÊNCIAS
# ================================================================

@app.route("/ocorrencias")
def ocorrencias():

    conn = get_db()

    lista = conn.execute(
        """
        SELECT o.*, c.codinome
        FROM ocorrencias o
        LEFT JOIN criminosos c
            ON c.id = o.criminoso_id
        ORDER BY o.id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "ocorrencias.html",
        ocorrencias=lista
    )


# ================================================================
# ADICIONAR OCORRÊNCIA
# ================================================================

@app.route(
    "/ocorrencia/adicionar",
    methods=["GET", "POST"]
)
def adicionar_ocorrencia():

    conn = get_db()

    criminosos_lista = conn.execute(
        """
        SELECT id, codinome
        FROM criminosos
        ORDER BY codinome
        """
    ).fetchall()

    if request.method == "POST":

        dados = (
            request.form["titulo"].strip(),
            request.form["descricao"].strip(),
            request.form["local"].strip(),
            request.form["data"],
            request.form["status"].strip(),
            request.form.get("criminoso_id") or None
        )

        conn.execute(
            """
            INSERT INTO ocorrencias
            (
                titulo,
                descricao,
                local,
                data,
                status,
                criminoso_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            dados
        )

        conn.commit()
        conn.close()

        flash(
            "Ocorrência registrada no Batcomputador.",
            "success"
        )

        return redirect(url_for("ocorrencias"))

    conn.close()

    return render_template(
        "form_ocorrencia.html",
        criminosos=criminosos_lista
    )


# ================================================================
# EXCLUIR OCORRÊNCIA
# ================================================================

@app.post(
    "/ocorrencia/<int:ocorrencia_id>/excluir"
)
def excluir_ocorrencia(ocorrencia_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM ocorrencias WHERE id = ?",
        (ocorrencia_id,)
    )

    conn.commit()
    conn.close()

    flash(
        "Ocorrência removida.",
        "success"
    )

    return redirect(url_for("ocorrencias"))


# ================================================================
# INICIALIZAÇÃO
# ================================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)