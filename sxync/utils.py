
def cleanText(text):
    """Regresa texto en minúsculas y sin acentos :> thx linkkg"""
    text = text.lower().strip()
    clean = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "@": "", "?": "", "!": "!", ",": "", ".": "", "¿": ""
        }
    for y in clean:
        if y in text:
            text = text.replace(y, clean[y])
    return text

def public_attributes(obj):
    return [
        x for x in set(list(obj.__dict__.keys()) + list(dir(type(obj)))) if x[0] != "_"
    ]