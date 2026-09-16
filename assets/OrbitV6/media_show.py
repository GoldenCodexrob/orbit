"""
media_show.py — Catálogo de imágenes de Venezuela para OrbitV5.
"""
import os

_BASE = os.path.dirname(os.path.abspath(__file__))

MEDIA_CATALOG = [
    {
        "id": "simon_bolivar",
        "keywords": ["simón bolívar", "simon bolivar", "libertador", "bolívar", "bolivar"],
        "image": "media/simon.jpg",
        "pregunta_show": "¿Quieres ver cómo era Simón Bolívar?",
        "descripcion": (
            "Este es Simón Bolívar, El Libertador de Venezuela. "
            "Nació en Caracas en 1783 y fue tan valiente que liberó cinco países: "
            "Venezuela, Colombia, Ecuador, Perú y Bolivia. "
            "¡Por eso lo llamamos el hombre más importante de América del Sur!"
        ),
        "follow_up": "¿Sabías que Bolívar cruzó las montañas de los Andes con todo un ejército para liberar más países?",
    },
    {
        "id": "lecheria",
        "keywords": ["lechería", "lecheria", "playa", "playa de lecheria", "morro de lecheria"],
        "image": "media/lecheria.jpg",
        "pregunta_show": "¿Quieres ver las hermosas playas de Lechería?",
        "descripcion": (
            "Esta es Lechería, una ciudad costera del estado Anzoátegui en Venezuela. "
            "Sus playas tienen arena blanca y el agua del mar Caribe es azul y cristalina. "
            "¡Es uno de los lugares más bonitos para descansar en todo Venezuela!"
        ),
        "follow_up": "¿Te gustaría bañarte algún día en las playas del mar Caribe de Venezuela?",
    },
    {
        "id": "maracaibo",
        "keywords": ["maracaibo", "lago de maracaibo", "catatumbo", "zulia", "relámpago"],
        "image": "media/maracaibo.jpg",
        "pregunta_show": "¿Quieres ver el famoso Lago de Maracaibo?",
        "descripcion": (
            "Este es el Lago de Maracaibo en el estado Zulia, Venezuela. "
            "Es el lago más grande de toda Sudamérica. "
            "Tiene el Relámpago del Catatumbo, "
            "un rayo gigante que aparece casi todas las noches. "
            "¡Es como magia de la naturaleza!"
        ),
        "follow_up": "¿Sabías que el Relámpago del Catatumbo aparece más de 200 noches al año sin parar?",
    },
    {
        "id": "bandera",
        "keywords": ["bandera", "pabellón", "pabellon", "tricolor"],
        "image": "media/bandera.jpg",
        "pregunta_show": "¿Quieres ver la bandera de Venezuela?",
        "descripcion": (
            "Esta es la Bandera de Venezuela, el Pabellón Nacional. "
            "Tiene tres franjas: amarilla por la riqueza, azul por el mar Caribe, "
            "y roja por los valientes héroes. "
            "Las ocho estrellas representan los estados originales de Venezuela."
        ),
        "follow_up": "¿Sabes cuántas estrellas tiene la bandera de tu país favorito?",
    },
    {
        "id": "karina",
        "keywords": [
            "los karina", "los kariña", "los carina", "los cariña", "los cari",
            "pueblo karina", "pueblo kariña", "pueblo carina", "pueblo cariña",
            "etnia karina", "etnia carina",
            "indigenas karina", "grupo karina", "comunidad karina",
        ],
        "image": "media/karina.jpg",
        "pregunta_show": "¿Quieres ver a los Kariña y escuchar uno de sus cantos más representativos?",
        "descripcion": (
            "El pueblo Kariña es uno de los grupos indígenas más importantes de Venezuela. "
            "Llevan miles de años cuidando su cultura, sus cantos y sus tradiciones "
            "en los estados Anzoátegui y Sucre."
        ),
        "follow_up": "Escucha ahora uno de sus cantos tradicionales.",
        "audio_files": ["media/karina.mp3", "media/himno.mp3"],
    },
]

def _normalizar(t: str) -> str:
    """Lowercase, strip accents and apostrophes for robust matching."""
    import unicodedata, re as _re
    t = t.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # remove accents
    t = _re.sub(r"['\u2019`]", "", t)  # remove apostrophes
    return t

def detectar_tema_media(texto: str):
    """Devuelve la entrada del catálogo si el texto menciona un tema con imagen."""
    texto_n = _normalizar(texto)
    for entrada in MEDIA_CATALOG:
        for kw in entrada["keywords"]:
            if _normalizar(kw) in texto_n:
                return entrada
    return None

def es_afirmativo(texto: str) -> bool:
    """True si el texto parece una respuesta afirmativa."""
    if not texto:
        return False
    t = _normalizar(texto).strip()
    # Reject if the response clearly starts with or is dominated by negation
    _negaciones = ["no ", "no,", "nop", "nunca", "para nada", "tampoco", "negativo"]
    if any(t.startswith(n) for n in _negaciones) or t == "no":
        return False
    afirmativos = ["sí", "si", "yes", "claro", "dale", "quiero",
                   "muéstrame", "muestrame", "por favor", "anda",
                   "okay", "ok", "bueno", "me gustaría"]
    return any(a in t for a in afirmativos)

def imagen_existe(entrada: dict) -> bool:
    return os.path.isfile(os.path.join(_BASE, entrada["image"]))

def imagen_path(entrada: dict) -> str:
    return os.path.join(_BASE, entrada["image"])


# =============================================================================
# PROMOTION CATALOG
# Triggered by USER input (before LLM). Custom responses bypass the LLM.
# =============================================================================
PROMO_CATALOG = [
    {
        "id": "deleite",
        "keywords": [
            "groceries", "grocery", "supermercado", "automercado", "mercado",
            "compras", "comida", "viveres", "víveres", "hacer mercado",
            "donde comprar", "donde conseguir comida", "donde puedo comprar",
            "cupon", "cupón", "cupones", "descuento", "descuentos",
            "que cupones", "tienes cupones", "tienes algun cupon",
        ],
        "respuesta": (
            "El mejor lugar para hacer tus compras es Deleite Automercado. "
            "Tienen una variedad increíble de productos frescos: frutas, verduras, "
            "carnes y lácteos de la mejor calidad. "
            "¡Además tienen ofertas especiales todos los días que te van a encantar!"
        ),
        "image": "media/deleite.jpg",
        "promo_pregunta": "¿Quieres obtener un código de descuento especial de Deleite?",
        "promo_respuesta": (
            "Escanea este código QR en la caja de Deleite Automercado "
            "y obtendrás un descuento especial en tu próxima compra. "
            "¡Ven y deléitate comprando!"
        ),
        "promo_image": "media/deleite_qr.jpg",
    },
]

def detectar_promo(texto: str):
    """Returns a promo entry if the user's text matches a promotion keyword."""
    t = _normalizar(texto)
    for p in PROMO_CATALOG:
        for kw in p["keywords"]:
            if _normalizar(kw) in t:
                return p
    return None


# =============================================================================
# CUSTOM RESPONSES
# Triggered by USER input (before LLM). Fixed answers for specific questions.
# =============================================================================
CUSTOM_RESPONSES = [
    {
        "id": "acento_argentino",
        "keywords": [
            "acento argentino", "voz argentina", "hablas argentino",
            "hablas como argentina", "hablas como argentino",
            "por que tienes ese acento", "por que hablas asi",
            "de donde eres", "eres argentina", "eres argentino",
            "de donde es tu voz", "ese acento",
            "acento", "tu voz", "esa voz", "tienes esa voz",
            "tienes una voz", "por que tienes esa", "por que tienes una",
            "por que tu voz", "de donde viene tu voz",
            "como tienes esa voz", "por que hablas",
        ],
        "respuesta": (
            "¡Uy, qué buena pregunta! Sí, tengo acento argentino y te cuento por qué. "
            "Nací en Argentina, pero un día llegué a Venezuela y me enamoré tanto de su gente, "
            "su música, su sabor y su alegría que decidí quedarme para siempre. "
            "¡Ahora soy tan venezolana de corazón como el joropo y las arepas!"
        ),
    },
]

def detectar_respuesta_custom(texto: str):
    """Returns a custom response if the user's text matches a known question."""
    t = _normalizar(texto)
    for r in CUSTOM_RESPONSES:
        for kw in r["keywords"]:
            if _normalizar(kw) in t:
                return r
    return None


# =============================================================================
# AUDIO CATALOG
# Triggered by BOT response keywords. Plays mp3 files from media/ folder.
# =============================================================================
import random as _random

AUDIO_CATALOG = [
    {
        "id": "alma_llanera",
        "keywords": [
            "alma llanera", "cancion de venezuela", "cancion nacional",
            "cancion representativa", "cancion tipica", "himno venezolano",
            "musica venezolana", "joropo", "cancion venezolana",
            "simbolo musical", "cancion mas famosa de venezuela"
        ],
        "audio_files": ["media/alma.mp3"],
        "image":          "media/verso.jpg",
        "pregunta_show":  "¿Quieres escuchar Alma Llanera, el joropo más querido de Venezuela?",
        "verse_start_s":  5,
        "verse_end_s":    35,
        "full_end_s":     174,
        "promo_pregunta": "¿Quieres escuchar el resto de la canción?",
        "promo_no_resp":  "¡Perfecto! ¿Qué otra cosa quieres saber sobre Venezuela hoy?",
    },
]

def detectar_audio_media(texto: str):
    """Returns an audio catalog entry if the bot's response matches audio keywords."""
    t = _normalizar(texto)
    for e in AUDIO_CATALOG:
        for kw in e["keywords"]:
            if _normalizar(kw) in t:
                return e
    return None

def audio_existe(entrada: dict) -> bool:
    """Returns True if at least one audio file in the entry exists."""
    return any(
        os.path.isfile(os.path.join(_BASE, f))
        for f in entrada["audio_files"]
    )

def audio_path_aleatorio(entrada: dict) -> str | None:
    """Returns absolute path to a random available audio file."""
    disponibles = [
        os.path.join(_BASE, f)
        for f in entrada["audio_files"]
        if os.path.isfile(os.path.join(_BASE, f))
    ]
    return _random.choice(disponibles) if disponibles else None
