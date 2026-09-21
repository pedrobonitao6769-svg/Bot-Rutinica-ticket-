import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configuração de Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class MinecraftTicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
        # Configurações padrão gravadas em memória
        self.config = {
            "ticket_channel_id": None,
            "staff_role_id": None,
            "panel_title": "⛏️ Central de Atendimento - CraftWorld",
            "panel_description": (
                "Olá, aventureiro! Selecione abaixo a categoria do seu atendimento.\n\n"
                "🛒 **Compras:** Produtos, VIPs, Kits e Loja.\n"
                "💰 **Financeiro:** Pagamentos e questões financeiras.\n"
                "🔨 **Bugs:** Reportar falhas no servidor.\n"
                "❗ **Denunciar:** Denunciar jogadores quebrando regras.\n"
                "👤 **Outros:** Dúvidas gerais ou outros assuntos."
            ),
            "panel_image": "https://i.imgur.com/39AQA24.png",  # Banner estilo Minecraft
            "panel_thumbnail": "https://i.imgur.com/JpE44pG.png"  # Ícone/Bloco
        }

    async def setup_hook(self):
        # Registra as views de forma permanente para os botões continuarem funcionando após reiniciar
        self.add_view(TicketCategoryView(self))
        self.add_view(TicketControlView(self))
        # Sincroniza os slash commands globalmente
        await self.tree.sync()

bot = MinecraftTicketBot()


# -------------------------------------------------------------------
# VIEWS & INTERAÇÕES DO TICKET
# -------------------------------------------------------------------

class TicketCategoryView(discord.ui.View):
    """View contendo os botões para abertura de tickets por categoria."""
    def __init__(self, bot_instance: MinecraftTicketBot):
        super().__init__(timeout=None)
        self.bot = bot_instance

    async def create_ticket(self, interaction: discord.Interaction, category_name: str, emoji: str):
        guild = interaction.guild
        user = interaction.user

        # Verifica se o cargo de staff está configurado
        staff_role_id = self.bot.config.get("staff_role_id")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        # Permissões do canal privado do ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{category_name.lower()}-{user.name}"
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Ticket de {category_name} criado por {user.display_name}"
        )

        # Mensagem interna do ticket
        embed = discord.Embed(
            title=f"{emoji} Atendimento - {category_name.capitalize()}",
            description=(
                f"Olá {user.mention}, bem-vindo ao seu ticket de **{category_name.capitalize()}**!\n"
                "Descreva em detalhes o seu problema ou dúvida para que a nossa equipe possa te ajudar."
            ),
            color=discord.Color.dark_green()
        )
        embed.set_footer(text="Servidor Minecraft • Pressione o botão abaixo para encerrar.")
        
        await channel.send(content=f"{user.mention} " + (staff_role.mention if staff_role else ""), embed=embed, view=TicketControlView(self.bot))
        await interaction.response.send_message(f"✅ Seu ticket foi criado no canal {channel.mention}!", ephemeral=True)

    @discord.ui.button(label="Compras", style=discord.ButtonStyle.success, emoji="🛒", custom_id="mc_ticket_compras")
    async def compras_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "compras", "🛒")

    @discord.ui.button(label="Financeiro", style=discord.ButtonStyle.secondary, emoji="💰", custom_id="mc_ticket_financeiro")
    async def financeiro_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "financeiro", "💰")

    @discord.ui.button(label="Bugs", style=discord.ButtonStyle.secondary, emoji="🔨", custom_id="mc_ticket_bugs")
    async def bugs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "bugs", "🔨")

    @discord.ui.button(label="Denunciar", style=discord.ButtonStyle.danger, emoji="❗", custom_id="mc_ticket_denunciar")
    async def denunciar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "denunciar", "❗")

    @discord.ui.button(label="Outros", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="mc_ticket_outros")
    async def outros_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "outros", "👤")


class TicketControlView(discord.ui.View):
    """View de controle interna dentro do canal do ticket criado."""
    def __init__(self, bot_instance: MinecraftTicketBot):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="mc_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando este ticket em 5 segundos...")
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket fechado pelo usuário/staff.")


# -------------------------------------------------------------------
# SLASH COMMANDS
# -------------------------------------------------------------------

@bot.tree.command(name="config", description="Configura o canal dos tickets e o cargo responsável pela staff.")
@app_commands.describe(
    canal="Canal onde o painel de tickets será referenciado",
    cargo_staff="Cargo que terá acesso de administração aos tickets"
)
@app_commands.checks.has_permissions(administrator=True)
async def config(interaction: discord.Interaction, canal: discord.TextChannel, cargo_staff: discord.Role):
    bot.config["ticket_channel_id"] = canal.id
    bot.config["staff_role_id"] = cargo_staff.id

    embed = discord.Embed(
        title="⚙️ Configurações Atualizadas",
        color=discord.Color.green()
    )
    embed.add_field(name="Canal Definido", value=canal.mention, inline=False)
    embed.add_field(name="Cargo de Suporte", value=cargo_staff.mention, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="painelconfig", description="Exibe e atualiza o visual da embed principal do ticket.")
@app_commands.describe(
    titulo="Novo título para o painel de tickets",
    descricao="Nova descrição para o painel de tickets",
    imagem_url="URL de uma imagem grande para o rodapé do painel",
    icone_url="URL de um ícone pequeno (Thumbnail) para a lateral do painel"
)
@app_commands.checks.has_permissions(administrator=True)
async def painel_config(
    interaction: discord.Interaction,
    titulo: str = None,
    descricao: str = None,
    imagem_url: str = None,
    icone_url: str = None
):
    if titulo:
        bot.config["panel_title"] = titulo
    if descricao:
        bot.config["panel_description"] = descricao
    if imagem_url:
        bot.config["panel_image"] = imagem_url
    if icone_url:
        bot.config["panel_thumbnail"] = icone_url

    embed = discord.Embed(
        title="⚙️ Configuração do Painel Atualizada!",
        description="Abaixo está a prévia de como ficará o embed principal:",
        color=discord.Color.gold()
    )
    embed.add_field(name="Título Atual", value=bot.config["panel_title"], inline=False)
    embed.add_field(name="Descrição Atual", value=bot.config["panel_description"], inline=False)
    
    if bot.config["panel_thumbnail"]:
        embed.set_thumbnail(url=bot.config["panel_thumbnail"])
    if bot.config["panel_image"]:
        embed.set_image(url=bot.config["panel_image"])

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="painelembed", description="Envia o painel de suporte com os botões de ticket.")
@app_commands.checks.has_permissions(administrator=True)
async def painel_embed(interaction: discord.Interaction):
    channel_id = bot.config.get("ticket_channel_id")
    target_channel = interaction.guild.get_channel(channel_id) if channel_id else interaction.channel

    embed = discord.Embed(
        title=bot.config["panel_title"],
        description=bot.config["panel_description"],
        color=discord.Color.dark_green()
    )
    
    if bot.config["panel_thumbnail"]:
        embed.set_thumbnail(url=bot.config["panel_thumbnail"])
    if bot.config["panel_image"]:
        embed.set_image(url=bot.config["panel_image"])

    embed.set_footer(text="⛏️ Sistema de Tickets • Suporte do Servidor")

    await target_channel.send(embed=embed, view=TicketCategoryView(bot))
    await interaction.response.send_message(f"✅ Painel enviado com sucesso no canal {target_channel.mention}!", ephemeral=True)


@bot.event
async def on_ready():
    print(f"⛏️ Bot online como {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="⛏️ Jogando no Servidor Minecraft"))

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("O token do Discord não foi encontrado. Verifique seu arquivo .env.")
    bot.run(TOKEN)
