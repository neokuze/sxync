import sys, os
import sxync

for_owners = True
for_anons = False

async def Run(self, message, args, lcs):
    # load_cmds = lcs['cfg'].load_cmds
    if args:
        locs = {}
        try:
            # Just for python 3.9 >=
            glibs = globals() | locals()
            string = 'async def execute(): return ' + " ".join(args)
            exec(string, glibs, locs)
            r = await locs["execute"]()
        except Exception as E:
            r = sys.exc_info()[1].args[0]
        if r == None:
            r = "Done."
        return str(r)
    return  "no arguments ;("
