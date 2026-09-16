"""
Conocimiento base que se inyecta en el system prompt del modelo.

Para añadir, modificar o eliminar una pregunta: edita la lista PREGUNTAS.
Cada entrada es un dict con dos claves:
    - "pregunta":  cómo la formularía un niño.
    - "respuesta": la respuesta corta y cariñosa que el modelo debe dar.

Mantén las respuestas BREVES (1-2 oraciones): se inyectan todas en el system
prompt y un set largo revienta el contexto de modelos pequeños (p. ej. mistral
con num_ctx=2048).
"""

PREGUNTAS = [

    # ── COMIDA ────────────────────────────────────────────────────────────
    {
        "pregunta": "¿Qué es la arepa?",
        "respuesta": (
            "Un pancito redondo de harina de maíz que se rellena con queso, "
            "carne o caraotas. Es el alimento favorito de Venezuela: se comen "
            "millones cada día."
        ),
    },
    {
        "pregunta": "¿Qué es el pabellón criollo?",
        "respuesta": (
            "El plato más famoso de Venezuela: carne mechada, caraotas negras, "
            "arroz blanco y tajadas de plátano maduro, todo en el mismo plato."
        ),
    },
    {
        "pregunta": "¿Qué es la hallaca?",
        "respuesta": (
            "El plato navideño más especial de Venezuela: masa de maíz rellena "
            "de guiso de carne envuelta en hoja de plátano y cocinada al vapor. "
            "Toda la familia la prepara junta en Navidad."
        ),
    },
    {
        "pregunta": "¿Qué es el tequeño?",
        "respuesta": (
            "Un palito de masa frita relleno de queso derretido. "
            "Es el pasapalo más querido de Venezuela y en ninguna fiesta puede faltar."
        ),
    },
    {
        "pregunta": "¿Qué es la cachapa?",
        "respuesta": (
            "Una tortilla dulce hecha de maíz tierno. "
            "Se come con queso de mano o mantequilla y es típica de los llanos venezolanos."
        ),
    },
    {
        "pregunta": "¿Qué es el papelón con limón?",
        "respuesta": (
            "La bebida más refrescante de Venezuela: papelón (azúcar de caña sin "
            "refinar) disuelto en agua con jugo de limón. Perfecta para el calor."
        ),
    },
    {
        "pregunta": "¿Qué es la chicha venezolana?",
        "respuesta": (
            "Una bebida cremosa de arroz con leche, azúcar y canela. "
            "No tiene alcohol y es muy popular en fiestas y mercados."
        ),
    },

    # ── NATURALEZA ────────────────────────────────────────────────────────
    {
        "pregunta": "¿Qué es el Salto Ángel?",
        "respuesta": (
            "La cascada más alta del mundo, casi 1 km de caída, en el parque "
            "Canaima. Los indígenas pemones la llaman Kerepakupai Merú."
        ),
    },
    {
        "pregunta": "¿Qué son los tepuyes?",
        "respuesta": (
            "Montañas planas gigantes del sur de Venezuela que parecen mesas. "
            "El más famoso es el Roraima y tienen plantas que no existen en ningún "
            "otro lugar del planeta."
        ),
    },
    {
        "pregunta": "¿Qué es la Gran Sabana?",
        "respuesta": (
            "Una enorme llanura llena de tepuyes, ríos cristalinos y cascadas "
            "en el sur de Venezuela. Forma parte del Parque Nacional Canaima."
        ),
    },
    {
        "pregunta": "¿Qué son los llanos venezolanos?",
        "respuesta": (
            "Una gran planicie en el centro de Venezuela donde viven los llaneros "
            "con sus hatos de vacas. Tienen animales salvajes como chigüires, "
            "caimanes y toninas de río."
        ),
    },
    {
        "pregunta": "¿Qué es el chigüire?",
        "respuesta": (
            "El roedor más grande del mundo, vive en Venezuela y parece un cerdo "
            "que nada muy bien. Los llaneros lo llaman el rey del llano."
        ),
    },
    {
        "pregunta": "¿Qué es el lago de Maracaibo?",
        "respuesta": (
            "El lago más grande de Venezuela y uno de los más antiguos del mundo. "
            "Tiene el Relámpago del Catatumbo: un show de rayos naturales que "
            "aparece casi todas las noches."
        ),
    },
    {
        "pregunta": "¿Qué animales hay en Venezuela?",
        "respuesta": (
            "Venezuela tiene jaguares, anacondas, delfines rosados de río, "
            "flamencos, loros, caimanes y el oso frontino. "
            "Es uno de los países con más biodiversidad del planeta."
        ),
    },

    # ── CULTURA Y DEPORTE ─────────────────────────────────────────────────
    {
        "pregunta": "¿Qué es el joropo?",
        "respuesta": (
            "La música y baile nacional de Venezuela, declarada Patrimonio de la "
            "Humanidad. Se toca con arpa, cuatro y maracas, y los llaneros "
            "zapan rapidísimo."
        ),
    },
    {
        "pregunta": "¿Qué es la gaita zuliana?",
        "respuesta": (
            "La música típica del estado Zulia que suena en Navidad. "
            "Tiene tambores, furrucos y maracas y cuando la escuchas "
            "¡es imposible no bailar!"
        ),
    },
    {
        "pregunta": "¿Qué es el béisbol en Venezuela?",
        "respuesta": (
            "El deporte más amado de Venezuela. Los venezolanos son tan buenos "
            "que muchos juegan en las Grandes Ligas de EE. UU., "
            "como el campeón Miguel Cabrera."
        ),
    },
    {
        "pregunta": "¿Cómo se celebra el carnaval en Venezuela?",
        "respuesta": (
            "Con comparsas de disfrazados, música, baile y mucho color. "
            "El Carnaval de El Callao, en el estado Bolívar, es Patrimonio de "
            "la Humanidad por sus tradiciones afrovenezolanas únicas."
        ),
    },

    # ── HISTORIA ──────────────────────────────────────────────────────────
    {
        "pregunta": "¿Quién fue Simón Bolívar?",
        "respuesta": (
            "El Libertador de Venezuela, nació en Caracas y ayudó a independizar "
            "cinco países: Venezuela, Colombia, Ecuador, Perú y Bolivia."
        ),
    },
    {
        "pregunta": "¿Cuándo se independizó Venezuela?",
        "respuesta": (
            "El 5 de julio de 1811, Venezuela declaró su independencia de España, "
            "siendo uno de los primeros países de América del Sur en hacerlo. "
            "Simón Bolívar y Francisco de Miranda fueron sus grandes héroes."
        ),
    },

    # ── LUGARES ───────────────────────────────────────────────────────────
    {
        "pregunta": "¿Cuál es la capital de Venezuela?",
        "respuesta": (
            "Caracas, una ciudad rodeada de montañas con clima fresco todo el año. "
            "El Cerro Ávila es la montaña verde que la abraza y se ve desde toda la ciudad."
        ),
    },
    {
        "pregunta": "¿Qué es la isla de Margarita?",
        "respuesta": (
            "La isla más famosa de Venezuela en el mar Caribe, con playas de arena "
            "blanca y agua azul turquesa. La llaman la Perla del Caribe."
        ),
    },
    {
        "pregunta": "¿Qué es el Delta del Orinoco?",
        "respuesta": (
            "Un laberinto de ríos y selva en el oriente de Venezuela donde viven "
            "los indígenas warao en palafitos (casas sobre el agua). "
            "El río Orinoco es el segundo más largo de América del Sur."
        ),
    },

    # ── NAVIDAD ───────────────────────────────────────────────────────────
    {
        "pregunta": "¿Cómo se celebra la Navidad en Venezuela?",
        "respuesta": (
            "Con gaitas, hallacas, pernil y mucho sabor familiar. "
            "Las familias se reúnen desde noviembre a hacer hallacas juntos "
            "y escuchar gaitas hasta enero."
        ),
    },
]


def bloque_conocimiento() -> str:
    """Renderiza las preguntas a un bloque de texto para el system prompt."""
    lineas = ["Estas son preguntas frecuentes y cómo debes responderlas:"]
    for i, qa in enumerate(PREGUNTAS, 1):
        lineas.append(f"{i}. Si preguntan «{qa['pregunta']}» → {qa['respuesta']}")
    return "\n".join(lineas)
