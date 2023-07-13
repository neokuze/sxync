#! /usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import time
import sxync

class config:
    prefix = ["!"]
    botuser = ["tester", "passwd"]
    rooms = ['sudoers']

class Super(sxync.client.Bot):
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
            if cmd in ['hello', 'test', 'a']:
                await message.room.send_msg(f"Hello {user}") #user must me be handle by id.

    async def on_connect(self, room):
        print(f"[info] Estoy conectado en {room.name}.")

bot = Super(config.botuser[0], config.botuser[1], config.rooms)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(bot.start())
    loop.run_forever()
except KeyboardInterrupt:
    print("[KeyboardInterrupt] Killed bot.")
finally:
    loop.run_until_complete(bot.stop_all())
