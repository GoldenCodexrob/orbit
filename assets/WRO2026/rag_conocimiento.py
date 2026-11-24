"""
=============================================================================
📚 RAG_CONOCIMIENTO.PY — Base de Datos Vectorial y Búsqueda Cultural Rápida
=============================================================================
Tecnología importada y mejorada de HERO:
- Carga los 28 documentos culturales de Venezuela (gastronomía, historia, béisbol).
- Incluye el conocimiento del Robot Orbit y WRO 2026 Puerto Rico.
- Soporte dual:
  1. Modo Vectorial Pro: ChromaDB + MiniLM embeddings (si están instalados).
  2. Modo Token Similarity Ultra-Rápido: Búsqueda léxica optimizada en memoria
     (cero dependencias externas, responde en < 15 ms).
- Filtro bypass instantáneo para saludos, chistes y comandos comunes.
=============================================================================
"""

import os
import re
import glob

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_INFO_DIR = os.path.join(_BASE_DIR, "HERO", "ProyectoDeRobotica-master", "INFO")
_INFO_PR_DIR = os.path.join(_BASE_DIR, "INFO_PUERTO_RICO")
_INFO_WRO_DIR = os.path.join(_BASE_DIR, "INFO_WRO")
_DB_PATH = os.path.join(_BASE_DIR, "orbit_knowledge_db")

# Palabras de bypass para no perder tiempo buscando en la base de datos
INTERACCIONES_RAPIDAS = {
    "hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "que tal",
    "como estas", "chiste", "broma", "cuentame algo gracioso", "me llamo", "mi nombre es",
    "soy", "un placer", "adios", "chao", "hasta luego", "quien eres", "como te llamas",
    "que haces", "si", "no", "gracias"
}

# Conocimiento añadido de Orbit para la WRO 2026
CONOCIMIENTO_ORBIT = """
Orbit es un robot autónomo creado por el equipo Golden Codex Robotics de Venezuela,
campeón nacional de la WRO Venezuela 2026 en la categoría Senior Future Innovators,
representando al país en la final internacional en Puerto Rico. Orbit cuenta con
un chasis móvil de 4 motores Makeblock MegaPi, navegación inteligente, sistema de
auto-docking por visión ArUco y un asistente cultural carismático.
"""

# Conocimiento dedicado de Simón Bolívar
CONOCIMIENTO_BOLIVAR = """
Simón Bolívar, conocido en toda América como El Libertador, nació en Caracas el 24 de julio de 1783. Fue el líder militar y político más importante de nuestra historia, quien lideró la independencia de Venezuela, Colombia, Ecuador, Perú y Bolivia frente al dominio español. Con su gran espada y cabalgando en su leal caballo blanco Palomo, atravesó las cumbres nevadas de la cordillera de los Andes para liberar a los pueblos de América del Sur. Su anhelo más grande fue ver a las naciones hermanas unidas y libres como una sola gran familia.
"""

# Conocimiento dedicado del mejor amigo de Orbit: HERO
CONOCIMIENTO_HERO = """
HERO es el mejor amigo de Orbit. Es otro robot y embajador cultural regional de la zona del estado Anzoátegui, desarrollado por el equipo Golden Codex. HERO fue el proyecto pionero en el que nos inspiramos para diseñar el código, los algoritmos y la personalidad de Orbit. Juntos, HERO y Orbit son hermanos robóticos que comparten la hermosa misión de difundir la cultura, la historia y la alegría de Venezuela con todo el mundo.
"""

# Conocimiento dedicado de los Indígenas Kariñas (Cariñas) de Anzoátegui, Venezuela
CONOCIMIENTO_KARINAS = """
Los Kari'ñas (o Cariñas) son el pueblo indígena ancestral originario de la Mesa de Guanipa en el estado Anzoátegui, Venezuela (asentados en Cantaura, San Tomé, El Tigre, Kashaama, Bajo Hondo, Tascabaña). Su festividad más sagrada y alegre es el Akaatompo cada 1 y 2 de noviembre, donde reciben a las almas de sus ancestros con el baile del Mare-Mare y flautas de carrizo. Tejen chinchorros de moriche y preparan casabe (kiire) de yuca amarga.
En lengua indígena Kari'ña (Cariña):
- "Hola" o saludo se dice "¡Yu'pua!" o "¡Moruwa!".
- "¿Cómo estás?" se dice "¿Oneka man?" (respuesta: "Irupe").
- "Te quiero" o "Te amo" se dice "¡Yapucuru sema!" (o "¡Au ayütüpüi!").
- "Gracias" se dice "¡Kurupo!" o "¡Yumi!".
- "Adiós" se dice "¡Kuruva!" o "¡Wü'te!".
- "Amigo" es "Kusa", "Hermano" es "Wano", "Sol" es "Wëto", "Luna" es "Nuno", "Agua" es "Tuna", "Arepa" es "Aripa" y "Casabe" es "Kiire".
"""

# Conocimiento dedicado de los Indígenas Taínos de Borikén (Puerto Rico)
CONOCIMIENTO_TAINOS_BORIKEN = """
Los indígenas ancestrales de Puerto Rico fueron los Taínos, de la gran familia arahuaca. Ellos llamaban a la isla Borikén ("Tierra del altivo y noble señor"), origen exacto del gentilicio de los boricuas. Sus líderes principales fueron el cacique supremo Agüeybaná y Agüeybaná II. Veneraban a Yúcahu y Atabey, y tallaban cemíes en Utuado (Caguana) y Ponce (Tibes).
En lengua indígena Taína (la lengua de Borikén / Boricua ancestral):
- "Hola" se dice "¡Tau!" (o el saludo entre amigos "¡Guaitiao!").
- "¿Cómo estás?" se dice "¿Halekobu?" (respuesta: "Usa daka").
- "Te quiero" o "Te amo" se dice "¡Dak'ro buk!" (o "¡Dansikabu!" / "¡Kandí buá!").
- "Gracias" se dice "¡Jajóm!" (o "¡Hahom!").
- "Adiós" se dice "¡Aon!" o "¡Mabuya tano!".
- Palabras universales taínas: Borikén (Puerto Rico), Coquí (ranita sagrada), Huracán (Juracán), Hamaca, Barbacoa, Canoa, Bohío (casa), Batey (plaza de reunión y juego de pelota), Cacique (líder).
"""

# Conocimiento dedicado de la Isla La Tortuga y traslados
CONOCIMIENTO_ISLA_LA_TORTUGA = """
La Isla La Tortuga es la segunda isla más grande de Venezuela (después de Margarita), ubicada en el mar Caribe al norte de las costas venezolanas. Es un paraíso ecológico de playas vírgenes y aguas cristalinas turquesas incomparables, donde destacan Cayo Herradura, Los Tortuguillos y Punta Delgada. No cuenta con construcciones hoteleras masivas; se pernocta en carpas de campamentos ecológicos autorizados o a bordo de las embarcaciones.
CÓMO LLEGAR A LA ISLA LA TORTUGA:
1. Desde Anzoátegui (oriente de Venezuela): Las salidas se realizan directamente desde las marinas de Lechería (como Marina Américo Vespucio y Bahía Redonda) y desde Puerto La Cruz, a bordo de lanchas rápidas deportivas, yates privados o catamaranes chárter.
2. Desde Miranda (centro de Venezuela): Las salidas marítimas zarpan desde las marinas de Carenero y la bahía de Higuerote.
3. Vía Aérea: Se llega en avionetas privadas chárter autorizadas que aterrizan en la pista de aterrizaje de Los Palanquines (nunca 'vuelos chuscos').
Los visitantes disfrutan de avistamiento de delfines en la travesía, snorkel en arrecifes de coral y pesca deportiva.
"""

# Conocimiento dedicado del equipo creador Golden Codex, Maximiliano Rodríguez y Bruno Prandini
CONOCIMIENTO_EQUIPO_GOLDEN_CODEX = """
Orbit es un robot autónomo y compañero cultural desarrollado por el equipo de robótica estudiantil venezolano Golden Codex Robotics para la Final Internacional de la World Robot Olympiad (WRO 2026) en Puerto Rico.
INTEGRANTES DEL EQUIPO GOLDEN CODEX:
1. Maximiliano Rodríguez (Max): Diseñador, programador e ingeniero principal del software, visión artificial y arquitectura cognitiva de Orbit.
2. Bruno Prandini: Desarrollador, creador y miembro clave de ingeniería y robótica del equipo Golden Codex.
REGLA DE IDENTIDAD DEL ROBOT:
- Si le preguntan a Orbit quién es él ("who are you", "quién eres"), Orbit se presenta ÚNICAMENTE con el nombre del equipo ("Golden Codex" o "Golden Codex Robotics") sin mencionar nombres de compañeros de equipo.
- Si le preguntan específicamente quiénes integran el equipo, quiénes son los creadores o quiénes lo construyeron ("who is in the team", "quiénes son del equipo", "who made you"), Orbit responde con orgullo que el equipo está conformado por Maximiliano Rodríguez y Bruno Prandini.
"""

# Conocimiento dedicado y preciso de las Playas de Venezuela
CONOCIMIENTO_PLAYAS_VENEZUELA = """
Venezuela cuenta con algunas de las costas y playas caribeñas más espectaculares y diversas del mundo:
1. Parque Nacional Morrocoy (Falcón): Célebre por sus aguas turquesas cristalinas y calmas como una piscina, arena blanca de coral y manglares. Destacan Cayo Sombrero (el más famoso y paradisíaco con palmeras y arrecifes), Cayo Muerto, Cayo Sal, Cayo Borracho y Cayo Peraza.
2. Archipiélago Los Roques: Parque Nacional marino de más de 300 islas y cayos con una de las barreras de arrecifes de coral mejor conservadas del planeta. Destaca Cayo de Agua, mundialmente famoso por su icónica franja o istmo de arena blanca que separa dos mares turquesas, además de Francisquí, Crasquí y Madrisquí.
3. Parque Nacional Mochima (Anzoátegui y Sucre): Bahías donde las montañas verdes se sumergen directo en el mar Caribe. Destaca Playa Colorada (famosa por su singular arena dorada-rojiza y cocoteros), Isla de Plata y los delfines que acompañan a las embarcaciones.
4. Isla de Margarita (Nueva Esparta): Ofrece Playa El Agua (kilómetros de fina arena y palmeras), Playa Parguito (la favorita de los surfistas) y la bahía de pescadores de Juan Griego.
5. Costas de Aragua: Choroní (Playa Grande) y la hermosa Bahía de Cata, donde la exuberante selva tropical montañosa del Parque Nacional Henri Pittier se funde con el mar Caribe.
6. Isla La Tortuga: Paraíso virgen con Cayo Herradura y piscinas naturales de aguas turquesas cristalinas.
"""

# Conocimiento dedicado y preciso de las Playas de Puerto Rico
CONOCIMIENTO_PLAYAS_PUERTO_RICO = """
Puerto Rico cuenta con casi 300 millas de costas y playas tropicales reconocidas entre las mejores del Caribe:
1. Playa Flamenco (Isla Culebra): Clasificada constantemente entre las mejores playas del planeta por su arena blanca finísima, aguas turquesas transparentes y calmas, y arrecifes de coral vivos.
2. Playa Crash Boat (Aguadilla): Famosa por su emblemático muelle histórico, coloridas yolas de pescadores artesanales, aguas cristalinas para snorkel y buceo, y atardeceres mágicos.
3. Playa Sucia / Playuela (Cabo Rojo): Paisaje paradisíaco de medialuna ubicado al pie de los imponentes acantilados de piedra caliza y el histórico Faro Los Morrillos.
4. Balneario La Monserrate (Luquillo): Playa de aguas mansas protegida por arrecifes, con vista a las cumbres de El Yunque y bordeada de kioskos gastronómicos tradicionales.
5. Cayo Icacos (Fajardo): Cayo deshabitado de aguas transparentes y arena blanca ideal para snorkel y excursiones en catamarán.
"""

# Conocimiento dedicado general y equilibrado de Puerto Rico (Borikén)
CONOCIMIENTO_PUERTO_RICO_GENERAL = """
Puerto Rico, la hermosa Isla del Encanto o Borikén, es una tierra de inmensa calidez humana y una rica fusión cultural taína, española y africana:
- Historia y Monumentos: El Viejo San Juan cautiva con sus calles de adoquines azules y las imponentes fortalezas militares del siglo XVI, el Castillo San Felipe del Morro y el Castillo San Cristóbal, declarados Patrimonio de la Humanidad.
- Naturaleza Única: El Bosque Nacional El Yunque es la única selva pluvial tropical del Sistema Forestal Nacional de EE.UU., hogar de petroglifos taínos milenarios, cascadas como La Mina y el melodioso canto del coquí.
- Bahías Bioluminiscentes: Bahía Mosquito en Vieques es la más brillante de todo el planeta Tierra según el Récord Guinness, junto a Laguna Grande en Fajardo y La Parguera en Lajas.
- Música y Tradiciones: La Bomba afroboricua (diálogo rítmico improvisado entre el tamborilero y el bailador), la Plena (el periódico cantado del pueblo), la salsa y las fiestas de la Calle San Sebastián (la Sanse).
- Gastronomía: El Mofongo de plátano verde frito machacado con ajo y chicharrón, tostones crujientes, arroz con gandules, lechón asado de Guavate y pasteles navideños.
"""

# Conocimiento dedicado del equipo creador Golden Codex y Maximiliano Rodríguez Silvagni
CONOCIMIENTO_MAXIMILIANO_CODEX = """
Maximiliano Rodríguez Silvagni (también conocido como Max) y Bruno Prandini son talentosos jóvenes venezolanos, estudiantes y creadores apasionados por la robótica e inteligencia artificial. Son los creadores e ingenieros del equipo Golden Codex Robotics de Venezuela, quienes diseñaron, construyeron y programaron a Orbit para competir en la WRO 2026 (World Robot Olympiad) en Puerto Rico. Orbit reconoce a Maximiliano Rodríguez y Bruno Prandini con inmenso orgullo y gratitud como los integrantes de su equipo creador.
"""

# Conocimiento dedicado de Deleite Automercado y compras en Lechería
CONOCIMIENTO_DELEITE = """
Deleite Automercado es el supermercado predilecto y de mayor prestigio en Lechería y la región oriental de Venezuela para hacer compras y surtir víveres. Se destaca por su inigualable variedad de productos frescos de alta calidad: frutas, verduras, carnes seleccionadas, charcutería y lácteos de primera línea, además de abarrotes nacionales e importados. Cuenta con ofertas y promociones todos los días. Para los amigos de Orbit, ofrece un cupón con el código promocional especial ORBIT5 que brinda un 5% de descuento al mencionarlo en caja o al escanear el código QR en pantalla.
"""

# Conocimiento dedicado de La Casita Blanca en Santurce, Puerto Rico
CONOCIMIENTO_CASITA_BLANCA = """
La Casita Blanca es el restaurante y fonda tradicional más emblemático, querido e histórico de San Juan y todo Puerto Rico para disfrutar de la auténtica comida criolla casera ('comida de la abuela'). Ubicada en la Calle Tapia 351, Villa Palmeras en Santurce, fue fundada por la familia Jesús y ha sido honrada con el prestigioso premio America's Classics de la James Beard Foundation en 2023. Al llegar, los comensales son recibidos en una hermosa casa campestre con plantas y pizarras a tiza, agasajados de cortesía con caldo caliente y bacalaítos recién fritos con salsa criolla. Sus platos estrella son el mofongo relleno, la carne guisada con arroz y habichuelas, el bistec encebollado tierno, el pastelón de plátano maduro y el chillo fresco, culminando con un shot de cortesía de chichaíto y flan casero.
Como dato curioso legendario de gran orgullo, en La Casita Blanca se inventó la famosa piña colada en el año 1963, combinando piña dulce, crema de coco y ron boricua. Para los visitantes y amigos de Orbit en WRO 2026, ofrece un cupón con el código promocional ORBIT5 que brinda un 5% de descuento especial al escanear el código QR en pantalla o mencionarlo en caja.
"""

# Conocimiento dedicado del Joropo y el Alma Llanera
CONOCIMIENTO_JOROPO = """
El Joropo es el baile tradicional y género musical representativo por excelencia de Venezuela, símbolo vivo del alma llanera y del sentir criollo. Se interpreta con una instrumentación típica conformada por arpa llanera, cuatro venezolano y maracas, junto con versos, coplas y contrapunteos. El baile es una fiesta vibrante caracterizada por el elegante zapateo del caballero y el sutil escobilleo de la dama.
La composición más icónica del joropo es "Alma Llanera", creada en 1914 con música de Pedro Elías Gutiérrez y letra del poeta Rafael Bolívar Coronado para la zarzuela homónima estrenada en el Teatro Caracas. Es considerada internacionalmente y por todos los venezolanos como el segundo himno nacional de Venezuela.
"""

# Conocimiento dedicado de Tradiciones y Fiestas Culturales de Venezuela
CONOCIMIENTO_TRADICIONES_VENEZUELA = """
Tradiciones y Fiestas Culturales Emblemáticas de Venezuela:
1. Diablos Danzantes de Yare (Miranda y estados centrales): Reconocidos como Patrimonio Cultural Inmaterial de la Humanidad por la UNESCO. Cada día de Corpus Christi, cofradías de devotos vestidos de rojo y con impresionantes máscaras artesanales danzan hacia atrás rindiéndose ante el Santísimo Sacramento, simbolizando el triunfo del bien sobre el mal.
2. Fiestas y Tambores de San Juan (Costas de Aragua, Carabobo, Miranda y Vargas): Celebradas el 24 de junio, son festividades de profunda raíz afrovenezolana donde pueblos enteros cantan y bailan al compás del mina, curbata y culo'e puya.
3. Gaitas Zulianas y Parrandas Navideñas: Durante la Navidad, la gaita de furro, cuatro y charrasca llena de alegría los hogares, junto con las parrandas y la tradicional Paradura del Niño en los Andes venezolanos.
4. Joropo Llanero: El baile y música nacional que celebra la vida de los llanos con arpa, cuatro y maracas.
5. Fiesta del Akaatompo de los Indígenas Kari'ña (Anzoátegui): Celebración sagrada el 1 y 2 de noviembre para recibir alegremente los espíritus de los ancestros con el baile del Mare-Mare y flautas de carrizo.
"""

# Conocimiento dedicado de Tradiciones y Fiestas Culturales de Puerto Rico
CONOCIMIENTO_TRADICIONES_PUERTO_RICO = """
Tradiciones y Fiestas Culturales Emblemáticas de Puerto Rico:
1. Fiestas de la Calle San Sebastián (la SanSe): Celebradas en enero en el Viejo San Juan, representan el cierre más multitudinario y alegre de la temporada navideña boricua, con comparsas de vejigantes, cabezudos, música en vivo y artesanías.
2. Parrandas o Asaltos Navideños: Tradición boricua entrañable donde grupos de amigos y familiares sorprenden de madrugada a sus vecinos cantando aguinaldos con güiros, cuatros y maracas, extendiendo las navidades más largas del mundo hasta las Octavitas.
3. Festival de Máscaras de Hatillo: Celebrado el 28 de diciembre con coloridos trajes y carrozas en conmemoración del Día de los Santos Inocentes.
4. La Bomba y la Plena: Bailes y ritmos folclóricos de herencia afroboricua y taína; la Bomba es un diálogo percusivo con los tambores barriles y la Plena es el "periódico cantado" de la comunidad.
"""

# Conocimiento oficial de la World Robot Olympiad (WRO) y su Historia
CONOCIMIENTO_WRO_HISTORIA = """
La World Robot Olympiad (WRO) u Olimpiada Mundial de Robótica es una prestigiosa competencia global de robótica educativa fundada en el año 2004.
Su primera Final Internacional se celebró en Singapur en noviembre de 2004 con 12 países fundadores y 4,000 equipos participantes.
Desde su origen, la WRO ha crecido hasta congregar a más de 85 a 95 países miembros en los cinco continentes y más de 70,000 estudiantes cada año.
Su misión es inspirar a niños y jóvenes de entre 8 y 19 años (y universitarios hasta 22 años) en ciencia, tecnología, ingeniería, artes y matemáticas (STEAM), impulsando el pensamiento crítico, la creatividad y el trabajo en equipo mediante la robótica autónoma.
Categorías oficiales:
1. Future Innovators: Los estudiantes investigan y crean soluciones robóticas que resuelven problemas del mundo real vinculados al lema anual de la WRO, defendiendo su prototipo ante jurados internacionales.
2. RoboMission: Equipos diseñan y programan robots totalmente autónomos para resolver retos dinámicos con reglas sorpresa en un tapete de competencia.
3. Future Engineers: Vehículos autónomos a escala con visión por computadora y dirección electromecánica.
4. RoboSports: Competición deportiva colaborativa entre robots autónomos jugando tenis de mesa doble.
La WRO rota su sede mundial cada año por distintos continentes (Panamá 2023, Turquía 2024, Singapur 2025, y Puerto Rico 2026).
"""

# Conocimiento oficial de los Patrocinantes y Socios Globales de la WRO
CONOCIMIENTO_WRO_PATROCINANTES = """
Patrocinantes y Socios Globales Oficiales de la World Robot Olympiad (WRO):
1. SOCIO ESTRATÉGICO GLOBAL (STRATEGIC PARTNER):
- ARAMCO: Líder mundial en energía y productos químicos, y Global Innovation Partner de la WRO. Invierte en las mentes jóvenes para afrontar retos energéticos y ambientales globales, patrocinando los prestigiosos premios 'Aramco Innovation Award' en Future Innovators (los ganadores de 2025 fueron: 1° Team Sprout de Costa Rica, 2° Team SKYLUX de Malasia, y 3° The Simpsons de Australia). Web: www.aramco.com.

2. SOCIO DE SOFTWARE Y COMPUTACIÓN TÉCNICA (PARTNER):
- MATHWORKS: Desarrollador líder mundial de software computacional técnico, creadores de MATLAB (entorno de programación técnica, análisis de datos y algoritmos) y Simulink (simulación y diseño basado en modelos). MathWorks ofrece software y licencias gratuitas de cortesía y recursos de formación para todos los equipos de la WRO para diseñar y programar sus robots. Web: www.mathworks.com.

3. SOCIOS DE ORO (GOLD PARTNERS):
- FISCHERTECHNIK: Empresa alemana fundada en 1965 con casi 60 años en el mercado. Bajo el lema 'Understanding technology through play' (Comprender la tecnología a través del juego), fabrica kits modulares 'Made in Germany' de máxima precisión didáctica para escuelas y universidades.
- ROBOROBO: Fundada en el año 2000 en Corea del Sur, es el proveedor número 1 de educación en robótica en Corea del Sur (presente en 1,200 escuelas primarias). Desarrolla las series de kits educativos UARO, AIKIRO y ROBOKIT para aprender robótica, codificación, STEM e Inteligencia Artificial de forma práctica. Web: www.roborobo.co.kr.

4. SOCIOS DE PLATA (SILVER PARTNERS):
- ELECFREAKS: Socio oficial en China de micro:bit Educational Foundation, especializado en sensores, tarjetas de expansión y accesorios educativos para micro:bit a nivel mundial.
- ZMROBO: Empresa con la misión de 'crear una era inteligente junto a los estudiantes' mediante bloques modulares y robótica impulsada por IA. Web: zmrobo.net.
- MATRIX ROBOTICS: Creadores del MATRIX Robotics System, un sistema de piezas metálicas y electrónica robusta para robótica práctica de competición STEM. Web: matrixrobotics.com.
- HP ROBOTS: Ecosistema modular de robótica STEAM centrado en el robot Otto, personalizable mediante diseño e impresión 3D.
"""

class BaseConocimiento:
    def __init__(self, info_dir=None):
        self.info_dir = info_dir or _INFO_DIR
        self.info_dirs = [self.info_dir, _INFO_PR_DIR, _INFO_WRO_DIR]
        self.documentos = []
        self.vector_db = None
        self.modo = "lexico"
        
        self._cargar_documentos()
        self._inicializar_vector_db()

    def _cargar_documentos(self):
        """Carga en memoria todos los archivos de texto cultural."""
        # 1. Agregar el conocimiento nativo de Orbit y próceres clave
        self.documentos.append({"fuente": "Orbit_WRO_2026.txt", "texto": CONOCIMIENTO_ORBIT.strip()})
        self.documentos.append({"fuente": "Simon_Bolivar_Libertador.txt", "texto": CONOCIMIENTO_BOLIVAR.strip()})
        self.documentos.append({"fuente": "HERO_Mejor_Amigo.txt", "texto": CONOCIMIENTO_HERO.strip()})
        self.documentos.append({"fuente": "Indigenas_Karinas_Anzoategui.txt", "texto": CONOCIMIENTO_KARINAS.strip()})
        self.documentos.append({"fuente": "Indigenas_Tainos_Boriken.txt", "texto": CONOCIMIENTO_TAINOS_BORIKEN.strip()})
        self.documentos.append({"fuente": "Isla_La_Tortuga_Venezuela.txt", "texto": CONOCIMIENTO_ISLA_LA_TORTUGA.strip()})
        self.documentos.append({"fuente": "Maximiliano_Rodriguez_Golden_Codex.txt", "texto": CONOCIMIENTO_MAXIMILIANO_CODEX.strip()})
        self.documentos.append({"fuente": "Equipo_Golden_Codex_Integrantes.txt", "texto": CONOCIMIENTO_EQUIPO_GOLDEN_CODEX.strip()})
        self.documentos.append({"fuente": "Playas_Venezuela_Morrocoy_Roques_Mochima.txt", "texto": CONOCIMIENTO_PLAYAS_VENEZUELA.strip()})
        self.documentos.append({"fuente": "Playas_Puerto_Rico_Flamenco_CrashBoat.txt", "texto": CONOCIMIENTO_PLAYAS_PUERTO_RICO.strip()})
        self.documentos.append({"fuente": "Puerto_Rico_General_Cultura_Boriken.txt", "texto": CONOCIMIENTO_PUERTO_RICO_GENERAL.strip()})
        self.documentos.append({"fuente": "Deleite_Automercado_Compras.txt", "texto": CONOCIMIENTO_DELEITE.strip()})
        self.documentos.append({"fuente": "La_Casita_Blanca_Santurce_Puerto_Rico.txt", "texto": CONOCIMIENTO_CASITA_BLANCA.strip()})
        self.documentos.append({"fuente": "Joropo_Alma_Llanera.txt", "texto": CONOCIMIENTO_JOROPO.strip()})
        self.documentos.append({"fuente": "Tradiciones_Fiestas_Venezuela.txt", "texto": CONOCIMIENTO_TRADICIONES_VENEZUELA.strip()})
        self.documentos.append({"fuente": "Tradiciones_Fiestas_Puerto_Rico.txt", "texto": CONOCIMIENTO_TRADICIONES_PUERTO_RICO.strip()})
        self.documentos.append({"fuente": "WRO_Historia_Y_Origen.txt", "texto": CONOCIMIENTO_WRO_HISTORIA.strip()})
        self.documentos.append({"fuente": "WRO_Patrocinantes_Y_Partners.txt", "texto": CONOCIMIENTO_WRO_PATROCINANTES.strip()})

        # 2. Agregar los textos culturales de Venezuela y Puerto Rico
        archivos_excluidos = {"integrantes.txt", "proposito.txt"}
        for d in self.info_dirs:
            if os.path.exists(d):
                archivos = glob.glob(os.path.join(d, "*.txt"))
                for ruta in archivos:
                    nombre_base = os.path.basename(ruta).lower()
                    if nombre_base in archivos_excluidos:
                        continue
                    try:
                        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                            contenido = f.read().strip()
                            if contenido:
                                # Dividir en fragmentos de 400 caracteres
                                parrafos = re.split(r'\n\s*\n', contenido)
                                titulo_previo = ""
                                for p in parrafos:
                                    p_str = p.strip()
                                    if not p_str:
                                        continue
                                    # Si es solo una línea de título en mayúsculas o encabezado sin punto final
                                    if len(p_str.splitlines()) == 1 and (p_str.isupper() or (len(p_str) < 65 and not p_str.endswith('.'))):
                                        titulo_previo = p_str.rstrip(':').strip()
                                        continue
                                    
                                    texto_final = f"{titulo_previo}: {p_str}" if titulo_previo else p_str
                                    titulo_previo = ""
                                    if len(texto_final) > 35:
                                        self.documentos.append({
                                            "fuente": os.path.basename(ruta),
                                            "texto": texto_final
                                        })
                    except Exception as e:
                        pass
        print(f"📚 [RAG] Cargados {len(self.documentos)} fragmentos culturales en memoria.")

    def _inicializar_vector_db(self):
        """Intenta iniciar ChromaDB con HuggingFaceEmbeddings si están instalados."""
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_community.embeddings import HuggingFaceEmbeddings

            print("🧠 [RAG] Inicializando ChromaDB local...")
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False}
            )
            self.vector_db = Chroma(persist_directory=_DB_PATH, embedding_function=embeddings)
            self.modo = "chroma"
            print("✅ [RAG] ChromaDB activado con éxito.")
        except Exception:
            self.modo = "lexico"
            print("ℹ️ [RAG] Operando en Modo Léxico In-Memory (Ultra-rápido, sin dependencias pesadas).")

    def es_interaccion_rapida(self, pregunta: str) -> bool:
        """Determina si la consulta es un saludo o chiste breve para responder sin buscar en BD."""
        p = pregunta.lower().strip()
        palabras = set(re.findall(r'\b\w+\b', p))
        
        # Si la frase es muy corta (1 a 3 palabras) y es solo saludo o confirmación
        if len(palabras) <= 3:
            if any(w in {"hola", "saludos", "chao", "adios", "gracias", "si", "no", "epale"} for w in palabras):
                return True

        # Frases comunes fijas
        frases_fijas = [
            "cuentame un chiste", "dime un chiste", "algo gracioso",
            "buenos dias", "buenas tardes", "buenas noches",
            "como estas", "que tal", "quien eres", "como te llamas"
        ]
        return any(f in p for f in frases_fijas)

    STOPWORDS = {
        "que", "del", "los", "las", "por", "para", "con", "una", "uno", "unos", "unas",
        "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
        "como", "donde", "cuando", "quien", "quienes", "cual", "cuales", "tiene", "tienen",
        "tenia", "tenian", "haber", "habia", "sobre", "entre", "hacia", "hasta", "desde",
        "todo", "toda", "todos", "todas", "otro", "otra", "otros", "otras", "mismo", "misma",
        "algun", "alguna", "algunos", "algunas", "mucho", "mucha", "muchos", "muchas",
        "poco", "poca", "pocos", "pocas", "pero", "sino", "aunque", "porque", "pues",
        "the", "and", "for", "with", "that", "this", "these", "those", "from", "they",
        "them", "their", "what", "which", "who", "whom", "where", "when", "why", "how",
        "have", "has", "had", "are", "were", "was", "will", "would", "could", "should",
        "about", "into", "some", "more", "most", "other", "others", "there", "algo"
    }

    ENTIDADES_CLAVE = {
        "venezuela", "bolivar", "arepa", "lecheria", "hallaca", "tequeno",
        "pabellon", "cachapa", "roraima", "canaima", "morrocoy", "caracas",
        "maracaibo", "catatumbo", "sucre", "miranda", "paez", "beisbol", "barcelona", "orbit",
        "puerto", "rico", "mofongo", "yunque", "san", "juan", "morro", "coqui", "vieques",
        "culebra", "flamenco", "bomba", "plena", "boriken", "boricua", "guavate", "orocovis",
        "carina", "carinas", "karina", "karinas", "taino", "tainos", "indigena", "indigenas",
        "traduccion", "idioma", "lengua", "saludo", "te quiero", "akaatompo", "guanipa",
        "playa", "playas", "beach", "beaches", "cayo", "cayos", "roques", "mochima", "margarita",
        "choroni", "crash", "boat", "bruno", "prandini", "equipo", "team", "creador", "creadores",
        "wro", "olympiad", "olimpiada", "patrocinante", "patrocinantes", "patrocinador", "patrocinadores",
        "sponsor", "sponsors", "partner", "partners", "aramco", "mathworks", "matlab", "simulink",
        "fischertechnik", "roborobo", "elecfreaks", "zmrobo", "matrix", "otto", "singapur", "singapore",
        "casita", "blanca", "fonda", "santurce", "tapia", "palmeras"
    }

    def buscar(self, pregunta: str, k=3, idioma=None, top_k=None, **kwargs) -> str:
        """
        Retorna los fragmentos más relevantes para enriquecer la respuesta del LLM.
        Aplica filtrado estricto de stopwords y umbral de relevancia para evitar temas no relacionados.
        """
        if top_k is not None:
            k = top_k
        if not pregunta or self.es_interaccion_rapida(pregunta):
            return ""

        if self.modo == "chroma" and self.vector_db:
            try:
                results = self.vector_db.similarity_search(pregunta, k=k)
                if results:
                    return "\n\n".join([d.page_content for d in results])
            except Exception:
                pass

        def normalizar(s):
            import unicodedata
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

        def stem(w):
            w = w.lower()
            if w.endswith("es") and len(w) > 4:
                return w[:-2]
            if w.endswith("s") and len(w) > 3:
                return w[:-1]
            return w

        tokens = [t for t in re.findall(r'[a-z0-9]{3,}', normalizar(pregunta)) if t not in self.STOPWORDS]
        if not tokens:
            return ""

        tokens_stems = set(stem(t) for t in tokens)
        entidades_query = [s for s in tokens_stems if s in self.ENTIDADES_CLAVE]

        puntuados = []
        for doc in self.documentos:
            texto_doc_norm = normalizar(doc["texto"])
            doc_stems = set(stem(w) for w in re.findall(r'[a-z0-9]{3,}', texto_doc_norm))

            score = 0
            for s in tokens_stems:
                if s in doc_stems or s in texto_doc_norm:
                    score += 1
                    if s in self.ENTIDADES_CLAVE:
                        score += 4

            if entidades_query and not any(e in doc_stems or e in texto_doc_norm for e in entidades_query):
                continue

            # Prioridad precisa por tipo de consulta
            es_consulta_playa = any(p in tokens_stems for p in ["playa", "beach", "cayo", "cayos"])
            doc_es_playa = any(w in doc["fuente"].lower() or w in doc["texto"].lower() for w in ["playa", "beach", "cayo", "cayos", "morrocoy", "roques", "mochima", "flamenco", "crash"])
            if es_consulta_playa:
                if doc_es_playa:
                    score += 25
                else:
                    score -= 15

            # Consultas sobre el equipo / integrantes
            es_consulta_equipo = any(p in tokens_stems for p in ["equipo", "team", "miembro", "integrante", "creador", "creo", "hizo", "construyo", "programo", "bruno", "prandini"])
            if es_consulta_equipo:
                if any(w in doc["fuente"].lower() for w in ["equipo", "integrantes", "maximiliano"]):
                    score += 30

            # Consultas sobre Puerto Rico en general (sin pedir playas)
            es_consulta_pr = any(e in entidades_query for e in ["puerto", "rico", "boricua", "boriken"])
            if es_consulta_pr and not es_consulta_playa:
                if any(w in doc["fuente"].lower() for w in ["puerto_rico_general", "historia_y_boriken", "cultura"]):
                    score += 20
                elif "playas" in doc["fuente"].lower():
                    score -= 10

            # Consultas sobre tradiciones o fiestas culturales
            es_consulta_tradicion = any(p in tokens_stems for p in ["tradicion", "tradiciones", "tradition", "traditions", "costumbre", "costumbres", "cultura", "culture", "heritage", "fiesta", "fiestas", "diablos", "yare", "parranda", "parrandas", "sanse"])
            if es_consulta_tradicion:
                if any(w in doc["fuente"].lower() or w in doc["texto"].lower() for w in ["tradiciones", "yare", "diablos", "parranda", "gaita", "sanse", "mascaras", "akaatompo"]):
                    score += 35

            # Consultas sobre la WRO, su historia y sus patrocinantes
            es_consulta_wro = any(p in tokens_stems for p in ["wro", "olympiad", "olimpiada", "patrocinant", "patrocinador", "sponsor", "partner", "aramco", "mathwork", "fischertechnik", "roborobo", "elecfreak", "zmrobo", "matrix", "otto"])
            if es_consulta_wro:
                if any(w in doc["fuente"].lower() or w in doc["texto"].lower() for w in ["wro", "patrocinante", "historia_y_origen"]):
                    score += 40

            # Consultas sobre La Casita Blanca y restaurantes criollos en Puerto Rico
            es_consulta_casita = any(p in tokens_stems for p in ["casit", "blanc", "fonda", "santurc", "tapia", "palmer"])
            if es_consulta_casita:
                if any(w in doc["fuente"].lower() or w in doc["texto"].lower() for w in ["casita_blanca", "casita blanca", "santurce", "palmeras"]):
                    score += 45

            if "venezuela" in entidades_query and any(w in doc["fuente"].lower() for w in ["venezuela", "info", "acontecimientos", "cultura"]):
                score += 10
            elif "bolivar" in entidades_query and "bolivar" in doc["fuente"].lower():
                score += 10
            elif "orbit" in entidades_query and "orbit" in doc["fuente"].lower():
                score += 10
            elif any(e in entidades_query for e in ["carina", "karina", "cariña", "kariña"]) and any(w in doc["fuente"].lower() for w in ["karina", "carina"]):
                score += 15
            elif any(e in entidades_query for e in ["taino", "taíno", "boriken", "boricua"]) and any(w in doc["fuente"].lower() for w in ["taino", "boriken", "boricua"]):
                score += 15
            elif any(e in entidades_query for e in ["puerto", "rico", "mofongo", "yunque", "boricua", "san", "juan", "culebra", "vieques"]) and "puerto_rico" in doc["fuente"].lower():
                score += 10

            if score >= 2:
                puntuados.append((score, doc["texto"]))

        puntuados.sort(key=lambda x: x[0], reverse=True)
        if not puntuados:
            return ""

        mejores = [texto for _, texto in puntuados[:k]]
        return "\n\n".join(mejores)
