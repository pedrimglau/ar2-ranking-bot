import sqlite3
import os

DATABASE = os.getenv("DATABASE_PATH", "database.db")


def conectar():
    return sqlite3.connect(DATABASE)


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            nome TEXT PRIMARY KEY,
            pontos INTEGER NOT NULL DEFAULT 0,
            vitorias INTEGER NOT NULL DEFAULT 0,
            derrotas INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            discord_id INTEGER PRIMARY KEY,
            jogador TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partidas (
            id INTEGER PRIMARY KEY,
            modo TEXT NOT NULL,
            hoster_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'esperando'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participantes_partida (
            partida_id INTEGER NOT NULL,
            discord_id INTEGER NOT NULL,
            jogador TEXT NOT NULL,

            PRIMARY KEY (partida_id, discord_id)
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# JOGADORES
# ==========================================

def criar_jogador(nome):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO players
        (nome, pontos, vitorias, derrotas)
        VALUES (?, 0, 0, 0)
    """, (nome,))

    conn.commit()
    conn.close()


def buscar_jogador(nome):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, pontos, vitorias, derrotas
        FROM players
        WHERE nome = ?
    """, (nome,))

    jogador = cursor.fetchone()

    conn.close()
    return jogador


def registrar_vitoria(nome, pontos):
    criar_jogador(nome)

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE players
        SET pontos = pontos + ?,
            vitorias = vitorias + 1
        WHERE nome = ?
    """, (pontos, nome))

    conn.commit()
    conn.close()


def registrar_derrota(nome, pontos):
    criar_jogador(nome)

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE players
        SET pontos = pontos - ?,
            derrotas = derrotas + 1
        WHERE nome = ?
    """, (pontos, nome))

    conn.commit()
    conn.close()


# ==========================================
# VINCULAÇÃO
# ==========================================

def vincular_conta(discord_id, jogador):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT discord_id
        FROM links
        WHERE jogador = ?
    """, (jogador,))

    existente = cursor.fetchone()

    if (
        existente is not None
        and existente[0] != discord_id
    ):
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO links (discord_id, jogador)
        VALUES (?, ?)
        ON CONFLICT(discord_id)
        DO UPDATE SET jogador = excluded.jogador
    """, (discord_id, jogador))

    conn.commit()
    conn.close()

    return True


def buscar_vinculo(discord_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT jogador
        FROM links
        WHERE discord_id = ?
    """, (discord_id,))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return resultado[0]

    return None


# ==========================================
# RANKING
# ==========================================

def buscar_top():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, pontos, vitorias, derrotas
        FROM players
        ORDER BY pontos DESC
        LIMIT 10
    """)

    ranking = cursor.fetchall()

    conn.close()

    return ranking


# ==========================================
# PARTIDAS
# ==========================================

def pegar_proximo_id_partida():
    """
    Procura o primeiro número disponível.

    Exemplos:

    Existem #1 e #2
    -> próxima será #3

    Existem #1 e #3
    -> próxima será #2

    Não existe nenhuma
    -> próxima será #1
    """

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM partidas
        ORDER BY id ASC
    """)

    ids = cursor.fetchall()

    conn.close()

    proximo_id = 1

    for registro in ids:
        id_atual = registro[0]

        if id_atual == proximo_id:
            proximo_id += 1

        elif id_atual > proximo_id:
            break

    return proximo_id


def criar_partida(modo, hoster_id):

    partida_id = pegar_proximo_id_partida()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO partidas (
            id,
            modo,
            hoster_id,
            status
        )
        VALUES (?, ?, ?, 'esperando')
    """, (
        partida_id,
        modo,
        hoster_id
    ))

    conn.commit()
    conn.close()

    return partida_id


def buscar_partida(partida_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, modo, hoster_id, status
        FROM partidas
        WHERE id = ?
    """, (partida_id,))

    partida = cursor.fetchone()

    conn.close()

    return partida


def apagar_partida(partida_id):
    """
    Apaga participantes e depois
    apaga completamente a partida.
    """

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM participantes_partida
        WHERE partida_id = ?
    """, (partida_id,))

    cursor.execute("""
        DELETE FROM partidas
        WHERE id = ?
    """, (partida_id,))

    conn.commit()
    conn.close()


def adicionar_participante(
    partida_id,
    discord_id,
    jogador
):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO participantes_partida (
                partida_id,
                discord_id,
                jogador
            )
            VALUES (?, ?, ?)
        """, (
            partida_id,
            discord_id,
            jogador
        ))

        conn.commit()
        sucesso = True

    except sqlite3.IntegrityError:
        sucesso = False

    conn.close()

    return sucesso


def remover_participante(
    partida_id,
    discord_id
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM participantes_partida
        WHERE partida_id = ?
        AND discord_id = ?
    """, (
        partida_id,
        discord_id
    ))

    conn.commit()
    conn.close()


def buscar_participantes(partida_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT discord_id, jogador
        FROM participantes_partida
        WHERE partida_id = ?
        ORDER BY rowid ASC
    """, (partida_id,))

    jogadores = cursor.fetchall()

    conn.close()

    return jogadores


def atualizar_status_partida(
    partida_id,
    status
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE partidas
        SET status = ?
        WHERE id = ?
    """, (
        status,
        partida_id
    ))

    conn.commit()
    conn.close()


criar_tabelas()