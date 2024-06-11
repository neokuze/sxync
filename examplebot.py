#! /usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import time
import sys
import sxync

class config:
    prefix = ["!"]
    botuser = ["us3rname", "password_0f_bot"] # user_name, password
    rooms = ['examplegroup']

class Super(sxync.client.Bot):
    async def on_init(self):
        pass # init something here

    async def on_connect(self, room):
        print(f"[info] Joining {room.name}.")

    async def on_disconnect(self, room):
        print(f"[info] Leaving {room.name}.")

    async def on_reconnect(self, room):
        print(f"[info] Reconnecting in {room.name}.")

    async def on_message(self, message):
        user = f"{message.user.showname if message.user.showname is None else message.user.name}"
        print(time.strftime("%b/%d-%H:%M:%S", time.localtime(message.time)),
              message.room.name, user , ascii(message.body)[1:-1])
        message_content = message.body
        if len(message_content.split()) > 1:
            cmd, args = message_content.split(" ", 1)
            args = args.split()
        else:
            cmd, args = message_content, []
        cmd = cmd.lower()
        if cmd[0] in config.prefix:
            use_prefix = True
            cmd = cmd[1:]
        else: 
            use_prefix = False
        if use_prefix:
            if cmd in ['id']:
                await message.room.send_msg(f"You are {message.user.id}") 
            elif cmd in ['hello', 'test', 'a']:
                await message.room.send_msg(f"Hello {user}") #user must me be handle by id.
            

bot = Super(config.botuser[0], config.botuser[1], config.rooms)

async def main():
    await bot.start()

async def stop():
    await bot.stop_all()
    
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(start())
    loop.run_forever()
except KeyboardInterrupt:
    print("[bot] Killed by end user.")
finally:
    loop.run_until_complete(stop())
    # loop.run_until_complete(cfg.save_all()) # aiofiles
    loop.close()
    sys.exit()
