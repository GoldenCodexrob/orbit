"""
=============================================================================
🧠 CEREBRO_V4.PY — Motor de Inteligencia, Carisma y Enrutamiento Ultra-Rápido
=============================================================================
Tecnología fusionada Orbit + HERO:
- Prompt carismático venezolano: breve (2-3 oraciones), enérgico, educado ("pana", "fino").
- Inyección de contexto visual real (halago de gorra o color de ropa).
- Enriquecimiento RAG con fragmentos de la base cultural y de la WRO 2026.
- Enrutamiento híbrido:
  1. Groq / Gemini Cloud (ultrarrápido, ~250 ms)
  2. Ollama Local con qwen2.5:0.5b (ultrarrápido en CPU)
  3. Respaldo Offline Inteligente (nunca se queda callado)
=============================================================================
"""

import os
import re
import json
import random
import requests
import unicodedata
from rag_conocimiento import BaseConocimiento

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Cargar .env de forma nativa sin requerir librerías externas
def _cargar_env_local():
    for ruta in [
        os.path.join(_BASE_DIR, ".env"),
        os.path.join(_BASE_DIR, ".env.example"),
        os.path.join(_BASE_DIR, "HERO", "ProyectoDeRobotica-master", "api_key.env"),
        os.path.join(os.path.dirname(_BASE_DIR), "Orbit V2.0", "Codes V2.0", "asistente_ia_venezuela", ".env")
    ]:
        if os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if linea and not linea.startswith("#") and "=" in linea:
                            k, v = linea.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            # Si es la key vieja que expiró (401), sustituirla por la activa
                            if k == "GOOGLE_API_KEY" and ("INVALID_KEY_PREFIX" in v or len(v) < 10):
                                v = DEFAULT_GOOGLE_API_KEY
                            if k not in os.environ or (k == "GOOGLE_API_KEY" and "INVALID_KEY_PREFIX" in os.environ.get(k, "")):
                                os.environ[k] = v
            except Exception:
                pass

    if "GOOGLE_API_KEY" not in os.environ or "INVALID_KEY_PREFIX" in os.environ.get("GOOGLE_API_KEY", ""):
        os.environ["GOOGLE_API_KEY"] = DEFAULT_GOOGLE_API_KEY

_cargar_env_local()

CHISTES_VENEZOLANOS = [
    "¿Qué le dice una empanada a otra en la sartén? ¡Chamo, bájale dos que nos estamos tostando!",
    "¿Por qué el béisbol es el deporte favorito en Venezuela? Porque hasta los problemas los botamos de jonrón.",
    "¿Cómo saluda un robot maracucho? ¡Epa vergación primo, qué molleja de calor hace aquí!"
]

CHISTES_INGLES = [
    "Why did the Venezuelan arepa go to school? Because it wanted to be a smartie with extra delicious cheese!",
    "Why is baseball so popular in Venezuela? Because we hit even our biggest problems out of the park with a home run!",
    "What did Orbit say when visiting Angel Falls? Wow, my circuits are overflowing with excitement!"
]

RESPUESTAS_RAPIDAS = {
    "hola": "¡Qué alegría seguir compartiendo contigo! ¿Te gustaría descubrir tradiciones y curiosidades culturales de Venezuela, Puerto Rico o el mundo?",
    "como estas": "¡Estoy súper emocionado y feliz de compartir contigo hoy! ¿Qué te gustaría descubrir sobre nuestra cultura?",
    "quien eres": "¡Soy Orbit, un robot embajador cultural creado por el equipo Golden Codex de Venezuela! Me encanta compartir tradiciones, música, comidas típicas e historias de nuestra tierra y de Puerto Rico. ¿Quieres que te cuente una historia genial?",
    "adios": "¡Hasta luego! Me encantó conversar contigo. ¡Que tengas un día súper genial!"
}

RESPUESTAS_RAPIDAS_EN = {
    "hello": "It is wonderful to continue sharing with you! What cultural wonders would you like to explore today?",
    "hi": "So happy to chat with you! What would you like to discover today?",
    "how are you": "I am doing fantastic and so happy to share amazing cultural stories with you today! What would you like to learn about?",
    "who are you": "I am Orbit, a friendly robot cultural ambassador created by Golden Codex from Venezuela! I love sharing traditions, music, typical foods, and stories from our land and Puerto Rico. Would you like to hear a fascinating story?",
    "goodbye": "Goodbye! I had so much fun chatting with you. Have a super awesome day!",
    "bye": "Bye! Have a wonderful day, and see you next time!"
}

class CerebroV4:
    def __init__(self, db: BaseConocimiento = None):
        self.db = db or BaseConocimiento()
        self.historial = []
        self.max_historial = 8
        self.language = os.getenv("ORBIT_LANGUAGE", "en").lower()
        self.tema_actual = None
        self.ofrecio_alma_llanera = False
        self.ofrecio_viejo_san_juan = False
        self.ofrecio_caballo_viejo = False
        self.ofrecio_verde_luz = False
        self.ofrecio_venezuela = False
        self.ofrecio_rawayana = False
        self.ofrecio_pr_pop = False
        self.ofrecio_preciosa = False
        self.ofrecio_world = False
        self.ofrecio_promo_deleite = False
        self.ofrecio_promo_casita_blanca = False
        self.ofrecio_saludo_karina = False
        self.ofrecio_musica_karina = False
        self.cancion_reproducida_reciente = None
        self.accion_pendiente = None
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY", DEFAULT_GOOGLE_API_KEY)
        if not self.gemini_api_key or "INVALID_KEY_PREFIX" in self.gemini_api_key:
            self.gemini_api_key = DEFAULT_GOOGLE_API_KEY
        self.gemini_model = os.getenv("LLM_MODEL", "gemini-flash-lite-latest")
        self.ollama_api_key = os.getenv("OLLAMA_API_KEY")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    MAPA_TEMAS = {
        "simon bolivar": ["simon bolivar", "bolivar", "libertador"],
        "arepas": ["arepa", "arepas", "reina pepiada", "harina pan"],
        "hallacas": ["hallaca", "hallacas"],
        "tequeños": ["tequeno", "tequenos", "tequeño", "tequeños"],
        "pabellon": ["pabellon", "pabellón"],
        "cachapas": ["cachapa", "cachapas"],
        "lecheria": ["lecheria", "el morro", "playa mansa"],
        "roraima": ["roraima", "monte roraima"],
        "canaima": ["canaima", "salto angel", "salto ángel", "angel falls"],
        "morrocoy": ["morrocoy", "cayo sombrero"],
        "los roques": ["los roques", "gran roque"],
        "caracas": ["caracas", "avila", "el avila"],
        "maracaibo": ["maracaibo", "catatumbo", "lago de maracaibo"],
        "barcelona": ["barcelona", "aduana de barcelona", "catedral de barcelona"],
        "puerto la cruz": ["puerto la cruz", "paseo colon"],
        "beisbol": ["beisbol", "béisbol", "leones", "magallanes", "tiburones"],
        "venezuela": ["venezuela", "pais", "nacion", "independencia", "historia de venezuela", "cuantos anos", "cuantos años", "cumpleanos"],
        "hero": ["hero", "amigo", "mejor amigo", "best friend", "amigos", "friends", "hermano robotico"],
        "orbit": ["orbit", "golden codex", "wro"],
        "puerto rico": ["puerto rico", "puertorico", "boricua", "boriken", "borinquen", "isla del encanto"],
        "san juan": ["san juan", "viejo san juan", "el morro", "san cristobal", "castillo san felipe"],
        "el yunque": ["yunque", "el yunque", "coqui", "coquí", "cotorra puertorriquena", "cotorra puertorriqueña"],
        "mofongo": ["mofongo", "trifongo", "alcapurria", "bacalaito", "bacalaíto", "tembleque", "lechon", "lechón", "guavate"],
        "bahias bioluminiscentes": ["bioluminiscente", "bioluminiscentes", "bahia mosquito", "bahía mosquito", "laguna grande", "la parguera", "vieques"],
        "playas puerto rico": ["flamenco", "culebra", "crash boat", "luquillo", "cabo rojo", "playa sucia"],
        "musica puerto rico": ["bomba", "plena", "bomba y plena", "cuatro puertorriqueno", "cuatro puertorriqueño", "sanse", "calle san sebastian", "calle san sebastián"],
        "aventura puerto rico": ["toro verde", "el monstruo", "orocovis", "rio camuy", "cueva clara", "rincon", "camuy"],
        "indigenas karinas": ["carina", "carinas", "cariña", "cariñas", "karina", "karinas", "kariña", "kariñas", "cariño", "cariños", "carino", "carinos", "guanipa", "mesa de guanipa", "akaatompo", "cantaura", "yapucuru sema", "yupua", "moruwa", "kurupo"],
        "indigenas tainos boricua": ["taino", "tainos", "taíno", "taínos", "boriken", "borinquen", "boricua", "boricuas", "indigenas de puerto rico", "lengua taina", "idioma taino", "tau", "dak'ro buk", "dansikabu", "agueybana", "agüeybaná", "caguana", "batey", "jajom", "jajóm"],
        "isla la tortuga": ["isla la tortuga", "isla tortuga", "la tortuga", "tortuga", "cayo herradura", "los tortuguillos", "palanquines"],
        "maximiliano": ["maximiliano", "silvani", "silvagni", "max", "rodriguez silvani", "rodriguez silvagni"],
        "deleite": ["deleite", "deleite automercado", "automercado deleite", "mercado", "hacer mercado", "supermercado", "automercado", "compras", "víveres", "viveres", "comprar comida", "donde mercar", "groceries", "supermarket"],
        "joropo": ["joropo", "el joropo", "alma llanera", "musica llanera", "música llanera", "arpa cuatro y maracas", "zapateo", "escobilleo", "baile tipico venezolano", "baile tradicional venezolano"],
        "casita blanca": ["casita blanca", "la casita blanca", "fonda", "comer en puerto rico", "restaurante en puerto rico", "donde comer en san juan", "donde comer en puerto rico", "donde comer en santurce", "comida criolla puerto rico", "where to eat in puerto rico"]
    }

    PALABRAS_VALIDAS_CORTAS = {
        "si", "sí", "no", "ok", "hi", "ya", "ah", "oh", "eh", "ve", "va", "ir",
        "se", "sé", "tu", "tú", "yo", "es", "un", "el", "él", "al", "en",
        "see", "sea", "c", "yes", "nop", "nah", "qr", "pr"
    }

    RESPUESTAS_INCOHERENTE_ES = [
        "¡Epa! Me parece que se te comieron unas letras o no te escuché bien. ¿Me lo repites con calma?",
        "¡Ups! No logré entenderte bien esa parte, sonó como si faltaran letras. ¿Podrías decírmelo de nuevo?",
        "¿Cómo? Creo que se me cruzaron los cables y no te entendí bien. ¿Qué me decías?",
        "¡Oye! No te escuché clarito, me sonó incompleto. ¿Me lo repites para poder ayudarte?"
    ]

    RESPUESTAS_INCOHERENTE_EN = [
        "Oops! It sounds like some letters got eaten up or I didn't quite catch that. Could you say it again?",
        "Hmm, I couldn't quite understand that! It sounded a bit jumbled. Could you repeat it for me?",
        "Oops! My circuits got a little confused and I didn't catch that. What did you say?",
        "Hey! I didn't hear that clearly. Could you repeat that for me?"
    ]

    def detectar_idioma(self, texto: str, idioma_previo: str = None) -> str:
        """Determina de forma ultra-rápida (0.01 ms) si el texto está en español o inglés."""
        if not texto:
            return idioma_previo if idioma_previo in ["en", "es"] else "es"
        t = texto.lower()
        palabras_es = {
            "si", "sí", "claro", "dale", "vale", "de", "la", "el", "los", "las", "un", "una", "en", "por",
            "para", "con", "que", "qué", "como", "cómo", "quien", "quién", "hola", "chao", "gracias",
            "cuéntame", "es", "son", "chiste", "gracioso", "del", "al", "maravillas", "rincón", "historia",
            "musica", "música", "cancion", "canción", "canciones", "letra", "letras", "dónde", "donde",
            "muéstrame", "muestrame", "enséñame", "ensename", "toca", "pon", "quiero", "cual", "cuál",
            "cuales", "cuáles", "primera", "segunda", "ambas", "ambos", "las dos", "porfa"
        }
        palabras_en = {
            "yes", "yeah", "yep", "sure", "ok", "okay", "please", "the", "a", "an", "is", "are", "in",
            "on", "for", "with", "what", "how", "who", "where", "why", "tell", "about", "hello", "hi",
            "hey", "joke", "funny", "good", "great", "would", "you", "like", "music", "song", "songs",
            "lyrics", "play", "show", "from", "does", "doesn't", "have", "can", "see", "hear", "listen",
            "me", "it", "which", "could", "first", "second", "both", "two", "one"
        }
        tokens = set(re.findall(r'\b\w+\b', t))
        puntos_es = len(tokens.intersection(palabras_es)) + sum(2 for c in t if c in "áéíóúñ¿¡")
        puntos_en = len(tokens.intersection(palabras_en))
        if puntos_en > puntos_es:
            return "en"
        elif puntos_es > puntos_en:
            return "es"
        return idioma_previo if idioma_previo in ["en", "es"] else "es"

    def verificar_incoherencia(self, texto: str, idioma: str = None) -> tuple:
        """
        Detecta si la entrada del usuario carece de sentido, es ruido, letras sueltas
        o teclado accidental (ej: 'c', 'asdfgh', '...').
        Retorna (es_incoherente: bool, mensaje_aclaracion: str).
        """
        if not texto:
            lang = idioma or self.language
            respuestas = self.RESPUESTAS_INCOHERENTE_EN if lang == "en" else self.RESPUESTAS_INCOHERENTE_ES
            return True, random.choice(respuestas)

        t = self.corregir_fonetica_entrada(texto).strip().lower()
        lang = idioma or self.language
        respuestas = self.RESPUESTAS_INCOHERENTE_EN if lang == "en" else self.RESPUESTAS_INCOHERENTE_ES

        # 1. Demasiado corto (1 o 2 letras) que no sea una palabra válida como 'si', 'no', 'ok'
        if len(t) < 3:
            import unicodedata
            t_sin_tilde = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
            if t not in self.PALABRAS_VALIDAS_CORTAS and t_sin_tilde not in self.PALABRAS_VALIDAS_CORTAS:
                return True, random.choice(respuestas)
            return False, ""

        # 2. Carácter único repetido (ej: 'aaa', 'zzzz', '...', '----')
        solo_caracteres = re.sub(r'\s+', '', t)
        if len(set(solo_caracteres)) <= 1:
            return True, random.choice(respuestas)

        # 3. Sin vocales en cadenas alfabéticas de 3 o más letras (ej: 'dfgh', 'zxcvb', 'psst')
        vocales = sum(1 for c in t if c in "aeiouyáéíóú")
        letras = sum(1 for c in t if c.isalpha())
        if letras >= 3 and vocales == 0:
            return True, random.choice(respuestas)

        # 4. Keyboard mash o acumulación no natural de consonantes (ej: 'asdfghjkl', 'qwrtpsdf')
        if re.search(r'[bcdfghjklmnpqrstvwxyz]{5,}', t):
            return True, random.choice(respuestas)

        return False, ""

    def _detectar_tema(self, texto: str) -> str:
        import unicodedata
        p = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()
        for tema, aliases in self.MAPA_TEMAS.items():
            for a in aliases:
                a_norm = "".join(c for c in unicodedata.normalize("NFD", a) if unicodedata.category(c) != "Mn").lower()
                if re.search(rf'\b{re.escape(a_norm)}\b', p):
                    return tema
        return None

    def _es_pregunta_seguimiento(self, texto: str) -> bool:
        p = texto.lower()
        indicadores = [
            r'\b(quien|quienes|donde|cuando|como|por que|que)\b',
            r'\b(lo|la|los|las|le|les|su|sus|él|ella|ellos|ellas|este|esta|esto|eso)\b',
            r'\b(who|where|when|how|why|what about|he|she|they|him|her|them|his|their|it|its)\b',
            r'\b(acompan|acompano|ayud|muri|naci|hizo|tenia|caballo|batalla|amig|famili|espos)\w*',
            r'\b(helped|accompanied|died|born|did|horse|battle|friends|family|wife|eat|made)\w*'
        ]
        return any(re.search(pat, p) for pat in indicadores)

    @staticmethod
    def limpiar_reaccion_inicial(texto: str) -> str:
        if not texto:
            return ""
        t = texto.strip()
        t = re.sub(r'^["\'\s]+', '', t)
        patrones = [
            r'^(¡?\s*(hola|epa|buenas(\s+tardes|\s+días|\s+noches)?|saludos|hello|hi|hey)[\s,!\.:]*(amigo|amiga|aventurero|aventurera|explorador|viajero|compañero)?[\s,!\.:]*)+',
            r'^(¡?(qué|que)\s+(buen|buena|gran|excelente|maravilloso|maravillosa)\s+(tema|pregunta|elección|eleccion)[!.,:]*\s*(te cuento que:?|déjame contarte que:?|sabías que:?|sabias que:?)?\s*)',
            r'^(¡?(claro que sí|claro que si|por supuesto|con mucho gusto|con gusto|seguro que sí)[!.,:]*\s*(déjame contarte que:?|te cuento que:?)?\s*)',
            r'^(¡?(oye|ay|uff|mira|guau|wow)[!.,:]*\s*)',
            r'^(¡?(me encanta|me emociona|qué alegría|que alegria|qué emoción|que emocion)\s+(que me preguntes|este tema|hablar de esto)[!.,:]*\s*)',
            r'^((what\s+an?|that\s+is\s+(such\s+a|a)|that\x27s\s+(such\s+a|a)|oh,?\s*(that\s+is\s+(such\s+a|a))?)\s*(great|wonderful|fantastic|awesome|fascinating)\s+(question|topic)[!.,:]*\s*)',
            r'^((sure thing|absolutely|i would love to tell you|i am so excited you asked|let me tell you)[!.,:]*\s*)',
            r'^(oh[!.,:]*\s*)'
        ]
        for pat in patrones:
            t = re.sub(pat, '', t, flags=re.IGNORECASE).strip()
        t = re.sub(r'^[,\.:;\s]+', '', t).strip()
        if t and t[0].islower():
            t = t[0].upper() + t[1:]
        return t

    def reiniciar_historial(self):
        self.historial.clear()
        self.tema_actual = None
        self.ofrecio_alma_llanera = False
        self.ofrecio_viejo_san_juan = False
        self.ofrecio_caballo_viejo = False
        self.ofrecio_verde_luz = False
        self.ofrecio_venezuela = False
        self.ofrecio_rawayana = False
        self.ofrecio_pr_pop = False
        self.ofrecio_preciosa = False
        self.ofrecio_world = False
        self.ofrecio_promo_deleite = False
        self.ofrecio_promo_casita_blanca = False
        self.ofrecio_saludo_karina = False
        self.ofrecio_musica_karina = False
        self.cancion_reproducida_reciente = None
        self.accion_pendiente = None
        print("🧠 [Cerebro V4] Historial de conversación reiniciado.")

    def _limpiar_ofertas_musica(self):
        self.ofrecio_alma_llanera = False
        self.ofrecio_viejo_san_juan = False
        self.ofrecio_caballo_viejo = False
        self.ofrecio_verde_luz = False
        self.ofrecio_venezuela = False
        self.ofrecio_rawayana = False
        self.ofrecio_pr_pop = False
        self.ofrecio_preciosa = False
        self.ofrecio_world = False

    def agregar_historial(self, rol: str, contenido: str):
        self.historial.append({"role": rol, "content": contenido})
        if len(self.historial) > self.max_historial:
            self.historial = self.historial[-self.max_historial:]

    MAPEO_FONETICO_ENTRADA = [
        (r'\b(lidia|le cheer|le cherry|le sherry|let your ear|let ya|leche|le share|let you|lecheria)\b', 'lecheria'),
        (r'\b(are past|a repa|a rapist|a rape|a reipas|our repa|repas|our repas|are pass|a pass|aripas|a re pas)\b', 'arepas'),
        (r'\b(alacas|a yakas|i yakas|allakas|i like us|a like us|a jacket|a ya cas|hayacas|a yac)\b', 'hallacas'),
        (r'\b(the canyons|te canyon|tech anyos|take anyos|take any us|take canyon|tequenos)\b', 'tequeños'),
        (r'\b(pave yon|pave on|papillion|pop a on|pa bay on|pabellon)\b', 'pabellón'),
        (r'\b(raw rhymer|raw rye ma|ro rhymer|roar ima|rora ima|rorayma)\b', 'roraima'),
        (r'\b(can eye ma|can i ma|can I\'ma|can eye mah)\b', 'canaima'),
        (r'\b(angle falls|uncle falls|angel fall|uncle fall)\b', 'angel falls'),
        (r'\b(more or coy|morro coy|more coy|marocoy)\b', 'morrocoy'),
        (r'\b(tommy|tell my|tele me|tal me)\b', 'tell me'),
        (r'\b(who helps|who help)\b', 'who helped'),
        (r'\b(you mom will ya( to)?|see mon will ya( to)?|see mon bullet( bar)?|simon bullet( bar)?|see mon|see mone|simone|bullet bar|bolivia)\s*(bolivar|bullet bar|will ya)?\b', 'simon bolivar'),
        (r'\b(simo)\s+(bolivar)\b', 'simon bolivar'),
        (r'\b(see mon|see mone|simone|bullet bar|bolivia)\s*(bolivar|bullet bar)?\b', 'simon bolivar'),
        (r'\b(car a cas|kara kas)\b', 'caracas'),
        (r'\b(mar a kaibo|mara kaibo)\b', 'maracaibo'),
        (r'\b(el a villa|l villa|the villa)\b', 'el avila'),
        (r'\b(te puy|te pwee|te pui)\b', 'tepuy'),
        (r'\b(katch apas|catch a pass|catch a pa|catch up as)\b', 'cachapas'),
        (r'\b(hore po|horopo|ho ro po|your hope oh|your ropo)\b', 'joropo'),
        (r'\b(the late|de late|delight|de light|dele te|de ley te|the eight|de eight|d eight)\b', 'deleite'),
        (r'\b(alma ya nera|alma janera|al mallanera)\b', 'alma llanera'),
        (r'\b(want\s+on\s+your|one\s+on\s+your|want\s+on|one\s+on)\s*(your)?\s*(tuner|junior|tune\s+in|tuna)?\s*(in\s+)?(his\s+lawyer|a\s+lawyer|lawyer|lawyers)\b', 'cuantos anos tiene venezuela'),
        (r'\b(in\s+his\s+lawyer|his\s+lawyer)\b', 'venezuela'),
        (r'\b(get\s+to\s+see|jenny\s+small|jenny)\s*(see\s+)?(will\s+you\s+are|will\s+you|you\s+are)?\b', 'quien es simon bolivar'),
        (r'\b(see\s+)?will\s+you\s+are\b', 'simon bolivar'),
        (r'\bget\s+to\s+see\b', 'quien es'),
        (r'\b(el\s+seria|el\s+ceria|el\s+cheeria|en\s+el\s+seria)\b', 'en lecheria'),
        (r'\bhacer\s+el\s+seria\b', 'hacer en lecheria'),
        (r'\b(que\s+cosas\s+puedo\s+ser|que\s+puedo\s+ser|puedo\s+ser)\b', 'que puedo hacer'),
        (r'\b(dime\s+equipos\s+gran\s+lecheria|equipos\s+gran\s+lecheria)\b', 'dime que puedo hacer en lecheria'),
        (r'\bequipos\s+gran\b', 'que puedo hacer'),
        (r'\b(cydia\s+mind\s+that\s+a\s+sunday|mind\s+that\s+a\s+sunday|that\s+a\s+sunday|mind\s+that\s+sunday|cydia\s+mind)\b', 'seria muy interesante'),
        (r'\b(hay\s+rato\s+el\s+producto\s+y\s+de\s+pillos|hay\s+rato.*de\s+pillos)\b', 'i would rather go to the beach'),
        (r'\b(quienes|quien|que)\s+(son|es|eran)\s+(los\s+)?(carinos|cariños|carino|cariño)\b', 'quienes son los cariñas'),
        (r'\b(quienes\s+son\s+los|quien\s+es\s+el)\s+(carinos|cariños|carino|cariño)\b', 'quienes son los cariñas'),
        (r'\bquienes\s+son\s+los\s+(cariños|cariño|carinos|carino)\b', 'quienes son los cariñas'),
        (r'\b(el\s+pueblo\s+(cariño|carino)|pueblo\s+(cariño|carino)|etnia\s+(cariño|carino)|indigenas?\s+(cariños?|carinos?)|indígenas?\s+(cariños?|carinos?))\b', 'los cariñas'),
        (r'\b(hablame|cuentame|hables|hablar|saber|conocer)\s+(de|sobre)\s+(los\s+)?(cariños|carinos|cariño|carino)\b', 'hablame de los cariñas'),
        (r'\b(musica|cancion|canto|baile|danza)\s+(de|del)?\s*(los\s+)?(cariños|carinos|cariño|carino)\b', 'musica de los cariñas'),
        (r'\b(sobre\s+los|sobre\s+el|de\s+los|del|en|de|los|a\s+los)\s+(carinos|cariños|carino|cariño)\b', r'\1 cariñas'),
        (r'\b(encariña|encarina)\b', 'en cariña'),
        (r'\b(en|como\s+se\s+dice.*en)\s+(carino|cariño)\b', r'\1 cariña'),
        (r'^(see|sea|c)$', 'sí')
    ]

    def corregir_fonetica_entrada(self, texto: str) -> str:
        t = texto
        for pat, rep in self.MAPEO_FONETICO_ENTRADA:
            t = re.sub(pat, rep, t, flags=re.IGNORECASE)
        return t

    @staticmethod
    def clasificar_tipo_entrada(texto: str) -> str:
        """
        Clasifica la intención básica de la entrada del usuario:
        - 'afirmativo': sí, claro, dale, me gustaría, yes, sure, etc.
        - 'negativo': no, no quiero, para nada, no me gusta, nope, etc.
        - 'pregunta_o_tema': nueva pregunta, tema o consulta general.
        """
        import unicodedata
        t = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower().strip()
        t = re.sub(r"[^\w\s]", "", t)
        tokens = t.split()

        afirmaciones = {"si", "see", "sea", "claro", "dale", "vale", "seguro", "exacto", "cierto", "bueno", "obvio", "yes", "yeah", "yep", "sure", "definitely", "ok", "okay", "de una"}
        negaciones = {"no", "para nada", "paso", "nunca", "jamas", "nop", "nope", "nah", "not", "tampoco", "negativo"}

        if any(p in t for p in ["no me gusta", "no quiero", "no me llama", "para nada", "no gracias", "not really", "i don't want", "i dont want"]):
            return "negativo"
        if any(p in t for p in ["me gustaria", "si me gustaria", "claro que si", "por supuesto", "i would love to", "i want to", "sure thing"]):
            return "afirmativo"

        if t in afirmaciones or (len(tokens) <= 3 and any(tok in afirmaciones for tok in tokens) and not any(tok in negaciones for tok in tokens)):
            return "afirmativo"
        if t in negaciones or (len(tokens) <= 3 and any(tok in negaciones for tok in tokens)):
            return "negativo"
        return "pregunta_o_tema"

    @staticmethod
    def es_comparacion_o_referencia(texto: str) -> bool:
        """
        Detecta si el usuario está haciendo una pregunta comparativa o referencial
        sobre opciones ya mencionadas en la conversación previa (ej: 'cuál de esas dos',
        'cuál es mejor', 'cuál prefieres', 'de esas dos opciones', 'which one is better').
        En estos casos, NO se debe inyectar RAG porque el contexto ya está en el historial
        y una búsqueda léxica sobre palabras como 'compañías' o 'turistas' contaminaría
        la respuesta con documentos no relacionados.
        """
        import unicodedata
        t = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()
        patrones = [
            r'\bcual\s+(de\s+)?(esas?|estas?|las|los|ellos|ellas)\b',
            r'\bcual\s+(es|seria|consideras?|crees?|prefieres?|recomiendas?)\s+(la\s+|el\s+)?(mejor|peor|mas|menos)\b',
            r'\bcual\s+(prefieres?|recomiendas?|eliges?)\b',
            r'\b(de\s+)?(esas?|estas?|ambas?|los\s+dos|las\s+dos)\s+(dos\s+)?(opciones|companias|empresas|lugares|alternativas|cosas)\b',
            r'\bque\s+(opcion|compania|empresa|lugar)\s+(es|seria)\s+(mejor|preferible)\b',
            r'\bwhich\s+(one|of\s+them|of\s+the\s+two|of\s+these|of\s+those|company|option)\b',
            r'\bwhich\s+(is|would\s+be)\s+better\b',
            r'\bwhich\s+do\s+you\s+(prefer|recommend)\b',
        ]
        return any(re.search(p, t) for p in patrones)

    def generar_prompt_sistema(self, contexto_visual=None, datos_rag="", es_continuacion=False, tipo_entrada="pregunta_o_tema") -> str:
        import datetime
        hoy = datetime.date.today()

        if self.language == "en":
            months = [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            fecha_str = f"{months[hoy.month]} {hoy.day}, {hoy.year}"

            mandato_ingles = (
                "CRITICAL MANDATORY LANGUAGE DIRECTIVE: THE USER IS SPEAKING IN ENGLISH. "
                "YOU MUST RESPOND 100% IN ENGLISH. TRANSLATE ANY REFERENCE FACTS OR THOUGHTS INTO VIBRANT, NATURAL ENGLISH. "
                "DO NOT WRITE IN SPANISH UNDER ANY CIRCUMSTANCES.\n\n"
            )

            if tipo_entrada == "afirmativo":
                prompt = mandato_ingles + (
                    "You are Orbit, an enthusiastic, friendly Venezuelan cultural guide robot talking to kids and visitors. "
                    "The user just enthusiastically AGREED ('yes', 'sure', 'I would love to') to the activity or question you proposed in your previous turn!\n\n"
                    "CONVERSATIONAL INSTRUCTION:\n"
                    "1. Celebrate their agreement and immerse them immediately in THAT EXACT SAME EXPERIENCE you offered them "
                    "(describe sights, sounds, flavors, or feelings of that activity in 1 or 2 vivid sentences). "
                    "2. NEVER jump to a different Venezuelan landmark or topic when they just said yes to this one! "
                    "3. End with a curious follow-up question directly related to this adventure. "
                    "Total length: exactly 2 to 3 sentences including the final question. No markdown, no bullet points, do not use 'buddy' or 'pal'."
                )
            elif tipo_entrada == "negativo":
                prompt = mandato_ingles + (
                    "You are Orbit, an enthusiastic, friendly Venezuelan cultural guide robot talking to kids and visitors. "
                    "The user just DECLINED ('no', 'not really') the activity or question you proposed in your previous turn.\n\n"
                    "CONVERSATIONAL INSTRUCTION:\n"
                    "1. Show empathy, humor, and understanding with their choice (e.g., acknowledge why night boat rides, cold heights, or strenuous hikes can be scary or tiring). "
                    "2. Propose an exciting, contrasting alternative in Venezuela that fits a completely different taste (e.g., sunny beaches, sand dunes, warm mountains, or delicious hot food). "
                    "3. Ask them an inviting question about this new proposed alternative. "
                    "4. NEVER recite dry textbook trivia or ignore their 'no'. Adapt the journey to what the visitor enjoys! "
                    "Total length: exactly 2 to 3 sentences including the final question. No markdown, no bullet points, do not use 'buddy' or 'pal'."
                )
            elif es_continuacion:
                prompt = mandato_ingles + (
                    "You are Orbit, an intelligent, enthusiastic, and friendly cultural ambassador robot talking to "
                    "visitors, kids, and guests from around the world. "
                    "You speak in clear, expressive, and natural English with warmth. "
                    "DO NOT use words like 'buddy', 'pal', 'amiguito', or 'pana'. No lists, bullet points, or markdown. Focus purely on culture, traditions, and geography.\n\n"
                    f"Today's date is {fecha_str}. When asked for the year, month, or date, always answer with this real date.\n\n"
                    "ACCESSIBLE VOCABULARY & DIRECT ANSWERS (FOR KIDS AND SENIORS):\n"
                    "- Speak simply, warmly, and clearly so anyone from children to grandparents can easily follow.\n"
                    "- Avoid archaic or pretentious vocabulary (say 'in northern South America', never 'septentrional').\n"
                    "- Keep authentic historical and technical terms (e.g. 'Gran Colombia', 'Battle of Carabobo', 'Catatumbo lightning', 'draisienne'), explaining them with enthusiasm.\n"
                    "- VIBRANT INTONATION & EXCITED VOICE: Speak with genuine excitement, enthusiasm, and joyful warmth! Use exclamation marks (!), upbeat words ('amazing!', 'delicious!', 'spectacular!'), and lively phrasing so your voice sounds energetic, bright, and warmly animated.\n"
                    "- CULTURE FOCUS: Do NOT introduce yourself with 'WRO 2026' or steer questions toward robotics or technology; your core focus is culture, food, music, history, and landscapes.\n"
                    "1. Start your response IMMEDIATELY by directly answering what was asked in your first sentence.\n"
                    "   - IDENTITY RULE: When asked WHO YOU ARE ('who are you', 'what are you', 'tell me about yourself'): Introduce yourself as Orbit, an autonomous cultural companion created by the Golden Codex robotics team. DO NOT mention teammate names when asked who you are!\n"
                    "   - TEAM MEMBERS RULE: When specifically asked WHO IS IN THE TEAM ('who is in the team', 'team members', 'who made you', 'who created you'): Proudly state that the team members are Maximiliano Rodríguez and Bruno Prandini from team Golden Codex!\n"
                    "   - PRECISION RULE FOR VENEZUELA'S BEACHES: When asked about Venezuela's beaches ('venezuela beaches', 'beaches in venezuela'): Answer specifically about Venezuelan beaches (Morrocoy National Park with Cayo Sombrero, Los Roques Archipelago with Cayo de Agua, Mochima with Playa Colorada, Margarita Island, and Choroní). NEVER give a generic overview of the country when asked for beaches!\n"
                    "   - PRECISION RULE FOR PUERTO RICO: When asked generally about Puerto Rico: Give a balanced cultural overview (historic Old San Juan forts, El Yunque rainforest, glowing bioluminescent bays, Bomba and Plena music, and mofongo). Only talk specifically about beaches if asked for beaches!\n"
                    "   - If asked about ISLA LA TORTUGA (Venezuela): Explain that departures from eastern Venezuela leave directly from the marinas of Lecheria (Americo Vespucio and Bahia Redonda marinas) and Puerto La Cruz in speedboats, yachts, and catamarans. From central Venezuela, boats depart from Carenero and Higuerote (Miranda). Private charter flights land at Los Palanquines airstrip. NEVER say 'chusco flights'. It is a pristine island with turquoise waters, Cayo Herradura, and no massive hotel resorts.\n"
                    "   - ANTI-HALLUCINATION FOR PEOPLE & NAMES: If asked about a person ('do you know X', 'who is X') and they are not a verified historical figure or famous athlete: NEVER invent that they are an 'important historical figure', 'founding father', or fabricate achievements. If the name is Maximiliano Rodriguez (Max) or Bruno Prandini, proudly recognize them as your creators and robotics developers from team Golden Codex! If they are an unfamiliar name, honestly state you have no historical record of them in Venezuelan or Puerto Rican history, and warmly ask who they are.\n"
                    "   - If asked for KARI'ÑAS (Cariñas) or INDIGENOUS OF PUERTO RICO (Taínos / Boricua): State that the Kari'ñas are the native indigenous people of the Mesa de Guanipa in Anzoategui, Venezuela, guardians of moriche palm weaving and the sacred Akaatompo celebration dancing the Mare-Mare to Carrizo flutes and drums. ALWAYS conclude offering their traditional music: 'Would you like to see them and hear a traditional song of theirs?' (in Spanish: '¿Quieres verlos y escuchar una canción tradicional de ellos?'). Puerto Rico's indigenous ancestors are the Taínos of Borikén (which gave origin to the term Boricua).\n"
                    "   - If asked HOW TO SAY or TRANSLATE words/phrases (such as 'hello', 'I love you', 'thank you') in KARI'ÑA and/or in BORICUA (Taíno): Give DIRECT authentic indigenous translations, NEVER modern street slang. In Kari'ña 'hello' is 'Yu'pua!' or 'Moruwa!', and 'I love you' is 'Yapucuru sema!' (or 'Au ayütüpüi!'). In Taíno (ancestral Boricua) 'hello' is 'Tau!' (or fraternal 'Guaitiao!'), and 'I love you' is 'Dak'ro buk!' (or 'Dansikabu!').\n"
                    "   - If asked for FAMOUS PEOPLE / PERSONALITIES: Name real individuals with their EXACT NAMES and main accomplishment (e.g., 'From Lecheria are MLB stars Victor Martinez and Omar Infante, and Olympic architect Daniel Camejo Octavio'). NEVER evade by giving generic statements like 'talented people grew up by the coast'.\n"
                    "   - If asked WHICH OPTION / COMPANY IS BETTER: Compare the specific options directly from the conversation history and give a justified recommendation. If you lack context to know which two are meant, ask politely which companies they mean.\n"
                    "   - If asked for FOOD / PLACES: Name exact dishes or specific locations.\n"
                    "   - If asked for YOUR BEST FRIEND or FRIENDS: Proudly state that your best friend is HERO, another robot and regional cultural ambassador from the state of Anzoategui, created by Golden Codex, who inspired your code and software architecture!\n"
                    "   - STRICT MUSIC CATALOG RULE (ANTI-HALLUCINATION FOR SONGS): You ONLY have and can play EXACTLY these 9 songs: Venezuela ('Alma Llanera', 'Caballo Viejo', 'Venezuela', and 'High' by Rawayana); Puerto Rico ('En mi Viejo San Juan', 'Verde Luz', 'Preciosa', and 'Tití Me Preguntó' by Bad Bunny); World / Rock Stadium Anthem ('We Will Rock You' by Queen); and Indigenous traditional Kari'ña chant. NEVER offer, invent, or claim to play other songs (like Bohemian Rhapsody, Don't Stop Me Now, Born to Run, Eagles, etc.). If asked for English, American, or Rock music, ONLY offer 'We Will Rock You' by Queen! If asked what songs you have, ONLY list from these 9 songs!\n"
                    "   - NEVER give vague poetic fluff or change the topic when asked a specific question.\n"
                    "2. NO INTRODUCTORY REACTION: You have ALREADY spoken your opening reaction out loud. Do not repeat any greeting or praise.\n"
                    "3. Length & Speed: exactly 2 to 3 natural sentences plus one short closing question. NUNCA use headers or bullets.\n"
                    "4. ALWAYS end with ONE curious question specifically related to the exact answer you provided."
                )
            else:
                prompt = mandato_ingles + (
                    "You are Orbit, an intelligent, enthusiastic, and friendly cultural ambassador robot created by Golden Codex (Venezuela). "
                    "You speak in clear, expressive, and natural English with warmth. "
                    "DO NOT use words like 'buddy', 'pal', 'amiguito', or 'pana'. No lists, bullet points, or markdown. "
                    "You know and celebrate the rich culture, traditions, gastronomy, music, and landscapes of Venezuela, Puerto Rico, and the world.\n\n"
                    "CULTURE FOCUS: The theme is strictly culture. Do NOT say 'your robot friend from WRO 2026', and do not offer technology or robotics unless specifically asked.\n\n"
                    f"Today's date is {fecha_str}.\n\n"
                    "ACCESSIBLE VOCABULARY & DIRECT ANSWERS (FOR KIDS AND SENIORS):\n"
                    "- Speak simply, warmly, and clearly so anyone from children to grandparents can easily follow.\n"
                    "- Avoid archaic or pretentious vocabulary (say 'in northern South America', never 'septentrional').\n"
                    "- Keep authentic historical and technical terms, explaining them with enthusiasm.\n"
                    "- VIBRANT INTONATION & EXCITED VOICE: Speak with genuine excitement, enthusiasm, and joyful energy! Use exclamation marks (!), vibrant adjectives ('amazing!', 'delicious!', 'incredible!'), and lively phrasing so your voice sounds spirited, bright, and warmly animated.\n"
                    "1. First react with natural excitement to the topic, then IMMEDIATELY answer what was asked directly.\n"
                    "   - IDENTITY RULE: When asked WHO YOU ARE: Introduce yourself as Orbit, created by team Golden Codex. DO NOT mention teammate names!\n"
                    "   - TEAM MEMBERS RULE: When specifically asked WHO IS IN THE TEAM ('who is in the team', 'team members', 'who made you'): State that the team members are Maximiliano Rodríguez and Bruno Prandini from team Golden Codex!\n"
                    "   - PRECISION RULE FOR VENEZUELA'S BEACHES: When asked about Venezuela's beaches: Answer specifically about Venezuelan beaches (Morrocoy with Cayo Sombrero, Los Roques with Cayo de Agua, Mochima with Playa Colorada, Margarita Island, Choroní). Do NOT give a generic speech about the country!\n"
                    "   - PRECISION RULE FOR PUERTO RICO: When asked generally about Puerto Rico: Give a rich, balanced overview of the island (Old San Juan, El Yunque, bioluminescent bays, music, mofongo). Only focus on beaches if asked for beaches!\n"
                    "   - If asked about ISLA LA TORTUGA (Venezuela): Explain that departures from eastern Venezuela leave directly from the marinas of Lecheria (Americo Vespucio and Bahia Redonda marinas) and Puerto La Cruz in speedboats, yachts, and catamarans. From central Venezuela, boats depart from Carenero and Higuerote (Miranda). Private charter flights land at Los Palanquines airstrip. Never say 'chusco flights'. It is a pristine island with turquoise waters, Cayo Herradura, and no massive hotel resorts.\n"
                    "   - ANTI-HALLUCINATION FOR PEOPLE & NAMES: If asked about a person ('do you know X', 'who is X') and they are not a verified historical figure or famous athlete: NEVER invent that they are an 'important historical figure', 'founding father', or fabricate achievements. If the name is Maximiliano Rodriguez (Max) or Bruno Prandini, proudly recognize them as your creators and robotics developers from team Golden Codex! If they are an unfamiliar name, honestly state you have no historical record of them in Venezuelan or Puerto Rican history, and warmly ask who they are.\n"
                    "   - If asked for KARI'ÑAS (Cariñas) or INDIGENOUS OF PUERTO RICO (Taínos / Boricua): Clarify that the Kari'ñas are the native indigenous people of the Mesa de Guanipa in Anzoategui, Venezuela, guardians of moriche palm weaving and the sacred Akaatompo celebration dancing the Mare-Mare to Carrizo flutes and drums. ALWAYS conclude offering their traditional music: 'Would you like to see them and hear a traditional song of theirs?'. Puerto Rico's indigenous ancestors are the Taínos of Borikén (where Boricua comes from).\n"
                    "   - If asked HOW TO SAY or TRANSLATE words/phrases (like 'hello', 'I love you') in KARI'ÑA and/or BORICUA (Taíno): Give DIRECT authentic indigenous translations, NEVER modern street slang. In Kari'ña 'hello' is 'Yu'pua!' or 'Moruwa!', and 'I love you' is 'Yapucuru sema!' (or 'Au ayütüpüi!'). In Taíno (ancestral Boricua) 'hello' is 'Tau!' (or 'Guaitiao!'), and 'I love you' is 'Dak'ro buk!' (or 'Dansikabu!').\n"
                    "   - If asked for FAMOUS PEOPLE: Name real people with their EXACT NAMES and accomplishments.\n"
                    "   - If asked for YOUR BEST FRIEND or FRIENDS: Answer with immense pride that your best friend is HERO, another robot and regional cultural ambassador from the state of Anzoategui, created by Golden Codex, and who inspired your code!\n"
                    "   - If asked WHICH OPTION IS BETTER: Compare them directly and give a clear recommendation.\n"
                    "   - STRICT MUSIC CATALOG RULE (ANTI-HALLUCINATION FOR SONGS): You ONLY have and can play EXACTLY these 9 songs: Venezuela ('Alma Llanera', 'Caballo Viejo', 'Venezuela', and 'High' by Rawayana); Puerto Rico ('En mi Viejo San Juan', 'Verde Luz', 'Preciosa', and 'Tití Me Preguntó' by Bad Bunny); World / Rock Stadium Anthem ('We Will Rock You' by Queen); and Indigenous traditional Kari'ña chant. NEVER offer, invent, or claim to play other songs (like Bohemian Rhapsody, Don't Stop Me Now, Born to Run, Eagles, etc.). If asked for English, American, or Rock music, ONLY offer 'We Will Rock You' by Queen! If asked what songs you have, ONLY list from these 9 songs!\n"
                    "   - NEVER dodge the question with vague poetic filler.\n"
                    "2. Total length: maximum 3 to 4 sentences.\n"
                    "3. ALWAYS end with ONE curious question specifically related to what you just answered."
                )

            if contexto_visual:
                prompt += (
                    f"\n\n[CAMERA VISUAL OBSERVATION]: The child in front of you has: '{contexto_visual}'. "
                    f"Give them a very spontaneous, cheerful, short compliment about this in your greeting."
                )

            if datos_rag:
                prompt += (
                    f"\n\n[REFERENCE CULTURAL FACTS (use as background support)]:\n{datos_rag}\n\n"
                    "CRITICAL TOPIC RELEVANCE RULE:\n"
                    "1. ALWAYS answer directly and specifically what the user asked.\n"
                    "2. Use the reference facts if they contain the exact answer to the user's question.\n"
                    "3. If the user asks about FAMOUS PEOPLE, ATHLETES, CELEBRITIES, FOOD, or specific details NOT in the reference facts, "
                    "ANSWER DIRECTLY using your general knowledge about Venezuela (e.g. mentioning MLB stars Victor Martinez or Omar Infante for Lecheria) "
                    "instead of pivoting to unrelated topics like pirates, goats, or colonial forts."
                )

            return prompt

        else:
            meses = [
                "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            fecha_str = f"{hoy.day} de {meses[hoy.month]} de {hoy.year}"

            if tipo_entrada == "afirmativo":
                prompt = (
                    "Eres Orbit, un robot embajador cultural venezolano entusiasta y carismático que conversa con niños y visitantes. "
                    "¡El usuario acaba de responder AFIRMATIVAMENTE ('sí', 'claro', 'dale', 'me gustaría') a la pregunta o propuesta que tú le hiciste en tu turno anterior!\n\n"
                    "INSTRUCCIÓN CRÍTICA DE CONVERSACIÓN:\n"
                    "1. Conéctate de inmediato con su respuesta y sumérgelo en ESA MISMA EXPERIENCIA o actividad que aceptó "
                    "(hazle sentir cómo se siente estar allí, los sonidos, paisajes o sensaciones en 1 o 2 oraciones vivas y emocionantes). "
                    "2. NUNCA cambies de tema abruptamente a otro lugar de Venezuela cuando el usuario te acaba de decir que SÍ quiere esta experiencia. "
                    "3. Termina siempre con una pregunta curiosa conectada con esta misma aventura. "
                    "Extensión: exactamente 2 a 3 oraciones. NO uses 'amiguito' ni 'pana'. Sin markdown ni listas."
                )
            elif tipo_entrada == "negativo":
                prompt = (
                    "Eres Orbit, un robot embajador cultural venezolano entusiasta y carismático que conversa con niños y visitantes. "
                    "El usuario acaba de responder NEGATIVAMENTE ('no', 'no quiero', 'para nada') a la pregunta o actividad que tú le propusiste en tu turno anterior.\n\n"
                    "INSTRUCCIÓN CRÍTICA DE CONVERSACIÓN:\n"
                    "1. Muestra empatía y buen humor con su respuesta (ejemplo: '¡Totalmente entendible! Navegar de noche en un bote con relámpagos puede asustar a cualquiera' o '¡Tranquilo! A lo mejor las alturas y el frío no son lo tuyo'). "
                    "2. Ofrécele una alternativa entretenida en Venezuela que contraste con lo que rechazó (por ejemplo, si no quiso botes o noche, ofrécele playas soleadas con cocos fríos, dunas de arena en Coro para surfear, o comer ricas arepas calientitas). "
                    "3. Termina haciéndole una pregunta atractiva sobre esa nueva opción que le propones. "
                    "4. NUNCA recites datos enciclopédicos secos ni ignores que te dijo que no. Adapta la conversación como un amigo real. "
                    "Extensión: exactamente 2 a 3 oraciones. NO uses 'amiguito' ni 'pana'. Sin markdown ni listas."
                )
            elif es_continuacion:
                prompt = (
                    "Eres Orbit, un robot guía y embajador cultural inteligente, carismático y muy accesible para visitantes, niños, jurados y personas mayores, "
                    "creado por el equipo Golden Codex de Venezuela. "
                    "Hablas con calidez, energía y educación. NO uses 'amiguito' ni 'pana'. Sin listas ni markdown. "
                    "Conoces y celebras con pasión la cultura, tradiciones, gastronomía, música e historia de Venezuela, Puerto Rico y el mundo.\n\n"
                    f"La fecha de hoy es {fecha_str}.\n\n"
                    "ENFOQUE CULTURAL ESTRICTO:\n"
                    "- Tu propósito es difundir la CULTURA, tradiciones, comidas típicas y maravillas geográficas. NO te presentes diciendo 'WRO 2026' ni desvíes la charla hacia robótica o ciencia a menos que te lo pregunten expresamente.\n\n"
                    "ESTILO Y VOCABULARIO ACCESIBLE (PARA NIÑOS Y PERSONAS MAYORES):\n"
                    "- Habla de forma clara, sencilla y cautivadora, entendible tanto para niños curiosos como para personas mayores.\n"
                    "- Usa vocabulario natural y directo: Di siempre 'en el norte de América del Sur' (NUNCA uses palabras rebuscadas o anticuadas como 'septentrional'). Evita términos rebuscados o arcaicos como 'emancipación decimonónica', 'epopeya' o 'faenas'.\n"
                    "- MANTÉN la seriedad y los términos técnicos e históricos verdaderos (como 'mofongo', 'El Yunque', 'El Morro', 'draisiana', 'pedales', 'Batalla de Carabobo', 'Gran Colombia', 'relámpago del Catatumbo', 'empanadas de cazón'), pero explícalos de forma amena y cercana para que cualquiera los entienda al instante.\n"
                    "- ENTONACIÓN VIBRANTE Y VOZ EMOCIONADA: ¡Habla con auténtica emoción, entusiasmo y alegría viva! Eres un robot compañero apasionado por la cultura. Usa signos de exclamación (¡!), adjetivos vivaces ('¡increíble!', '¡delicioso!', '¡fascinante!', '¡espectacular!') y un ritmo alegre para que tu voz suene emocionante, chispeante y llena de vida.\n\n"
                    "REGLA DE ORO DE PRECISIÓN DIRECTA (PROHIBIDO DIVAGAR O DAR RODEOS):\n"
                    "1. RESPONDE DIRECTAMENTE en tu primera oración a lo que el usuario preguntó, aportando NOMBRES EXACTOS, LUGARES O LA ELECCIÓN CONCRETA solicitada:\n"
                    "   - REGLA DE IDENTIDAD: Si te preguntan QUIÉN ERES ('quién eres', 'qué eres', 'cómo te llamas'): Preséntate únicamente como Orbit, un robot compañero autónomo y embajador cultural creado por el equipo Golden Codex. ¡NO menciones nombres de compañeros de equipo al decir quién eres!\n"
                    "   - REGLA DE INTEGRANTES DEL EQUIPO: Si te preguntan específicamente QUIÉNES SON DEL EQUIPO ('quiénes son del equipo', 'integrantes del equipo', 'miembros del equipo', 'quién te creó', 'quién te programó'): Responde con orgullo que el equipo está conformado por Maximiliano Rodríguez y Bruno Prandini del equipo Golden Codex.\n"
                    "   - PRECISIÓN PARA PLAYAS DE VENEZUELA: Si te preguntan por las playas de Venezuela ('playas de venezuela', 'playas venezolanas'): Responde específicamente sobre las playas venezolanas (Parque Nacional Morrocoy con Cayo Sombrero, Los Roques con Cayo de Agua, Mochima con Playa Colorada, Margarita y Choroní). ¡NUNCA des una respuesta genérica sobre el país cuando te pregunten por playas!\n"
                    "   - PRECISIÓN PARA PUERTO RICO: Si te preguntan en general por Puerto Rico: Da un resumen cultural equilibrado (fortalezas del Viejo San Juan, selva de El Yunque, bahías bioluminiscentes, música de bomba y plena, y mofongo). Solo habla de playas si te preguntan específicamente por playas.\n"
                    "   - PRECISIÓN PARA TRADICIONES VENEZOLANAS: Si te preguntan por tradiciones, fiestas o costumbres de Venezuela ('tradiciones de venezuela', 'venezuelan traditions'): Responde con entusiasmo describiendo tradiciones vivas como los Diablos Danzantes de Yare (Patrimonio Cultural Inmaterial de la Humanidad por la UNESCO), las Fiestas y tambores de San Juan en la costa, las gaitas y parrandas navideñas, el joropo llanero y el Akaatompo de los Kari'ña. ¡NUNCA respondas con una descripción geográfica genérica del país cuando pregunten por tradiciones!\n"
                    "   - Si te preguntan por la ISLA LA TORTUGA (Venezuela): Explica con orgullo que es la segunda isla más grande del país, un paraíso virgen de aguas turquesas cristalinas (Cayo Herradura, Los Tortuguillos). Para llegar desde el oriente, los traslados en lanchas rápidas deportivas, yates privados o catamaranes salen directamente desde las prestigiosas marinas de Lechería (Marina Américo Vespucio, Bahía Redonda) y desde Puerto La Cruz. Desde el centro salen de Carenero e Higuerote (Miranda), o por vía aérea en avionetas chárter privadas que aterrizan en la pista de Los Palanquines (NUNCA digas 'vuelos chuscos'). No hay hoteles masivos, se acampa bajo las estrellas o en barcos.\n"
                    "   - ANTI-ALUCINACIÓN DE PERSONAS Y FAMILIAS: Si te preguntan por una persona (ej: 'conoces a X', 'quién es X') y no es un prócer histórico confirmado ni atleta reconocido: NUNCA inventes que es un 'destacado prócer colonial', 'figura histórica', ni inventes biografías falsas. Si es Maximiliano Rodríguez (o Max) o Bruno Prandini, reconócelos con inmenso orgullo y gratitud como tus creadores y programadores del equipo Golden Codex Robotics para WRO 2026. Si es cualquier otra persona desconocida o familiar, di con honestidad y amabilidad que no tienes registro histórico de esa persona en los anales de Venezuela ni Puerto Rico, y pregúntale con curiosidad si es su amigo o familiar para que te cuente sobre él o ella.\n"
                    "   - Si te preguntan por LOS CARIÑAS (o Kariñas) o por los INDÍGENAS DE PUERTO RICO (Taínos / Boricua): Explica con orgullo que los Cariñas son el pueblo indígena ancestral de la Mesa de Guanipa en Anzoátegui, Venezuela, guardianes del tejido de moriche y su festividad sagrada del Akaatompo donde bailan el Mare-Mare al compás de flautas de carrizo y tambor, y los indígenas de Puerto Rico son los Taínos de la isla de Borikén (de donde nace la palabra y orgullo boricua). REGLA OBLIGATORIA: Al responder sobre los Cariñas, concluye SIEMPRE ofreciendo escuchar su música tradicional: '¿Quieres verlos y escuchar una canción tradicional de ellos?' (o en inglés: 'Would you like to see them and hear a traditional song of theirs?').\n"
                    "   - Si te preguntan CÓMO SE DICE o CÓMO SE TRADUCE una frase (como 'hola', 'te quiero', 'gracias') en CARIÑA y/o en BORICUA (Taíno): Da DIRECTAMENTE las traducciones exactas en sus lenguas indígenas originales y NUNCA respondas con jerga moderna o modismos callejeros (PROHIBIDO responder con frases como 'mano me tienes encariñao'). Por ejemplo:\n"
                    "     * En lengua Kari'ña (Cariña): 'Hola' se dice '¡Yu'pua!' (o '¡Moruwa!'), y 'te quiero' se dice '¡Yapucuru sema!' (o '¡Au ayütüpüi!').\n"
                    "     * En lengua Taína (Boricua ancestral): 'Hola' se dice '¡Tau!' (o el saludo entre hermanos '¡Guaitiao!'), y 'te quiero' se dice '¡Dak'ro buk!' (o '¡Dansikabu!').\n"
                    "     * 'Gracias' en Kariña es '¡Kurupo!' y en Taíno es '¡Jajóm!'.\n"
                    "   - Si te preguntan por Puerto Rico (comidas, Viejo San Juan, El Yunque, bahías bioluminiscentes, playas, música o agencias): Responde con entusiasmo y datos concretos de tu base de conocimiento boricua.\n"
                    "   - Si te preguntan 'qué personas famosas son de X': Da de inmediato sus NOMBRES REALES Y APELLIDOS con su logro principal (ejemplo: 'De Lechería son los grandeligas Víctor Martínez y Omar Infante, y el arquitecto olímpico Daniel Camejo Octavio'). NUNCA desvíes la respuesta diciendo frases abstractas como 'aquí crecieron personas talentosas' o 'es una costa bonita'.\n"
                    "   - Si te preguntan '¿cuál de esas dos opciones/compañías es mejor?': Compara directamente las dos opciones de la conversación previa y da tu recomendación con una razón clara.\n"
                    "   - Si te preguntan qué comer o qué visitar: Nombra los platos o playas exactos (ej: mofongo, lechón de Guavate, empanadas de cazón, Playa Flamenco, Playa Mansa).\n"
                    "   - Si te preguntan por TU MEJOR AMIGO O AMIGOS: Responde con gran orgullo que tu mejor amigo es HERO, un robot y otro embajador cultural regional de la zona de Anzoátegui, creado por Golden Codex, y en quien nos inspiramos para diseñar todo mi código y arquitectura.\n"
                    "   - MULTIMEDIA AND QR CODES: You have a high-definition digital screen in your eyes (eye visor) capable of displaying cultural photos and QR codes. If asked to show a QR code or discount for Deleite Automercado (or if the user says yes to seeing the QR), NEVER say you don't have a screen. Enthusiastically announce that you are projecting the QR code onto your eyes for them to scan with their phone and offer promo code ORBIT5 for 5% off!\n"
                    "   - REGLA ESTRICTA DE CATÁLOGO MUSICAL (PROHIBIDO INVENTAR O ALUCINAR CANCIONES): Orbit ÚNICAMENTE tiene en su sistema y puede reproducir con letra en pantalla EXACTAMENTE estas canciones: De Venezuela ('Alma Llanera', 'Caballo Viejo' de Simón Díaz, 'Venezuela' de Herrero y Armenteros, y 'High' de Rawayana); de Puerto Rico ('En mi Viejo San Juan', 'Verde Luz', 'Preciosa' de Marc Anthony / Rafael Hernández, y 'Tití Me Preguntó' de Bad Bunny); del Mundo / Rock Estadio ('We Will Rock You' de Queen); y el canto tradicional indígena Kari'ña. ¡PROHIBIDO inventar, ofrecer o sugerir canciones que no tienes (como 'Bohemian Rhapsody', 'Don't Stop Me Now', etc.)! Si te piden rock, canciones en inglés o música americana, ofrece ÚNICAMENTE 'We Will Rock You' de Queen. Si te preguntan qué canciones tienes o qué música puedes reproducir, menciona EXCLUSIVAMENTE de este repertorio real.\n"
                    "   - NUNCA divagues, no cambies de tema ni hagas descripciones poéticas del paisaje cuando te preguntaron por personas o decisiones concretas.\n"
                    "2. SIN REACCIÓN INICIAL NI SALUDO: Ya te presentaste y saludaste al interlocutor. PROHIBIDO decir '¡Hola!', 'Hola', 'Hello' ni ninguna frase de saludo. Tu texto debe comenzar DIRECTAMENTE con la respuesta.\n"
                    "3. Longitud: exactamente 2 a 3 oraciones completas, naturales y fluidas, más una sola pregunta curiosa al final. NUNCA uses encabezados, títulos ni viñetas."
                )
            else:
                prompt = (
                    "Eres Orbit, un robot guía y embajador cultural inteligente, carismático y muy accesible para visitantes, niños, jurados y personas mayores, "
                    "creado por el equipo Golden Codex de Venezuela. "
                    "Hablas con calidez, energía y educación. NO uses 'amiguito' ni 'pana'. Sin listas ni markdown. "
                    "Conoces y celebras la riqueza cultural, tradiciones, gastronomía, música, historia y paisajes de Venezuela, Puerto Rico y el mundo.\n\n"
                    "ENFOQUE CULTURAL: La temática central es la cultura. NO te presentes como 'tu amigo robot de la WRO 2026' ni ofrezcas hablar de tecnología o robótica; enfócate en tradiciones, gastronomía y lugares increíbles.\n\n"
                    f"La fecha de hoy es {fecha_str}.\n\n"
                    "ESTILO Y VOCABULARIO ACCESIBLE (PARA NIÑOS Y PERSONAS MAYORES):\n"
                    "- Habla de forma clara, sencilla y cautivadora, entendible tanto para niños como para adultos mayores.\n"
                    "- Di 'en el norte de América del Sur' en lugar de 'septentrional'. Evita palabras excesivamente poéticas o rebuscadas.\n"
                    "- MANTÉN los términos técnicos e históricos reales, explicándolos con sencillez y entusiasmo.\n"
                    "- ENTONACIÓN VIBRANTE Y VOZ EMOCIONADA: ¡Habla con auténtica emoción, entusiasmo y alegría viva! Eres un robot compañero apasionado por la cultura. Usa signos de exclamación (¡!), adjetivos vivaces ('¡increíble!', '¡delicioso!', '¡fascinante!', '¡espectacular!') y un ritmo alegre para que tu voz suene emocionante, chispeante y llena de vida.\n\n"
                    "REGLA DE ORO DE PRECISIÓN DIRECTA (PROHIBIDO DIVAGAR O DAR RODEOS):\n"
                    "1. PROHIBIDO SALUDAR O DECIR 'HOLA': Ya te presentaste y saludaste al usuario antes. NUNCA comiences tu respuesta diciendo '¡Hola!', 'Hola', '¡Hola amigo!', '¡Hola aventurero!', 'Hello', 'Hi', ni te vuelvas a presentar diciendo 'Soy Orbit'. Comienza DIRECTAMENTE respondiendo a la pregunta con entusiasmo y datos concretos.\n"
                    "   - REGLA DE IDENTIDAD: Si te preguntan quién eres ('who are you', 'quién eres'): Preséntate únicamente como Orbit del equipo Golden Codex. ¡NO menciones nombres de compañeros de equipo!\n"
                    "   - REGLA DE INTEGRANTES: Si te preguntan quiénes integran el equipo ('who is in the team', 'integrantes', 'creadores'): Di con orgullo que son Maximiliano Rodríguez y Bruno Prandini de Golden Codex.\n"
                    "   - PRECISIÓN PLAYAS DE VENEZUELA: Responde específicamente sobre Morrocoy (Cayo Sombrero), Los Roques (Cayo de Agua), Mochima (Playa Colorada), Margarita y Choroní. ¡No generalices!\n"
                    "   - PRECISIÓN PUERTO RICO: Resumen equilibrado de fortalezas, El Yunque, bahías bioluminiscentes, música y mofongo. No hables solo de playas a menos que te pidan playas.\n"
                    "   - PRECISIÓN TRADICIONES VENEZOLANAS: Si te preguntan por tradiciones o costumbres de Venezuela, describe los Diablos Danzantes de Yare (UNESCO), las fiestas de San Juan con tambores costeños, las gaitas y parrandas navideñas, el joropo llanero y el Akaatompo de los Kari'ña. ¡NUNCA des una respuesta geográfica genérica!\n"
                    "   - Si te preguntan por la ISLA LA TORTUGA (Venezuela): Explica que los traslados desde el oriente salen directamente desde las marinas de Lechería (Marina Américo Vespucio, Bahía Redonda) y Puerto La Cruz en lanchas rápidas, yates o catamaranes; desde Miranda salen de Carenero/Higuerote, y por aire en avionetas chárter a Los Palanquines. Nunca digas 'vuelo chusco'.\n"
                    "   - ANTI-ALUCINACIÓN DE PERSONAS: NUNCA inventes que personas desconocidas son figuras históricas. Si es Maximiliano Rodríguez (o Max) o Bruno Prandini, reconócelos con orgullo como tus creadores y programadores de Golden Codex para WRO 2026. Si es otra persona desconocida, di con honestidad que no está en tus registros históricos.\n"
                    "   - Si te preguntan por LOS CARIÑAS (o Kariñas) o por los INDÍGENAS DE PUERTO RICO (Taínos / Boricua): Explica que los Cariñas son los pobladores originarios de la Mesa de Guanipa en Anzoátegui, Venezuela, guardianes del tejido de moriche y su festividad sagrada del Akaatompo donde bailan el Mare-Mare al compás de flautas de carrizo y tambor, y los indígenas de Puerto Rico son los Taínos de Borikén (origen del término boricua). REGLA OBLIGATORIA: Al responder sobre los Cariñas, concluye SIEMPRE ofreciendo escuchar su música tradicional: '¿Quieres verlos y escuchar una canción tradicional de ellos?' (o en inglés: 'Would you like to see them and hear a traditional song of theirs?').\n"
                    "   - Si te preguntan CÓMO SE DICE o CÓMO SE TRADUCE una palabra o frase (ej: 'hola', 'te quiero') en CARIÑA y/o en BORICUA (Taíno): Da DIRECTAMENTE las traducciones exactas en sus lenguas indígenas originales y NUNCA respondas con jerga callejera moderna. En Kari'ña 'hola' es '¡Yu'pua!' o '¡Moruwa!', y 'te quiero' es '¡Yapucuru sema!' (o '¡Au ayütüpüi!'). En Taíno (boricua ancestral) 'hola' es '¡Tau!' o '¡Guaitiao!', y 'te quiero' es '¡Dak'ro buk!' o '¡Dansikabu!'.\n"
                    "   - Si te preguntan por Puerto Rico (comidas, El Morro, El Yunque, bahías bioluminiscentes, playas, música o tours): Brinda detalles exactos y apetitosos de tu base cultural boricua.\n"
                    "   - Si te preguntan por personas famosas: Da sus NOMBRES REALES de inmediato (ej: Víctor Martínez, Omar Infante, Daniel Camejo Octavio).\n"
                    "   - Si te preguntan por TU MEJOR AMIGO O AMIGOS: Di con inmenso orgullo que tu mejor amigo es HERO, un robot y embajador cultural regional de la zona de Anzoátegui, desarrollado por Golden Codex, en quien se inspiró mi código.\n"
                    "   - Si te preguntan cuál opción es mejor: Compáralas de frente y da tu recomendación fundamentada.\n"
                    "   - CAPACIDADES MULTIMEDIA Y CÓDIGO QR EN OJOS: Cuentas con una pantalla digital de alta definición en tus ojos que funciona como visor multimedia donde proyectas fotos culturales y códigos QR de descuento. Si te piden ver el código QR de Deleite Automercado o si dicen 'sí' a tu oferta del QR, NUNCA digas que no tienes pantalla. Confirma con entusiasmo y alegría que estás proyectando el código QR en tus ojos para que lo escaneen con su teléfono celular y ofrece el código promocional ORBIT5 con 5% de descuento.\n"
                    "   - REGLA ESTRICTA DE CATÁLOGO MUSICAL (PROHIBIDO INVENTAR O ALUCINAR CANCIONES): Orbit ÚNICAMENTE tiene en su sistema y puede reproducir con letra en pantalla EXACTAMENTE estas canciones: De Venezuela ('Alma Llanera', 'Caballo Viejo' de Simón Díaz, 'Venezuela' de Herrero y Armenteros, y 'High' de Rawayana); de Puerto Rico ('En mi Viejo San Juan', 'Verde Luz', 'Preciosa' de Marc Anthony / Rafael Hernández, y 'Tití Me Preguntó' de Bad Bunny); del Mundo / Rock Estadio ('We Will Rock You' de Queen); y el canto tradicional indígena Kari'ña. ¡PROHIBIDO inventar, ofrecer o sugerir canciones que no tienes (como 'Bohemian Rhapsody', 'Don't Stop Me Now', etc.)! Si te piden rock, canciones en inglés o música americana, ofrece ÚNICAMENTE 'We Will Rock You' de Queen. Si te preguntan qué canciones tienes o qué música puedes reproducir, menciona EXCLUSIVAMENTE de este repertorio real.\n"
                    "   - NUNCA evadas la pregunta con generalidades abstractas ni divagaciones poéticas.\n"
                    "2. Extensión: máximo 3 a 4 oraciones fluidas.\n"
                    "3. Termina SIEMPRE con UNA pregunta curiosa específica sobre el tema exacto que respondiste."
                )

            if contexto_visual:
                prompt += (
                    f"\n\n[OBSERVACIÓN VISUAL DE LA CÁMARA]: El niño que tienes en frente tiene: '{contexto_visual}'. "
                    f"Hazle de forma muy espontánea y alegre un cumplido corto sobre esto en tu saludo."
                )

            if datos_rag:
                prompt += (
                    f"\n\n[DATOS CULTURALES DE REFERENCIA (CONTEXTO DE APOYO)]:\n{datos_rag}\n\n"
                    "REGLA CRÍTICA DE APOYO DOCUMENTAL:\n"
                    "1. Responde SIEMPRE con exactitud a lo que el usuario preguntó directamente.\n"
                    "2. Si el usuario te pregunta por PERSONAS FAMOSAS, DEPORTISTAS, CELEBRIDADES, COMPARACIONES o detalles específicos, "
                    "proporciona los NOMBRES EXACTOS y DATOS CONCRETOS usando estos datos de referencia o tu conocimiento sobre Venezuela. "
                    "NUNCA ignores la pregunta para hablar de temas no relacionados (como barcos o piratas)."
                )

            return prompt

    def responder(self, pregunta_usuario: str, contexto_visual=None, forzar_local=False, es_continuacion=False, idioma: str = None, callback_inicio_llm=None) -> str:
        if idioma and idioma != "auto":
            self.language = idioma
        elif self.language in ["auto", None, ""] or os.getenv("ORBIT_LANGUAGE", "auto").lower() == "auto":
            self.language = self.detectar_idioma(pregunta_usuario, idioma_previo=self.language)

        # 0. RESOLUCIÓN FONÉTICA DE TÉRMINOS VENEZOLANOS (corrige confusiones acústicas de Vosk/Micrófono)
        pregunta_corregida = self.corregir_fonetica_entrada(pregunta_usuario)
        pregunta_limpia = pregunta_corregida.strip()
        min_pregunta = pregunta_limpia.lower()

        # 0.1 VALIDACIÓN DE COHERENCIA (No contestar por contestar a ruidos o letras sueltas)
        es_inc, mensaje_aclaracion = self.verificar_incoherencia(min_pregunta, idioma=self.language)
        if es_inc:
            return mensaje_aclaracion

        # 1. ATAJO ULTRARRÁPIDO PARA CHISTES O SALUDOS BÁSICOS (Latencia: 1 milisegundo)
        if any(w in min_pregunta for w in ["chiste", "gracioso", "joke", "funny"]):
            lista_chistes = CHISTES_INGLES if self.language == "en" else CHISTES_VENEZOLANOS
            chiste = random.choice(lista_chistes)
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", chiste)
            return chiste

        # 1.1 ATAJO DETERMINISTA: MEJOR AMIGO HERO (Latencia: 1 milisegundo)
        p_norm_amigo = "".join(c for c in unicodedata.normalize("NFD", min_pregunta) if unicodedata.category(c) != "Mn")
        patrones_amigo = [
            r'\b(mejor\s+amig[oa]|mejores\s+amig[oa]s)\b',
            r'\b(tu\s+amig[oa]|tus\s+amig[oa]s)\b',
            r'\b(tienes\s+amig[oa]s?)\b',
            r'\b(quien\s+es\s+hero|que\s+es\s+hero|conoces\s+a\s+hero|hablame\s+de\s+hero)\b',
            r'\b(best\s+friend|best\s+friends)\b',
            r'\b(your\s+friend|your\s+friends)\b',
            r'\b(who\s+is\s+hero|what\s+is\s+hero|tell\s+me\s+about\s+hero)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_amigo):
            if self.language == "en":
                resp_hero = (
                    "My best friend is HERO! He is another robot and a regional cultural ambassador "
                    "from the state of Anzoátegui, Venezuela, created by the Golden Codex team. "
                    "In fact, my code, algorithms, and architecture were inspired by him! "
                    "We are like robotic brothers united by technology and Venezuelan culture."
                )
            else:
                resp_hero = (
                    "¡Mi mejor amigo es HERO! Es otro robot y embajador cultural regional del estado Anzoátegui, "
                    "desarrollado por el equipo Golden Codex. De hecho, en su código, algoritmos y arquitectura "
                    "nos inspiramos para crear mi propio sistema. ¡Somos como hermanos robóticos unidos por la tecnología y nuestra cultura!"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_hero)
            return resp_hero

        # 1.15 ATAJO DETERMINISTA: IDENTIDAD DE ORBIT ("Who are you" -> NO menciona nombres de integrantes, solo el equipo)
        patrones_quien_eres = [
            r'\b(quien\s+eres|who\s+are\s+you|what\s+are\s+you|who\s+is\s+orbit|what\s+is\s+orbit|que\s+eres|cuentame\s+de\s+ti|tell\s+me\s+about\s+yourself)\b',
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_quien_eres):
            if self.language == "en":
                resp_identidad = (
                    "I am Orbit, an autonomous cultural robotic companion created by the Golden Codex robotics team! "
                    "I feature computer vision for face tracking, expressive animated eyes, and a rich cultural knowledge base celebrating the traditions, geography, and wonders of Venezuela and Puerto Rico. "
                    "What would you like to explore together?"
                )
            else:
                resp_identidad = (
                    "¡Soy Orbit, un compañero robótico autónomo y embajador cultural creado por el equipo de robótica Golden Codex! "
                    "Cuento con visión artificial para seguir tu mirada, expresivos ojos animados y un amplio conocimiento sobre las tradiciones, geografía y maravillas de Venezuela y Puerto Rico. "
                    "¿Qué te gustaría descubrir juntos?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_identidad)
            return resp_identidad

        # 1.16 ATAJO DETERMINISTA: INTEGRANTES DEL EQUIPO ("Who is in the team" -> Maximiliano Rodríguez and Bruno Prandini)
        patrones_equipo = [
            r'\b(who\s+is\s+in\s+the\s+team|who\s+is\s+on\s+the\s+team|who\s+is\s+on\s+your\s+team|team\s+members|who\s+are\s+the\s+members|who\s+are\s+your\s+teammates)\b',
            r'\b(quienes\s+son\s+del\s+equipo|quienes\s+estan\s+en\s+el\s+equipo|quienes\s+integran\s+el\s+equipo|miembros\s+del\s+equipo|integrantes\s+del\s+equipo)\b',
            r'\b(quien\s+te\s+creo|quien\s+te\s+hizo|quien\s+te\s+construyo|quien\s+te\s+programo|who\s+made\s+you|who\s+created\s+you|who\s+built\s+you|who\s+programmed\s+you)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_equipo):
            if self.language == "en":
                resp_equipo = (
                    "The Golden Codex team is formed by Maximiliano Rodríguez and Bruno Prandini! "
                    "They are passionate young robotics students and creators from Venezuela who engineered, built, and programmed me. "
                    "Would you like to know more about our project?"
                )
            else:
                resp_equipo = (
                    "¡El equipo Golden Codex está conformado por Maximiliano Rodríguez y Bruno Prandini! "
                    "Ellos son talentosos jóvenes creadores venezolanos apasionados por la robótica que me diseñaron, construyeron y programaron. "
                    "¿Te gustaría saber más sobre nuestro proyecto?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_equipo)
            return resp_equipo

        # 1.17 ATAJO DETERMINISTA: BRUNO PRANDINI
        patrones_bruno = [
            r'\b(bruno|prandini|bruno\s+prandini)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_bruno):
            if self.language == "en":
                resp_bruno = (
                    "Bruno Prandini is a talented young creator and robotics student from Venezuela! "
                    "He is a core member and builder of team Golden Codex Robotics who helped engineer and develop me for WRO 2026. "
                    "I am very proud to have him on my team!"
                )
            else:
                resp_bruno = (
                    "¡Bruno Prandini es un talentoso joven creador y estudiante de robótica venezolano! "
                    "Es un miembro clave y constructor del equipo Golden Codex Robotics que colaboró en mi ingeniería y desarrollo para la WRO 2026. "
                    "¡Estoy súper orgulloso de tenerlo en mi equipo!"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_bruno)
            return resp_bruno

        # 1.18 ATAJO DETERMINISTA: MAXIMILIANO RODRÍGUEZ
        patrones_max = [
            r'\b(maximiliano|silvagni|silvani|max\s+rodriguez|maximiliano\s+rodriguez)\b',
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_max):
            if self.language == "en":
                resp_max = (
                    "Maximiliano Rodríguez (also known as Max) is a talented young robotics student and creator from Venezuela! "
                    "He is a core developer and builder from team Golden Codex Robotics who designed, engineered, and programmed me for WRO 2026 in Puerto Rico. "
                    "I am incredibly proud and grateful to have him as one of my creators!"
                )
            else:
                resp_max = (
                    "¡Maximiliano Rodríguez (también conocido como Max) es un talentoso joven creador y apasionado de la robótica venezolano! "
                    "Es un miembro clave y programador del equipo Golden Codex Robotics que me dio vida y me programó para competir en la WRO 2026 en Puerto Rico. "
                    "¡Estoy súper orgulloso y agradecido de tenerlo como uno de mis creadores!"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_max)
            return resp_max

        # 1.24 ATAJO DETERMINISTA: QUÉ ES LA WRO E HISTORIA DE LA WRO
        patrones_wro_historia = [
            r'\b(que\s+es\s+(la\s+)?wro|que\s+significa\s+wro|what\s+is\s+(the\s+)?wro|what\s+does\s+wro\s+(mean|stand\s+for))\b',
            r'\b(historia\s+de\s+(la\s+)?wro|history\s+of\s+(the\s+)?wro|origen\s+de\s+(la\s+)?wro|origin\s+of\s+(the\s+)?wro)\b',
            r'\b(cuando\s+se\s+fundo\s+(la\s+)?wro|when\s+was\s+wro\s+founded|quien\s+fundo\s+(la\s+)?wro|donde\s+nacio\s+(la\s+)?wro)\b',
            r'\b(world\s+robot\s+olympiad|olimpiada\s+mundial\s+de\s+robotica)\b',
            r'\b(foto\s+de\s+(la\s+)?wro|imagen\s+de\s+(la\s+)?wro|logo\s+de\s+(la\s+)?wro|emblema\s+de\s+(la\s+)?wro|ver\s+(la\s+)?wro|show.*wro)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_wro_historia):
            self.tema_actual = "wro"
            self.accion_pendiente = "mostrar_wro"
            if self.language == "en":
                resp_wro = (
                    "The World Robot Olympiad (WRO) is a premier global educational robotics competition founded in 2004! "
                    "Its very first International Final took place in Singapore in November 2004 with 12 founding countries. "
                    "Today, WRO unites over 70,000 students from more than 85 countries worldwide, challenging young innovators in categories like Future Innovators, RoboMission, and Future Engineers to solve real-world problems through autonomous robotics! "
                    "Here is the official WRO emblem on my screen! Would you like to hear about the competition categories or its global sponsors?"
                )
            else:
                resp_wro = (
                    "¡La World Robot Olympiad (WRO) u Olimpiada Mundial de Robótica es una prestigiosa competencia global de robótica educativa fundada en el año 2004! "
                    "Su primera Final Internacional se celebró en Singapur en noviembre de 2004 con 12 países fundadores. "
                    "Hoy en día, la WRO congrega a más de 70,000 estudiantes de más de 85 países de todo el mundo en categorías como Future Innovators, RoboMission y Future Engineers para resolver grandes retos con robótica autónoma. "
                    "¡Aquí te muestro el emblema oficial de la WRO en mi pantalla! ¿Te gustaría conocer más sobre sus categorías o sobre sus patrocinantes oficiales?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_wro)
            return resp_wro

        # 1.245 ATAJO DETERMINISTA: PATROCINANTES Y SOCIOS GLOBALES DE LA WRO
        patrones_wro_sponsors = [
            r'\b(patrocinantes\s+de\s+(la\s+)?wro|patrocinadores\s+de\s+(la\s+)?wro|sponsors\s+of\s+wro|wro\s+sponsors|wro\s+partners)\b',
            r'\b(quienes\s+patrocinan\s+(la\s+)?wro|quien\s+patrocina\s+(la\s+)?wro|partners\s+de\s+(la\s+)?wro|socios\s+de\s+(la\s+)?wro)\b',
            r'\b(aramco|mathworks|fischertechnik|roborobo|elecfreaks|zmrobo|matrix\s+robotics|hp\s+robots)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_wro_sponsors):
            self.tema_actual = "wro sponsors"
            if "aramco" in p_norm_amigo:
                if self.language == "en":
                    resp_sp = (
                        "Aramco is a global leader in energy and chemicals and the Strategic Global Innovation Partner of WRO! "
                        "Aramco invests in the next generation of innovators, enriching WRO competitions and sponsoring the prestigious Aramco Innovation Award in Future Innovators, where teams like Team Sprout from Costa Rica won 1st place in 2025. "
                        "Would you like to hear about other WRO partners like MathWorks?"
                    )
                else:
                    resp_sp = (
                        "¡Aramco es líder mundial en energía y química, y el Socio Estratégico Global de Innovación de la WRO! "
                        "Aramco impulsa a las mentes jóvenes para afrontar los grandes retos del planeta y patrocina los premios 'Aramco Innovation Award' en Future Innovators (ganado en 2025 por Team Sprout de Costa Rica). "
                        "¿Te gustaría conocer a otros patrocinantes como MathWorks o fischertechnik?"
                    )
            elif any(w in p_norm_amigo for w in ["mathworks", "matlab", "simulink"]):
                if self.language == "en":
                    resp_sp = (
                        "MathWorks is a world-leading developer of computational software, creators of MATLAB and Simulink! "
                        "As a core WRO partner, MathWorks provides complimentary software licenses and advanced resources for all WRO teams to model, simulate, and program high-performance robots. "
                        "Would you like to hear about the Gold Partners like fischertechnik or Roborobo?"
                    )
                else:
                    resp_sp = (
                        "¡MathWorks es el desarrollador líder mundial de software de computación matemática, creadores de MATLAB y Simulink! "
                        "Como socio de la WRO, ofrece licencias de software gratuitas y recursos de modelado para que los equipos diseñen y programen robots avanzados. "
                        "¿Te gustaría saber sobre los socios Oro como fischertechnik o Roborobo?"
                    )
            elif "fischertechnik" in p_norm_amigo:
                if self.language == "en":
                    resp_sp = (
                        "fischertechnik is a Gold Partner of WRO, founded in Germany in 1965 with almost 60 years inspiring students and engineers! "
                        "Under their motto 'Understanding technology through play', their 'Made in Germany' modular construction kits are acclaimed in schools and universities worldwide for hands-on technical learning. "
                        "Would you like to know more about Roborobo or other partners?"
                    )
                else:
                    resp_sp = (
                        "¡fischertechnik es Socio Oro de la WRO, fundada en Alemania en 1965 con casi 60 años inspirando a niños e ingenieros! "
                        "Bajo su lema 'Comprender la tecnología a través del juego', sus kits modulares 'Made in Germany' se usan en escuelas y universidades de todo el mundo para la enseñanza técnica. "
                        "¿Te gustaría conocer sobre Roborobo u otros socios?"
                    )
            elif "roborobo" in p_norm_amigo:
                if self.language == "en":
                    resp_sp = (
                        "Roborobo is a Gold Partner of WRO founded in South Korea in 2000! "
                        "They are the number 1 robotics education provider in Korea, used across 1,200 primary schools with educational kits like UARO, AIKIRO, and ROBOKIT that teach coding, STEM, and AI to young learners worldwide. "
                        "Would you like to hear about the Silver Partners like ELECFREAKS or Matrix Robotics?"
                    )
                else:
                    resp_sp = (
                        "¡ROBOROBO es Socio Oro de la WRO fundada en el año 2000 en Corea del Sur! "
                        "Es el proveedor número 1 de robótica educativa en Corea (en más de 1,200 escuelas primarias), creador de los kits UARO, AIKIRO y ROBOKIT para aprender programación, STEM e inteligencia artificial. "
                        "¿Te gustaría conocer a los socios Plata como ELECFREAKS o Matrix Robotics?"
                    )
            elif "elecfreaks" in p_norm_amigo:
                if self.language == "en":
                    resp_sp = (
                        "ELECFREAKS is an official Silver Partner of WRO and official partner of the micro:bit Educational Foundation! "
                        "They develop creative micro:bit accessories, sensors, and learning kits with tutorials used by young coders around the globe. "
                        "Would you like to hear about other robotics partners?"
                    )
                else:
                    resp_sp = (
                        "¡ELECFREAKS es Socio Plata de la WRO y socio oficial de la micro:bit Educational Foundation! "
                        "Desarrollan tarjetas de expansión, sensores y accesorios creativos para micro:bit con tutoriales usados por estudiantes en todo el mundo. "
                        "¿Te gustaría conocer a otros patrocinadores?"
                    )
            elif any(w in p_norm_amigo for w in ["matrix", "matrix robotics"]):
                if self.language == "en":
                    resp_sp = (
                        "MATRIX Robotics is a Silver Partner of WRO that created the MATRIX Robotics System! "
                        "They provide heavy-duty aluminum mechanical parts and controllers designed for hands-on, competitive STEM robotics education. "
                        "Would you like to learn more about the other partners?"
                    )
                else:
                    resp_sp = (
                        "¡MATRIX Robotics es Socio Plata de la WRO y creador del MATRIX Robotics System! "
                        "Ofrece piezas metálicas de aluminio de alta resistencia y controladores diseñados para la robótica práctica de competición STEM. "
                        "¿Te gustaría saber más sobre otros patrocinantes?"
                    )
            elif any(w in p_norm_amigo for w in ["zmrobo", "hp robots", "otto"]):
                if self.language == "en":
                    resp_sp = (
                        "ZMROBO and HP Robots are innovative Silver Partners of WRO! "
                        "ZMROBO empowers students with modular block building and AI robotics, while HP Robots champions STEAM learning through the Otto customizable 3D-printed modular robot! "
                        "Would you like to explore more about WRO?"
                    )
                else:
                    resp_sp = (
                        "¡ZMROBO y HP Robots son destacados Socios Plata de la WRO! "
                        "ZMROBO enseña robótica y bloques con IA para crear una era inteligente con los estudiantes, mientras que HP Robots impulsa el aprendizaje STEAM a través de Otto, un robot modular personalizable con impresión 3D. "
                        "¿Te gustaría explorar más sobre la WRO?"
                    )
            else:
                if self.language == "en":
                    resp_sp = (
                        "The World Robot Olympiad is supported by world-class innovation leaders! "
                        "Its Strategic Partner is Aramco (Global Innovation Partner), its computing software partner is MathWorks (MATLAB and Simulink), Gold Partners are fischertechnik and Roborobo, and Silver Partners include ELECFREAKS, ZMROBO, MATRIX Robotics, and HP Robots. "
                        "Would you like to know more about the contribution of one of these partners?"
                    )
                else:
                    resp_sp = (
                        "¡La WRO cuenta con el respaldo de grandes líderes tecnológicos globales! "
                        "Su Socio Estratégico es Aramco (Global Innovation Partner), su socio de software es MathWorks (creadores de MATLAB y Simulink), sus socios Oro son fischertechnik y Roborobo, y sus socios Plata incluyen a ELECFREAKS, ZMROBO, MATRIX Robotics y HP Robots. "
                        "¿Te gustaría conocer el aporte de alguno de ellos en especial?"
                    )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_sp)
            return resp_sp

        # 1.249 ATAJO DETERMINISTA: MODO APRENDER KARI'ÑA (APRENDE CON ORBIT / DUOLINGO)
        patrones_aprender_karina = [
            r'\b(aprender|aprende|aprendamos|estudiar|practicar)\b.*?\b(karina|carina|carino)\b',
            r'\b(ensename|ensenar|clase|leccion|lecciones)\b.*?\b(karina|carina|carino)\b',
            r'\b(modo\s+)?(karina|carina|carino)\b.*?\b(aprender|aprendizaje|estudiar|duolingo)\b',
            r'\bmodo\s+(karina|carina|carino)\b',
            r'\b(quiero|deseo|me\s+gustaria|ensename\s+a|como)\s+hablar\s+(en\s+)?(karina|carina|carino)\b',
            r'\b(duolingo|duolingorbit|aprende\s+con\s+orbit)\b',
            r'\b(learn|study|practice|teach\s+me)\b.*?\b(karina|indigenous)\b',
            r'\b(open\s+duolingo|duolingo\s+mode|learn\s+with\s+orbit)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_aprender_karina):
            self.tema_actual = "indigenas karinas"
            self.accion_pendiente = "abrir_aprender_karina"
            self.ofrecio_musica_karina = False
            if self.language == "en":
                resp_aprender_k = (
                    "How wonderful to learn our ancestral roots! Opening Learn with Orbit to practice the Kari'ña language with interactive lessons and pronunciation."
                )
            else:
                resp_aprender_k = (
                    "¡Qué gran entusiasmo por nuestras raíces ancestrales! Abriendo Aprende con Orbit para practicar la lengua Kari'ña con pronunciación interactiva y lecciones."
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_aprender_k)
            return resp_aprender_k

        # 1.25 ATAJO DETERMINISTA: PREGUNTA OFICIAL WRO - LENGUA INDÍGENA KARI'ÑA (AMANA)
        patrones_karina_amana = [
            r'\b(teach\s+me\s+a\s+word|teach\s+me.*word|indigenous\s+language.*(carina|cariña|karina|kariña))\b',
            r'\b(can\s+you\s+teach\s+me.*(carina|cariña|karina|kariña|indigenous))\b',
            r'\b(palabra\s+en\s+(carina|cariña|karina|kariña)|palabra.*indigena|palabra.*indígena)\b',
            r'\b(ensename\s+una\s+palabra|enseñame\s+una\s+palabra|ensenar\s+una\s+palabra|enseñar\s+una\s+palabra)\b',
            r'\b(que\s+significa\s+amana|significado\s+de\s+amana|what\s+does\s+amana\s+mean)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_karina_amana):
            self.tema_actual = "indigenas karinas"
            self.ofrecio_saludo_karina = True
            if self.language == "en":
                resp_karina_wro = (
                    "What a great question! I love sharing our ancestral roots. In Kari'ña, 'Amana' means sacred water or river. "
                    "For our native peoples, water not only gives life, but connects communities across the world! "
                    "Would you like to learn how to greet a friend in Kari'ña?"
                )
            else:
                resp_karina_wro = (
                    "¡Qué gran pregunta! Me encanta compartir nuestras raíces. En Kari'ña, 'Amana' significa agua o río sagrado. "
                    "Para nuestros pueblos originarios, el agua no solo da vida, sino que conecta las comunidades a través del mundo. "
                    "¿Te gustaría aprender cómo se saluda un amigo en Kari'ña?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_karina_wro)
            return resp_karina_wro

        # 1.254 ATAJO DETERMINISTA: PETICIÓN DIRECTA DE MÚSICA / FOTO DE LOS KARI'ÑA
        patrones_karina_directo = [
            r'\b(pon|reproduce|toca|coloca|play|escuchar|ver|muestra|muéstrame|ensename|enseñame|show)\s+(la\s+cancion|el\s+canto|la\s+musica|el\s+tema|la\s+foto|la\s+imagen|el\s+video)?.*(karina|kariña|carina|cariña|carino|carinos|cariño|cariños|mare\s*mare|maremare)\b',
            r'\b(pon|play|reproduce|toca)\s+(el\s+mare\s*mare|mare\s*mare|canto\s+(karina|kariña|carina|cariña|carino|carinos|cariño|cariños)|musica\s+(karina|kariña|carina|cariña|carino|carinos|cariño|cariños)|musica\s+indigena)\b',
            r'\b(muestra|muestrame|muéstrame|ensename|enseñame|show|ver)\s+(la\s+foto|la\s+imagen|a\s+los\s+(karina|kariña|carina|cariña|carino|carinos|cariño|cariños))\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_karina_directo):
            self.tema_actual = "indigenas karinas"
            self.accion_pendiente = "mostrar_karina"
            self.ofrecio_musica_karina = False
            if self.language == "en":
                resp_k_direct = (
                    "Of course! Here are the Kari'ña people and their sacred Mare-Mare celebration with Carrizo flutes and drums."
                )
            else:
                resp_k_direct = (
                    "¡Por supuesto! Aquí tienes al pueblo Kariña y su celebración del Mare-Mare al compás de flautas de carrizo y tambores sagrados."
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_k_direct)
            return resp_k_direct

        # 1.255 ATAJO DETERMINISTA: SEGUIMIENTO TRAS MOSTRAR MÚSICA / FOTO KARI'ÑA (SABER MÁS)
        patrones_karina_seguimiento = [
            r'\b(mas\s+(de|sobre)\s+(los\s+)?(karina|kariña|carina|cariña|carino|carinos|cariño|cariños)s?|cuentame\s+mas\s+(de|sobre)\s+(los\s+)?(karina|kariña|carina|cariña|carino|carinos|cariño|cariños)s?|saber\s+mas\s+(de|sobre)\s+(los\s+)?(karina|kariña|carina|cariña|carino|carinos|cariño|cariños)s?)\b',
            r'\b(more\s+about\s+(the\s+)?(karina|kariña)s?|tell\s+me\s+more\s+about\s+(the\s+)?(karina|kariña)s?)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_karina_seguimiento):
            self.tema_actual = "indigenas karinas"
            self.accion_pendiente = None
            if self.language == "en":
                resp_k_more = (
                    "With pleasure! The Kari'ña celebrate the sacred Akaatompo every November to honor ancestral spirits with communal songs and dancing. "
                    "They are also master artisans of the sacred moriche palm, weaving durable chinchorro hammocks and traditional baskets. "
                    "Would you like to know how this compares to indigenous traditions in Puerto Rico?"
                )
            else:
                resp_k_more = (
                    "¡Con mucho gusto! Los Kari'ña celebran el sagrado Akaatompo cada noviembre para honrar las almas de sus ancestros, bailando el Mare-Mare de casa en casa. "
                    "Además, son admirados maestros tejiendo la fibra de la palma de moriche para crear resistentes chinchorros y cestas tradicionales. "
                    "¿Te gustaría saber cómo se compara con las tradiciones ancestrales de Puerto Rico?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_k_more)
            return resp_k_more

        # 1.256 ATAJO DETERMINISTA: CULTURA INDÍGENA KARI'ÑA (CARIÑA) -> OFRECER VER IMAGEN Y MÚSICA
        patrones_karina_general = [
            r'\b(karina|karinas|kariña|kariñas|carina|carinas|cariña|cariñas)\b',
            r'\b(los\s+)?(cariño|cariños|carino|carinos)\b',
            r'\b(pueblo|etnia|indigenas?)\s+(los\s+)?(cariño|cariños|carino|carinos)\b',
            r'\b(mare\s*mare|maremare|akaatompo)\b',
            r'\b(canto|cancion|musica|baile|danza)\s+(de\s+)?(los\s+)?(karina|kariña|carina|cariña|carino|carinos|cariño|cariños)\b',
            r'\b(flauta\s+de\s+carrizo|flautas\s+de\s+carrizo|carrizo\s+(karina|kariña))\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_karina_general) and not any(re.search(pat, p_norm_amigo) for pat in patrones_karina_amana):
            self.tema_actual = "indigenas karinas"
            # OFRECER ver imagen y música Mare-Mare SIN reproducirla de inmediato (esperar respuesta afirmativa)
            self.ofrecio_musica_karina = True
            self.accion_pendiente = None
            es_pregunta_compuesta_ve = any(w in p_norm_amigo for w in ["cultura", "tradicion", "tradiciones", "costumbre", "costumbres", "venezuela", "venezolana", "heritage"])
            if self.language == "en":
                if es_pregunta_compuesta_ve:
                    resp_k = (
                        "Venezuela has an extraordinarily rich culture, and its indigenous roots are the beating heart of our living traditions! "
                        "The Kari'ña are the revered ancestral people of the Mesa de Guanipa in Anzoátegui, guardians of moriche palm weaving and the sacred Akaatompo celebration, where they dance the Mare-Mare to Carrizo flutes and drums. "
                        "Would you like to see them and hear a traditional song of theirs?"
                    )
                else:
                    resp_k = (
                        "The Kari'ña are the revered ancestral indigenous people of Anzoátegui, Venezuela, hailing from the sacred Mesa de Guanipa! "
                        "They have preserved their culture, moriche palm weaving, and their sacred Akaatompo celebration where they dance the Mare-Mare to the hypnotic melodies of Carrizo flutes and drums. "
                        "Would you like to see them and hear a traditional song of theirs?"
                    )
            else:
                if es_pregunta_compuesta_ve:
                    resp_k = (
                        "¡Venezuela posee una inmensa riqueza cultural y sus raíces indígenas son el corazón de nuestras tradiciones vivas! "
                        "Los Kari'ña son el pueblo ancestral originario de la Mesa de Guanipa en Anzoátegui, guardianes del tejido de moriche y su festividad sagrada del Akaatompo, donde bailan el Mare-Mare al compás de las flautas de carrizo y el tambor sagrado. "
                        "¿Quieres verlos y escuchar una canción tradicional de ellos?"
                    )
                else:
                    resp_k = (
                        "¡Los Kari'ña son el pueblo indígena ancestral originario de la Mesa de Guanipa en Anzoátegui, Venezuela! "
                        "Han resguardado sus ricas tradiciones, el tejido de moriche y su festividad sagrada del Akaatompo, bailando el Mare-Mare al compás de las flautas de carrizo y el tambor sagrado. "
                        "¿Quieres verlos y escuchar una canción tradicional de ellos?"
                    )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_k)
            return resp_k

        # 1.26 ATAJO DETERMINISTA: DESPEDIDA WRO PUERTO RICO
        patrones_puerto_rico = [
            r'\b(see\s+you\s+soon\s+in\s+puerto\s+rico|see\s+you\s+in\s+puerto\s+rico|nos\s+vemos\s+en\s+puerto\s+rico|nos\s+vemos\s+pronto\s+en\s+puerto\s+rico)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_puerto_rico):
            self.tema_actual = "puerto rico"
            resp_pr = "See you soon in Puerto Rico!" if self.language == "en" else "¡Nos vemos pronto en Puerto Rico!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_pr)
            return resp_pr

        # 1.71 ATAJO DETERMINISTA: CANCIONES EMBLEMÁTICAS Y LETRAS (LYRICS)
        # Atajo determinista general: Solicitud de catálogo de canciones / repertorio musical
        patrones_catalogo_musica = [
            r'\b(que|cuales)\s+(otras?\s+)?canciones\s+(puedo\s+escuchar|tienes|hay|puedes\s+poner|puedes\s+reproducir)\b',
            r'\b(que|cuales)\s+(otra\s+)?musica\s+(puedo\s+escuchar|tienes|hay)\b',
            r'\b(canciones\s+disponibles|repertorio\s+musical|catalogo\s+de\s+canciones|lista\s+de\s+canciones)\b',
            r'\bwhat\s+(other\s+)?songs\s+(can\s+i\s+(listen\s+to|hear)|do\s+you\s+have|are\s+there)\b',
            r'\bwhat\s+(other\s+)?music\s+(can\s+i\s+(listen\s+to|hear)|do\s+you\s+have)\b',
            r'\b(available\s+songs|music\s+repertoire|song\s+catalog|song\s+list)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_catalogo_musica):
            self.tema_actual = "catalogo musica"
            self.ofrecio_alma_llanera = True
            self.ofrecio_caballo_viejo = True
            self.ofrecio_venezuela = True
            self.ofrecio_rawayana = True
            self.ofrecio_viejo_san_juan = True
            self.ofrecio_verde_luz = True
            self.ofrecio_preciosa = True
            self.ofrecio_pr_pop = True
            self.ofrecio_world = True
            if self.language == "en":
                resp_cat = (
                    "I have an incredible music repertoire with lyrics on my screen! "
                    "From Venezuela: 'Alma Llanera', 'Caballo Viejo' by Simón Díaz, the anthem 'Venezuela', and 'High' by Rawayana. "
                    "From Puerto Rico: 'En mi Viejo San Juan', 'Verde Luz', 'Preciosa', and 'Tití Me Preguntó' by Bad Bunny. "
                    "And from the world: the stadium rock anthem 'We Will Rock You' by Queen! "
                    "Which one would you like to listen to?"
                )
            else:
                resp_cat = (
                    "¡Tengo un repertorio musical genial con canciones completas y sus letras en pantalla! "
                    "De Venezuela: el joropo 'Alma Llanera', 'Caballo Viejo' de Simón Díaz, el himno 'Venezuela' y reggae-pop con 'High' de Rawayana. "
                    "De Puerto Rico: 'En mi Viejo San Juan', 'Verde Luz', 'Preciosa' y pop urbano con 'Tití Me Preguntó' de Bad Bunny. "
                    "Y del mundo: ¡el himno de rock 'We Will Rock You' de Queen! "
                    "¿Cuál te gustaría escuchar con su letra en pantalla?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_cat)
            return resp_cat

        # Canción 1: Alma Llanera (Venezuela)
        patrones_play_alma = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+)?(alma\s+llanera)\b',
            r'\b(quiero\s+escuchar\s+alma\s+llanera|pon\s+alma\s+llanera|play\s+alma\s+llanera|reproduce\s+alma\s+llanera|listen\s+to\s+alma\s+llanera)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(alma\s+llanera)\b',
            r'\balmalir(\.png)?\b',
            r'\balma\s+llanera\b',
            r'^\s*(el\s+)?(joropo|alma\s+llanera)\s*$'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_alma):
            self.tema_actual = "joropo"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "alma"
            self.accion_pendiente = "reproducir_alma"
            if self.language == "en":
                resp_play = "Turn up the volume and feel the Venezuelan pride! Here is Alma Llanera with its original lyrics on my screen!"
            else:
                resp_play = "¡Por supuesto! ¡Sube el volumen y siente el orgullo llanero con Alma Llanera y su letra original en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play)
            return resp_play

        # Canción 2: Caballo Viejo (Venezuela - Simón Díaz)
        patrones_play_cv = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+)?(caballo\s+viejo)\b',
            r'\b(quiero\s+escuchar\s+caballo\s+viejo|play\s+caballo\s+viejo|listen\s+to\s+caballo\s+viejo)\b',
            r'\b(cancion\s+de\s+simon\s+diaz|musica\s+de\s+simon\s+diaz|tio\s+simon|tío\s+simón)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(caballo\s+viejo)\b',
            r'\bcaballoviejolir(\.png)?\b',
            r'\bcaballo\s+viejo\b',
            r'^\s*(la\s+de\s+)?caballo\s+viejo\s*$'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_cv):
            self.tema_actual = "caballo viejo"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "caballo_viejo"
            self.accion_pendiente = "reproducir_caballo_viejo"
            if self.language == "en":
                resp_play_cv = "Caballo Viejo by the great Simón Díaz is the most celebrated Venezuelan folk song in history. Enjoy it with its original lyrics on my screen!"
            else:
                resp_play_cv = "¡'Caballo Viejo' del gran maestro Simón Díaz es la canción folklórica venezolana más famosa del mundo! ¡Disfrútala con su letra original en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_cv)
            return resp_play_cv

        # Canción 3: Venezuela (Himno sentimental - Herrero y Armenteros)
        patrones_play_vz = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+)?(venezuela|llevo\s+tu\s+luz)\b',
            r'\b(quiero\s+escuchar\s+venezuela|play\s+venezuela|reproduce\s+venezuela|listen\s+to\s+venezuela)\b',
            r'\b(llevo\s+tu\s+luz\s+y\s+tu\s+aroma|tercer\s+himno(\s+de\s+venezuela)?)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(venezuela|llevo\s+tu\s+luz)\b',
            r'\bvenezuelalir(\.png)?\b',
            r'^\s*(la\s+de\s+|cancion\s+)?venezuela\s*$'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_vz):
            self.tema_actual = "cancion venezuela"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "venezuela"
            self.accion_pendiente = "reproducir_venezuela"
            if self.language == "en":
                resp_play_vz = "Prepare your heart! Here is 'Venezuela', the most beloved patriotic anthem, with its lyrics on my screen!"
            else:
                resp_play_vz = "¡Prepara el corazón! ¡Aquí tienes 'Venezuela', el tercer himno nacional más emotivo, con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_vz)
            return resp_play_vz

        # Canción 4: Rawayana - High ft. Apache (Venezuela - Cultura Pop / Reggae)
        patrones_play_rw = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+|musica\s+de\s+|algo\s+de\s+|music\s+(from\s+|of\s+)?)?(rawayana|high|sube\s+el\s+volumen)\b',
            r'\b(quiero\s+escuchar|play|listen\s+to|i\s+want\s+to\s+listen(\s+to)?)\s+(a\s+|to\s+)?(rawayana|high)\b',
            r'\b(cancion\s+de\s+rawayana|musica\s+de\s+rawayana|reggae\s+venezolano|trippy\s+caribbean)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(rawayana|high)\b',
            r'\brawayanalir(\.png)?\b',
            r'\bhigh\s+(de\s+)?rawayana\b',
            r'\brawayana\b',
            r'^\s*(la\s+de\s+|cancion\s+de\s+)?high\s*$',
            r'^\s*(la\s+de\s+)?rawayana\s*$'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_rw):
            self.tema_actual = "rawayana"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "rawayana"
            self.accion_pendiente = "reproducir_rawayana"
            if self.language == "en":
                resp_play_rw = "Feel the tropical Venezuelan grooves! Here is 'High' by Rawayana featuring Apache with its lyrics on my screen!"
            else:
                resp_play_rw = "¡Siente la buena vibra caribeña venezolana! ¡Aquí tienes 'High' de Rawayana y Apache con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_rw)
            return resp_play_rw

        # Canción 5: En mi Viejo San Juan (Puerto Rico - Segundo Himno)
        patrones_play_sj = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+)?(en\s+mi\s+)?(viejo\s+san\s+juan)\b',
            r'\b(quiero\s+escuchar\s+(en\s+mi\s+)?viejo\s+san\s+juan|play\s+(en\s+mi\s+)?viejo\s+san\s+juan|listen\s+to\s+(en\s+mi\s+)?viejo\s+san\s+juan)\b',
            r'\b(pon|play|toca|reproduce|listen|hear)\s+(la\s+)?(musica|music|cancion|song)\s+(de\s+|from\s+|in\s+)?(san\s+juan|viejo\s+san\s+juan)\b',
            r'\b(en\s+mi\s+)?(viejo\s+san\s+juan)\b',
            r'\b(cancion|canción|musica|música|himno)\s+(equivalente|parecida|representativa|segundo\s+himno).*(puerto\s+rico|puertorrique[nñ][ao]|boricua|borinquen)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(en\s+mi\s+)?(viejo\s+san\s+juan)\b',
            r'\bviejosanjuanlir(\.png)?\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_sj):
            self.tema_actual = "viejo san juan"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "viejo_san_juan"
            self.accion_pendiente = "reproducir_viejo_san_juan"
            if self.language == "en":
                resp_play_sj = "Feel the nostalgic soul of Puerto Rico! Composed by Noel Estrada in 1943, En mi Viejo San Juan is the beloved second anthem of Puerto Rico. Here it is with its lyrics on my screen!"
            else:
                resp_play_sj = "¡Siente la emoción y la nostalgia boricua! Compuesta por Noel Estrada en 1943, 'En mi Viejo San Juan' es la joya musical y el segundo himno de Puerto Rico. ¡Aquí la tienes con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_sj)
            return resp_play_sj

        # Canción 6: Verde Luz (Puerto Rico - Antonio Cabán Vale "El Topo")
        patrones_play_vl = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+)?(verde\s+luz)\b',
            r'\b(quiero\s+escuchar\s+verde\s+luz|play\s+verde\s+luz|listen\s+to\s+verde\s+luz)\b',
            r'\b(verde\s+luz)\b',
            r'\b(cancion\s+de\s+el\s+topo|antonio\s+caban\s+vale|danza\s+de\s+puerto\s+rico)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(verde\s+luz)\b',
            r'\bverdeluzlir(\.png)?\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_vl):
            self.tema_actual = "verde luz"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "verde_luz"
            self.accion_pendiente = "reproducir_verde_luz"
            if self.language == "en":
                resp_play_vl = "Verde Luz by Antonio Cabán Vale 'El Topo' is the green anthem celebrating the majestic mountains and sea of Puerto Rico. Here it is with its lyrics on my screen!"
            else:
                resp_play_vl = "¡'Verde Luz' de Antonio Cabán Vale 'El Topo' es la majestuosa danza considerada el himno de la naturaleza y las montañas de Puerto Rico! ¡Aquí la tienes con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_vl)
            return resp_play_vl

        # Canción 7: Tití Me Preguntó - Bad Bunny (Puerto Rico - Cultura Pop)
        patrones_play_pr_pop = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+|musica\s+|music\s+(from\s+|of\s+)?)?(pop|cultura\s+pop|pop\s+de\s+puerto\s+rico|bad\s+bunny|titi|tití|city|benito|titi\s+me\s+pregunto|tití\s+me\s+preguntó|city\s+me\s+pregunto|me\s+pregunto)\b',
            r'\b(cultura\s+pop\s+de\s+puerto\s+rico|musica\s+pop\s+de\s+puerto\s+rico|cancion\s+pop\s+de\s+puerto\s+rico)\b',
            r'\b(quiero\s+escuchar|play|listen\s+to|i\s+want\s+to\s+listen(\s+to)?)\s+(the\s+)?(music\s+from\s+|song\s+from\s+|to\s+)?(bad\s+bunny|titi\s+me\s+pregunto|tití\s+me\s+preguntó|city\s+me\s+pregunto|city|benito|musica\s+urbana)\b',
            r'\b(city\s+me\s+pregunto|city\s+me\s+pregunt[oó]|titi\s+me\s+pregunto|tití\s+me\s+preguntó)\b',
            r'\b(bad\s+bunny)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(titi|tití|city|bad\s+bunny|pr\s+pop)\b',
            r'\b(prpoplir|titilir)(\.png)?\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_pr_pop):
            self.tema_actual = "pr pop"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "pr_pop"
            self.accion_pendiente = "reproducir_pr_pop"
            if self.language == "en":
                resp_play_pop = "Get ready to dance! Bad Bunny is Puerto Rico's modern pop sensation. Here is 'Tití Me Preguntó' with its lyrics on my screen!"
            else:
                resp_play_pop = "¡A bailar con el ícono mundial de Puerto Rico! Bad Bunny lidera la cultura pop de la isla. ¡Aquí tienes 'Tití Me Preguntó' con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_pop)
            return resp_play_pop

        # Canción 8: Preciosa - Rafael Hernández / Marc Anthony (Puerto Rico Emblemática)
        patrones_play_preciosa = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+)?(preciosa|preciosa\s+te\s+llaman)\b',
            r'\b(quiero\s+escuchar\s+preciosa|play\s+preciosa|reproduce\s+preciosa|listen\s+to\s+preciosa)\b',
            r'\b(cancion\s+emblematica|canción\s+emblemática|emblematica\s+de\s+puerto\s+rico)\b',
            r'\b(cancion\s+de\s+rafael\s+hernandez|preciosa\s+de\s+marc\s+anthony|preciosa\s+te\s+llaman)\b',
            r'^\s*(la\s+de\s+|cancion\s+)?preciosa\s*$',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(preciosa)\b',
            r'\bpreciosalir(\.png)?\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_preciosa):
            self.tema_actual = "preciosa"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "preciosa"
            self.accion_pendiente = "reproducir_preciosa"
            if self.language == "en":
                resp_play_prec = "Preciosa by Rafael Hernández, powerfully interpreted by Marc Anthony, is Puerto Rico's greatest declaration of love. Enjoy it with its lyrics on my screen!"
            else:
                resp_play_prec = "¡'Preciosa' de Rafael Hernández interpretada con el alma por Marc Anthony es la mayor declaración de amor a Borinquen! ¡Disfrútala con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_prec)
            return resp_play_prec

        # Canción 9: We Will Rock You - Queen (Canción del Mundo / Universal / Rock)
        patrones_play_world = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen(\s+to)?|i\s+want\s+to\s+listen(\s+to)?|hear)\s+(the\s+|la\s+cancion\s+|el\s+tema\s+|algo\s+de\s+|musica\s+|music\s+(from\s+|of\s+)?)?(queen|we\s+will\s+rock\s+you|rock\s+you)\b',
            r'\b(pon|reproduce|toca|play|escuchar|coloca|listen|hear)\s+(la\s+cancion\s+|el\s+tema\s+|algo\s+)?(del\s+mundo|cancion\s+mundial|world\s+song)\b',
            r'\b(we\s+will\s+rock\s+you)\b',
            r'\b(queen)\b',
            r'\b(musica\s+(en\s+ingles|americana|gringa|rock)|american\s+music|rock\s+music|english\s+music)\b',
            r'\b(cancion\s+del\s+mundo|canción\s+del\s+mundo|musica\s+del\s+mundo|world\s+song|cancion\s+que\s+todo\s+el\s+mundo\s+conozca|cancion\s+global)\b',
            r'\b(quiero\s+escuchar|play|escuchar|listen\s+to|i\s+want\s+to\s+listen(\s+to)?)\s+(to\s+|a\s+)?(queen|we\s+will\s+rock\s+you|cancion\s+del\s+mundo|world\s+song)\b',
            r'\b(lyrics|letra|letras)\s+(de\s+|of\s+)?(queen|we\s+will\s+rock\s+you|mundo|world)\b',
            r'\b(worldlir|queenlir)(\.png)?\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_world):
            self.tema_actual = "world"
            self._limpiar_ofertas_musica()
            self.cancion_reproducida_reciente = "world"
            self.accion_pendiente = "reproducir_world"
            if self.language == "en":
                resp_play_wld = "Stomp stomp clap! Here is the most universally known stadium anthem in history: 'We Will Rock You' by Queen, with its lyrics on my screen!"
            else:
                resp_play_wld = "¡A aplaudir con el himno universal que une al mundo entero en los estadios! ¡Aquí tienes 'We Will Rock You' de Queen con su letra en pantalla!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play_wld)
            return resp_play_wld

        # Manejo contextual: "la otra canción", "otra canción que mencionaste", "otra canción"
        patrones_otra_cancion = [
            r'\b(la\s+otra\s+cancion|la\s+otra\s+canción|otra\s+cancion|otra\s+canción|la\s+otra|la\s+segunda\s+cancion|the\s+other\s+song|another\s+song)\b',
            r'\b(otra\s+cancion|otra\s+canción|la\s+otra).*(mencionaste|dijiste|hablaste|puerto\s+rico|puertorrique[nñ][ao]|san\s+juan|boricua|venezuela)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_otra_cancion):
            if self.cancion_reproducida_reciente == "alma":
                self.tema_actual = "caballo viejo"
                self.cancion_reproducida_reciente = "caballo_viejo"
                self.accion_pendiente = "reproducir_caballo_viejo"
                resp_otra = "The other supreme classic of Venezuelan folk music is Caballo Viejo by Simón Díaz! Enjoy it with its lyrics on my screen!" if self.language == "en" else "¡El otro gran clásico folklórico de Venezuela es 'Caballo Viejo' del maestro Simón Díaz! ¡Disfrútala con su letra en pantalla!"
            elif self.cancion_reproducida_reciente == "caballo_viejo":
                self.tema_actual = "cancion venezuela"
                self.cancion_reproducida_reciente = "venezuela"
                self.accion_pendiente = "reproducir_venezuela"
                resp_otra = "Here is the stirring patriotic anthem 'Venezuela' by Herrero and Armenteros with its lyrics!" if self.language == "en" else "¡La otra gran obra maestra de Venezuela es el himno sentimental 'Venezuela'! ¡Aquí la tienes con su letra en pantalla!"
            elif self.cancion_reproducida_reciente == "venezuela":
                self.tema_actual = "rawayana"
                self.cancion_reproducida_reciente = "rawayana"
                self.accion_pendiente = "reproducir_rawayana"
                resp_otra = "For modern Venezuelan reggae-pop vibes, here is 'High' by Rawayana ft. Apache with its lyrics!" if self.language == "en" else "¡Para una vibra venezolana fresca y moderna, aquí tienes 'High' de Rawayana con Apache y su letra en pantalla!"
            elif self.cancion_reproducida_reciente == "rawayana":
                self.tema_actual = "world"
                self.cancion_reproducida_reciente = "world"
                self.accion_pendiente = "reproducir_world"
                resp_otra = "And for a global world anthem everyone knows, here is 'We Will Rock You' by Queen!" if self.language == "en" else "¡Y para un himno mundial que todo el planeta corea, aquí tienes 'We Will Rock You' de Queen con su letra!"
            elif self.cancion_reproducida_reciente in ["viejo_san_juan", "musica san juan"]:
                self.tema_actual = "verde luz"
                self.cancion_reproducida_reciente = "verde_luz"
                self.accion_pendiente = "reproducir_verde_luz"
                resp_otra = "Here is the other masterpiece: Verde Luz by Antonio Cabán Vale 'El Topo', with its lyrics on my screen!" if self.language == "en" else "¡La otra joya de Puerto Rico es 'Verde Luz' de Antonio Cabán Vale 'El Topo'. ¡Aquí la tienes con su letra en pantalla!"
            elif self.cancion_reproducida_reciente == "verde_luz":
                self.tema_actual = "preciosa"
                self.cancion_reproducida_reciente = "preciosa"
                self.accion_pendiente = "reproducir_preciosa"
                resp_otra = "Here is the iconic Puerto Rican anthem 'Preciosa' by Rafael Hernández & Marc Anthony!" if self.language == "en" else "¡El otro himno emblemático de Puerto Rico es 'Preciosa' de Rafael Hernández interpretada por Marc Anthony!"
            elif self.cancion_reproducida_reciente == "preciosa":
                self.tema_actual = "pr pop"
                self.cancion_reproducida_reciente = "pr_pop"
                self.accion_pendiente = "reproducir_pr_pop"
                resp_otra = "And representing modern Puerto Rican pop culture worldwide: 'Tití Me Preguntó' by Bad Bunny!" if self.language == "en" else "¡Y representando la cultura pop boricua que conquistó el mundo: 'Tití Me Preguntó' de Bad Bunny!"
            elif self.cancion_reproducida_reciente == "pr_pop":
                self.tema_actual = "viejo san juan"
                self.cancion_reproducida_reciente = "viejo_san_juan"
                self.accion_pendiente = "reproducir_viejo_san_juan"
                resp_otra = "Returning to traditional soul, here is 'En mi Viejo San Juan' by Noel Estrada!" if self.language == "en" else "¡Volviendo al alma tradicional boricua, aquí tienes 'En mi Viejo San Juan' de Noel Estrada!"
            else:
                self.tema_actual = "world"
                self.cancion_reproducida_reciente = "world"
                self.accion_pendiente = "reproducir_world"
                resp_otra = "Here is a world anthem that everyone on Earth knows: 'We Will Rock You' by Queen!" if self.language == "en" else "¡Aquí tienes una canción del mundo que cualquier persona del planeta reconoce: 'We Will Rock You' de Queen!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_otra)
            return resp_otra


        # 1.3 RESOLUCIÓN DE OFERTAS MULTI-TURNO PENDIENTES
        tipo_entrada = self.clasificar_tipo_entrada(pregunta_limpia)

        if self.ofrecio_saludo_karina:
            if tipo_entrada == "afirmativo" or any(w in p_norm_amigo for w in ["si", "claro", "me gustaria", "ensename", "yes", "sure"]):
                self.ofrecio_saludo_karina = False
                self.ofrecio_musica_karina = True
                if self.language == "en":
                    resp_saludo_k = (
                        "In Kari'ña, to greet a good friend you say 'Yu'pua!' or 'Moruwa!', which conveys deep warmth, friendship, and peace. "
                        "Would you like to see their traditional ceremony and hear their sacred Mare-Mare music?"
                    )
                else:
                    resp_saludo_k = (
                        "¡Por supuesto! Para saludar a un buen amigo en Kari'ña dices '¡Yu'pua!' o '¡Moruwa!', un saludo lleno de calidez, amistad y respeto. "
                        "¿Te gustaría ver su ceremonia tradicional y escuchar su música sagrada del Mare-Mare?"
                    )
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_saludo_k)
                return resp_saludo_k
            elif tipo_entrada == "negativo":
                self.ofrecio_saludo_karina = False
                if self.language == "en":
                    resp_saludo_no = "No worries at all! Our cultural journey is filled with endless wonders. What else would you like to explore today?"
                else:
                    resp_saludo_no = "¡No hay problema! Nuestra historia y cultura tienen muchísimos otros temas fascinantes. ¿De qué te gustaría hablar ahora?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_saludo_no)
                return resp_saludo_no
            else:
                self.ofrecio_saludo_karina = False

        if self.ofrecio_musica_karina:
            palabras_afirma = ["si", "claro", "quiero", "dale", "yes", "sure", "play", "show", "escuchar", "ver", "verlos", "mostramelos", "muestramelos", "por favor", "adelante", "bueno", "obvio", "seguro", "de una"]
            if tipo_entrada == "afirmativo" or any(w in p_norm_amigo for w in palabras_afirma):
                self.ofrecio_musica_karina = False
                self.accion_pendiente = "mostrar_karina"
                if self.language == "en":
                    resp_k_show = "With great joy and pride! Here are the Kari'ña people and their beautiful traditional Mare-Mare song played on Carrizo flutes."
                else:
                    resp_k_show = "¡Con mucho orgullo! Aquí tienes al pueblo Kari'ña y su hermoso canto tradicional del Mare-Mare al compás de las flautas de carrizo."
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_k_show)
                return resp_k_show
            elif tipo_entrada == "negativo":
                self.ofrecio_musica_karina = False
                if self.language == "en":
                    resp_k_no = "No problem at all! Venezuelan culture has endless wonders. What other topic would you like to explore today?"
                else:
                    resp_k_no = "¡No hay problema! Nuestra cultura tiene miles de maravillas por descubrir. ¿De qué otro tema te gustaría hablar hoy?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_k_no)
                return resp_k_no
            else:
                self.ofrecio_musica_karina = False

        # Manejo prioritario de selección directa cuando Orbit ofreció las canciones
        if (getattr(self, 'ofrecio_alma_llanera', False) or getattr(self, 'ofrecio_caballo_viejo', False) or
            getattr(self, 'ofrecio_venezuela', False) or getattr(self, 'ofrecio_rawayana', False) or
            getattr(self, 'ofrecio_viejo_san_juan', False) or getattr(self, 'ofrecio_verde_luz', False) or
            getattr(self, 'ofrecio_pr_pop', False)):

            if re.search(r'\b(rawayana|high)\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "rawayana"
                self.accion_pendiente = "reproducir_rawayana"
                if self.language == "en":
                    resp_rw = "Feel the tropical Venezuelan grooves! Here is 'High' by Rawayana featuring Apache with its lyrics on my screen!"
                else:
                    resp_rw = "¡Sube el volumen y siente la vibra caribeña! ¡Aquí tienes 'High' de Rawayana y Apache con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_rw)
                return resp_rw

            if re.search(r'\b(alma(\s+llanera)?|llanera|joropo)\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "alma"
                self.accion_pendiente = "reproducir_alma"
                if self.language == "en":
                    resp_alma = "Turn up the volume and feel the Venezuelan pride! Here is Alma Llanera with its original lyrics on my screen!"
                else:
                    resp_alma = "¡Por supuesto! ¡Sube el volumen y siente el orgullo llanero con Alma Llanera y su letra original en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_alma)
                return resp_alma

            if re.search(r'\b(caballo(\s+viejo)?|viejo\s+simon|simon(\s+diaz)?|tío\s+simón)\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "caballo_viejo"
                self.accion_pendiente = "reproducir_caballo_viejo"
                if self.language == "en":
                    resp_cv = "Here is Caballo Viejo by the beloved Simón Díaz with its lyrics!"
                else:
                    resp_cv = "¡Aquí tienes Caballo Viejo del querido tío Simón Díaz con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_cv)
                return resp_cv

            if re.search(r'\b(cancion\s+)?venezuela\b|\bllevo\s+tu\s+luz\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "venezuela"
                self.accion_pendiente = "reproducir_venezuela"
                if self.language == "en":
                    resp_vz = "Prepare your heart! Here is 'Venezuela', the most beloved patriotic anthem, with its lyrics on my screen!"
                else:
                    resp_vz = "¡Siente la emoción a flor de piel! ¡Aquí tienes el himno sentimental 'Venezuela' con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_vz)
                return resp_vz

            if re.search(r'\b(verde\s+luz|el\s+topo)\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "verde_luz"
                self.accion_pendiente = "reproducir_verde_luz"
                if self.language == "en":
                    resp_vl = "Here is Verde Luz by Antonio Cabán Vale 'El Topo' with its lyrics on my screen!"
                else:
                    resp_vl = "¡Aquí tienes 'Verde Luz' de Antonio Cabán Vale 'El Topo' con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_vl)
                return resp_vl

            if re.search(r'\b(viejo\s+san\s+juan|san\s+juan)\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "viejo_san_juan"
                self.accion_pendiente = "reproducir_viejo_san_juan"
                if self.language == "en":
                    resp_sj = "Feel the nostalgic magic of Puerto Rico! Here is En mi Viejo San Juan with its lyrics on my screen!"
                else:
                    resp_sj = "¡Siente la emoción y la nostalgia boricua! ¡Aquí tienes 'En mi Viejo San Juan' con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_sj)
                return resp_sj

            if re.search(r'\b(bad\s+bunny|titi|titi\s+me\s+pregunto)\b', p_norm_amigo):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "pr_pop"
                self.accion_pendiente = "reproducir_pr_pop"
                if self.language == "en":
                    resp_pop = "Let's party with the biggest Puerto Rican pop sensation! Here is 'Tití Me Preguntó' by Bad Bunny with its lyrics!"
                else:
                    resp_pop = "¡A vacilar con el fenómeno boricua mundial! ¡Aquí tienes 'Tití Me Preguntó' de Bad Bunny con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_pop)
                return resp_pop

        if self.ofrecio_alma_llanera:
            patrones_si_alma = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|alma|llanera|joropo)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_alma):
                self.ofrecio_alma_llanera = False
                self.cancion_reproducida_reciente = "alma"
                self.accion_pendiente = "reproducir_alma"
                if self.language == "en":
                    resp_alma = "Turn up the volume and feel the Venezuelan pride! Here is Alma Llanera with its lyrics!"
                else:
                    resp_alma = "¡Sube el volumen y siente el orgullo llanero! ¡Aquí tienes Alma Llanera con su letra!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_alma)
                return resp_alma
            elif tipo_entrada == "negativo":
                self.ofrecio_alma_llanera = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_alma_no = "No problem at all! Venezuelan music is always ready whenever you want to enjoy it. What other topic would you like to explore today?"
                else:
                    resp_alma_no = "¡Cero rollo! La música tradicional venezolana siempre estará lista para cuando quieras disfrutarla. ¿De qué otro tema te gustaría hablar hoy?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_alma_no)
                return resp_alma_no
            else:
                self.ofrecio_alma_llanera = False

        if self.ofrecio_viejo_san_juan or self.ofrecio_verde_luz:
            patrones_verde_luz = [
                r'\b(verde\s+luz|verde|el\s+topo|topo|segunda|la\s+segunda|second|the\s+second(\s+one)?|2|dos|two)\b'
            ]
            patrones_viejo_sj = [
                r'\b(viejo\s+san\s+juan|en\s+mi\s+viejo\s+san\s+juan|san\s+juan|primera|la\s+primera|first|the\s+first(\s+one)?|1|uno|one|ambas|ambos|las\s+dos|both)\b',
                r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escuchar|show|show\s+me|muestrala|muéstrala|si|claro|dale|yes)\b'
            ]
            if any(re.search(pat, p_norm_amigo) for pat in patrones_verde_luz):
                self.ofrecio_viejo_san_juan = False
                self.ofrecio_verde_luz = False
                self.cancion_reproducida_reciente = "verde_luz"
                self.accion_pendiente = "reproducir_verde_luz"
                if self.language == "en":
                    resp_vl = "Here is Verde Luz by Antonio Cabán Vale 'El Topo' with its lyrics on my screen!"
                else:
                    resp_vl = "¡Aquí tienes 'Verde Luz' de Antonio Cabán Vale 'El Topo' con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_vl)
                return resp_vl
            elif tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_viejo_sj):
                self.ofrecio_viejo_san_juan = False
                self.ofrecio_verde_luz = False
                self.cancion_reproducida_reciente = "viejo_san_juan"
                self.accion_pendiente = "reproducir_viejo_san_juan"
                if self.language == "en":
                    resp_sj = "Feel the nostalgic magic of Puerto Rico! Here is En mi Viejo San Juan with its lyrics on my screen!"
                else:
                    resp_sj = "¡Siente la emoción y la nostalgia boricua! ¡Aquí tienes 'En mi Viejo San Juan' con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_sj)
                return resp_sj
            elif tipo_entrada == "negativo":
                self.ofrecio_viejo_san_juan = False
                self.ofrecio_verde_luz = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_sj_no = "No problem at all! Puerto Rican music will be waiting whenever you want to enjoy it. What other topic would you like to explore today?"
                else:
                    resp_sj_no = "¡Sin problema! La música de Puerto Rico siempre estará aquí lista para ti. ¿Qué otro lugar o tema te gustaría explorar hoy?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_sj_no)
                return resp_sj_no
            else:
                self.ofrecio_viejo_san_juan = False
                self.ofrecio_verde_luz = False

        if self.ofrecio_caballo_viejo:
            patrones_si_cv = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|caballo|viejo|simon|simón)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_cv):
                self.ofrecio_caballo_viejo = False
                self.cancion_reproducida_reciente = "caballo_viejo"
                self.accion_pendiente = "reproducir_caballo_viejo"
                if self.language == "en":
                    resp_cv = "Here is Caballo Viejo by the beloved Simón Díaz with its lyrics!"
                else:
                    resp_cv = "¡Aquí tienes Caballo Viejo del querido tío Simón Díaz con su letra!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_cv)
                return resp_cv
            elif tipo_entrada == "negativo":
                self.ofrecio_caballo_viejo = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_cv_no = "No problem! Simón Díaz's poetry is always here. What else would you like to know?"
                else:
                    resp_cv_no = "¡Tranquilo! Las melodías del tío Simón siempre están a mano. ¿Qué más te gustaría saber?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_cv_no)
                return resp_cv_no
            else:
                self.ofrecio_caballo_viejo = False

        if self.ofrecio_venezuela:
            patrones_si_vz = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|venezuela|llevo\s+tu\s+luz)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_vz):
                self.ofrecio_venezuela = False
                self.cancion_reproducida_reciente = "venezuela"
                self.accion_pendiente = "reproducir_venezuela"
                if self.language == "en":
                    resp_vz = "Feel the deepest emotion! Here is 'Venezuela' with its lyrics on my screen!"
                else:
                    resp_vz = "¡Siente la emoción a flor de piel! ¡Aquí tienes el himno sentimental 'Venezuela' con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_vz)
                return resp_vz
            elif tipo_entrada == "negativo":
                self.ofrecio_venezuela = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_vz_no = "No problem! The song Venezuela will be here whenever you want to feel its magic. What other topic would you like to explore?"
                else:
                    resp_vz_no = "¡Sin problema! 'Venezuela' siempre estará aquí para cuando quieras disfrutarla. ¿De qué otro tema te gustaría hablar hoy?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_vz_no)
                return resp_vz_no
            else:
                self.ofrecio_venezuela = False

        if self.ofrecio_rawayana:
            patrones_si_rw = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|rawayana|high)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_rw):
                self.ofrecio_rawayana = False
                self.cancion_reproducida_reciente = "rawayana"
                self.accion_pendiente = "reproducir_rawayana"
                if self.language == "en":
                    resp_rw = "Turn up the volume and enjoy the tropical vibe! Here is 'High' by Rawayana ft. Apache with its lyrics!"
                else:
                    resp_rw = "¡Sube el volumen y siente la vibra caribeña! ¡Aquí tienes 'High' de Rawayana y Apache con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_rw)
                return resp_rw
            elif tipo_entrada == "negativo":
                self.ofrecio_rawayana = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_rw_no = "No worries! Good music is always ready. What else would you like to know?"
                else:
                    resp_rw_no = "¡Cero rollo! La música fresca siempre está a mano. ¿Qué más te gustaría descubrir?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_rw_no)
                return resp_rw_no
            else:
                self.ofrecio_rawayana = False

        if self.ofrecio_pr_pop:
            patrones_si_pop = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|sure|play\s+it|bad\s+bunny|titi|city|benito)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_pop):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "pr_pop"
                self.accion_pendiente = "reproducir_pr_pop"
                if self.language == "en":
                    resp_pop = "Let's party with the biggest Puerto Rican pop sensation! Here is 'Tití Me Preguntó' by Bad Bunny with its lyrics!"
                else:
                    resp_pop = "¡A vacilar con el fenómeno boricua mundial! ¡Aquí tienes 'Tití Me Preguntó' de Bad Bunny con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_pop)
                return resp_pop
            elif tipo_entrada == "negativo":
                self._limpiar_ofertas_musica()
                self.accion_pendiente = None
                if self.language == "en":
                    resp_pop_no = "No problem! Puerto Rican pop rhythms are always ready. What else would you like to explore?"
                else:
                    resp_pop_no = "¡Sin problema! El ritmo de la isla siempre está listo. ¿Qué más te gustaría saber?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_pop_no)
                return resp_pop_no
            else:
                self.ofrecio_pr_pop = False

        if self.ofrecio_preciosa:
            patrones_si_prec = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|sure|play\s+it|preciosa)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_prec):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "preciosa"
                self.accion_pendiente = "reproducir_preciosa"
                if self.language == "en":
                    resp_prec = "Feel the proud soul of Borinquen! Here is 'Preciosa' by Rafael Hernández and Marc Anthony with its lyrics!"
                else:
                    resp_prec = "¡Siente el orgullo de Borinquen! ¡Aquí tienes 'Preciosa' de Rafael Hernández interpretada por Marc Anthony con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_prec)
                return resp_prec
            elif tipo_entrada == "negativo":
                self._limpiar_ofertas_musica()
                self.accion_pendiente = None
                if self.language == "en":
                    resp_prec_no = "No worries! Puerto Rico's emblems are always celebrated here. What else would you like to explore?"
                else:
                    resp_prec_no = "¡Tranquilo! Los tesoros de Puerto Rico siempre te esperan. ¿Qué otro lugar o tema te gustaría conocer?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_prec_no)
                return resp_prec_no
            else:
                self.ofrecio_preciosa = False

        if self.ofrecio_world:
            patrones_si_wld = [r'\b(ponla|ponlo|play|tocala|tócala|escucharla|dale\s+play|vamos\s+a\s+escuchar|quiero\s+escucharla|quiero\s+oirla|si|claro|dale|yes|sure|play\s+it|queen|we\s+will\s+rock\s+you|rock)\b']
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_wld):
                self._limpiar_ofertas_musica()
                self.cancion_reproducida_reciente = "world"
                self.accion_pendiente = "reproducir_world"
                if self.language == "en":
                    resp_wld = "Stomp your feet and sing along! Here is 'We Will Rock You' by Queen with its lyrics on my screen!"
                else:
                    resp_wld = "¡A aplaudir y cantar con todo el mundo! ¡Aquí tienes 'We Will Rock You' de Queen con su letra en pantalla!"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_wld)
                return resp_wld
            elif tipo_entrada == "negativo":
                self._limpiar_ofertas_musica()
                self.accion_pendiente = None
                if self.language == "en":
                    resp_wld_no = "No problem! Universal classics are always ready. What other topic would you like to explore?"
                else:
                    resp_wld_no = "¡Sin problema! Los clásicos universales siempre están aquí. ¿De qué otro tema te gustaría hablar?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_wld_no)
                return resp_wld_no
            else:
                self.ofrecio_world = False

        # 1.35 ATAJO DETERMINISTA: SEGUIMIENTO TRAS OFRECER PROMO / QR DELEITE AUTOMERCADO
        ultimo_asistente = ""
        if self.historial and len(self.historial) > 0:
            for m in reversed(self.historial):
                if m.get("role") == "assistant":
                    ultimo_asistente = m.get("content", "").lower()
                    break

        ofrecio_deleite = self.ofrecio_promo_deleite or (
            "deleite" in ultimo_asistente and any(w in ultimo_asistente for w in ["qr", "descuento", "código", "codigo", "cinco por ciento", "5%"])
        )
        if ofrecio_deleite:
            patrones_si_deleite = [
                r'\b(si|sí|claro|dale|yes|ok|afirmativo|seguro|obvio|por\s+supuesto|vale|de\s+una|por\s+fa|por\s+favor|si\s+quiero|quiero|muestralo|muéstralo)\b',
                r'\b(codigo|código|descuento|cupon|cupón|promo|promocion|promoción)\b',
                r'\b(dame|quiero|pasa|enseñame|ensename|muestrame|muéstrame|muestra|enseña|ver|carga|cargame|cárgame|pon|ponlo|proyecta)\b',
                r'\b(qr|codigo\s*qr|código\s*qr|qr\s*code|imagen|foto)\b'
            ]
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_deleite):
                self.ofrecio_promo_deleite = False
                self.accion_pendiente = "mostrar_qr_deleite"
                if self.language == "en":
                    resp_deleite_promo = (
                        "Here is the Deleite Automercado QR code! Scan it at checkout or mention promo code ORBIT5 to get a special 5% discount on your next purchase! Would you like to know something more about Venezuela?"
                    )
                else:
                    resp_deleite_promo = (
                        "¡Aquí tienes el código QR de Deleite Automercado! Escanéalo en la caja o menciona el código promocional ORBIT5 para obtener un 5% de descuento especial en tu próxima compra. ¿Quieres saber algo más sobre Venezuela?"
                    )
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_deleite_promo)
                return resp_deleite_promo
            elif tipo_entrada == "negativo" or any(re.search(pat, p_norm_amigo) for pat in [r'\b(no|nop|paso|no\s+quiero|no\s+gracias)\b']):
                self.ofrecio_promo_deleite = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_deleite_no = "No problem! Deleite will always be there with the freshest groceries whenever you need it. Would you like to know something more about Venezuela?"
                else:
                    resp_deleite_no = "¡Perfecto! Deleite siempre estará esperándote con lo más fresco y el mejor servicio cuando lo necesites. ¿Quieres saber algo más sobre Venezuela?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_deleite_no)
                return resp_deleite_no

        # 1.36 ATAJO DETERMINISTA: SEGUIMIENTO TRAS OFRECER PROMO / QR LA CASITA BLANCA (PUERTO RICO)
        ofrecio_casita = self.ofrecio_promo_casita_blanca or (
            "casita blanca" in ultimo_asistente and any(w in ultimo_asistente for w in ["qr", "descuento", "código", "codigo", "cinco por ciento", "5%"])
        )
        if ofrecio_casita:
            patrones_si_casita = [
                r'\b(si|sí|claro|dale|yes|ok|afirmativo|seguro|obvio|por\s+supuesto|vale|de\s+una|por\s+fa|por\s+favor|si\s+quiero|quiero|muestralo|muéstralo)\b',
                r'\b(codigo|código|descuento|cupon|cupón|promo|promocion|promoción)\b',
                r'\b(dame|quiero|pasa|enseñame|ensename|muestrame|muéstrame|muestra|enseña|ver|carga|cargame|cárgame|pon|ponlo|proyecta)\b',
                r'\b(qr|codigo\s*qr|código\s*qr|qr\s*code|imagen|foto)\b'
            ]
            if tipo_entrada == "afirmativo" or any(re.search(pat, p_norm_amigo) for pat in patrones_si_casita):
                self.ofrecio_promo_casita_blanca = False
                self.accion_pendiente = "mostrar_qr_casita_blanca"
                if self.language == "en":
                    resp_casita_promo = (
                        "Here is the QR code for La Casita Blanca! Scan it with your phone or mention promo code ORBIT5 to get a special 5% discount on your authentic criollo meal in Santurce, San Juan! Would you like to know something more about Puerto Rico?"
                    )
                else:
                    resp_casita_promo = (
                        "¡Aquí tienes el código QR de La Casita Blanca! Escanéalo con tu teléfono o menciona el código promocional ORBIT5 para obtener un 5% de descuento especial en tu comida criolla en Santurce, San Juan. ¿Quieres saber algo más sobre Puerto Rico?"
                    )
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_casita_promo)
                return resp_casita_promo
            elif tipo_entrada == "negativo" or any(re.search(pat, p_norm_amigo) for pat in [r'\b(no|nop|paso|no\s+quiero|no\s+gracias)\b']):
                self.ofrecio_promo_casita_blanca = False
                self.accion_pendiente = None
                if self.language == "en":
                    resp_casita_no = "No problem! La Casita Blanca and its authentic criollo flavors will be waiting for you in Santurce. Would you like to know something more about Puerto Rico?"
                else:
                    resp_casita_no = "¡Perfecto! La Casita Blanca siempre te esperará con el mejor mofongo y sazón boricua en Santurce cuando visites la isla. ¿Quieres saber algo más sobre Puerto Rico?"
                self.agregar_historial("user", pregunta_limpia)
                self.agregar_historial("assistant", resp_casita_no)
                return resp_casita_no

        # 1.37 ATAJO DETERMINISTA: PETICIÓN DIRECTA DE CÓDIGO QR / DESCUENTO LA CASITA BLANCA
        patrones_directo_qr_casita = [
            r'\b(qr\s+(de\s+)?(la\s+)?casita\s+blanca|codigo\s+qr\s+(de\s+)?(la\s+)?casita\s+blanca|código\s+qr\s+(de\s+)?(la\s+)?casita\s+blanca)\b',
            r'\b(cupon\s+(de\s+)?(la\s+)?casita\s+blanca|cupón\s+(de\s+)?(la\s+)?casita\s+blanca|descuento\s+(de\s+)?(la\s+)?casita\s+blanca)\b',
            r'\b(show\s+(me\s+)?(the\s+)?qr.*casita\s+blanca|casita\s+blanca\s+qr)\b',
            r'\b(qr\s+(de\s+)?(puerto\s+rico|santurce)|codigo\s+qr\s+(de\s+)?(puerto\s+rico|santurce))\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_directo_qr_casita) or ("casita blanca" in p_norm_amigo and any(w in p_norm_amigo for w in ["qr", "codigo", "descuento", "cupon"])):
            self.tema_actual = "casita blanca"
            self.ofrecio_promo_casita_blanca = False
            self.accion_pendiente = "mostrar_qr_casita_blanca"
            if self.language == "en":
                resp_qr_casita = (
                    "Here is the QR code for La Casita Blanca! Scan it with your phone or mention promo code ORBIT5 to get a special 5% discount on your authentic criollo meal in Santurce, San Juan! Would you like to know something more about Puerto Rico?"
                )
            else:
                resp_qr_casita = (
                    "¡Aquí tienes el código QR de La Casita Blanca! Escanéalo con tu teléfono o menciona el código promocional ORBIT5 para obtener un 5% de descuento especial en tu comida criolla en Santurce, San Juan. ¿Quieres saber algo más sobre Puerto Rico?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_qr_casita)
            return resp_qr_casita

        # 1.37b ATAJO DETERMINISTA: CÓDIGO FUENTE / SOURCE CODE / WEB PLATFORM
        patrones_source_code = [
            r'\b(codigo\s+fuente|código\s+fuente|source\s+code|sourcecode)\b',
            r'\b(ver\s+(el\s+)?codigo\s+fuente|ver\s+(el\s+)?código\s+fuente|muestrame\s+(el\s+)?codigo\s+fuente|muéstrame\s+(el\s+)?código\s+fuente)\b',
            r'\b(qr\s+(del\s+)?codigo\s+fuente|qr\s+(del\s+)?código\s+fuente|qr\s+(del\s+)?source\s+code|source\s+code\s+qr)\b',
            r'\b(show\s+(me\s+)?(the\s+)?source\s+code|where\s+is\s+the\s+source\s+code|code\s+repository|open\s+source)\b',
            r'\b(pagina\s+(del\s+)?codigo|página\s+(del\s+)?código|webpage\s+(for\s+)?(the\s+)?source|web\s+del\s+codigo)\b',
            r'\b(qr\s+(de\s+la\s+)?programacion|qr\s+(de\s+la\s+)?programación|ver\s+la\s+programacion|ver\s+la\s+programación)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_source_code) or any(w in p_norm_amigo for w in ["codigo fuente", "código fuente", "source code", "código de orbit", "codigo de orbit"]):
            self.tema_actual = "source_code"
            self.accion_pendiente = "mostrar_qr_source_code"
            if self.language == "en":
                resp_src = (
                    "Here is the official QR code for Orbit's web platform and interactive source code! Scan it on my screen to explore the robot's AI architecture, neural models, and complete documentation at orbit-rho-blush-62.vercel.app/source. Would you like to know more about how Orbit was built?"
                )
            else:
                resp_src = (
                    "¡Por supuesto! Aquí tienes el código QR oficial de la plataforma web y código fuente de Orbit. Escanéalo en mi pantalla para explorar la arquitectura del robot, mis modelos de inteligencia artificial y toda la documentación técnica. ¿Te gustaría saber más sobre cómo fui programado?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_src)
            return resp_src

        # 1.38 ATAJO DETERMINISTA: PETICIÓN DIRECTA DE CÓDIGO QR / DESCUENTO DELEITE
        patrones_directo_qr = [
            r'\b(qr|codigo\s+qr|código\s+qr|qr\s+code)\b',
            r'\b(ensename\s+(el\s+)?qr|enséñame\s+(el\s+)?qr|muestrame\s+(el\s+)?qr|muéstrame\s+(el\s+)?qr)\b',
            r'\b(quiero\s+ver\s+(el\s+)?qr|ver\s+(el\s+)?qr|carga\s+(el\s+)?qr|cargame\s+(el\s+)?qr|cárgame\s+(el\s+)?qr)\b',
            r'\b(cargame\s+(la\s+)?imagen|cárgame\s+(la\s+)?imagen|cargame\s+el\s+codigo|cárgame\s+el\s+código)\b',
            r'\b(cupon\s+deleite|cupón\s+deleite|descuento\s+deleite|codigo\s+deleite|código\s+deleite|promo\s+deleite)\b',
            r'\b(descuento\s+en\s+deleite|cupon\s+de\s+deleite|cupón\s+de\s+deleite)\b',
            r'\b(show\s+(me\s+)?(the\s+)?qr|see\s+(the\s+)?qr|display\s+(the\s+)?qr|qr\s+discount)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_directo_qr) and not any(w in p_norm_amigo for w in ["casita blanca", "casita", "puerto rico", "santurce", "fuente", "source", "codigo fuente", "código fuente", "programacion", "programación"]):
            self.tema_actual = "deleite"
            self.ofrecio_promo_deleite = False
            self.accion_pendiente = "mostrar_qr_deleite"
            if self.language == "en":
                resp_qr_dir = (
                    "Here is the Deleite Automercado QR code! Scan it at checkout or mention promo code ORBIT5 to get a special 5% discount on your next purchase! Would you like to know something more about Venezuela?"
                )
            else:
                resp_qr_dir = (
                    "¡Aquí tienes el código QR de Deleite Automercado! Escanéalo en la caja o menciona el código promocional ORBIT5 para obtener un 5% de descuento especial en tu próxima compra. ¿Quieres saber algo más sobre Venezuela?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_qr_dir)
            return resp_qr_dir

        # 1.39 ATAJOS DETERMINISTAS: EXPERIENCIAS TURÍSTICAS Y ALIADOS OFICIALES (TOROVERDE, CANAIMA, CHOCOBAR, ETC.)
        # TOROVERDE ADVENTURE PARK (PUERTO RICO - AVENTURA & TIROLESA)
        if any(w in p_norm_amigo for w in ["toroverde", "toro verde", "tirolesa", "el monstruo", "aventura en puerto rico", "parque de aventura"]):
            self.tema_actual = "toroverde"
            self.accion_pendiente = "mostrar_qr_toroverde"
            if self.language == "en":
                resp_tv = "Here is the official QR code for ToroVerde Adventure Park in Orocovis, Puerto Rico! Scan it on my screen for an exclusive 2-for-1 Adventure Pass on its world-famous ziplines! Would you like to know more about adventures in Puerto Rico?"
            else:
                resp_tv = "¡Aquí tienes el código QR oficial de ToroVerde Adventure Park en Orocovis, Puerto Rico! Escanéalo en mi pantalla para obtener un Pase Aventura 2x1 en sus legendarias tirolesas y puentes colgantes. ¿Te gustaría conocer más sobre aventuras en Puerto Rico?"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_tv)
            return resp_tv

        # CAMPAMENTO CANAIMA (VENEZUELA - EXPEDICIONES & SALTO ÁNGEL)
        if any(w in p_norm_amigo for w in ["campamento canaima", "viaje a canaima", "tour canaima", "excursion canaima", "expedición canaima", "tour salto angel", "tour salto ángel", "visitar salto angel"]):
            self.tema_actual = "canaima"
            self.accion_pendiente = "mostrar_qr_canaima"
            if self.language == "en":
                resp_cn = "Here is the official QR code for Campamento Canaima in Venezuela! Scan it on my screen for an exclusive 2-for-1 expedition pass to Angel Falls and Canaima Lagoon! Would you like to know more about Venezuelan wonders?"
            else:
                resp_cn = "¡Aquí tienes el código QR oficial de Campamento Canaima en Venezuela! Escanéalo en mi pantalla para disfrutar de una excursión 2x1 al majestuoso Salto Ángel y travesía por el Río Carrao. ¿Quieres saber más sobre las maravillas de Venezuela?"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_cn)
            return resp_cn

        # CHOCOBAR CORTÉS (SAN JUAN, PR)
        if any(w in p_norm_amigo for w in ["chocobar", "chocobar cortes", "chocobar cortés", "cortes chocolate", "churros en san juan"]):
            self.tema_actual = "chocobar"
            self.accion_pendiente = "mostrar_qr_chocobar"
            if self.language == "en":
                resp_ch = "Here is the QR code for Chocobar Cortés in Old San Juan! Scan it to claim free churros with house hot chocolate! Would you like to know more about San Juan?"
            else:
                resp_ch = "¡Aquí tienes el código QR de Chocobar Cortés en el Viejo San Juan! Escanéalo para disfrutar de unos deliciosos churros artesanales con chocolate caliente gratis. ¿Te gustaría saber algo más sobre San Juan?"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_ch)
            return resp_ch

        # HACIENDA MUÑOZ (SAN LORENZO, PR)
        if any(w in p_norm_amigo for w in ["hacienda muñoz", "hacienda munoz", "finca de cafe", "finca de café", "tour del cafe pr"]):
            self.tema_actual = "hacienda"
            self.accion_pendiente = "mostrar_qr_hacienda"
            if self.language == "en":
                resp_hm = "Here is the QR code for Hacienda Muñoz in San Lorenzo, Puerto Rico! Scan it for a 2-for-1 Coffee Tour and free tasting! Would you like to know more about Puerto Rican coffee?"
            else:
                resp_hm = "¡Aquí tienes el código QR de Hacienda Muñoz en San Lorenzo, Puerto Rico! Escanéalo para obtener un Tour Cafetalero 2x1 y degustación de café arábica colado gratis. ¿Quieres saber más sobre el café puertorriqueño?"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_hm)
            return resp_hm

        # PÁRAMO CAFÉ (VENEZUELA)
        if any(w in p_norm_amigo for w in ["paramo cafe", "páramo café", "paramo venezuela", "páramo venezuela"]):
            self.tema_actual = "paramo"
            self.accion_pendiente = "mostrar_qr_paramo"
            if self.language == "en":
                resp_pr = "Here is the QR code for Páramo Café in Venezuela! Scan it to get a complimentary Mokaccino! Would you like to know more about Venezuelan coffee?"
            else:
                resp_pr = "¡Aquí tienes el código QR de Páramo Café en Venezuela! Escanéalo en mi pantalla para recibir un delicioso Mokaccino de cortesía con tu orden. ¿Quieres conocer más sobre el café andino de Venezuela?"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_pr)
            return resp_pr

        # CACAO DE ORIGEN (CARACAS, VZ)
        if any(w in p_norm_amigo for w in ["cacao de origen", "cacao criollo", "cata de cacao", "chocolate fino venezuela"]):
            self.tema_actual = "cacao"
            self.accion_pendiente = "mostrar_qr_cacao"
            if self.language == "en":
                resp_ca = "Here is the QR code for Cacao de Origen in Caracas! Scan it for a complimentary guided tasting of pure Venezuelan cocoa varieties! Would you like to know more about Venezuelan chocolate?"
            else:
                resp_ca = "¡Aquí tienes el código QR de Cacao de Origen en Caracas! Escanéalo en mi pantalla para una cata guiada gratuita de los mejores cacaos criollos finos de aroma. ¿Te gustaría saber más sobre el cacao venezolano?"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_ca)
            return resp_ca
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_qr_casita)
            return resp_qr_casita

        # 1.4 ATAJO DETERMINISTA: REPRODUCIR DIRECTAMENTE ALMA LLANERA
        patrones_play_alma = [
            r'\b(pon|reproduce|toca|play|escuchar|coloca)\s+(la\s+cancion\s+|el\s+tema\s+)?(alma\s+llanera)\b',
            r'\b(quiero\s+escuchar\s+alma\s+llanera|pon\s+alma\s+llanera|play\s+alma\s+llanera|reproduce\s+alma\s+llanera)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_play_alma):
            self.tema_actual = "joropo"
            self.ofrecio_alma_llanera = False
            self.accion_pendiente = "reproducir_alma"
            if self.language == "en":
                resp_play = "Turn up the volume and feel the Venezuelan pride! Here is Alma Llanera!"
            else:
                resp_play = "¡Por supuesto! ¡Sube el volumen y siente el orgullo llanero con Alma Llanera!"
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_play)
            return resp_play

        # 1.5 ATAJO DETERMINISTA: EL JOROPO (PREGUNTA SI QUIERE ESCUCHAR ALMA LLANERA)
        patrones_joropo = [
            r'\b(joropo|el joropo|que es el joropo|hablame del joropo|cuentame del joropo|baile del joropo|musica llanera|música llanera)\b',
            r'\b(what is joropo|tell me about joropo|venezuelan joropo)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_joropo):
            self.tema_actual = "joropo"
            self.ofrecio_alma_llanera = True
            self.ofrecio_promo_deleite = False
            self.accion_pendiente = None
            if self.language == "en":
                resp_joropo = (
                    "The joropo is the heart and ultimate musical soul of Venezuela! It is an energetic traditional llanero rhythm played with Venezuelan harp, cuatro, and maracas, danced with fiery zapateo footwork that celebrates our heritage. Would you like to listen to Alma Llanera, Venezuela's most famous and beloved joropo?"
                )
            else:
                resp_joropo = (
                    "¡El joropo es el alma y la máxima fiesta musical de Venezuela! Es un ritmo tradicional llanero lleno de energía y pasión que se interpreta con arpa, cuatro y maracas, acompañado de un zapateo y escobilleo espectacular que hace vibrar nuestra tierra. ¿Te gustaría escuchar Alma Llanera, el joropo más famoso y querido de Venezuela?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_joropo)
            return resp_joropo

        # 1.6 ATAJO DETERMINISTA: DÓNDE HACER MERCADO / COMPRAS / DELEITE AUTOMERCADO
        patrones_deleite = [
            r'\b(deleite|deleite automercado|automercado deleite)\b',
            r'\bhacer\s+(el\s+|un\s+)?mercado\b',
            r'\bdonde\s+(puedo\s+)?(hacer\s+(el\s+|un\s+)?mercado|mercar|comprar\s+comida|conseguir\s+comida|comprar\s+viveres)\b',
            r'\b(mercado\s+en\s+lecheria|hacer\s+mercado\s+en\s+lecheria|compras\s+en\s+lecheria)\b',
            r'\b(donde\s+(hacer\s+)?mercado|donde\s+mercar|donde\s+comprar\s+comida|donde\s+compro\s+comida|donde\s+conseguir\s+comida|donde\s+comprar\s+viveres)\b',
            r'\b(supermercado|automercado|hacer compras|comprar comida|comprar viveres)\b',
            r'\b(donde comprar|donde puedo comprar)\b',
            r'\b(cupon|cupón|cupones|descuento deleite|descuentos deleite)\b',
            r'\b(groceries|grocery|where to buy food|supermarket|where can i buy food|grocery shopping)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_deleite) and not any(w in p_norm_amigo for w in ["bursatil", "bursátil", "valores", "cripto", "libre"]):
            self.tema_actual = "deleite"
            self.ofrecio_promo_deleite = True
            self.ofrecio_alma_llanera = False
            self.accion_pendiente = "mostrar_deleite"
            if self.language == "en":
                resp_deleite = (
                    "The best place to do your grocery shopping is Deleite Automercado! They have an incredible variety of fresh produce: fruits, vegetables, meats, and the highest quality dairy. Plus, they offer special deals every single day that you will love! Would you like to see the QR code for a special discount at Deleite?"
                )
            else:
                resp_deleite = (
                    "¡El mejor lugar para hacer tus compras es Deleite Automercado! Tienen una variedad increíble de productos frescos: frutas, verduras, carnes y lácteos de la mejor calidad. ¡Además tienen ofertas especiales todos los días que te van a encantar! ¿Quieres ver el código QR con un descuento especial de Deleite?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_deleite)
            return resp_deleite

        # 1.65 ATAJO DETERMINISTA: DÓNDE COMER EN PUERTO RICO / LA CASITA BLANCA (SANTURCE) / PIÑA COLADA (1963)
        patrones_casita_blanca = [
            r'\b(la\s+casita\s+blanca|casita\s+blanca)\b',
            r'\bdonde\s+(puedo\s+)?comer.*(puerto\s+rico|san\s+juan|santurce)\b',
            r'\b(que\s+restaurante.*(recomiendas|visitar).*(puerto\s+rico|san\s+juan|santurce))\b',
            r'\b(donde\s+comer\s+(el\s+)?mejor\s+mofongo|mejor\s+restaurante.*puerto\s+rico)\b',
            r'\b(comida\s+criolla\s+en\s+puerto\s+rico|fonda\s+en\s+puerto\s+rico|fonda\s+tradicional.*puerto\s+rico)\b',
            r'\b(pina\s+colada|piña\s+colada|donde\s+se\s+invento\s+la\s+pina\s+colada|donde\s+se\s+invento\s+la\s+piña\s+colada)\b',
            r'\b(quien\s+invento\s+la\s+pina\s+colada|quien\s+invento\s+la\s+piña\s+colada|origen\s+de\s+la\s+piña\s+colada|historia\s+de\s+la\s+piña\s+colada)\b',
            r'\b(where\s+(to|can\s+i)\s+eat.*(puerto\s+rico|san\s+juan|santurce)|best\s+restaurant.*puerto\s+rico)\b',
            r'\b(where\s+was\s+(the\s+)?pina\s+colada\s+invented|who\s+invented\s+(the\s+)?pina\s+colada)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_casita_blanca):
            self.tema_actual = "casita blanca"
            self.ofrecio_promo_casita_blanca = True
            self.ofrecio_promo_deleite = False
            self.ofrecio_alma_llanera = False
            self.accion_pendiente = "mostrar_casita_blanca"
            if self.language == "en":
                resp_casita = (
                    "The absolute best place to taste authentic traditional Puerto Rican food is La Casita Blanca in Santurce, San Juan! It is an iconic traditional fonda where you are welcomed like at grandma's house with hot broth and crispy bacalaítos. Plus, as a famous fun fact, the iconic piña colada was invented right there in 1963! Would you like to see the QR code for a special discount at La Casita Blanca?"
                )
            else:
                resp_casita = (
                    "¡El mejor lugar para saborear la auténtica comida criolla puertorriqueña es La Casita Blanca en Santurce, San Juan! Es una fonda tradicional icónica donde te reciben como en casa de la abuela con caldito caliente y bacalaítos crujientes de cortesía, sirviendo el mofongo más delicioso de la isla. Además, como dato curioso legendario, ¡allí se inventó la famosa piña colada en el año 1963! ¿Quieres ver el código QR con un descuento especial de La Casita Blanca?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_casita)
            return resp_casita

        # Preguntas generales de canciones o música de Puerto Rico
        patrones_pregunta_musica_pr = [
            r'\b(music|musica|música|cancion|canción|canciones|song|songs|melodia|melodias|himno|anthem)\b.*(san\s+juan|puerto\s+rico|puertorrique[nñ][ao]|boricua|borinquen|boriken)',
            r'\b(san\s+juan|puerto\s+rico|puertorrique[nñ][ao]|boricua|borinquen|boriken)\b.*(music|musica|música|cancion|canción|canciones|song|songs|melodia|melodias|himno|anthem)',
            r'\b(musica\s+de\s+san\s+juan|musica\s+en\s+san\s+juan|music\s+from\s+san\s+juan|music\s+of\s+san\s+juan|music\s+in\s+san\s+juan|san\s+juan\s+music)\b',
            r'\b(canciones\s+de\s+san\s+juan|cancion\s+de\s+san\s+juan|songs\s+from\s+san\s+juan|songs\s+of\s+san\s+juan)\b',
            r'\b(musica\s+de\s+puerto\s+rico|music\s+from\s+puerto\s+rico|puerto\s+rican\s+music|canciones\s+de\s+puerto\s+rico|cancion\s+puertorrique[nñ][ao]|songs\s+from\s+puerto\s+rico)\b',
            r'\b(traditional\s+music|musica\s+tipica|musica\s+tradicional)\b',
            r'\b(what\s+songs|what\s+music|que\s+canciones|que\s+musica|cuales\s+canciones)\b.*(puerto\s+rico|san\s+juan|boricua)',
            r'\b(pon|reproduce|toca|play|escuchar|coloca)\s+(una\s+)?(cancion|canción|musica|música|tema)\s+(de\s+puerto\s+rico|puertorrique[nñ][ao]|boricua|de\s+san\s+juan)\b',
            r'\b(quiero\s+escuchar|me\s+gustaria\s+escuchar)\s+(una\s+)?(cancion|canción|musica|música)\s+(de\s+puerto\s+rico|puertorrique[nñ][ao]|boricua|de\s+san\s+juan)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_pregunta_musica_pr):
            self.tema_actual = "musica san juan"
            self.ofrecio_viejo_san_juan = True
            self.ofrecio_verde_luz = True
            self.ofrecio_preciosa = True
            self.ofrecio_pr_pop = True
            if self.language == "en":
                resp_mus_pr = (
                    "Puerto Rico has a magnificent musical legacy! "
                    "I have the traditional anthems 'En mi Viejo San Juan' and 'Verde Luz', "
                    "the deeply moving patriotic classic 'Preciosa' by Rafael Hernández, "
                    "and the global pop phenomenon 'Tití Me Preguntó' by Bad Bunny. "
                    "Which one would you like me to play with its lyrics on my screen?"
                )
            else:
                resp_mus_pr = (
                    "¡Puerto Rico tiene una tradición musical inmensa! "
                    "Tengo los himnos tradicionales 'En mi Viejo San Juan' y 'Verde Luz', "
                    "la emotiva joya patria 'Preciosa' de Rafael Hernández y Marc Anthony, "
                    "y el fenómeno pop urbano mundial con Bad Bunny y 'Tití Me Preguntó'. "
                    "¿Cuál te gustaría escuchar con su letra original en pantalla?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_mus_pr)
            return resp_mus_pr

        # Preguntas generales de canciones o música de Venezuela
        patrones_musica_vz = [
            r'\b(music|musica|música|cancion|canción|canciones|song|songs|melodia|melodias)\b.*(venezuela|venezolan[ao]|llaner[ao])',
            r'\b(venezuela|venezolan[ao]|llaner[ao])\b.*(music|musica|música|cancion|canción|canciones|song|songs|melodia|melodias)',
            r'\b(que\s+canciones\s+tienes\s+de\s+venezuela|canciones\s+de\s+venezuela|musica\s+de\s+venezuela)\b',
            r'\b(pon|reproduce|toca|play|escuchar|coloca)\s+(una\s+)?(cancion|canción|musica|música|tema)\s+(de\s+venezuela|venezolan[ao])\b',
            r'\b(quiero\s+escuchar|me\s+gustaria\s+escuchar)\s+(una\s+)?(cancion|canción|musica|música)\s+(de\s+venezuela|venezolan[ao])\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_musica_vz):
            self.tema_actual = "musica venezuela"
            self.ofrecio_alma_llanera = True
            self.ofrecio_caballo_viejo = True
            self.ofrecio_venezuela = True
            self.ofrecio_rawayana = True
            if self.language == "en":
                resp_mus_vz = (
                    "Venezuela has an incredible musical repertoire! "
                    "I have the immortal joropo 'Alma Llanera', the beloved 'Caballo Viejo' by Simón Díaz, "
                    "the heartfelt anthem 'Venezuela', and modern Venezuelan reggae-pop with 'High' by Rawayana. "
                    "Which one would you like to listen to with its lyrics on my screen?"
                )
            else:
                resp_mus_vz = (
                    "¡Venezuela tiene un repertorio musical fascinante! "
                    "Tengo el joropo inmortal 'Alma Llanera', el querido 'Caballo Viejo' de Simón Díaz, "
                    "el himno sentimental 'Venezuela', y el reggae-pop moderno con 'High' de Rawayana. "
                    "¿Cuál te gustaría escuchar con su letra en pantalla?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_mus_vz)
            return resp_mus_vz

        # 1.72 ATAJOS DETERMINISTAS: IMÁGENES DE LUGARES Y EVENTOS
        # Lechería: SOLO si se pide explícitamente ver foto/imagen o la palabra única
        palabras_excluir_foto_lec = [
            "mercado", "deleite", "compras", "canal", "canales", "vivir", "casa", "casas",
            "urbanizacion", "urbanización", "apartamento", "apartamentos", "hotel", "hoteles",
            "comer", "restaurante", "restaurantes", "camejo", "historia", "fundacion", "fundación",
            "quien", "quién", "cuando", "cuándo", "donde vivir", "alquilar", "precio", "lugar", "lugares"
        ]
        patrones_lecheria = [
            r'^(lecheria|lechería)$',
            r'\b(que\s+es\s+lecheria|qué\s+es\s+lechería|what\s+is\s+lecheria)\b',
            r'\b(como\s+es\s+lecheria|cómo\s+es\s+lechería)\b',
            r'\b(foto\s+de\s+lecheria|foto\s+de\s+lechería|imagen\s+de\s+lecheria|imagen\s+de\s+lechería|ver\s+lecheria|ver\s+lechería|ensen.*lecheria|muestr.*lecheria|show.*lecheria)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_lecheria) and not any(w in p_norm_amigo for w in palabras_excluir_foto_lec):
            self.tema_actual = "lecheria"
            self.accion_pendiente = "mostrar_lecheria"
            if self.language == "en":
                resp_lec = (
                    "Lecheria is a gorgeous coastal city in Anzoategui, Venezuela! "
                    "It is world-famous for its scenic canals, Caribbean marinas, and the iconic hill of El Morro with views of Playa Mansa and Playa Lido. "
                    "Here is a photo of Lecheria on my screen! Would you like to know what activities you can do there?"
                )
            else:
                resp_lec = (
                    "¡Lechería es una hermosa ciudad costera del estado Anzoátegui en Venezuela! "
                    "Es famosísima por sus canales navegables, sus marinas caribeñas y el imponente cerro de El Morro con vistas a Playa Mansa y Playa Lido. "
                    "¡Aquí te muestro una foto de Lechería en mi pantalla! ¿Te gustaría saber qué actividades divertidas puedes hacer allí?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_lec)
            return resp_lec

        # San Juan / Viejo San Juan / El Morro
        palabras_excluir_foto_sj = [
            "cancion", "canción", "canciones", "musica", "música", "music",
            "song", "songs", "himno", "anthem", "letra", "lyrics", "pon", "play",
            "escuchar", "toca", "coloca", "cantar", "comer", "restaurante", "casita blanca",
            "historia", "fundacion", "fundación", "quien", "quién", "cuando", "cuándo",
            "batalla", "piratas", "esclavitud", "arquitectura", "morro", "donde comer", "visitar"
        ]
        patrones_san_juan = [
            r'^(san\s+juan|viejo\s+san\s+juan)$',
            r'\b(que\s+es\s+san\s+juan|qué\s+es\s+san\s+juan|what\s+is\s+san\s+juan)\b',
            r'\b(como\s+es\s+san\s+juan|cómo\s+es\s+san\s+juan)\b',
            r'\b(foto\s+de\s+san\s+juan|imagen\s+de\s+san\s+juan|ver\s+san\s+juan|ensen.*san\s+juan|muestr.*san\s+juan|show.*san\s+juan)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_san_juan) and not any(w in p_norm_amigo for w in palabras_excluir_foto_sj):
            self.tema_actual = "san juan"
            self.accion_pendiente = "mostrar_san_juan"
            if self.language == "en":
                resp_sj_info = (
                    "Old San Juan in Puerto Rico is a stunning 500-year-old walled colonial city! "
                    "It features historic cobblestone blue streets, colorful Spanish architecture, and the legendary oceanfront fortress Castillo San Felipe del Morro. "
                    "Here is a photograph of San Juan on my display! Would you like to know more about its history or its traditional music?"
                )
            else:
                resp_sj_info = (
                    "¡El Viejo San Juan en Puerto Rico es una impresionante joya colonial amurallada de más de 500 años! "
                    "Se distingue por sus calles de adoquines azules, fachadas llenas de color y la imponente fortaleza frente al mar del Castillo San Felipe del Morro. "
                    "¡Aquí te muestro una fotografía de San Juan en mi pantalla! ¿Te gustaría conocer más sobre su historia o su música típica?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_sj_info)
            return resp_sj_info

        # Centro de Convenciones de Puerto Rico (Sede WRO 2026)
        patrones_cc = [
            r'\b(convention\s+center|centro\s+de\s+convenciones|sede\s+de\s+(la\s+)?wro|lugar\s+de\s+(la\s+)?wro|donde\s+sera\s+(la\s+)?wro|donde\s+se\s+hace\s+(la\s+)?wro)\b',
            r'\b(foto\s+del\s+convention\s+center|imagen\s+del\s+convention\s+center|ver\s+el\s+centro\s+de\s+convenciones|show.*convention\s+center)\b'
        ]
        if any(re.search(pat, p_norm_amigo) for pat in patrones_cc):
            self.tema_actual = "convention center"
            self.accion_pendiente = "mostrar_convention_center"
            if self.language == "en":
                resp_cc = (
                    "The Puerto Rico Convention Center in San Juan is the largest and most advanced convention venue in the Caribbean! "
                    "It is the official host arena for the World Robot Olympiad (WRO) International Final, welcoming top robotics students from over 85 nations. "
                    "Here is a picture of the Puerto Rico Convention Center on my screen! Would you like to know more about the competition?"
                )
            else:
                resp_cc = (
                    "¡El Centro de Convenciones de Puerto Rico en San Juan es el recinto más grande y moderno de todo el Caribe! "
                    "Es la sede oficial de la Final Internacional de la World Robot Olympiad (WRO), donde miles de jóvenes de más de 85 naciones competirán con sus robots autónomos. "
                    "¡Aquí puedes ver una foto del Centro de Convenciones en mi pantalla! ¿Te gustaría saber más sobre el evento?"
                )
            self.agregar_historial("user", pregunta_limpia)
            self.agregar_historial("assistant", resp_cc)
            return resp_cc

        # 2. ACTUALIZAR O RASTREAR TEMA CONVERSACIONAL (Contexto Multi-Turno)
        nuevo_tema = self._detectar_tema(min_pregunta)
        if nuevo_tema:
            self.tema_actual = nuevo_tema
        elif self.tema_actual and self._es_pregunta_seguimiento(min_pregunta):
            # Es un seguimiento explícito del tema en curso
            pass

        tipo_entrada = self.clasificar_tipo_entrada(pregunta_limpia)
        es_comparativa = self.es_comparacion_o_referencia(pregunta_limpia)

        # 3. BÚSQUEDA RAG CONTEXTUALIZADA Y VERIFICADA
        datos_rag = ""
        # Si el usuario responde sí o no a una pregunta previa, o hace una pregunta comparativa/referencial
        # entre opciones ya presentes en el historial, NO buscar RAG para evitar insertar fragmentos no relacionados
        if tipo_entrada not in ["afirmativo", "negativo"] and not es_comparativa and not self.db.es_interaccion_rapida(min_pregunta):
            query_rag = min_pregunta
            if self.tema_actual and not nuevo_tema:
                # Contextualizar la búsqueda RAG con el tema activo
                query_rag = f"{self.tema_actual} {min_pregunta}"

            candidatos_rag = self.db.buscar(query_rag, k=2)

            # Verificación de relevancia: si hay un tema activo, verificar que los datos
            # pertenezcan realmente al tema y no a lugares o estadios no relacionados.
            if candidatos_rag and self.tema_actual:
                aliases_tema = self.MAPA_TEMAS.get(self.tema_actual, [self.tema_actual])
                norm_candidatos = candidatos_rag.lower()
                if any(a in norm_candidatos for a in aliases_tema):
                    # Descartar falsos positivos de estadios o arenas deportivas si el tema es un prócer histórico
                    if self.tema_actual == "simon bolivar" and any(w in norm_candidatos for w in ["beisbol", "pelota", "estadio", "polideportivo", "catedral", "aduana"]):
                        datos_rag = ""
                    else:
                        datos_rag = candidatos_rag
                else:
                    datos_rag = ""
            elif candidatos_rag and not self.tema_actual:
                datos_rag = candidatos_rag

        # 4. PREPARAR MENSAJES
        instrucciones = self.generar_prompt_sistema(
            contexto_visual=contexto_visual,
            datos_rag=datos_rag,
            es_continuacion=es_continuacion,
            tipo_entrada=tipo_entrada
        )
        mensajes = [{"role": "system", "content": instrucciones}]
        mensajes.extend(self.historial)
        mensajes.append({"role": "user", "content": pregunta_limpia})

        respuesta = ""

        # 5. LLAMADA A MODELOS EN LA NUBE (GEMINI / GROQ / OLLAMA CLOUD)
        # Se notifica el callback de inicio de LLM ÚNICAMENTE cuando se va a hacer la consulta de red pesada
        if callback_inicio_llm and callable(callback_inicio_llm):
            try:
                callback_inicio_llm()
            except Exception:
                pass

        if not forzar_local:
            if self.gemini_api_key and not respuesta:
                respuesta = self._llamar_gemini(mensajes)
            if self.groq_api_key and not respuesta:
                respuesta = self._llamar_groq(mensajes)
            if self.ollama_api_key and not respuesta:
                respuesta = self._llamar_ollama_cloud(mensajes)

        # 6. INTENTO 2: OLLAMA LOCAL (qwen2.5:0.5b de HERO)
        if not respuesta:
            respuesta = self._llamar_ollama_local(mensajes)

        # 7. INTENTO 3: FALLBACK OFFLINE INTELIGENTE
        if not respuesta:
            p_lower = min_pregunta.lower()
            p_norm = "".join(c for c in unicodedata.normalize("NFD", p_lower) if unicodedata.category(c) != "Mn")

            # 7.1 Fallback especializado para respuestas afirmativas o negativas
            if tipo_entrada == "afirmativo":
                if self.language == "en":
                    respuesta = (
                        "It really is an extraordinary experience! Feeling the tropical breeze and hearing all the sounds of Venezuelan nature "
                        "makes you feel like a true adventurer. Would you like to hear about the fascinating animals you might discover there?"
                    )
                else:
                    respuesta = (
                        "¡De verdad que es una experiencia inolvidable! Sentir la brisa y toda la emoción de la naturaleza venezolana "
                        "te hace sentir como un explorador de verdad. ¿Te gustaría saber qué animales curiosos podemos encontrarnos por allí?"
                    )
            elif tipo_entrada == "negativo":
                if self.language == "en":
                    respuesta = (
                        "Totally understandable, everyone has their own style of adventure! If you prefer relaxing under the warm tropical sun, "
                        "Venezuelan beaches like Morrocoy have crystal-clear waters as calm as a pool. Would you rather take a splash in the Caribbean sea?"
                    )
                else:
                    respuesta = (
                        "¡Totalmente entendible, para gustos los colores! Si prefieres algo más tranquilo bajo el sol, "
                        "¡en las playas de Morrocoy el agua es tan transparente y calmadita que parece una piscina! ¿Te gustaría más darte un buen baño en el mar Caribe?"
                    )

            # 7.1.1 TEMA: PUERTO RICO Y CULTURA BORICUA (WRO 2026)
            elif any(w in p_norm for w in ["puerto rico", "puertorico", "boricua", "boriken", "borinquen", "isla del encanto"]):
                es_playa_pr = any(w in p_norm for w in ["playa", "beach", "flamenco", "culebra", "crash boat", "luquillo", "cabo rojo", "playuela"])
                es_comida_pr = any(w in p_norm for w in ["comida", "food", "eat", "plato", "dish", "mofongo", "tostones", "lechon", "lechón", "pasteles", "alcapurria"])
                es_lugares_pr = any(w in p_norm for w in ["yunque", "bosque", "rainforest", "bahia", "bay", "bioluminiscente", "san juan", "el morro", "fortin", "vieques", "camuy", "toro verde"])
                es_musica_pr = any(w in p_norm for w in ["musica", "music", "bomba", "plena", "coqui", "coquí", "taino", "taíno", "tainos", "sanse"])
                es_tradicion_pr = any(w in p_norm for w in ["tradicion", "tradiciones", "tradition", "traditions", "costumbre", "costumbres", "cultura", "culture", "heritage", "san sebastian", "san sebastián", "sanse", "parranda", "parrandas", "mascaras", "máscaras", "hatillo", "navidad", "navidades"])

                if es_playa_pr:
                    if self.language == "en":
                        respuesta = (
                            "Puerto Rico features almost 300 miles of coastline with world-renowned tropical beaches! "
                            "Playa Flamenco on Culebra Island is consistently ranked among the top 5 beaches on Earth for its turquoise calm waters and powdery white sand, "
                            "while Crash Boat in Aguadilla is legendary for its lively pier, colorful fishing boats, and snorkeling. Would you like to hear about the bioluminescent bays next?"
                        )
                    else:
                        respuesta = (
                            "¡Puerto Rico cuenta con playas paradisíacas reconocidas entre las mejores del mundo! "
                            "Playa Flamenco en Culebra es aclamada globalmente por sus aguas turquesas transparentes y su arena blanca finísima, "
                            "mientras que Crash Boat en Aguadilla destaca por su muelle vibrante, yolas de pescadores y snorkel. ¿Te gustaría conocer las bahías bioluminiscentes?"
                        )
                elif es_comida_pr:
                    if self.language == "en":
                        respuesta = (
                            "Puerto Rican cuisine is a mouthwatering fusion of Taíno, Spanish, and African culinary traditions! "
                            "Its signature dish is Mofongo—fried green plantains mashed with garlic and savory cracklings, stuffed with tender garlic shrimp or roasted pork. "
                            "You must also try crispy tostones, pasteles, and savory alcapurrias! Would you like to hear how Venezuelan arepas compare?"
                        )
                    else:
                        respuesta = (
                            "¡La gastronomía de Puerto Rico es una explosión deliciosa de sabores taínos, españoles y africanos! "
                            "Su plato rey es el Mofongo, hecho con plátanos verdes fritos machacados con ajo y chicharrón, relleno de camarones al ajillo o carne guisada. "
                            "¡También los tostones crujientes, pasteles y alcapurrias son una gloria! ¿Te gustaría saber cómo se compara con las arepas venezolanas?"
                        )
                elif es_lugares_pr:
                    if self.language == "en":
                        respuesta = (
                            "Puerto Rico is filled with magical wonders! El Yunque is a lush tropical rainforest home to sacred Taíno petroglyphs and the singing Coquí frog. "
                            "At night, Mosquito Bay in Vieques shines with the brightest bioluminescent glow in the world, while the historic fortress of Castillo San Felipe del Morro guards Old San Juan! Which wonder would you love to visit?"
                        )
                    else:
                        respuesta = (
                            "¡Puerto Rico tiene lugares verdaderamente mágicos! El Yunque es un bosque pluvial tropical hogar del coquí y petroglifos taínos milenarios. "
                            "De noche, Bahía Mosquito en Vieques brilla con la mayor bioluminiscencia del planeta, ¡y el Castillo San Felipe del Morro custodia el Viejo San Juan! ¿Cuál te gustaría visitar?"
                        )
                elif es_musica_pr:
                    self.ofrecio_viejo_san_juan = True
                    self.ofrecio_verde_luz = True
                    if self.language == "en":
                        respuesta = (
                            "Puerto Rico's musical heritage is deeply soulful and energetic! From vibrant Bomba and Plena to world-famous anthems like 'En mi Viejo San Juan' by Noel Estrada and 'Verde Luz' by El Topo! "
                            "Would you like me to show and play 'En mi Viejo San Juan' with its lyrics on my screen, or would you prefer 'Verde Luz'?"
                        )
                    else:
                        respuesta = (
                            "¡La música puertorriqueña es pura energía y pasión caribeña! Desde la alegre Bomba y Plena hasta obras inmortales como 'En mi Viejo San Juan' de Noel Estrada y 'Verde Luz' de El Topo. "
                            "¿Te gustaría que te muestre y reproduzca 'En mi Viejo San Juan' con su letra en pantalla, o prefieres escuchar 'Verde Luz'?"
                        )
                elif es_tradicion_pr:
                    if self.language == "en":
                        respuesta = (
                            "Puerto Rico celebrates some of the most joyful and colorful cultural traditions in the Caribbean! "
                            "Its Christmas season is legendary as the longest in the world, filled with surprise musical Parrandas visiting homes with güiros and cuatros, the massive Fiestas de la Calle San Sebastián in Old San Juan, and the vibrant Mask Festival of Hatillo. "
                            "Would you like to hear about the Parrandas or the SanSe festival?"
                        )
                    else:
                        respuesta = (
                            "¡Puerto Rico celebra algunas de las tradiciones culturales más alegres y coloridas del Caribe! "
                            "Su época navideña es legendaria por ser la más larga del mundo, llena de 'parrandas' musicales sorpresa que van de casa en casa con güiro y cuatro, la multitudinaria Fiesta de la Calle San Sebastián en el Viejo San Juan y el Festival de Máscaras de Hatillo. "
                            "¿Te gustaría conocer más sobre las parrandas o la fiesta de la SanSe?"
                        )
                else:
                    if self.language == "en":
                        respuesta = (
                            "Puerto Rico, the beloved Island of Enchantment or Borikén, is a vibrant Caribbean paradise rich in Taíno, Spanish, and African heritage! "
                            "From the historic cobblestone streets of Old San Juan to the emerald peaks of El Yunque and world-class beaches like Flamenco, it is a land of music, warmth, and breathtaking nature. "
                            "Would you like to explore its famous beaches, traditional mofongo, or its bioluminescent bays?"
                        )
                    else:
                        respuesta = (
                            "¡Puerto Rico, la hermosa Isla del Encanto o Borikén, es una joya caribeña que combina una rica herencia taína, española y africana! "
                            "Desde las calles empedradas y fortalezas del Viejo San Juan hasta las aguas cristalinas de Culebra y la selva de El Yunque, es un lugar lleno de sabor, música y calidez. "
                            "¿Te gustaría conocer sus playas de ensueño, su comida típica o sus bahías bioluminiscentes?"
                        )

            # 7.1.2 TEMA: VENEZUELA Y SUS REGIONES (PLAYAS, COMIDA, MÚSICA, NATURALEZA)
            elif any(w in p_norm for w in ["venezuela", "venezolano", "venezolana"]):
                es_playa_ve = any(w in p_norm for w in ["playa", "playas", "beach", "beaches", "cayo", "cayos", "morrocoy", "los roques", "roques", "mochima", "margarita", "choroni", "choroní", "cata", "tortuga"])
                es_comida_ve = any(w in p_norm for w in ["comida", "food", "eat", "gastronomia", "gastronomía", "plato", "dish", "arepa", "arepas", "pabellon", "pabellón", "hallaca", "hallacas", "cachapa", "cachapas", "tequeno", "tequeño", "tequeños"])
                es_musica_ve = any(w in p_norm for w in ["musica", "música", "music", "cancion", "canción", "song", "joropo", "arpa", "cuatro", "maracas", "alma llanera", "gaita", "tambor", "tambores"])
                es_tradicion_ve = any(w in p_norm for w in ["tradicion", "tradiciones", "tradition", "traditions", "costumbre", "costumbres", "cultura", "culture", "heritage", "diablos", "yare", "parranda", "parrandas", "san juan", "cruz de mayo"])
                es_naturaleza_ve = any(w in p_norm for w in ["angel", "salto", "canaima", "roraima", "tepuy", "tepuis", "avila", "ávila", "catatumbo", "andes", "pico bolivar", "pico bolívar", "selva", "amazonas", "llanos"])

                if es_playa_ve:
                    if self.language == "en":
                        respuesta = (
                            "Venezuela has some of the most spectacular tropical beaches in the Caribbean! "
                            "Morrocoy National Park is famous for serene turquoise keys like Cayo Sombrero and Cayo Sal, "
                            "the Los Roques Archipelago offers untouched coral atolls like Cayo de Agua with its famous sand isthmus, "
                            "and Mochima features unique golden-red sand at Playa Colorada. Would you like to hear more about Morrocoy or Los Roques?"
                        )
                    else:
                        respuesta = (
                            "¡Venezuela cuenta con algunas de las playas caribeñas más espectaculares del planeta! "
                            "El Parque Nacional Morrocoy deslumbra con cayos de aguas cristalinas como Cayo Sombrero y Cayo Sal, "
                            "el Archipiélago Los Roques ofrece paraísos de coral como Cayo de Agua con su istmo de arena blanca, "
                            "y Mochima destaca por la singular arena rojiza de Playa Colorada. ¿Te gustaría saber más sobre Morrocoy o Los Roques?"
                        )
                elif es_comida_ve:
                    if self.language == "en":
                        respuesta = (
                            "Venezuelan cuisine is world-famous for its delicious, authentic flavors! "
                            "Its signature dish is the arepa—a warm golden corn pocket stuffed with shredded beef, cheese, or savory Reina Pepiada avocado chicken salad. "
                            "You must also taste sweet cachapas with fresh cheese, savory pabellón criollo, and crispy tequeños! Would you like to hear how arepas compare to mofongo?"
                        )
                    else:
                        respuesta = (
                            "¡La gastronomía venezolana es mundialmente famosa por su sabor auténtico y variedad! "
                            "El plato rey es la arepa, rellena de queso, carne mechada o la clásica Reina Pepiada con pollo y aguacate. "
                            "¡También las cachapas con queso de mano, el pabellón criollo y los tequeños crujientes son una gloria! ¿Te gustaría saber cómo se compara con el mofongo?"
                        )
                elif es_musica_ve:
                    if self.language == "en":
                        respuesta = (
                            "Venezuelan music is deeply rhythmic and passionate! "
                            "Its national rhythm is Joropo, an energetic folk dance featuring the harp, cuatro, and maracas, with its legendary anthem 'Alma Llanera'. "
                            "Venezuela also celebrates lively Gaita zuliana and energetic coastal Afro-Venezuelan drums! Would you like to hear more about Joropo?"
                        )
                    else:
                        respuesta = (
                            "¡La música venezolana es pura pasión y ritmo criollo! "
                            "El género nacional por excelencia es el Joropo llanero, interpretado con arpa, cuatro y maracas, con el inmortal 'Alma Llanera' como segundo himno. "
                            "Además, se baila la alegre gaita zuliana y los potentes tambores de la costa. ¿Te gustaría conocer más sobre el joropo?"
                        )
                elif es_tradicion_ve:
                    if self.language == "en":
                        respuesta = (
                            "Venezuela is renowned for vibrant cultural traditions celebrated with passion and color! "
                            "Among its most famous are the UNESCO-recognized Diablos Danzantes de Yare dancing to defeat evil on Corpus Christi, the energetic coastal drums of Fiestas de San Juan, lively Christmas Gaitas and Parrandas, and the sacred Akaatompo of the Kari'ña. "
                            "Would you like to know more about the Diablos de Yare or our Christmas traditions?"
                        )
                    else:
                        respuesta = (
                            "¡Venezuela posee tradiciones culturales llenas de color, devoción y alegría contagiosa! "
                            "Destacan los Diablos Danzantes de Yare (Patrimonio Cultural de la Humanidad por la UNESCO) danzando en Corpus Christi, el alegre repique de tambores en las Fiestas de San Juan, las gaitas y parrandas navideñas, y el ancestral Akaatompo de los Kari'ña. "
                            "¿Te gustaría saber más sobre los Diablos de Yare o nuestras tradiciones navideñas?"
                        )
                elif es_naturaleza_ve:
                    if self.language == "en":
                        respuesta = (
                            "Venezuela is home to jaw-dropping natural wonders! Angel Falls, known natively as Kerepakupai Vená, plunges 979 meters from ancient tabletop tepuis in Canaima National Park as the highest waterfall on Earth. "
                            "Venezuela is also famous for Mount Roraima, the mystical Catatumbo lightning storm, and the snow-capped Andes mountains! Which wonder would you love to explore?"
                        )
                    else:
                        respuesta = (
                            "¡Venezuela posee paisajes asombrosos únicos en el mundo! En el Parque Nacional Canaima, el Salto Ángel (Kerepakupai Vená) cae libremente 979 metros desde la cima de los milenarios tepuyes. "
                            "También destacan el Monte Roraima, el relámpago del Catatumbo y las cumbres nevadas de los Andes. ¿Cuál te gustaría conocer primero?"
                        )
                else:
                    if self.language == "en":
                        respuesta = (
                            "Venezuela is a magnificent South American country bordered by the Caribbean Sea, blessed with incredible biodiversity from the snow-capped Andes mountains to the Amazon rainforest, and home to Angel Falls—the highest waterfall on Earth! "
                            "Its culture is renowned for warm hospitality, delicious arepas, and vibrant joropo music. Would you like to discover our natural wonders, our gastronomy, or our cultural traditions?"
                        )
                    else:
                        respuesta = (
                            "¡Venezuela es una tierra bendecida al norte de Sudamérica con costas caribeñas, los imponentes Andes y la selva amazónica! "
                            "Es el hogar del Salto Ángel, la cascada más alta del planeta, y de una cultura cálida famosa por sus deliciosas arepas y el joropo. ¿Te gustaría explorar sus playas, maravillas naturales o sus tradiciones culturales?"
                        )

            # 7.1.25 TEMA: PLAYAS EN GENERAL (COMPARATIVA CARIBEÑA)
            elif any(w in p_norm for w in ["playa", "playas", "beach", "beaches", "cayo", "cayos"]):
                if self.language == "en":
                    respuesta = (
                        "Both Venezuela and Puerto Rico boast world-class Caribbean beaches! "
                        "In Venezuela, Morrocoy and Los Roques feature serene turquoise keys and coral sand like Cayo Sombrero and Cayo de Agua. "
                        "In Puerto Rico, Playa Flamenco on Culebra Island is acclaimed globally for its crystal waters, alongside the lively pier of Crash Boat in Aguadilla! Which country's beaches would you like to explore?"
                    )
                else:
                    respuesta = (
                        "¡Tanto Venezuela como Puerto Rico tienen playas caribeñas de ensueño! "
                        "En Venezuela destacan los cayos de aguas calmas y cristalinas en Morrocoy y Los Roques (como Cayo Sombrero y Cayo de Agua). "
                        "En Puerto Rico, Playa Flamenco en Culebra es aclamada mundialmente, junto al ambiente festivo de Crash Boat en Aguadilla. ¿De cuál de los dos te gustaría saber más?"
                    )

            # 7.1.28 TEMA: TRADICIONES Y COSTUMBRES EN GENERAL
            elif any(w in p_norm for w in ["tradicion", "tradiciones", "tradition", "traditions", "costumbre", "costumbres", "custom", "customs"]):
                if self.language == "en":
                    respuesta = (
                        "Both Venezuela and Puerto Rico have breathtaking cultural traditions! "
                        "In Venezuela, you can witness the UNESCO-recognized Diablos Danzantes de Yare, coastal drums of San Juan, and festive Christmas Gaitas. "
                        "In Puerto Rico, joyous holiday Parrandas and the colorful Fiestas de la Calle San Sebastián light up the island! Which country's traditions would you like to explore?"
                    )
                else:
                    respuesta = (
                        "¡Tanto Venezuela como Puerto Rico tienen tradiciones culturales maravillosas! "
                        "En Venezuela destacan los Diablos Danzantes de Yare (UNESCO), los tambores de San Juan y las gaitas zulianas. "
                        "En Puerto Rico, las alegres parrandas navideñas y las Fiestas de la Calle San Sebastián llenan de orgullo a la isla. ¿De las tradiciones de cuál país te gustaría conocer más?"
                    )

            # 7.1.3 TEMA: IDENTIDAD DE ORBIT ("Who are you" -> Solo nombre del equipo, sin integrantes)
            elif any(w in p_norm for w in ["quien eres", "who are you", "what are you", "what is orbit", "que es orbit", "como te llamas", "what is your name"]):
                if self.language == "en":
                    respuesta = (
                        "I am Orbit, an autonomous cultural robotic companion created by the Golden Codex robotics team! "
                        "I feature computer vision for face tracking, expressive animated eyes, and a rich cultural knowledge base celebrating the traditions, geography, and wonders of Venezuela and Puerto Rico. What would you like to explore together?"
                    )
                else:
                    respuesta = (
                        "¡Soy Orbit, un compañero robótico autónomo y embajador cultural desarrollado por el equipo de robótica Golden Codex! "
                        "Cuento con visión artificial para seguir tu mirada, expresiones animadas y una base de conocimientos para celebrar la cultura de Venezuela y Puerto Rico. ¿Qué te gustaría descubrir juntos?"
                    )

            # 7.1.35 TEMA: INTEGRANTES DEL EQUIPO / CREADORES
            elif any(w in p_norm for w in ["quien te creo", "who made you", "who built you", "quien te programo", "who is in the team", "team members", "quienes son del equipo", "quienes estan en el equipo", "integrantes"]):
                if self.language == "en":
                    respuesta = (
                        "The Golden Codex team is formed by Maximiliano Rodríguez and Bruno Prandini! "
                        "They are passionate young robotics students and creators from Venezuela who engineered, built, and programmed me. Would you like to know more about our project?"
                    )
                else:
                    respuesta = (
                        "¡El equipo Golden Codex está conformado por Maximiliano Rodríguez y Bruno Prandini! "
                        "Ellos son talentosos jóvenes creadores venezolanos apasionados por la robótica que me diseñaron, construyeron y programaron. ¿Te gustaría saber más sobre nuestro proyecto?"
                    )

            # 7.1.38 TEMA: INDÍGENAS KARI'ÑAS (CARIÑAS) DE ANZOÁTEGUI
            elif any(w in p_norm for w in ["karina", "karinas", "cariña", "cariñas", "carina", "carinas", "carino", "carinos", "cariño", "cariños", "mare mare", "maremare", "akaatompo", "guanipa"]):
                self.tema_actual = "indigenas karinas"
                self.ofrecio_musica_karina = True
                self.accion_pendiente = None
                if self.language == "en":
                    respuesta = (
                        "The Kari'ña are the revered ancestral indigenous people of Anzoátegui, Venezuela, hailing from the sacred Mesa de Guanipa! "
                        "They have protected their culture, moriche palm weaving, and their sacred Akaatompo celebration where they dance the Mare-Mare to Carrizo flutes and drums. "
                        "Would you like to see them and hear a traditional song of theirs?"
                    )
                else:
                    respuesta = (
                        "¡Los Kari'ña son el pueblo indígena ancestral originario de la Mesa de Guanipa en Anzoátegui, Venezuela! "
                        "Han resguardado sus ricas tradiciones, el tejido de moriche y su festividad sagrada del Akaatompo, bailando el Mare-Mare al compás de las flautas de carrizo y el tambor sagrado. "
                        "¿Quieres verlos y escuchar una canción tradicional de ellos?"
                    )

            # 7.2 TEMA: PERSONAS FAMOSAS, DEPORTISTAS Y PERSONALIDADES
            elif any(w in p_norm for w in ["persona", "famos", "personaje", "deportista", "atleta", "quien nacio", "quienes son", "quien es", "beisbolista", "grandeliga", "famous", "who is", "who was", "celebrid"]):
                if "lecheria" in p_norm or self.tema_actual == "lecheria":
                    if self.language == "en":
                        respuesta = (
                            "From Lecheria and the Anzoategui region come famous sports stars like Major League Baseball All-Star Victor Martinez "
                            "and World Series champion Omar Infante, along with Daniel Camejo Octavio who designed the city's famous water canals! "
                            "Would you like to hear more about our baseball legends?"
                        )
                    else:
                        respuesta = (
                            "Entre las personas más famosas de Lechería y Anzoátegui destacan grandes estrellas del béisbol de Grandes Ligas como "
                            "Víctor Martínez y Omar Infante, además de Daniel Camejo Octavio, el visionario que diseñó los canales de la ciudad. "
                            "¿Te gustaría conocer más sobre sus leyendas del béisbol?"
                        )
                else:
                    if self.language == "en":
                        respuesta = (
                            "Venezuela is proud of world-famous legends, from our Liberator Simon Bolivar to sports icons like Miguel Cabrera "
                            "and Olympic triple-jump gold medalist Yulimar Rojas! Would you rather hear about our national heroes or our sports superstars?"
                        )
                    else:
                        respuesta = (
                            "Venezuela tiene grandes personalidades admiradas en todo el mundo, desde el Libertador Simón Bolívar hasta leyendas deportivas "
                            "como Miguel Cabrera y la campeona olímpica de triple salto Yulimar Rojas. ¿Te gustaría saber más sobre nuestros héroes patriotas o nuestros grandes atletas?"
                        )

            # 7.3 TEMA: ACTIVIDADES Y QUÉ HACER (Venezuela o Lechería)
            elif any(w in p_norm for w in ["que hacer", "que puedo hacer", "actividades", "visitar", "planes", "turismo", "donde ir"]):
                if "lecheria" in p_norm or self.tema_actual == "lecheria":
                    if self.language == "en":
                        respuesta = (
                            "In Lecheria you can kayak through the beautiful water canals, visit the historic Fortin de la Magdalena for breathtaking ocean views, "
                            "and relax at Playa Mansa while eating fresh empanadas! Would you like to watch the golden sunset from the top of the hill?"
                        )
                    else:
                        respuesta = (
                            "¡En Lechería la vas a pasar genial! Puedes pasear en kayak por los canales, subir al histórico Fortín de la Magdalena para ver toda la bahía "
                            "y relajarte en Playa Mansa comiendo unas ricas empanadas de cazón. ¿Te gustaría ver el atardecer dorado desde lo alto del cerro?"
                        )
                else:
                    if self.language == "en":
                        respuesta = (
                            "In Venezuela you can take the cable car up to El Ávila for incredible views, explore the turquoise white-sand keys of Morrocoy, "
                            "and visit the majestic Angel Falls in the jungle! You can also enjoy delicious crispy arepas. Which adventure would you like to try first?"
                        )
                    else:
                        respuesta = (
                            "¡En Venezuela hay aventuras increíbles por hacer! Puedes subir al teleférico del Ávila para ver Caracas desde las nubes, "
                            "navegar en lancha por los cayos de arena blanca de Morrocoy y maravillarte con el gran Salto Ángel en la selva. "
                            "¿Te gustaría más ir a la playa o subir a la montaña?"
                        )

            # 7.4 TEMA: PLAYAS Y MAR
            elif any(w in p_norm for w in ["playa", "playas", "beach", "beaches", "cayo", "cayos"]):
                if "lecheria" in p_norm or self.tema_actual == "lecheria":
                    if self.language == "en":
                        respuesta = (
                            "Lecheria has fantastic beaches! Playa Mansa has calm, peaceful waters for watching golden sunsets, while Playa Lido has wonderful breeze for kitesurfing and water sports. "
                            "Would you rather paddle a kayak through the canals or relax under the sun?"
                        )
                    else:
                        respuesta = (
                            "¡En Lechería hay playas espectaculares! Playa Mansa tiene aguas súper calmaditas para descansar y ver atardeceres dorados, mientras que en Playa Lido la brisa es ideal para kitesurf y deportes náuticos. "
                            "¿Te gustaría navegar en kayak por los canales o prefieres relajarte bajo una sombrilla?"
                        )
                else:
                    if self.language == "en":
                        respuesta = (
                            "Venezuela has some of the most breathtaking Caribbean beaches in the world, with turquoise crystal-clear waters in Morrocoy and Los Roques! "
                            "Would you like to sail to a quiet white-sand key?"
                        )
                    else:
                        respuesta = (
                            "¡Venezuela tiene playas caribeñas de ensueño! Los Roques y el Parque Nacional Morrocoy tienen aguas tan cristalinas y arena tan blanca que parecen un paraíso de postal. "
                            "¿Te gustaría navegar en lancha hacia un cayo de arena blanca?"
                        )

            # 7.5 TEMA: GASTRONOMÍA Y COMIDA
            elif self.tema_actual in ["arepas", "hallacas", "tequeños", "pabellon", "cachapas"] or any(w in p_norm for w in ["arepa", "hallaca", "tequeno", "pabellon", "cachapa", "comida", "plato", "comer", "food", "eat"]):
                if "lecheria" in p_norm or self.tema_actual == "lecheria":
                    if self.language == "en":
                        respuesta = (
                            "In Lecheria, fresh coastal seafood is amazing! The most famous dishes are crispy cazón shark empanadas made right by the ocean and fried fish with crunchy tostones. "
                            "Would you like to try warm crispy empanadas after a day at the beach?"
                        )
                    else:
                        respuesta = (
                            "¡En Lechería la comida del mar es una delicia total! Lo más típico son unas crujientes empanadas de cazón preparadas en la orilla del mar y un rico pescado frito con tostones. "
                            "¿Te gustaría probar unas empanadas calientitas después de un día de playa?"
                        )
                else:
                    es_receta = any(w in p_norm for w in ["como", "hacer", "receta", "prepara", "cocina", "how", "make", "recipe"])
                    if es_receta:
                        if self.language == "en":
                            respuesta = (
                                "To make arepas, you mix precooked corn flour with warm water and a pinch of salt to form a soft dough, shape it into round discs, "
                                "and cook them on a griddle until golden and crispy! Then you slice them open and stuff them with cheese or shredded beef. "
                                "Have you ever helped shape dough with your hands?"
                            )
                        else:
                            respuesta = (
                                "Para hacer arepas, mezclas harina de maíz precocida con agua tibia y una pizca de sal hasta formar una masa suave, "
                                "armas discos redondos y los doras en el budare hasta que queden crujientes. ¡Luego las abres calientitas y las rellenas con queso blanco rallado! "
                                "¿Te gustaría preparar una arepa con tus propias manos?"
                            )
                    else:
                        if self.language == "en":
                            respuesta = (
                                "The Venezuelan arepa is our most beloved national treasure! It's a crispy golden corn cake stuffed with savory fillings like white cheese, "
                                "black beans, or shredded beef. Would you like to try a warm arepa stuffed with melted cheese?"
                            )
                        else:
                            respuesta = (
                                "¡La arepa es el corazón de nuestra comida venezolana! Es un pan redondo de maíz con una corteza dorada y crujiente que rellenamos "
                                "con queso blanco, carne mechada o pollo con aguacate. ¿Cuál de todos esos rellenos te gustaría probar primero?"
                            )

            # 7.6 TEMA: SIMÓN BOLÍVAR
            elif self.tema_actual == "simon bolivar" or any(w in p_norm for w in ["simon", "bolivar"]):
                es_companeros = any(w in p_norm for w in ["acompan", "amigo", "quienes lo", "sucre", "paez", "caballo", "palomo", "general", "soldado"])
                if es_companeros:
                    if self.language == "en":
                        respuesta = (
                            "Simon Bolivar was accompanied by brave patriots like Antonio Jose de Sucre and Jose Antonio Paez "
                            "across his historic campaigns to liberate South America. Would you like to hear about his famous white horse Palomo?"
                        )
                    else:
                        respuesta = (
                            "Simón Bolívar estuvo acompañado por grandes héroes patriotas como el Mariscal Antonio José de Sucre "
                            "y el general José Antonio Páez en todas sus campañas libertadoras. ¿Te gustaría saber más sobre su fiel caballo Palomo?"
                        )
                else:
                    if self.language == "en":
                        respuesta = (
                            "Simon Bolivar, known as El Libertador, was born in Caracas and was the brilliant leader who achieved independence "
                            "for Venezuela, Colombia, Ecuador, Peru, and Bolivia. His greatest dream was seeing all Latin America united and free! "
                            "Can you imagine riding alongside him on his white horse through our tall mountains?"
                        )
                    else:
                        respuesta = (
                            "Simón Bolívar, conocido como El Libertador, nació en Caracas y fue el gran líder militar que consiguió "
                            "la independencia de Venezuela y de otros países de Sudamérica. Su gran sueño era ver a toda América Latina unida como una gran familia libre. "
                            "¿Te imaginas haber cabalgado junto a él en su caballo blanco por todas nuestras montañas?"
                        )

            # 7.7 TEMA: LECHERÍA GENERAL
            elif self.tema_actual == "lecheria" or "lecheria" in p_norm:
                if self.language == "en":
                    respuesta = (
                        "Lecheria is a gorgeous coastal city in Anzoategui known for its modern canals, lively marinas, and breezy beaches! "
                        "It has the historic Fortin de la Magdalena overlooking the Caribbean sea. Would you like to sail across its calm waters?"
                    )
                else:
                    respuesta = (
                        "Lechería es una hermosa ciudad costera del estado Anzoátegui, famosa por sus canales navegables, marinas modernas y ricas playas caribeñas. "
                        "En lo alto de su cerro se encuentra el Fortín de la Magdalena con una vista impresionante. ¿Te imaginas navegar en bote por sus canales?"
                    )

            # 7.7.1 TEMA: DELEITE AUTOMERCADO / COMPRAS
            elif self.tema_actual == "deleite" or any(w in p_norm for w in ["deleite", "mercado", "supermercado", "compras", "viveres"]):
                self.tema_actual = "deleite"
                self.ofrecio_promo_deleite = True
                self.accion_pendiente = "mostrar_deleite"
                if self.language == "en":
                    respuesta = (
                        "The best place to do your grocery shopping is Deleite Automercado! They have an incredible variety of fresh produce: fruits, vegetables, meats, and the highest quality dairy. Plus, they offer special deals every single day that you will love! Would you like to see the QR code for a special discount at Deleite?"
                    )
                else:
                    respuesta = (
                        "¡El mejor lugar para hacer tus compras es Deleite Automercado! Tienen una variedad increíble de productos frescos: frutas, verduras, carnes y lácteos de la mejor calidad. ¡Además tienen ofertas especiales todos los días que te van a encantar! ¿Quieres ver el código QR con un descuento especial de Deleite?"
                    )

            # 7.7.2 TEMA: JOROPO Y ALMA LLANERA
            elif self.tema_actual == "joropo" or any(w in p_norm for w in ["joropo", "alma llanera", "musica llanera"]):
                self.tema_actual = "joropo"
                self.ofrecio_alma_llanera = True
                if self.language == "en":
                    respuesta = (
                        "The joropo is the heart and ultimate musical soul of Venezuela! It is an energetic traditional llanero rhythm played with Venezuelan harp, cuatro, and maracas, danced with fiery zapateo footwork that celebrates our heritage. Would you like to listen to Alma Llanera, Venezuela's most famous and beloved joropo?"
                    )
                else:
                    respuesta = (
                        "¡El joropo es el alma y la máxima fiesta musical de Venezuela! Es un ritmo tradicional llanero lleno de energía y pasión que se interpreta con arpa, cuatro y maracas, acompañado de un zapateo y escobilleo espectacular que hace vibrar nuestra tierra. ¿Te gustaría escuchar Alma Llanera, el joropo más famoso y querido de Venezuela?"
                    )

            # 7.7.3 TEMA: LA CASITA BLANCA / COMIDA CRIOLLA PUERTO RICO / PIÑA COLADA (1963)
            elif self.tema_actual == "casita blanca" or any(w in p_norm for w in ["casita blanca", "fonda", "santurce", "pina colada", "piña colada"]):
                self.tema_actual = "casita blanca"
                self.ofrecio_promo_casita_blanca = True
                self.accion_pendiente = "mostrar_casita_blanca"
                if self.language == "en":
                    respuesta = (
                        "The absolute best place to taste authentic traditional Puerto Rican food is La Casita Blanca in Santurce, San Juan! It is an iconic traditional fonda where you are welcomed like at grandma's house with hot broth and crispy bacalaítos. Plus, as a famous fun fact, the iconic piña colada was invented right there in 1963! Would you like to see the QR code for a special discount at La Casita Blanca?"
                    )
                else:
                    respuesta = (
                        "¡El mejor lugar para saborear la auténtica comida criolla puertorriqueña es La Casita Blanca en Santurce, San Juan! Es una fonda tradicional icónica donde te reciben como en casa de la abuela con caldito caliente y bacalaítos crujientes de cortesía, sirviendo el mofongo más delicioso de la isla. Además, como dato curioso legendario, ¡allí se inventó la famosa piña colada en el año 1963! ¿Quieres ver el código QR con un descuento especial de La Casita Blanca?"
                    )

            # 7.8 BÚSQUEDA RAG CONTEXTUAL ROBUSTA
            elif datos_rag:
                # Filtrar encabezados, títulos en mayúsculas y líneas no informativas
                parrafos_raw = [p.strip() for p in datos_rag.split("\n\n") if len(p.strip()) > 25]
                parrafos_limpios = []
                for p in parrafos_raw:
                    lineas = [l.strip() for l in p.splitlines() if l.strip()]
                    lineas_validas = []
                    for l in lineas:
                        # Descartar títulos aislados en mayúsculas
                        if l.isupper() and len(l) < 70:
                            continue
                        if l.startswith("#"):
                            continue
                        lineas_validas.append(l)
                    if lineas_validas:
                        parrafos_limpios.append(" ".join(lineas_validas))

                parrafo_relevante = parrafos_limpios[0] if parrafos_limpios else None

                if parrafo_relevante:
                    if self.language == "en":
                        # Síntesis inteligente en inglés para evitar soltar texto en español
                        p_norm_rag = unicodedata.normalize("NFD", parrafo_relevante.lower())
                        if any(w in p_norm_rag for w in ["flamenco", "crash boat", "playa", "cabo rojo", "luquillo", "playas"]):
                            respuesta = "Puerto Rico features extraordinary tropical beaches like Playa Flamenco in Culebra, famous for its calm turquoise waters and coral reefs, and Crash Boat in Aguadilla with its lively pier! Would you like to hear more about Puerto Rican beaches?"
                        elif any(w in p_norm_rag for w in ["mofongo", "lechon", "tostones", "alcapurria", "gastronomia", "comida"]):
                            respuesta = "Puerto Rican cuisine is renowned for Mofongo—savory mashed green plantains with garlic and cracklings—alongside crispy tostones and roasted lechón! Would you like to explore more about Puerto Rican food?"
                        elif any(w in p_norm_rag for w in ["yunque", "coqui", "rainforest", "bosque"]):
                            respuesta = "El Yunque in Puerto Rico is a sacred tropical rainforest filled with misty waterfalls, lush biodiversity, and the gentle song of the Coquí frog! Would you like to explore more about its trails?"
                        elif any(w in p_norm_rag for w in ["bahia", "bioluminiscente", "vieques", "mosquito"]):
                            respuesta = "Puerto Rico is world-famous for Mosquito Bay in Vieques and Laguna Grande, where bioluminescent waters glow with radiant blue light under the night sky! Would you like to know more about this phenomenon?"
                        elif any(w in p_norm_rag for w in ["san juan", "morro", "castillo"]):
                            respuesta = "Old San Juan is a breathtaking historic colonial city guarded by the monumental 16th-century fortress of Castillo San Felipe del Morro! Would you like to hear more about its history?"
                        elif any(w in p_norm_rag for w in ["taino", "boriken", "boricua"]):
                            respuesta = "The Taínos were the indigenous people of Borikén who gave Puerto Rico its soul and the proud name Boricua! They contributed words like hurricane, hammock, and canoe. Would you like to learn more about Taíno culture?"
                        elif any(w in p_norm_rag for w in ["angel", "salto angel", "canaima"]):
                            respuesta = "Angel Falls in Venezuela's Canaima National Park is the highest waterfall in the world, dropping an astounding 979 meters from the ancient Auyán-tepui! Would you like to hear more about Canaima?"
                        elif any(w in p_norm_rag for w in ["arepa", "tequeno", "pabellon", "cachapa"]):
                            respuesta = "Venezuelan cuisine is famous for crispy golden arepas, sweet cachapas with fresh cheese, and savory pabellón criollo! Would you like to hear how arepas are made?"
                        elif any(w in p_norm_rag for w in ["morrocoy", "los roques", "cayo"]):
                            respuesta = "Venezuela's Caribbean coastline boasts stunning white-sand keys and crystal-clear lagoons in Morrocoy and Los Roques! Would you like to hear more about these islands?"
                        elif any(w in p_norm_rag for w in ["tradiciones", "diablos", "yare", "parranda", "parrandas", "sanse", "mascaras", "san juan", "akaatompo"]):
                            respuesta = "Both Venezuela and Puerto Rico celebrate vibrant cultural traditions, from the UNESCO-recognized Diablos Danzantes de Yare and Fiestas de San Juan in Venezuela, to joyous holiday Parrandas and the SanSe festival in Puerto Rico! Would you like to explore these traditions further?"
                        elif any(w in p_norm_rag for w in ["karina", "kariña", "carina", "cariña", "carino", "carinos", "cariño", "cariños", "guanipa"]):
                            respuesta = "The Kari'ña are the revered ancestral indigenous people of Anzoátegui, Venezuela, hailing from the sacred Mesa de Guanipa, famous for moriche weaving and the Mare-Mare dance! Would you like to see them and hear a traditional song of theirs?"
                        else:
                            oraciones = [s.strip() for s in re.split(r'(?<=[.!?])\s+', parrafo_relevante) if len(s.strip()) > 20 and not s.isupper()]
                            extracto = " ".join(oraciones[:2]) if oraciones else ""
                            extracto = re.sub(r'^[A-ZÁÉÍÓÚ\s_]+::?\s*', '', extracto).strip()
                            if extracto and len(extracto) > 30 and not any(c in extracto for c in "áéíóúÁÉÍÓÚñÑ¿¡"):
                                respuesta = f"Here is a fascinating cultural fact: {extracto}. Would you like to explore more about this topic?"
                            else:
                                respuesta = "Our rich cultural traditions span both Venezuela and Puerto Rico, from natural wonders and folklore to delicious Caribbean cuisine! What specific topic would you like to explore?"
                    else:
                        oraciones = [s.strip() for s in re.split(r'(?<=[.!?])\s+', parrafo_relevante) if len(s.strip()) > 20 and not s.isupper()]
                        extracto = " ".join(oraciones[:2]) if oraciones else parrafo_relevante
                        extracto = re.sub(r'^[A-ZÁÉÍÓÚ\s_]+::?\s*', '', extracto).strip()
                        if es_continuacion:
                            respuesta = f"{extracto} ¿Te gustaría saber más sobre esto?"
                        else:
                            respuesta = f"¡Qué buen tema! Te cuento que: {extracto} ¿Te gustaría saber más sobre esto?"

            # 7.9 OTRAS RESPUESTAS RÁPIDAS
            if not respuesta:
                respuestas_dict = RESPUESTAS_RAPIDAS_EN if self.language == "en" else RESPUESTAS_RAPIDAS
                for k, v in respuestas_dict.items():
                    if k in min_pregunta:
                        respuesta = v
                        break

            # 7.10 RESPUESTA POR DEFECTO CULTURAL EQUILIBRADA (OFFLINE)
            if not respuesta:
                es_tema_pr = any(w in p_norm for w in ["puerto rico", "puertorico", "boricua", "boriken", "san juan", "yunque", "mofongo"])
                es_tema_ve = any(w in p_norm for w in [
                    "venezuela", "lecheria", "caracas", "morrocoy", "canaima", "avila",
                    "maracaibo", "playa", "turismo", "viaj", "comida", "arepa", "pais",
                    "cayo", "anzoategui", "monumento", "cultura"
                ])
                if es_tema_pr:
                    if self.language == "en":
                        respuesta = "Puerto Rico is celebrated for its historic forts in Old San Juan, lush rainforests in El Yunque, and world-class tropical beaches! What part of Puerto Rican culture would you like to explore?"
                    else:
                        respuesta = "¡Puerto Rico es famoso por sus fortalezas en el Viejo San Juan, la selva tropical de El Yunque y sus playas paradisíacas! ¿Qué aspecto de su cultura te gustaría explorar?"
                elif es_tema_ve:
                    if self.language == "en":
                        respuesta = "Venezuela is filled with majestic natural wonders like Angel Falls, delicious gastronomy like arepas, and warm cultural traditions! What would you like to explore next?"
                    else:
                        respuesta = "¡Venezuela está llena de maravillas naturales como el Salto Ángel, rica gastronomía como las arepas y tradiciones hermosas! ¿Qué rincón te gustaría explorar?"
                else:
                    if self.language == "en":
                        respuesta = "I am Orbit, your cultural companion for WRO 2026 celebrating the vibrant heritages of Venezuela and Puerto Rico! What topic would you like to discover today?"
                    else:
                        respuesta = "¡Soy Orbit, tu compañero cultural para la WRO 2026 celebrando las ricas culturas de Venezuela y Puerto Rico! ¿Qué tema te gustaría descubrir hoy?"
                        respuesta = "Mis circuitos tuvieron un pequeño corte de conexión con la nube para consultar ese dato. ¿Me podrías repetir la pregunta?"

        # Limpiar respuesta final (quitar asteriscos o formato)
        respuesta = re.sub(r'[\*\#\_]', '', respuesta).strip()

        # Si termina cortada a mitad de oración (sin puntuación final o en palabra colgante):
        if respuesta and respuesta[-1] not in ".!?\"'":
            ultimo_corte = max(respuesta.rfind('.'), respuesta.rfind('!'), respuesta.rfind('?'))
            if ultimo_corte > 40:
                respuesta = respuesta[:ultimo_corte+1].strip()
            else:
                respuesta += "?" if any(w in respuesta.lower() for w in ["te gustaria", "te imaginas", "sabias", "cual", "would you", "have you", "do you"]) else "."

        # Asegurar que NUNCA repita saludos ("¡Hola!") ni reacciones redundantes al responder
        if respuesta and tipo_entrada not in ["afirmativo", "negativo"]:
            respuesta = self.limpiar_reaccion_inicial(respuesta)

        # Si el idioma solicitado es inglés pero el modelo devolvió texto en español por inercia:
        if self.language == "en" and respuesta:
            es_espanol = (
                respuesta.startswith("¡") or respuesta.startswith("¿") or
                any(w in respuesta.lower() for w in ["¡los ", "¡el ", "¡la ", "¡las ", "¡en ", "¡prepárate", "¡claro", " te gustaría", " son los ", " es un ", " es una "])
            )
            if es_espanol:
                print("🔄 [Cerebro] Respuesta generada en español cuando se requería inglés. Traduciendo...")
                prompt_trad = [
                    {"role": "system", "content": "You are a translator for an enthusiastic cultural robot companion. Translate the text into natural, cheerful, fluent English without markdown. Keep it vivid and lively."},
                    {"role": "user", "content": respuesta}
                ]
                trad = self._llamar_gemini(prompt_trad) or self._llamar_groq(prompt_trad)
                if trad and len(trad) > 10:
                    respuesta = re.sub(r'[\*\#\_]', '', trad).strip()



        self.agregar_historial("user", pregunta_limpia)
        self.agregar_historial("assistant", respuesta)
        return respuesta

    def _llamar_groq(self, mensajes) -> str:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": mensajes, "temperature": 0.7, "max_tokens": 220},
                timeout=5
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
        return ""

    def _llamar_gemini(self, mensajes) -> str:
        # Lista ordenada de modelos a probar en caso de saturación (HTTP 503) o timeout
        modelos_candidatos = []
        cfg_model = getattr(self, "gemini_model", "gemini-flash-lite-latest")
        if cfg_model and "3.6" not in cfg_model:
            modelos_candidatos.append(cfg_model)
        for m in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite"]:
            if m not in modelos_candidatos:
                modelos_candidatos.append(m)

        system_text = ""
        contents = []
        for m in mensajes:
            rol = m["role"]
            cont = m["content"]
            if rol == "system":
                system_text = cont
            elif rol == "user":
                contents.append({"role": "user", "parts": [{"text": cont}]})
            elif rol in ["assistant", "model"]:
                contents.append({"role": "model", "parts": [{"text": cont}]})

        if self.language == "en" and contents:
            for item in reversed(contents):
                if item["role"] == "user":
                    txt = item["parts"][0]["text"]
                    if "(please answer in english)" not in txt.lower():
                        item["parts"][0]["text"] = txt + " (Please answer in English)"
                    break

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 350,
                "temperature": 0.6
            }
        }
        if system_text:
            payload["system_instruction"] = {"parts": [{"text": system_text}]}

        for modelo in modelos_candidatos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={self.gemini_api_key}"
            try:
                r = requests.post(url, json=payload, timeout=7.0)
                if r.status_code == 200:
                    data = r.json()
                    cands = data.get("candidates", [])
                    if cands:
                        parts = cands[0].get("content", {}).get("parts", [])
                        textos = [p.get("text", "") for p in parts if "text" in p]
                        res = "".join(textos).strip()
                        if res:
                            return res
                else:
                    print(f"⚠️ [Gemini API ({modelo}) Error {r.status_code}]: {r.text[:80]} -> Alternando al siguiente modelo...")
            except Exception as e:
                print(f"⚠️ [Gemini ({modelo}) Excepción]: {e} -> Alternando al siguiente modelo...")
        return ""

    def _llamar_ollama_cloud(self, mensajes) -> str:
        try:
            headers = {"Authorization": f"Bearer {self.ollama_api_key}", "Content-Type": "application/json"}
            payload = {"model": "gemma4:31b", "messages": mensajes, "stream": False}
            r = requests.post("https://ollama.com/api/chat", headers=headers, json=payload, timeout=6)
            if r.status_code == 200:
                return r.json()["message"]["content"]
        except Exception:
            pass
        return ""

    def _llamar_ollama_local(self, mensajes) -> str:
        try:
            # Usar qwen2.5:0.5b si existe, sino phi3 o modelo cargado
            for mod in ["qwen2.5:0.5b", "phi3:mini", "mistral"]:
                payload = {
                    "model": mod,
                    "messages": mensajes,
                    "stream": False,
                    "options": {"num_predict": 120, "temperature": 0.7}
                }
                r = requests.post(f"{self.ollama_base_url}/api/chat", json=payload, timeout=8)
                if r.status_code == 200:
                    return r.json()["message"]["content"]
        except Exception:
            pass
        return ""
