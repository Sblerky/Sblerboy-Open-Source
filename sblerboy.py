import discord
from discord.ext import commands
from pyboy import PyBoy
from pyboy import PyBoy
from pyboy import WindowEvent
import threading
import asyncio
import io
import time
import sys
import configparser
import ast

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
has_reacted = False
input_wanted = None

intents = discord.Intents.default()
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix='%',
                   description='Emulating...', intents=intents)

# Launch Pyboy
pyboy = PyBoy('rom/rom.gb', window_type="headless")
try:
    save_file = open("rom/save_file.state", "rb")
    pyboy.load_state(save_file)
except:
    print("No save file found")

# Set Variables
config = configparser.ConfigParser()
try:
    config.read('config.ini')
except:
    print("No config file found, the bot will shutdown")
    sys.exit()
ID_CHANNEL = int(config['DEFAULT']['ID_CHANNEL'])
ID_GUILD = int(config['DEFAULT']['ID_GUILD'])
ID_LOG_CHANNEL = int(config['DEFAULT']['ID_LOG_CHANNEL'])
ID_CHAT_CHANNEL = int(config['DEFAULT']['ID_CHAT_CHANNEL'])
EMOTE_LIST = ast.literal_eval(config['DEFAULT']['EMOTE_LIST'])
BOT_TOKEN = config['DEFAULT']['BOT_TOKEN']


def tick_thread():
    global input_wanted
    old_input = input_wanted
    old_time = int(round(time.time() * 1000))
    while True:
        if old_input != input_wanted:
            pyboy.send_input(input_wanted)
            old_input = input_wanted
        old_time = tick_pyboy(old_time)


def tick_pyboy(old_time):
    now = int(round(time.time() * 1000))
    if now - old_time > 1000 / FRAME_PER_SECONDS:
        pyboy.tick()
        return now
    return old_time


pyboy_thread = threading.Thread(target=tick_thread)
pyboy_thread.start()


def set_input_wanted(input):
    global input_wanted
    input_wanted = input


async def get_main_guild():
    for guild in bot.guilds:
        if guild.id == ID_GUILD:
            return guild
    return 0


async def get_channel(id_channel):
    global main_guild
    for channel in main_guild.channels:
        if channel.id == id_channel:
            return channel
    return 0


async def get_or_send_message(channel_param):
    global main_message
    history = [history async for history in channel_param.history(limit=1)]
    if len(history) > 0:
        main_message = history[0]
        await send_new_screen(None, None, None, True)
    else:
        print("No message found")
        await send_new_screen(None, None, None, True)


@bot.event
async def on_ready():
    global main_guild
    global main_channel
    global logs_channel
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    activity = discord.Game(name="%help")
    main_guild = await get_main_guild()
    if main_guild != 0:
        main_channel = await get_channel(ID_CHANNEL)
    if main_channel != 0:
        await get_or_send_message(main_channel)
    if main_guild != 0:
        logs_channel = await get_channel(ID_LOG_CHANNEL)
        print('Init complete')

    print('------')
    await bot.change_presence(status=discord.Status.online, activity=activity)

bot.remove_command('help')


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Sblerboy", url="https://www.youtube.com/channel/UCLT5UPUWMaeZQznyQb1FsKA/?sub_confirmation=1",
                          description="Le meilleur émulateur Gameboy", color=0xeeb840)
    embed.set_author(name="Sblerboy", url="https://www.youtube.com/channel/UCLT5UPUWMaeZQznyQb1FsKA/?sub_confirmation=1",
                     icon_url="https://st2.depositphotos.com/25611412/46754/v/600/depositphotos_467548434-stock-illustration-gameboy-flat-illistration-old-game.jpg")
    embed.set_footer(
        text="Créé par Sblerky(franchement va t'abonner ça vaut le coup)")
    fonctionnement = "Sblerboy implémente un émulateur de Gameboy directement dans discord.  Actuellement, il vous permet de jouer à Pokémon version Rouge via des réactions à un message dans <#{main_channel_format}>\n\nLe principe de fonctionnement est simple, vous appuyez sur une réaction et le bot ajoute l'emoji :white_check_mark: au message pour vous dire qu'il a bien pris en compte votre action. Ensuite il va retranscrire cette action dans l'émulateur et mettre à jour le screen du message avec le nouvel état du jeu. Quand le bot enlève l'emoji :white_check_mark: , il est prêt à recevoir une nouvelle action (mais pas avant).\n\nLe but est bien sur de finir le jeu. Vous pouvez suivre l'avancement dans le salon <#{logs_channel_format}>  et vous pouvez discuter du jeu ou faire remonter des bugs dans <#{chat_channel_format}>\n\nA la fin du jeu, la personne qui aura le plus contribué à l'avancement du jeu recevra en récompense un rôle unique ainsi que le statut de VIP du serveur (si elle ne l'est pas déjà). ".format(
        main_channel_format=ID_CHANNEL, logs_channel_format=ID_LOG_CHANNEL, chat_channel_format=ID_CHAT_CHANNEL)
    embed.add_field(name="Principe de fonctionnement",
                    value=fonctionnement, inline=False)
    await ctx.send(embed=embed)


@bot.event
async def on_raw_reaction_add(ctx):
    global main_message
    global has_reacted
    if ctx.message_id == main_message.id and ctx.member.id != bot.user.id and not has_reacted:
        await process_reaction(ctx, ctx.emoji, ctx.member)


async def process_reaction(ctx, emoji, user):
    global has_reacted
    global main_message
    full_emoji_name = emoji.name + ":" + str(emoji.id)
    if emoji.name in EMOTE_LIST:
        full_emoji_name = emoji.name
    if full_emoji_name in EMOTE_LIST:
        has_reacted = True
        # Let the user know it's being processed
        await main_message.add_reaction("\U00002705")
        # Big ugly switch
        if full_emoji_name == EMOTE_LIST[0]:
            await up(1)
        if full_emoji_name == EMOTE_LIST[1]:
            await up(3)
        if full_emoji_name == EMOTE_LIST[2]:
            await down(1)
        if full_emoji_name == EMOTE_LIST[3]:
            await down(3)
        if full_emoji_name == EMOTE_LIST[4]:
            await left(1)
        if full_emoji_name == EMOTE_LIST[5]:
            await left(3)
        if full_emoji_name == EMOTE_LIST[6]:
            await right(1)
        if full_emoji_name == EMOTE_LIST[7]:
            await right(3)
        if full_emoji_name == EMOTE_LIST[8]:
            await a()
        if full_emoji_name == EMOTE_LIST[9]:
            await b()
        if full_emoji_name == EMOTE_LIST[10]:
            await start()
        if full_emoji_name == EMOTE_LIST[11]:
            await select()
        await proceed(ctx, full_emoji_name, user)
        await main_message.clear_reaction("\U00002705")
        has_reacted = False


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
    for i in range(0, multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_UP)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_UP)


async def down(multiplier):
    for i in range(0, multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_DOWN)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_DOWN)


async def left(multiplier):
    for i in range(0, multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_LEFT)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_LEFT)


async def right(multiplier):
    for i in range(0, multiplier):
        set_input_wanted(WindowEvent.PRESS_ARROW_RIGHT)
        await asyncio.sleep(PUSH_TIME)
        set_input_wanted(WindowEvent.RELEASE_ARROW_RIGHT)


async def proceed(ctx, emoji, user):
    await commit()
    image = await log_action(emoji, user)
    await send_new_screen(image, emoji, user, False)


async def commit():
    save_file = open("rom/save_file.state", "wb")
    pyboy.save_state(save_file)


async def send_new_screen(image, emoji, user, is_first):
    global main_message
    global main_channel
    if is_first:
        if main_message != None:
            await main_message.delete()
        embed = discord.Embed(title="Pokémon Rouge",
                              description="", color=0xeeb840)
        embed.add_field(name="Initialisation",
                        value="Initialiser le jeu en appuyant sur select", inline=False)
        main_message = await main_channel.send(embed=embed)
        for emote in EMOTE_LIST:
            await main_message.add_reaction(emote)
    else:
        topic = main_message.channel.topic
        embed = main_message.embeds[0]
        embed.clear_fields()
        if topic != None:
            embed.add_field(name="__Objectif actuel :__",
                            value=topic, inline=False)
        embed.set_image(url=image)
        await main_message.edit(embed=embed)
        cache_msg = await main_channel.fetch_message(main_message.id)
        await main_message.remove_reaction(emoji, user)


async def log_action(emoji, user):
    global logs_channel
    await asyncio.sleep(0.5)
    screen_object = pyboy.botsupport_manager().screen()
    new_image = screen_object.screen_image()
    new_image = new_image.resize((320, 288))

    embed = discord.Embed(title="Action enregistrée",
                          description="", color=0xeeb840)
    if ":" in emoji:
        embed.add_field(name="Informations sur le joueur: ", value="Le joueur <@" +
                        str(user.id)+"> a réagi avec <:" + emoji + ">.", inline=False)
    else:
        embed.add_field(name="Informations sur le joueur: ", value="Le joueur <@" +
                        str(user.id)+"> a réagi avec " + emoji + ".", inline=False)
    embed.set_image(url="attachment://image.png")
    embed.set_thumbnail(url=user.avatar)

    with io.BytesIO() as image_binary:
        new_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        log_message = await logs_channel.send(embed=embed, file=discord.File(fp=image_binary, filename='image.png'))
        return log_message.embeds[0].image.url


bot.run(BOT_TOKEN)
