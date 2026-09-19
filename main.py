import discord
from discord.ext import commands
from flask import Flask, request, jsonify
import threading
import random
import os
from dotenv import load_dotenv

from database import (
    criar_jogador,
    buscar_jogador,
    registrar_vitoria,
    registrar_derrota,
    vincular_conta,
    buscar_vinculo,
    buscar_top,
    criar_partida,
    buscar_partida,
    apagar_partida,
    adicionar_participante,
    remover_participante,
    buscar_participantes,
    atualizar_status_partida
)


# ==========================================
# DISCORD
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


# ==========================================
# API
# ==========================================

app = Flask(__name__)


@app.route("/result", methods=["POST"])
def result():

    data = request.json

    if not data:
        return jsonify({
            "erro": "Nenhum dado recebido."
        }), 400

    player = data.get("player")
    resultado = data.get("result")

    if not player:
        return jsonify({
            "erro": "Informe o jogador."
        }), 400

    if not resultado:
        return jsonify({
            "erro": "Informe o resultado."
        }), 400

    resultado = str(resultado).lower()

    if resultado not in ["win", "loss"]:
        return jsonify({
            "erro": "Resultado deve ser win ou loss."
        }), 400

    criar_jogador(player)

    if resultado == "win":

        pontos = random.randint(30, 40)

        registrar_vitoria(
            player,
            pontos
        )

        jogador = buscar_jogador(player)

        return jsonify({
            "sucesso": True,
            "jogador": player,
            "resultado": "WIN",
            "pontos_ganhos": pontos,
            "total": jogador[1],
            "vitorias": jogador[2],
            "derrotas": jogador[3]
        })

    pontos = random.randint(20, 30)

    registrar_derrota(
        player,
        pontos
    )

    jogador = buscar_jogador(player)

    return jsonify({
        "sucesso": True,
        "jogador": player,
        "resultado": "LOSS",
        "pontos_perdidos": pontos,
        "total": jogador[1],
        "vitorias": jogador[2],
        "derrotas": jogador[3]
    })


# ==========================================
# LINK
# ==========================================

@bot.command()
async def link(ctx, jogador=None):

    if jogador is None:
        await ctx.send(
            "❌ Use: `!link NomeDoJogador`"
        )
        return

    player = buscar_jogador(jogador)

    if player is None:
        await ctx.send(
            f"❌ O jogador **{jogador}** "
            "ainda não existe no ranking."
        )
        return

    sucesso = vincular_conta(
        ctx.author.id,
        jogador
    )

    if not sucesso:
        await ctx.send(
            "❌ Esse jogador já está "
            "vinculado a outra conta."
        )
        return

    await ctx.send(
        "🔗 **CONTA VINCULADA!**\n\n"
        f"👤 Discord: {ctx.author.mention}\n"
        f"🎮 Jogador: **{jogador}**"
    )


# ==========================================
# RANK
# ==========================================

@bot.command()
async def rank(ctx):

    nome = buscar_vinculo(
        ctx.author.id
    )

    if nome is None:
        await ctx.send(
            "❌ Você ainda não vinculou sua conta.\n\n"
            "Use `!link NomeDoJogador`"
        )
        return

    jogador = buscar_jogador(nome)

    if jogador is None:
        await ctx.send(
            "❌ Jogador não encontrado."
        )
        return

    nome = jogador[0]
    pontos = jogador[1]
    vitorias = jogador[2]
    derrotas = jogador[3]

    partidas = vitorias + derrotas

    await ctx.send(
        f"🏆 **RANK — {nome}**\n\n"
        f"💎 Pontos: **{pontos}**\n"
        f"🏆 Vitórias: **{vitorias}**\n"
        f"💀 Derrotas: **{derrotas}**\n"
        f"🎮 Partidas: **{partidas}**"
    )


# ==========================================
# TOP
# ==========================================

@bot.command()
async def top(ctx):

    ranking = buscar_top()

    if not ranking:
        await ctx.send(
            "📊 Ainda não existem jogadores."
        )
        return

    mensagem = (
        "🏆 **RANKING — APOCALYPSE RISING 2**\n\n"
    )

    medalhas = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for posicao, jogador in enumerate(
        ranking,
        start=1
    ):

        nome = jogador[0]
        pontos = jogador[1]

        if posicao <= 3:
            simbolo = medalhas[posicao - 1]
        else:
            simbolo = f"**{posicao}º**"

        mensagem += (
            f"{simbolo} {nome} — "
            f"**{pontos} pts**\n"
        )

    await ctx.send(mensagem)


# ==========================================
# MODOS
# ==========================================

MODOS = {
    "1v1": 2,
    "2v2": 4,
    "3v3": 6,
    "4v4": 8
}


# ==========================================
# BOTÃO DA PARTIDA
# ==========================================

class PartidaView(discord.ui.View):

    def __init__(
        self,
        partida_id,
        modo
    ):

        super().__init__(
            timeout=None
        )

        self.partida_id = partida_id
        self.modo = modo
        self.max_jogadores = MODOS[modo]


    @discord.ui.button(
        label="Entrar na Partida",
        emoji="🎮",
        style=discord.ButtonStyle.green
    )
    async def entrar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        partida = buscar_partida(
            self.partida_id
        )

        # Se foi cancelada, ela nem existe
        # mais no banco.
        if partida is None:

            await interaction.response.send_message(
                "❌ Essa partida não está mais ativa.",
                ephemeral=True
            )

            return


        if partida[3] == "iniciada":

            await interaction.response.send_message(
                "❌ Essa partida já começou.",
                ephemeral=True
            )

            return


        jogador = buscar_vinculo(
            interaction.user.id
        )

        if jogador is None:

            await interaction.response.send_message(
                "❌ Você precisa vincular sua conta.\n"
                "Use `!link NomeDoJogador`.",
                ephemeral=True
            )

            return


        participantes = buscar_participantes(
            self.partida_id
        )


        if len(participantes) >= self.max_jogadores:

            await interaction.response.send_message(
                "❌ A partida já está cheia.",
                ephemeral=True
            )

            return


        sucesso = adicionar_participante(
            self.partida_id,
            interaction.user.id,
            jogador
        )


        if not sucesso:

            await interaction.response.send_message(
                "❌ Você já entrou nessa partida.",
                ephemeral=True
            )

            return


        participantes = buscar_participantes(
            self.partida_id
        )


        # ==================================
        # PARTIDA CHEIA
        # ==================================

        if len(participantes) >= self.max_jogadores:

            atualizar_status_partida(
                self.partida_id,
                "iniciada"
            )

            button.disabled = True


            metade = (
                self.max_jogadores // 2
            )

            time_a = participantes[:metade]
            time_b = participantes[metade:]


            texto_a = "\n".join(
                f"🔵 **{p[1]}**"
                for p in time_a
            )

            texto_b = "\n".join(
                f"🔴 **{p[1]}**"
                for p in time_b
            )


            embed = discord.Embed(
                title=(
                    f"⚔️ PARTIDA "
                    f"#{self.partida_id} INICIADA"
                ),
                description=(
                    f"🎮 **Modo:** {self.modo}\n\n"

                    "🔵 **TIME A**\n"
                    f"{texto_a}\n\n"

                    "⚔️ **VS**\n\n"

                    "🔴 **TIME B**\n"
                    f"{texto_b}\n\n"

                    "🔥 **A PARTIDA COMEÇOU!**"
                )
            )


            await interaction.response.edit_message(
                embed=embed,
                view=self
            )

            return


        await interaction.response.send_message(
            "✅ Você entrou na partida!\n\n"
            f"👥 Jogadores: "
            f"**{len(participantes)}/"
            f"{self.max_jogadores}**",
            ephemeral=True
        )


# ==========================================
# CRIAR PARTIDA
# ==========================================

@bot.command()
async def partida(ctx, modo=None):

    if modo is not None:
        modo = modo.lower()


    if modo not in MODOS:

        await ctx.send(
            "❌ **Modo inválido.**\n\n"
            "Modos disponíveis:\n"
            "⚔️ `!partida 1v1`\n"
            "⚔️ `!partida 2v2`\n"
            "⚔️ `!partida 3v3`\n"
            "⚔️ `!partida 4v4`"
        )

        return


    partida_id = criar_partida(
        modo,
        ctx.author.id
    )

    quantidade = MODOS[modo]


    embed = discord.Embed(
        title="🎮 NOVA PARTIDA RANQUEADA",
        description=(
            f"⚔️ **Modo:** {modo}\n"
            f"👑 **Hoster:** {ctx.author.mention}\n\n"

            f"👥 **Jogadores:** 0/{quantidade}\n\n"

            "🏆 Vitória: **+30 a +40 pontos**\n"
            "💀 Derrota: **-20 a -30 pontos**\n\n"

            f"🆔 **Partida #{partida_id}**\n\n"

            "Clique abaixo para entrar!"
        )
    )


    await ctx.send(
        embed=embed,
        view=PartidaView(
            partida_id,
            modo
        )
    )


# ==========================================
# CANCELAR PARTIDA
# ==========================================

@bot.command()
async def cancelar(ctx, partida_id=None):

    if partida_id is None:

        await ctx.send(
            "❌ Informe o número da partida.\n\n"
            "Exemplo: `!cancelar 1`"
        )

        return


    try:
        partida_id = int(partida_id)

    except ValueError:

        await ctx.send(
            "❌ O ID precisa ser um número."
        )

        return


    partida = buscar_partida(
        partida_id
    )


    if partida is None:

        await ctx.send(
            f"❌ A partida **#{partida_id}** "
            "não está ativa."
        )

        return


    hoster_id = partida[2]


    if ctx.author.id != hoster_id:

        await ctx.send(
            "⛔ Somente o hoster pode "
            "cancelar essa partida."
        )

        return


    if partida[3] == "iniciada":

        await ctx.send(
            "❌ Essa partida já começou."
        )

        return


    # IMPORTANTE:
    # Agora apagamos a partida completamente.
    apagar_partida(
        partida_id
    )


    embed = discord.Embed(
        title=(
            f"🛑 PARTIDA "
            f"#{partida_id} CANCELADA"
        ),
        description=(
            f"👑 Cancelada por: "
            f"{ctx.author.mention}\n\n"
            "🗑️ Os registros desta partida "
            "foram removidos."
        )
    )


    await ctx.send(
        embed=embed
    )


# ==========================================
# PING
# ==========================================

@bot.command()
async def ping(ctx):

    await ctx.send(
        "🏓 Pong!"
    )


# ==========================================
# INICIAR API
# ==========================================

def run_api():

    print(
        "🌐 API iniciada em "
        "http://127.0.0.1:5000"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )


api_thread = threading.Thread(
    target=run_api,
    daemon=True
)

api_thread.start()


# ==========================================
# TOKEN
# ==========================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN não foi encontrado. "
        "Configure a variável no arquivo .env ou na hospedagem."
    )

bot.run(TOKEN)
