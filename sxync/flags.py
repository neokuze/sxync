from .utils import public_attributes

class RoomFlags:
    def __init__(self, data):
        self.BANEABLE = data.get('BANEABLE', False)
        self.IS_MOD = data.get('IS_MOD', False)
        self.IS_OWNER = data.get('IS_OWNER', 0)
        self.DELETE_MESSAGES = data.get('DELETE_MESSAGES', 0)
        self.DELETE_OWN_MESSAGES = data.get('DELETE_OWN_MESSAGES', 0)
        self.DUMMY = data.get('DUMMY', 0)
        self.DELETE_ALL_MESSAGES = data.get('DELETE_ALL_MESSAGES', 0)
        self.EDIT_OWN_MESSAGES = data.get('EDIT_OWN_MESSAGES', 0)
        self.ROOM_INFO = data.get('ROOM_INFO', 0)
        self.ROOM_SETTINGS = data.get('ROOM_SETTINGS', 0)
        self.ROOM_RESTRICTIONS = data.get('ROOM_RESTRICTIONS', 0)
        self.FLAG_USER = data.get('FLAG_USER', 0)
        self.SEE_IPS = data.get('SEE_IPS', 0)
        self.BAN_USERS = data.get('BAN_USERS', 0)
        self.UNBAN_USERS = data.get('UNBAN_USERS', 0)
        self.ADD_MOD = data.get('ADD_MOD', 0)
        self.CHANGE_MODS = data.get('CHANGE_MODS', 0)
        self.flag = data.get('flag', 0)

    def __dir__(self):
        return public_attributes(self)