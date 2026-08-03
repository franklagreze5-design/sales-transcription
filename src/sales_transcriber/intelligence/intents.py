"""intents.py"""


#
# Intent: Pricing
# Cliente preguntando por precio
#

PRICING_KEYWORDS = [

    "precio",

    "cuánto cuesta",
    "cuanto cuesta",

    "cuánto vale",
    "cuanto vale",

    "planes",

    "mensualmente",

    "tarifa",

    "costo",

    "costos",

]



#
# Intent: Implementation
# Cliente preguntando cómo funciona
#

IMPLEMENTATION_KEYWORDS = [

    "implementación",
    "implementacion",

    "instalación",
    "instalacion",

    "integración",
    "integracion",

    "configuración",
    "configuracion",

    "tiempo de implementación",

    "cuánto demora",
    "cuanto demora",

    "cómo se implementa",
    "como se implementa",

]



#
# Intent: Interest
# Interés explícito
#

INTEREST_KEYWORDS = [

    "me interesa",

    "interesante",

    "quiero saber más",
    "quiero saber mas",

    "cuéntame más",
    "cuentame mas",

    "nos interesa",

    "queremos conocer",

    "queremos avanzar",

    "quiero avanzar",

    "podemos comenzar",

]



#
# Intent: Discovery / Pain
# Cliente explicando problema
#

PAIN_KEYWORDS = [

    "problema",

    "problemas",

    "dificultad",

    "dificultades",

    "nos cuesta",

    "tenemos problemas",

    "queremos mejorar",

    "necesitamos mejorar",

    "actualmente tenemos",

    "estamos buscando una solución",

    "estamos buscando una solucion",

]



#
# Intent: Evaluation
# Cliente explorando alternativas.
#
# IMPORTANTE:
# Esto NO es objeción.
#

EVALUATION_KEYWORDS = [

    "evaluar alternativas",

    "evaluar opciones",

    "estamos evaluando",

    "queremos evaluar",

    "buscando alternativas",

    "otras alternativas",

    "comparar soluciones",

    "analizar opciones",

    "ver opciones",

    "explorar alternativas",

]



#
# Objection: Budget
#

BUDGET_OBJECTIONS = [

    "presupuesto",

    "sin presupuesto",

    "no tenemos presupuesto",

    "presupuesto limitado",

    "presupuesto actual",

    "muy caro",

    "demasiado caro",

    "precio alto",

    "fuera de presupuesto",

]



#
# Objection: Competitor
#
# Competencia real.
#
# NO incluir:
# - alternativas
# - evaluar opciones
# - buscar soluciones
#
# porque son parte normal del proceso comercial.
#

COMPETITOR_OBJECTIONS = [

    "ya usamos",

    "ya tenemos",

    "otro proveedor",

    "otros proveedores",

    "proveedor actual",

    "nuestro proveedor",

    "actualmente usamos",

    "trabajamos con",

    "la competencia",

    "un competidor",

    "otro sistema",

]



#
# Buying Signals
#

BUYING_SIGNALS = [

    "quiero una demo",

    "queremos una demo",

    "agendemos",

    "agenda",

    "enviar propuesta",

    "envía propuesta",

    "envíanos propuesta",

    "envíanos una propuesta",

    "envianos una propuesta",

    "propuesta comercial",

    "podemos avanzar",

    "avancemos",

    "nos interesa avanzar",

]



#
# Next step proposal
#

NEXT_STEP_PROPOSAL = [

    "enviar propuesta",

    "envíanos una propuesta",

    "envianos una propuesta",

    "propuesta comercial",

    "cotización",

    "cotizacion",

]



#
# Next step demo
#

NEXT_STEP_DEMO = [

    "demo",

    "demostración",

    "demostracion",

    "ver cómo funciona",

    "ver como funciona",

]



#
# Sentiment
#

POSITIVE_WORDS = [

    "interesante",

    "perfecto",

    "excelente",

    "me gusta",

    "me interesa",

    "nos interesa",

    "queremos",

    "buena idea",

]



NEGATIVE_WORDS = [

    "caro",

    "problema",

    "difícil",

    "dificil",

    "malo",

    "preocupación",

    "preocupacion",

    "riesgo",

]