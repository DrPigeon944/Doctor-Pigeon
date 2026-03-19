import sqlite3
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

TOKEN = "ur_Bot_token"
GUILD_ID = 1422687989913358380

DB_FILE = "bookkeeping.db"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            category TEXT,
            description TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_transaction(guild_id, user_id, t_type, amount, category, description):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions (guild_id, user_id, type, amount, category, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        guild_id,
        user_id,
        t_type,
        amount,
        category,
        description,
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()


def get_balance(guild_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END),
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END)
        FROM transactions
        WHERE guild_id=?
    """, (guild_id,))

    income, expense = cur.fetchone()
    conn.close()

    income = income or 0
    expense = expense or 0

    return income, expense


@bot.event
async def on_ready():
    init_db()

    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)

    print(f"Bot läuft als {bot.user}")


# -------------------------
# COMMANDS
# -------------------------

@bot.tree.command(name="ping", description="Test", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Bot funktioniert!")


@bot.tree.command(name="income", description="Add income", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(amount="Amount", category="Category", description="Description")
async def income(interaction: discord.Interaction, amount: float, category: Optional[str] = None, description: Optional[str] = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("No permission", ephemeral=True)
        return

    add_transaction(interaction.guild.id, interaction.user.id, "income", amount, category, description)

    await interaction.response.send_message(f"✅ Income added: {amount}€")


@bot.tree.command(name="expense", description="Add expense", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(amount="Amount", category="Category", description="Description")
async def expense(interaction: discord.Interaction, amount: float, category: Optional[str] = None, description: Optional[str] = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("No permission", ephemeral=True)
        return

    add_transaction(interaction.guild.id, interaction.user.id, "expense", amount, category, description)

    await interaction.response.send_message(f"💸 Expense added: {amount}€")


@bot.tree.command(name="balance", description="Show balance", guild=discord.Object(id=GUILD_ID))
async def balance(interaction: discord.Interaction):
    income, expense = get_balance(interaction.guild.id)

    balance = income - expense

    await interaction.response.send_message(
        f"💰 Income: {income}€\n"
        f"💸 Expense: {expense}€\n"
        f"📊 Balance: {balance}€"
    )

@bot.tree.command(name="history", description="Show transaction history", guild=discord.Object(id=GUILD_ID))
async def history(interaction: discord.Interaction):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT type, amount, category, description, created_at
        FROM transactions
        WHERE guild_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (interaction.guild.id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        await interaction.response.send_message("No transactions found.")
        return

    message = "📜 Last transactions:\n\n"

    for row in rows:
        emoji = "💰" if row["type"] == "income" else "💸"
        message += f"{emoji} {row['amount']}€ | {row['category'] or '-'} | {row['description'] or '-'}\n"

    await interaction.response.send_message(message)
bot.run(TOKEN)