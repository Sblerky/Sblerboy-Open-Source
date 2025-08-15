import discord
from discord.ext import commands
from pyboy import PyBoy
from pyboy.utils import WindowEvent
import threading
import asyncio
import io
import time
import sys
import configparser
import ast
from pathlib import Path
import atexit

EMOTE_LIST = None
ID_CHANNEL = 0
ID_GUILD = 0
ID_LOG_CHANNEL = 0
ID_CHAT_CHANNEL = 0
BOT_TOKEN = ""
PUSH_TIME = 0.1
FRAME_PER_SECONDS = 120
main_guild = None
main_channel = None
main_message = None
logs_channel = None

reaction_lock = asyncio.Lock()
stop_event = threading.Event()

intents = discord.Intents.default()
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='%', description='Emulating...', intents=intents)

Path("rom").mkdir(parents=True, exist_ok=True)

config_path = Path('config.ini')
if not config_path.exists():
    print("No config file found at", config_path.resolve())
    sys.exit(1)

config = configparser.ConfigParser()
read_files = []
for enc in ("utf-8", "utf-8-sig", "cp1252"):
    try:
        read_files = config.read(config_path, encoding=enc)
        if read_files:
            break
    except UnicodeDecodeError:
        continue
if not read_files:
    print("Failed to read config.ini")
    sys.exit(1)

required_keys = ["ID_CHANNEL", "ID_GUILD", "ID_LOG_CHANNEL", "ID_CHAT_CHANNEL", "EMOTE_LIST", "BOT_TOKEN"]
missing = [k for k in required_keys if k not in config['DEFAULT']]
if missing:
    print("Missing keys in config.ini:", ", ".join(missing))
    sys.exit(1)

try:
    ID_CHANNEL = int(config['DEFAULT']['ID_CHANNEL'])
    ID_GUILD = int(config['DEFAULT']['ID_GUILD'])
    ID_LOG_CHANNEL = int(config['DEFAULT']['ID_LOG_CHANNEL'])
    ID_CHAT_CHANNEL = int(config['DEFAULT']['ID_CHAT_CHANNEL'])
    EMOTE_LIST = ast.literal_eval(config['DEFAULT']['EMOTE_LIST'])
    BOT_TOKEN = config['DEFAULT']['BOT_TOKEN']
except Exception as e:
    print(f"Invalid config.ini: {e}")
    sys.exit(1)

# PyBoy
pyboy = PyBoy('rom/rom.gb', window="null", sound_emulated=False, sound_volume=0)
try:
    pyboy.set_emulation_speed(1)
except Exception:
    pass
try:
    with open("rom/save_file.state", "rb") as save_file:
        pyboy.load_state(save_file)
except Exception:
    print("No save file found")

# Thread PyBoy
_input_wanted = None
def set_input_wanted(inp):
    global _input_wanted
    _input_wanted = inp

def tick_pyboy(prev_ts):
    now = time.time()
    if (now - prev_ts) >= (1.0 / FRAME_PER_SECONDS):
        pyboy.tick()
        return now
    return prev_ts

def tick_thread():
    global _input_wanted
    old_input = _input_wanted
    prev_ts = time.time()
    while not stop_event.is_set():
        if old_input != _input_wanted and _input_wanted is not None:
            pyboy.send_input(_input_wanted)
            old_input = _input_wanted
        prev_ts = tick_pyboy(prev_ts)

pyboy_thread = threading.Thread(target=tick_thread, daemon=True)
pyboy_thread.start()

def _shutdown():
    stop_event.set()
    try:
        pyboy.stop()
    except Exception:
        pass
    pyboy_thread.join(timeout=1.0)
atexit.register(_shutdown)

# Utils Discord
async def get_main_guild():
    for guild in bot.guilds:
        if guild.id == ID_GUILD:
            return guild
    return None

def _tc_by_id(guild, chan_id):
    ch = guild.get_channel(chan_id)
    return ch if isinstance(ch, discord.TextChannel) else None

async def get_or_send_message(channel_param):
    global main_message
    try:
        history = [m async for m in channel_param.history(limit=1)]
    except Exception:
        history = []
    if history:
        main_message = history[0]
        await send_new_screen(None, None, None, True)
    else:
        await send_new_screen(None, None, None, True)

# Events / Commands
@bot.event
async def on_ready():
    global main_guild, main_channel, logs_channel
    print('Logged in as', bot.user.name, bot.user.id)
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="%help"))
    main_guild = await get_main_guild()
    if not main_guild:
        print("Guild not found")
        return
    main_channel = _tc_by_id(main_guild, ID_CHANNEL)
    logs_channel = _tc_by_id(main_guild, ID_LOG_CHANNEL)
    if not main_channel or not logs_channel:
        print("Channel(s) not found")
        return
    await get_or_send_message(main_channel)
    print('Init complete')

bot.remove_command('help')

@bot.command()
async def help(ctx: commands.Context):
    embed = discord.Embed(
        title="Sblerboy",
        url="https://www.youtube.com/channel/UCLT5UPUWMaeZQznyQb1FsKA/?sub_confirmation=1",
        description="Le meilleur émulateur Gameboy",
        color=0xeeb840
    )
    embed.set_author(
        name="Sblerboy",
        url="https://www.youtube.com/channel/UCLT5UPUWMaeZQznyQb1FsKA/?sub_confirmation=1",
        icon_url="https://st2.depositphotos.com/25611412/46754/v/600/depositphotos_467548434-stock-illustration-gameboy-flat-illistration-old-game.jpg"
    )
    embed.set_footer(text="Créé par Sblerky (franchement va t'abonner ça vaut le coup)")

    fonctionnement = f"""
Sblerboy implémente un émulateur de Gameboy directement dans Discord.
Actuellement, il vous permet de jouer à Pokémon version Rouge via des réactions à un message dans <#{ID_CHANNEL}>.

Principe : vous appuyez sur une réaction et le bot ajoute ✅ pour confirmer la prise en compte, puis retranscrit l’action dans l’émulateur et met à jour le screen. Quand ✅ disparaît, une nouvelle action est possible.

Suivez l’avancement dans <#{ID_LOG_CHANNEL}> et discutez/rapporter des bugs dans <#{ID_CHAT_CHANNEL}>.

À la fin, la personne ayant le plus contribué recevra un rôle unique + VIP.
"""

    embed.add_field(name="Principe de fonctionnement", value=fonctionnement, inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_raw_reaction_add(payload):
    global main_message
    if not main_message or payload.message_id != main_message.id or payload.user_id == bot.user.id:
        return
    async with reaction_lock:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        user = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
        if not user:
            return
        await process_reaction(payload.emoji, user)

async def process_reaction(emoji, user):
    global main_message
    full_emoji_name = f"{emoji.name}:{emoji.id}" if emoji.id else emoji.name
    if emoji.name in EMOTE_LIST:
        full_emoji_name = emoji.name
    if full_emoji_name not in EMOTE_LIST:
        return
    try:
        await main_message.add_reaction("✅")
    except Exception:
        pass
    idx = EMOTE_LIST.index(full_emoji_name)
    if idx == 0: await up(1)
    elif idx == 1: await up(3)
    elif idx == 2: await down(1)
    elif idx == 3: await down(3)
    elif idx == 4: await left(1)
    elif idx == 5: await left(3)
    elif idx == 6: await right(1)
    elif idx == 7: await right(3)
    elif idx == 8: await a()
    elif idx == 9: await b()
    elif idx == 10: await start()
    elif idx == 11: await select()
    await proceed(emoji, user)
    try:
        await main_message.clear_reaction("✅")
    except Exception:
        pass

# Actions Game Boy
async def start():
    set_input_wanted(WindowEvent.PRESS_BUTTON_START)
    await asyncio.sleep(PUSH_TIME)
    set_input_wanted(WindowEvent.RELEASE_BUTTON_START)

async def select():
    set_input_wanted(WindowEvent.PRESS_BUTTON_SELECT)
    await asyncio.sleep(PUSH_TIME)
    set_input_wanted(WindowEvent.RELEASE_BUTTON_SELECT)

async def a():
    set_input_wanted(WindowEvent.PRESS_BUTTON_A)
    await asyncio.sleep(PUSH_TIME)
    set_input_wanted(WindowEvent.RELEASE_BUTTON_A)

async def b():
    set_input_wanted(WindowEvent.PRESS_BUTTON_B)
    await asyncio.sleep(PUSH_TIME)
    set_input_wanted(WindowEvent.RELEASE_BUTTON_B)

async def up(multiplier):
    for _ in range(multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_UP)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_UP)

async def down(multiplier):
    for _ in range(multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_DOWN)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_DOWN)

async def left(multiplier):
    for _ in range(multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_LEFT)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_LEFT)

async def right(multiplier):
    for _ in range(multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_RIGHT)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_RIGHT)

async def proceed(emoji, user):
    await commit()
    image_url = await log_action(emoji, user)
    await send_new_screen(image_url, str(emoji), user, False)

async def commit():
    try:
        with open("rom/save_file.state", "wb") as save_file:
            pyboy.save_state(save_file)
    except Exception as e:
        print(f"Save failed: {e}")

async def send_new_screen(image_url, emoji, user, is_first):
    global main_message, main_channel
    if not main_channel:
        return
    if is_first:
        if main_message is not None:
            try:
                await main_message.delete()
            except Exception:
                pass
        embed = discord.Embed(title="Pokémon Rouge", description="", color=0xeeb840)
        embed.add_field(name="Initialisation", value="Initialiser le jeu en appuyant sur select", inline=False)
        main_message = await main_channel.send(embed=embed)
        for emote in EMOTE_LIST:
            try:
                await main_message.add_reaction(emote)
            except Exception:
                pass
    else:
        if not main_message:
            return
        embed = main_message.embeds[0] if main_message.embeds else discord.Embed(title="Pokémon Rouge", color=0xeeb840)
        embed.clear_fields()
        topic = getattr(main_message.channel, "topic", None)
        if topic:
            embed.add_field(name="__Objectif actuel :__", value=topic, inline=False)
        if image_url:
            embed.set_image(url=image_url)
        await main_message.edit(embed=embed)
        if emoji and user:
            try:
                await main_message.remove_reaction(emoji, user)
            except Exception:
                pass

async def log_action(emoji, user):
    global logs_channel
    if not logs_channel:
        return None
    await asyncio.sleep(0.5)
    try:
        pil_image = pyboy.screen.image
        new_image = pil_image.resize((320, 288))
    except Exception as e:
        print(f"Screen grab failed: {e}")
        return None
    embed = discord.Embed(title="Action enregistrée", description="", color=0xeeb840)
    if emoji.id:
        info = f"Le joueur <@{user.id}> a réagi avec <:{emoji.name}:{emoji.id}>."
    else:
        info = f"Le joueur <@{user.id}> a réagi avec {emoji.name}."
    embed.add_field(name="Informations sur le joueur:", value=info, inline=False)
    embed.set_image(url="attachment://image.png")
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    with io.BytesIO() as image_binary:
        new_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        log_message = await logs_channel.send(embed=embed, file=discord.File(fp=image_binary, filename='image.png'))
    try:
        return log_message.embeds[0].image.url
    except Exception:
        return None

bot.run(BOT_TOKEN)
