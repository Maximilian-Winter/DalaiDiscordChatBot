# bot.py
import asyncio
import os
import logging
from datetime import time
import aiohttp

import discord
from discord import app_commands, message, Message
from discord import Embed

from dotenv import load_dotenv

import json
import socketio
import time
import random

# Socket.IO setup
sio = socketio.Client()


@sio.event
def connect():
    print("Connected to the Socket.IO server")


@sio.event
def disconnect():
    print("Disconnected from the Socket.IO server")


def on_cancel():
    sio.emit('request', {'prompt': '/stop'})


@sio.event
def result(data):
    global output_text
    output_text += data['response']


def on_submit(prompt):
    config['prompt'] = create_prompt(prompt)
    config['id'] = "TS-" + str(int(time.time())) + "-" + str(int(random.random() * 100000))
    sio.emit('request', config)
    config['id'] = None


def create_prompt(instruction, input_data=None):
    if input_data:
        return f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.
                ### Instruction:
                {instruction}
                ### Input:
                {input_data}
                ### Response:
                """
    else:
        return f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.
                ### Instruction:
                {instruction}
                ### Response:
                """


# Load config from local storage (use a file instead)
#try:
#    with open("config.json", "r") as f:
#        config = json.load(f)
#except (FileNotFoundError, json.JSONDecodeError):
config = {
    "seed": -1,
    "threads": 16,
    "n_predict": 800,
    "top_k": 40,
    "top_p": 0.9,
    "temp": 0.8,
    "repeat_last_n": 64,
    "repeat_penalty": 1.3,
    "debug": False,
    "models": ["alpaca.7B", "alpaca.30B"],
    "model": "alpaca.7B"
}

# Replace 'http://localhost:3000' with the URL of your Socket.IO server
url = "http://localhost:3000"
sio.connect(url)


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        pass
        # This copies the global commands over to your guild.
        # self.tree.copy_global_to(guild=MY_GUILD)
        # await self.tree.sync(guild=MY_GUILD)


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MY_GUILD = discord.Object(id=int(os.getenv('DISCORD_GUILD')))
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.none()
client = MyClient(intents=intents)
intents.messages = True
output_text = ""
is_generating_chat_result = False
@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')


@client.tree.command(name='chatai')
@app_commands.describe(
    prompt='Your chat prompt.',
)
async def chat(interaction: discord.Interaction, prompt: str):
    """Chat with MaxPowerChat"""
    global is_generating_chat_result
    global output_text
    channel = interaction.channel
    await interaction.response.send_message(f'Please Wait.')
    if is_generating_chat_result:
        on_cancel()
        await asyncio.sleep(10)
        output_text = ""

    on_submit(prompt)
    is_generating_chat_result = True
    cmp_str = f'Compute Result'
    msg = await channel.send(cmp_str)
    while output_text.find("[end of text]") == -1:
        await asyncio.sleep(5)
        if output_text != "":
            if len(output_text) > 1950:
                msg = await channel.send(cmp_str)
            await msg.edit(content=output_text)

    await msg.edit(content=output_text)
    embed = Embed(title="Chat:",
                  description=prompt, color=0x93C54B)
    embed.add_field(name="Answer:", value=str(output_text), inline=False)
    # await msg.edit(embed=embed, content=None)
    output_text = ""
    is_generating_chat_result = False

# Save the config to a file when the application is closed
with open("config.json", "w") as f:
    json.dump(config, f)
    
    
client.run(TOKEN)


