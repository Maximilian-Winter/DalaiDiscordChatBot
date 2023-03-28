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


def on_submit(prompt, last_response):
    config['prompt'] = create_prompt(prompt, last_response)
    config['id'] = "TS-" + str(int(time.time())) + "-" + str(int(random.random() * 100000))
    sio.emit('request', config)
    config['id'] = None


def create_prompt(instruction, last_response=None):
    if last_response:
        return f"""You are a helpful and obedient chat bot, with the name 'BadMotherfucker'. You live in Max Power's Computer. Below is your last response followed by a new chat message from the user. Write a helpful and fitting response to it.
                        ### Last Response:
                        {last_response}
                        ### Message:
                        {instruction}
                        ### Response:
                        """
    else:
        return f"""You are a helpful and obedient chat bot, with the name 'BadMotherfucker'. You live in Max Power's Computer. Below is a chat message from a user. Write a helpful and fitting response to it.
                ### Message:
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
    "threads": 24,
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
old_output = ""

def to_utf8_compatible(input_string):
    if isinstance(input_string, str):
        return input_string.encode('utf-8', errors='replace').decode('utf-8')
    else:
        raise TypeError("Input must be a string")


def extract_text(input_str):
    end_idx = input_str.find("[end of text]")
    if end_idx == -1:
        return input_str
    else:
        return input_str[:end_idx]


def remove_x(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("X"):
            lines[i] = line[1:]
    return "\n".join(lines)


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
    global old_output
    marker = "### Response:"
    channel = interaction.channel

    if is_generating_chat_result:
        await interaction.response.send_message(f'Please Wait For The Other Response To Be Complete!')
        return False
    else:
        await interaction.response.send_message(f"Please Wait!\n'{prompt}'")

    if old_output != "":
        on_submit(prompt, old_output)
    else:
        on_submit(prompt, None)
    is_generating_chat_result = True
    cmp_str = f'Compute Result'
    msg = await channel.send(cmp_str)
    final_msg = ""
    while output_text.find("[end of text]") == -1:
        await asyncio.sleep(5)
        if output_text != "":
            if marker in output_text:
                response_start = output_text.index(marker) + len(marker)
                if len(output_text[response_start:].strip()) > 1950:
                    msg = await channel.send(cmp_str)
                final_msg = to_utf8_compatible(extract_text(remove_x(output_text[response_start:].strip())))
                await msg.edit(content=final_msg)
    response_start = output_text.index(marker) + len(marker)
    final_msg = to_utf8_compatible(extract_text(remove_x(output_text[response_start:].strip())))
    await msg.edit(content=to_utf8_compatible(extract_text(remove_x(final_msg))))
    embed = Embed(title="Chat:",
                  description=prompt, color=0x93C54B)
    embed.add_field(name="Answer:", value=str(output_text), inline=False)
    # await msg.edit(embed=embed, content=None)
    output_text = ""
    is_generating_chat_result = False
    old_output = final_msg
    await channel.send(f"Response completed!")

# Save the config to a file when the application is closed
with open("config.json", "w") as f:
    json.dump(config, f)


client.run(TOKEN)



