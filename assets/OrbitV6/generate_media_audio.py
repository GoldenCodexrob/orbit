"""
generate_media_audio.py — Pre-generates MP3s for media descriptions.
Run once: python3 generate_media_audio.py
"""
import asyncio, os, sys
import edge_tts

VOICE = "es-AR-ElenaNeural"
RATE  = "+10%"   # 10% faster than default
OUT   = "audio_cache"

AUDIOS = [
    ("media_simon_bolivar_desc",
     "Este es Simon Bolivar, El Libertador de Venezuela. "
     "Nacio en Caracas en 1783 y fue tan valiente que libero cinco paises: "
     "Venezuela, Colombia, Ecuador, Peru y Bolivia. "
     "Por eso lo llamamos el hombre mas importante de America del Sur!"),

    ("media_simon_bolivar_followup",
     "Sabias que Bolivar cruzo las montanas de los Andes con todo un ejercito "
     "para liberar mas paises?"),

    ("media_lecheria_desc",
     "Esta es Lecheria, una ciudad costera del estado Anzoategui en Venezuela. "
     "Sus playas tienen arena blanca y el agua del mar Caribe es azul y cristalina. "
     "Es uno de los lugares mas bonitos para descansar en toda Venezuela!"),

    ("media_lecheria_followup",
     "Te gustaria banarte algun dia en las playas del mar Caribe de Venezuela?"),

    ("media_maracaibo_desc",
     "Este es el Lago de Maracaibo en el estado Zulia, Venezuela. "
     "Es el lago mas grande de toda Sudamerica. "
     "Tiene el Relampago del Catatumbo, "
     "un rayo gigante que aparece casi todas las noches. "
     "Es como magia de la naturaleza!"),

    ("media_maracaibo_followup",
     "Sabias que el Relampago del Catatumbo aparece mas de 200 noches al ano sin parar?"),

    ("media_bandera_desc",
     "Esta es la Bandera de Venezuela, el Pabellon Nacional. "
     "Tiene tres franjas: amarilla por la riqueza de nuestra tierra, "
     "azul por el mar Caribe, y roja por los valientes heroes. "
     "Las ocho estrellas representan los estados originales de Venezuela."),

    ("media_bandera_followup",
     "Sabes cuantas estrellas tiene la bandera de tu pais favorito?"),

    ("media_karina_desc",
     "Este es el pueblo Karina, uno de los grupos indigenas mas importantes de Venezuela. "
     "Viven en los estados Anzoategui y Sucre y han cuidado su cultura por miles de anos. "
     "En Venezuela hay mas de 40 grupos indigenas con sus propias lenguas."),

    ("media_karina_followup",
     "Sabias que en Venezuela se hablan mas de 30 idiomas indigenas ademas del espanol?"),
]

async def generar(nombre, texto):
    path = os.path.join(OUT, f"{nombre}.mp3")
    print(f"  Generando {path} ...", end=" ", flush=True)
    com = edge_tts.Communicate(texto, voice=VOICE, rate=RATE)
    await com.save(path)
    print("OK")

async def main():
    os.makedirs(OUT, exist_ok=True)
    for nombre, texto in AUDIOS:
        await generar(nombre, texto)
    print(f"\nListo! {len(AUDIOS)} audios en {OUT}/")

asyncio.run(main())
