import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import swisseph as swe
from datetime import datetime, timedelta
from pytz import timezone as pytz_timezone
from timezonefinder import TimezoneFinder
import pytz
from pytz import timezone, utc

app = Flask(__name__)
CORS(app)

script_dir = os.path.dirname(os.path.realpath(__file__))  # Directorio actual del script
ephe_path = os.path.join(script_dir, "ephe")

print("Usando ephemeris desde:", ephe_path)
swe.set_ephe_path(ephe_path)

@app.route('/')
def home():
    return 'Bienvenido a la API de Carta Astral'

def decimal_to_degrees_minutes(decimal_degree):
    """Convierte un grado decimal a grados, minutos y segundos."""
    degrees = int(decimal_degree)
    remaining_decimal = (decimal_degree - degrees) * 60
    minutes = int(remaining_decimal)
    seconds = round((remaining_decimal - minutes) * 60)
    return degrees, minutes, seconds

signos_es = ["Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo", 
             "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"]

signos_en = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

PUNTOS_ASCENDENTE_EXTRA = 2.0  # Example value
PUNTOS_REGENTE_ASCENDENTE_EXTRA = 2.0  # Example value
PUNTOS_MC_EXTRA = 2.0
# Define points for each planet for elemental balance calculation
puntos_planetas = {
    "Sol": 5.0,
    "Luna": 5.0,
    "Mercurio": 3,
    "Venus": 3.0,
    "Marte": 3.0,
    "Júpiter": 2.0,
    "Saturno": 2.0,
    "Urano": 1.0,
    "Neptuno": 1.0,
    "Plutón": 1.0,
    "Quirón": 0.5,
    "Nodo Norte": 0.5,
    "Sun": 5.0,
    "Moon": 5.0,
    "Mercury": 3.0,
    "Venus": 3.0,
    "Mars": 3.0,
    "Jupiter": 2.0,
    "Saturn": 2.0,
    "Uranus": 1.0,
    "Neptune": 1.0,
    "Pluto": 1.0,
    "Chiron": 0.5,
    "North Node": 0.5,
}

# Sign to element mapping
signo_a_elemento = {
    "Aries": "Fuego", "Leo": "Fuego", "Sagitario": "Fuego",
    "Taurus": "Tierra", "Virgo": "Tierra", "Capricorn": "Tierra",
    "Gemini": "Aire", "Libra": "Aire", "Aquarius": "Aire",
    "Cancer": "Agua", "Scorpio": "Agua", "Pisces": "Agua",
    "Aries": "Fuego", "Leo": "Fuego", "Sagittarius": "Fuego",
    "Tauro": "Tierra", "Virgo": "Tierra", "Capricornio": "Tierra",
    "Géminis": "Aire", "Libra": "Aire", "Acuario": "Aire",
    "Cáncer": "Agua", "Escorpio": "Agua", "Piscis": "Agua",
}
signo_a_ritmo = {
    # Ritmo Cardinal
    "Aries": "Cardinal", "Cáncer": "Cardinal", "Libra": "Cardinal", "Capricornio": "Cardinal",
    "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal", # English

    # Ritmo Fijo
    "Tauro": "Fijo", "Leo": "Fijo", "Escorpio": "Fijo", "Acuario": "Fijo",
    "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed", # English

    # Ritmo Mutable
    "Géminis": "Mutable", "Virgo": "Mutable", "Sagitario": "Mutable", "Piscis": "Mutable",
    "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable", # English
}

signo_a_ritmo_es = {
    "Aries": "Cardinal", "Cáncer": "Cardinal", "Libra": "Cardinal", "Capricornio": "Cardinal",
    "Tauro": "Fijo", "Leo": "Fijo", "Escorpio": "Fijo", "Acuario": "Fijo",
    "Géminis": "Mutable", "Virgo": "Mutable", "Sagitario": "Mutable", "Piscis": "Mutable",
}

# Define Sign to rhythm mapping for English
signo_a_ritmo_en = {
    "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
    "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
    "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
}

signo_a_yin_yang = {
    # Yin Signs (Water and Earth)
    "Cáncer": "Yin", "Escorpio": "Yin", "Piscis": "Yin",
    "Tauro": "Yin", "Virgo": "Yin", "Capricornio": "Yin",
    "Cancer": "Yin", "Scorpio": "Yin", "Pisces": "Yin", # English
    "Taurus": "Yin", "Virgo": "Yin", "Capricorn": "Yin", # English

    # Yang Signs (Fire and Air)
    "Aries": "Yang", "Leo": "Yang", "Sagitario": "Yang",
    "Géminis": "Yang", "Libra": "Yang", "Acuario": "Yang",
    "Aries": "Yang", "Leo": "Yang", "Sagittarius": "Yang", # English
    "Gemini": "Yang", "Libra": "Yang", "Aquarius": "Yang", # English
}
# Regencies for each sign (English and Spanish)
regencias_signo_a_planeta = {
    "Aries": "Marte", "Tauro": "Venus", "Géminis": "Mercurio", "Cáncer": "Luna",
    "Leo": "Sol", "Virgo": "Mercurio", "Libra": "Venus", "Escorpio": "Marte",
    "Sagitario": "Júpiter", "Capricornio": "Saturno", "Acuario": "Urano", "Piscis": "Neptuno",
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune",
}


def obtener_signo(longitud):
    """Obtiene el signo, grado, minuto y segundo de una longitud eclíptica."""
    signo_numero = int(longitud // 30)
    grado_decimal = longitud % 30
    grados, minutos, segundos = decimal_to_degrees_minutes(grado_decimal)
    return signos_es[signo_numero], grados, minutos, segundos

def get_houses(jd, latitude, longitude, house_system, lang="es"):
    signos = signos_es if lang == "es" else signos_en
    result, err = swe.houses(jd, latitude, longitude, house_system)
    houses = result[:12]
    house_positions = []
    for i, house in enumerate(houses):
        sign = int(house / 30)
        degree_in_sign = house % 30
        degree, minutes, seconds = decimal_to_degrees_minutes(degree_in_sign)
        signo = signos[sign]
        # Exclude 'seconds' if not needed in the unpacking loop in calcular_carta
        house_positions.append((i + 1, signo, degree, minutes, house)) # Removed seconds
    return house_positions

def determine_house(longitude, house_positions):
    for i, (_, _, _, _, house_longitude) in enumerate(house_positions):
        next_house_longitude = house_positions[(i + 1) % 12][4]
        current_start = house_longitude % 360
        next_start = next_house_longitude % 360

        if current_start < next_start:
            if current_start <= longitude < next_start:
                return i + 1
        else:
            if current_start <= longitude < 360 or 0 <= longitude < next_start:
                return i + 1
    return 12

def get_timezone(latitude, longitude):
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
    return pytz.timezone(timezone_str)

def get_planet_position(jd, planet_code, lang="es"):
    """Obtiene la posición de un planeta en grado, minuto y segundo."""
    result, err = swe.calc(jd, planet_code)
    longitude = result[0]
    speed = result[3]

    signo_numero = int(longitude // 30)
    grado_decimal = longitude % 30
    grados, minutos, segundos = decimal_to_degrees_minutes(grado_decimal)
    if lang == "es":
        signo = signos_es[signo_numero]
    else:
        signo = signos_en[signo_numero]
    retrograde = speed < 0
    estacionario = abs(speed) < 0.001  

    return signo, grados, minutos, segundos, round(longitude, 6), round(speed, 6), retrograde, estacionario

def get_sun_position(date_str, time_str, tz_name):
    """Calcula la posición exacta del Sol en grado, minuto y segundo."""
    local_tz = pytz.timezone(tz_name)
    dt_local = local_tz.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    dt_utc = dt_local.astimezone(pytz.utc)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)

    result, _ = swe.calc(jd, swe.SUN)
    longitude = result[0]

    signo, grados, minutos, segundos = obtener_signo(longitude)

    return {
        "date": date_str,
        "time": time_str,
        "timezone": tz_name,
        "longitude": round(longitude, 6),
        "sign": signo,
        "degree": grados,
        "minute": minutos,
        "second": segundos
    }

def refine_position(planet_id, jd_low, jd_high, target_degree, tolerance=1e-7):
    """ Afina la búsqueda de la posición exacta del planeta. """
    while (jd_high - jd_low) > tolerance:
        jd_mid = (jd_low + jd_high) / 2.0
        result, _ = swe.calc(jd_mid, planet_id)
        mid_degree = result[0]

        if mid_degree < target_degree:
            jd_low = jd_mid
        else:
            jd_high = jd_mid
    return jd_high

def find_sun_repeat(sun_data, year):
    """Busca la repetición más precisa de la posición exacta del Sol."""
    target_sign = sun_data["sign"]
    target_degree = sun_data["degree"]
    target_minute = sun_data["minute"]
    target_second = sun_data["second"]

    zodiac_signs = signos_es  # Usamos el array ya definido en tu código

    sign_index = zodiac_signs.index(target_sign)
    target_degree_ecliptic = (
        sign_index * 30
        + target_degree
        + target_minute / 60
        + target_second / 3600
    )

    base_date = datetime.strptime(sun_data["date"], "%Y-%m-%d")
    jd_start = swe.julday(year, base_date.month, base_date.day) - 3
    jd_end = swe.julday(year, base_date.month, base_date.day) + 3

    step = 0.0001  # Más preciso
    tolerance = 1e-8

    best_diff = float("inf")
    best_jd = None

    jd = jd_start
    while jd <= jd_end:
        result, _ = swe.calc(jd, swe.SUN)
        sun_degree = result[0]
        diff = abs(sun_degree - target_degree_ecliptic)

        if diff < best_diff:
            best_diff = diff
            best_jd = jd

            if best_diff < tolerance:
                break

        jd += step

    if best_jd:
        year_found, month, day, ut_decimal = swe.revjul(best_jd)
        hour = int(ut_decimal)
        minute = int((ut_decimal - hour) * 60)
        second = int((((ut_decimal - hour) * 60) - minute) * 60)
        microsecond = int(((((ut_decimal - hour) * 60) - minute) * 60 - second) * 1_000_000)

        dt_return = datetime(year_found, month, day, hour, minute, second, microsecond, tzinfo=pytz.utc)
        return dt_return.isoformat()

    return None

@app.route('/revolucion_solar', methods=['GET'])
def revolucion_solar():
    # Obtener parámetros
    fecha_param = request.args.get('fecha', default=None)
    lat = request.args.get('lat', type=float, default=None) 
    lon = request.args.get('lon', type=float, default=None)
    lang = request.args.get('lang', default='es')
    sistema_casas = request.args.get('sistema_casas', 'T') 
    year_param = request.args.get('year_param', type=int, default=None)

    # Validaciones básicas
    if not lat or not lon:
        return jsonify({"error": "Se requiere latitud y longitud."}), 400

    # Fecha de entrada
    if fecha_param:
        try:
            user_datetime = datetime.fromisoformat(fecha_param)
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400
    else:
        user_datetime = datetime.now()

    # Calcular la zona horaria
    timezone = get_timezone(lat, lon)
    user_datetime_utc = timezone.localize(user_datetime).astimezone(pytz.utc)

    # Calcular el Julian Day
    jd = swe.julday(user_datetime_utc.year, user_datetime_utc.month, user_datetime_utc.day,
                    user_datetime_utc.hour + user_datetime_utc.minute / 60.0 + user_datetime_utc.second / 3600.0)

    if year_param:
        sun_data = get_sun_position(fecha_param.split("T")[0], fecha_param.split("T")[1], "America/Argentina/Buenos_Aires")
        solar_return_iso = find_sun_repeat(sun_data, year_param)
        if not solar_return_iso:
            return jsonify({"error": "No se encontró el momento en el rango establecido."}), 400

        exact_datetime = datetime.fromisoformat(solar_return_iso)
        user_datetime_utc = exact_datetime

        # Calcular el Julian Day para la revolución solar con la fecha de repetición
        jd = swe.julday(user_datetime_utc.year, user_datetime_utc.month, user_datetime_utc.day,
                        user_datetime_utc.hour + user_datetime_utc.minute / 60.0 + user_datetime_utc.second / 3600.0)

        # --- INICIO DEL CÓDIGO PARA LA FASE LUNAR EN REVOLUCIÓN SOLAR ---
        luna_pos = swe.calc_ut(jd, swe.MOON)[0][0]
        sol_pos = swe.calc_ut(jd, swe.SUN)[0][0]

        fase_lunar_grados = (luna_pos - sol_pos) % 360

        # Traducción de la fase lunar
        if lang == 'es':
            if 0 <= fase_lunar_grados < 45:
                fase_lunar = "Luna Nueva"
            elif 45 <= fase_lunar_grados < 90:
                fase_lunar = "Luna Creciente"
            elif 90 <= fase_lunar_grados < 135:
                fase_lunar = "Cuarto Creciente"
            elif 135 <= fase_lunar_grados < 180:
                fase_lunar = "Gibosa Creciente"
            elif 180 <= fase_lunar_grados < 225:
                fase_lunar = "Luna Llena"
            elif 225 <= fase_lunar_grados < 270:
                fase_lunar = "Gibosa Menguante"
            elif 270 <= fase_lunar_grados < 315:
                fase_lunar = "Cuarto Menguante"
            elif 315 <= fase_lunar_grados < 360:
                fase_lunar = "Luna Menguante"
            else:
                fase_lunar = "Luna Nueva"
        else: # Default to English
            if 0 <= fase_lunar_grados < 45:
                fase_lunar = "New Moon"
            elif 45 <= fase_lunar_grados < 90:
                fase_lunar = "Waxing Crescent"
            elif 90 <= fase_lunar_grados < 135:
                fase_lunar = "First Quarter"
            elif 135 <= fase_lunar_grados < 180:
                fase_lunar = "Waxing Gibbous"
            elif 180 <= fase_lunar_grados < 225:
                fase_lunar = "Full Moon"
            elif 225 <= fase_lunar_grados < 270:
                fase_lunar = "Waning Gibbous"
            elif 270 <= fase_lunar_grados < 315:
                fase_lunar = "Last Quarter"
            elif 315 <= fase_lunar_grados < 360:
                fase_lunar = "Waning Crescent"
            else:
                fase_lunar = "New Moon"

    planet_names_es = {
        "Sol": swe.SUN,
        "Luna": swe.MOON,
        "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS,
        "Marte": swe.MARS,
        "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN,
        "Urano": swe.URANUS,
        "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO,
        "Lilith": 13,
        "Quirón": swe.CHIRON,
        "Nodo Norte": 11,
    }

    planet_names_en = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
        "Lilith": 13,
        "Chiron": swe.CHIRON,
        "North Node": 11,
    }

    planet_names = planet_names_es if lang == 'es' else planet_names_en
    # Sistema de casas
    sistemas_casas = {
        "P": b'P', 
        "K": b'K', 
        "R": b'R', 
        "C": b'C', 
        "E": b'E',
        "W": b'W',
        "T": b'T' 
    }
    house_system = sistemas_casas.get(sistema_casas, b'T')

    # Obtener la fecha de la revolución solar si se proporciona el año
    if year_param:
        sun_data = get_sun_position(fecha_param.split("T")[0], fecha_param.split("T")[1], "America/Argentina/Buenos_Aires")
        solar_return_iso = find_sun_repeat(sun_data, year_param)
        if not solar_return_iso:
            return jsonify({"error": "No se encontró el momento en el rango establecido."}), 400

        exact_datetime = datetime.fromisoformat(solar_return_iso)
        user_datetime_utc = exact_datetime

        # Calcular el Julian Day para la revolución solar con la fecha de repetición
        jd = swe.julday(user_datetime_utc.year, user_datetime_utc.month, user_datetime_utc.day,
                        user_datetime_utc.hour + user_datetime_utc.minute / 60.0 + user_datetime_utc.second / 3600.0)

    # Calcular posiciones de planetas usando la fecha de repetición del Sol
    planet_positions = {}
    house_positions = get_houses(jd, lat, lon, house_system, lang)
    
    # Ascendant is at index 0 in house_positions
    ascendente_signo = house_positions[0][1] 
    regente_ascendente = regencias_signo_a_planeta.get(ascendente_signo)

    # Inicialización para el balance elemental
    balance_elemental_puntos = {
        "Fuego": 0.0,
        "Tierra": 0.0,
        "Aire": 0.0,
        "Agua": 0.0
    }
    if lang == 'en': # Adjust keys for English output if lang is 'en'
        balance_elemental_puntos = {
            "Fire": 0.0,
            "Earth": 0.0,
            "Air": 0.0,
            "Water": 0.0
        }

    balance_ritmico_puntos = {}
    if lang == 'es':
        balance_ritmico_puntos = {
            "Cardinal": 0.0,
            "Fijo": 0.0,
            "Mutable": 0.0,
        }
        current_sign_map_rhythm = signo_a_ritmo_es # Use the Spanish mapping
    else: # English
        balance_ritmico_puntos = {
            "Cardinal": 0.0,
            "Fixed": 0.0,
            "Mutable": 0.0,
        }
        current_sign_map_rhythm = signo_a_ritmo_en # Use the English mapping

    # NUEVO: Inicialización para el balance Yin/Yang
    balance_yin_yang_puntos = {
        "Yin": 0.0,
        "Yang": 0.0,
    }
    # No necesita traducción ya que "Yin" y "Yang" son universales.

    total_puntos_considerados = 0.0 # Este total se usará para todos los balances

    for planet_name_str, swe_code in planet_names.items():
        if planet_name_str not in puntos_planetas:
            puntos = 0.0
        else:
            puntos = puntos_planetas[planet_name_str]
            
        signo, degree, minutes, seconds, longitude, speed, retrograde, estacionario = get_planet_position(jd, swe_code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet_name_str] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "casa": house,
            "longitud": longitude,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }
        
        # Balance Elemental
        if lang == 'es':
            current_sign_map_element = signo_a_elemento
        else: # English
            current_sign_map_element = {
                "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
                "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
                "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
                "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
            }

        if signo in current_sign_map_element:
            elemento = current_sign_map_element[signo]
            balance_elemental_puntos[elemento] += puntos
            
        # Balance Rítmico
        if signo in current_sign_map_rhythm:
            ritmo = current_sign_map_rhythm[signo]
            balance_ritmico_puntos[ritmo] += puntos
            
        # NUEVO: Balance Yin/Yang
        # No necesita comprobación de idioma para el mapeo de signos, ya que signo_a_yin_yang tiene ambas versiones
        if signo in signo_a_yin_yang:
            yin_yang_type = signo_a_yin_yang[signo]
            balance_yin_yang_puntos[yin_yang_type] += puntos

        total_puntos_considerados += puntos # Se suma una sola vez por cada planeta

    # Puntos extra para Ascendente (Elemental)
    if lang == 'es':
        current_ascendant_sign_map_element = signo_a_elemento
    else: # English
        current_ascendant_sign_map_element = {
            "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
            "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
            "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
        }

    if ascendente_signo in current_ascendant_sign_map_element:
        elemento_ascendente = current_ascendant_sign_map_element[ascendente_signo]
        balance_elemental_puntos[elemento_ascendente] += PUNTOS_ASCENDENTE_EXTRA
        total_puntos_considerados += PUNTOS_ASCENDENTE_EXTRA # Suma estos puntos al total

    # Puntos extra para Ascendente (Rítmico)
    if lang == 'es':
        current_ascendant_sign_map_rhythm = signo_a_ritmo_es
    else: # English
        current_ascendant_sign_map_rhythm = signo_a_ritmo_en

    if ascendente_signo in current_ascendant_sign_map_rhythm:
        ritmo_ascendente = current_ascendant_sign_map_rhythm[ascendente_signo]
        balance_ritmico_puntos[ritmo_ascendente] += PUNTOS_ASCENDENTE_EXTRA
        # total_puntos_considerados ya fue incrementado por el ascendente_extra

    # NUEVO: Puntos extra para Ascendente (Yin/Yang)
    if ascendente_signo in signo_a_yin_yang:
        yin_yang_ascendente = signo_a_yin_yang[ascendente_signo]
        balance_yin_yang_puntos[yin_yang_ascendente] += PUNTOS_ASCENDENTE_EXTRA
        # total_puntos_considerados ya fue incrementado por el ascendente_extra


    # Puntos extra para el regente del Ascendente (Elemental)
    if regente_ascendente and regente_ascendente in planet_names:
        regente_ascendente_swe_code = planet_names[regente_ascendente]
        _, _, _, _, regente_ascendente_longitude, _, _, _ = get_planet_position(jd, regente_ascendente_swe_code, lang)
        
        regente_ascendente_signo_numero = int(regente_ascendente_longitude // 30)
        
        if lang == 'es':
            regente_ascendente_signo = signos_es[regente_ascendente_signo_numero]
            current_sign_map_for_regent_element = signo_a_elemento
        else:
            regente_ascendente_signo = signos_en[regente_ascendente_signo_numero] # Ensure English sign is used
            current_sign_map_for_regent_element = {
                "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
                "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
                "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
            }

        if regente_ascendente_signo in current_sign_map_for_regent_element:
            elemento_regente_ascendente = current_sign_map_for_regent_element[regente_ascendente_signo]
            balance_elemental_puntos[elemento_regente_ascendente] += PUNTOS_REGENTE_ASCENDENTE_EXTRA
            total_puntos_considerados += PUNTOS_REGENTE_ASCENDENTE_EXTRA # Suma estos puntos al total

        # Puntos extra para el regente del Ascendente (Rítmico)
    if lang == 'es':
        current_sign_map_for_regent_rhythm = signo_a_ritmo_es
    else:
        current_sign_map_for_regent_rhythm = signo_a_ritmo_en
        
        if regente_ascendente_signo in current_sign_map_for_regent_rhythm:
            ritmo_regente_ascendente = current_sign_map_for_regent_rhythm[regente_ascendente_signo]
            balance_ritmico_puntos[ritmo_regente_ascendente] += PUNTOS_REGENTE_ASCENDENTE_EXTRA
            # total_puntos_considerados ya fue incrementado

        # NUEVO: Puntos extra para el regente del Ascendente (Yin/Yang)
        if regente_ascendente_signo in signo_a_yin_yang:
            yin_yang_regente_ascendente = signo_a_yin_yang[regente_ascendente_signo]
            balance_yin_yang_puntos[yin_yang_regente_ascendente] += PUNTOS_REGENTE_ASCENDENTE_EXTRA
            # total_puntos_considerados ya fue incrementado

    # Puntos extra para el Medio Cielo (Elemental)
    mc_signo = None
    for house_num, signo, degree, minutes, house_longitude in house_positions:
        if house_num == 10: # Asumiendo que la Casa 10 es el MC
            mc_signo = signo
            break

    if mc_signo:
        if lang == 'es':
            current_mc_sign_map_element = signo_a_elemento
        else: # English
            current_mc_sign_map_element = {
                "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
                "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
                "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
            }
        
        if mc_signo in current_mc_sign_map_element:
            elemento_mc = current_mc_sign_map_element[mc_signo]
            balance_elemental_puntos[elemento_mc] += PUNTOS_MC_EXTRA
            total_puntos_considerados += PUNTOS_MC_EXTRA # Suma estos puntos al total

        # Puntos extra para el Medio Cielo (Rítmico)
    if lang == 'es':
        current_mc_sign_map_rhythm = signo_a_ritmo_es
    else:
        current_mc_sign_map_rhythm = signo_a_ritmo_en
        
        if mc_signo in current_mc_sign_map_rhythm:
            ritmo_mc = current_mc_sign_map_rhythm[mc_signo]
            balance_ritmico_puntos[ritmo_mc] += PUNTOS_MC_EXTRA
            # total_puntos_considerados ya fue incrementado

        # NUEVO: Puntos extra para el Medio Cielo (Yin/Yang)
        if mc_signo in signo_a_yin_yang:
            yin_yang_mc = signo_a_yin_yang[mc_signo]
            balance_yin_yang_puntos[yin_yang_mc] += PUNTOS_MC_EXTRA
            # total_puntos_considerados ya fue incrementado
            
    # Cálculo de porcentajes para balance elemental
    balance_elemental_porcentaje = {
        "Fuego": 0.0, "Tierra": 0.0, "Aire": 0.0, "Agua": 0.0
    }
    if lang == 'en':
        balance_elemental_porcentaje = {
            "Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0
        }

    if total_puntos_considerados > 0:
        for elemento, puntos_acumulados in balance_elemental_puntos.items():
            balance_elemental_porcentaje[elemento] = round((puntos_acumulados / total_puntos_considerados) * 100, 2)
            
    balance_elemental_porcentaje["Total_Puntos_Considerados"] = round(total_puntos_considerados, 2)

    balance_ritmico_porcentaje = {} # Initialize as empty
    if lang == 'es':
        balance_ritmico_porcentaje = {
            "Cardinal": 0.0, "Fijo": 0.0, "Mutable": 0.0
        }
    else: # English
        balance_ritmico_porcentaje = {
            "Cardinal": 0.0, "Fixed": 0.0, "Mutable": 0.0
        }

    if total_puntos_considerados > 0:
        for ritmo, puntos_acumulados in balance_ritmico_puntos.items():
            balance_ritmico_porcentaje[ritmo] = round((puntos_acumulados / total_puntos_considerados) * 100, 2)

    # NUEVO: Cálculo de porcentajes para balance Yin/Yang
    balance_yin_yang_porcentaje = {
        "Yin": 0.0, "Yang": 0.0
    }
    if total_puntos_considerados > 0:
        for tipo, puntos_acumulados in balance_yin_yang_puntos.items():
            balance_yin_yang_porcentaje[tipo] = round((puntos_acumulados / total_puntos_considerados) * 100, 2)


    # House longitudes from house_positions (Ascendant is house_positions[0])
    ascendente_longitude = house_positions[0][4]
    casa_2_longitude = house_positions[1][4]
    casa_3_longitude = house_positions[2][4]
    casa_4_longitude = house_positions[3][4]
    casa_5_longitude = house_positions[4][4]
    casa_6_longitude = house_positions[5][4]

    distancia_ascendente_casa2 = ((casa_2_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa3 = ((casa_3_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa4 = ((casa_4_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa5 = ((casa_5_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa6 = ((casa_6_longitude - ascendente_longitude) % 360)
    
    houses = {}
    for house_num, signo, degree, minutes, house_longitude in house_positions:
        houses[house_num] = {"signo": signo, "grado": degree, "minutos": minutes, "segundos": seconds}

    return jsonify({
        "fase_lunar": fase_lunar,
        "fecha_repeticion": solar_return_iso,  # Fecha y hora de la repetición solar
        "planetas": planet_positions,
        "casas": houses,
        "ascendente": ascendente_longitude,
        "distancia_ascendente_casa2": distancia_ascendente_casa2,
        "distancia_ascendente_casa3": distancia_ascendente_casa3,
        "distancia_ascendente_casa4": distancia_ascendente_casa4,
        "distancia_ascendente_casa5": distancia_ascendente_casa5,
        "distancia_ascendente_casa6": distancia_ascendente_casa6,
        "balance_elemental_porcentaje": balance_elemental_porcentaje,
        "balance_elemental_puntos": balance_elemental_puntos,
        "balance_ritmico_porcentaje": balance_ritmico_porcentaje,
        "balance_ritmico_puntos": balance_ritmico_puntos,
        "balance_yin_yang_porcentaje": balance_yin_yang_porcentaje, # NUEVO
        "balance_yin_yang_puntos": balance_yin_yang_puntos # NUEVO
    })

tf = TimezoneFinder()

def calcular_edad_decimal(año, mes, dia, hora, minuto, zona_horaria_str, fecha_hoy_str):
    """Calcula la edad decimal en años, usando la fecha proporcionada."""
    zona_horaria = tz.gettz(zona_horaria_str)
    fecha_hora_nacimiento = datetime(año, mes, dia, hora, minuto, tzinfo=zona_horaria)
    try:
        fecha_hoy = datetime.strptime(fecha_hoy_str, '%Y-%m-%d %H:%M')
        fecha_hora_actual = fecha_hoy.replace(tzinfo=zona_horaria)
    except ValueError:
        # Esto no debería ocurrir si el frontend envía la fecha en el formato correcto
        fecha_hora_actual = datetime.now(zona_horaria) # Fallback por si acaso
    diferencia = fecha_hora_actual - fecha_hora_nacimiento
    segundos_vividos = diferencia.total_seconds()
    segundos_en_un_año = 365.2425 * 24 * 3600
    edad_decimal = segundos_vividos / segundos_en_un_año
    return edad_decimal

def obtener_fecha_hora_progresada_por_edad(fecha_nacimiento_str, hora_nacimiento_str, lat_nacimiento, lon_nacimiento, edad_progresada):
    """Calcula la fecha y hora de la progresión secundaria usando la edad ingresada."""
    try:
        zona_horaria_nacimiento_str = tf.timezone_at(lng=lon_nacimiento, lat=lat_nacimiento)
        if not zona_horaria_nacimiento_str:
            return None, "No se pudo determinar la zona horaria para las coordenadas de nacimiento."

        zona_horaria_nacimiento = pytz.timezone(zona_horaria_nacimiento_str)
        fecha_hora_nacimiento_naive = datetime.strptime(f"{fecha_nacimiento_str} {hora_nacimiento_str}", '%Y-%m-%d %H:%M')
        fecha_hora_nacimiento_local = zona_horaria_nacimiento.localize(fecha_hora_nacimiento_naive)
        fecha_hora_utc_nacimiento = fecha_hora_nacimiento_local.astimezone(pytz.utc)

        dias_progresados = timedelta(days=edad_progresada) # Usar la edad directamente como días progresados
        fecha_hora_utc_progresada = fecha_hora_utc_nacimiento + dias_progresados
        return fecha_hora_utc_progresada, None
    except pytz.exceptions.UnknownTimeZoneError:
        return None, f"Zona horaria desconocida para las coordenadas de nacimiento."
    except ValueError:
        return None, "Formato de fecha u hora de nacimiento incorrecto."

def obtener_fecha_hora_progresada_por_coordenadas(fecha_nacimiento_str, hora_nacimiento_str, lat_nacimiento, lon_nacimiento, fecha_hoy_str):
    """Calcula la fecha y hora de la progresión secundaria usando coordenadas de nacimiento (edad actual)."""
    try:
        zona_horaria_nacimiento_str = tf.timezone_at(lng=lon_nacimiento, lat=lat_nacimiento)
        if not zona_horaria_nacimiento_str:
            return None, None, "No se pudo determinar la zona horaria para las coordenadas de nacimiento."

        zona_horaria_nacimiento = pytz.timezone(zona_horaria_nacimiento_str)
        fecha_hora_nacimiento_naive = datetime.strptime(f"{fecha_nacimiento_str} {hora_nacimiento_str}", '%Y-%m-%d %H:%M')
        fecha_hora_nacimiento_local = zona_horaria_nacimiento.localize(fecha_hora_nacimiento_naive)
        fecha_hora_utc_nacimiento = fecha_hora_nacimiento_local.astimezone(pytz.utc)

        edad_decimal = calcular_edad_decimal(
            fecha_hora_nacimiento_local.year,
            fecha_hora_nacimiento_local.month,
            fecha_hora_nacimiento_local.day,
            fecha_hora_nacimiento_local.hour,
            fecha_hora_nacimiento_local.minute,
            zona_horaria_nacimiento_str,
            fecha_hoy_str # Usar la fecha enviada desde el frontend
        )

        dias_progresados_decimal = edad_decimal
        un_dia_decimal = timedelta(days=dias_progresados_decimal)
        fecha_hora_utc_progresada = fecha_hora_utc_nacimiento + un_dia_decimal
        return fecha_hora_utc_progresada, edad_decimal, None
    except pytz.exceptions.UnknownTimeZoneError:
        return None, None, f"Zona horaria desconocida para las coordenadas de nacimiento."
    except ValueError:
        return None, None, "Formato de fecha u hora de nacimiento incorrecto."
    
@app.route('/progresiones', methods=['GET'])
def calcular_astros_progresados_coordenadas():
    fecha_nacimiento_str = request.args.get('fecha_nacimiento')
    hora_nacimiento_str = request.args.get('hora_nacimiento')
    lat_nacimiento = request.args.get('lat_nacimiento', type=float)
    lon_nacimiento = request.args.get('lon_nacimiento', type=float)
    lang = request.args.get('lang', default='es')
    edad_progresada_str = request.args.get('edad_progresada')
    fecha_hoy_str = request.args.get('fecha_hoy')# Nuevo parámetro

    if not all([fecha_nacimiento_str, hora_nacimiento_str, lat_nacimiento, lon_nacimiento]):
        return jsonify({"error": "Se requieren los parámetros: fecha_nacimiento, hora_nacimiento, lat_nacimiento y lon_nacimiento."}), 400

    if edad_progresada_str:
        try:
            edad_progresada = float(edad_progresada_str)
            fecha_hora_progresada, error = obtener_fecha_hora_progresada_por_edad(
                fecha_nacimiento_str, hora_nacimiento_str, lat_nacimiento, lon_nacimiento, edad_progresada
            )
            edad_actual = edad_progresada # Usar la edad ingresada como edad actual
            if error:
                return jsonify({"error": f"Error al calcular la fecha y hora progresada: {error}"}), 400
            if fecha_hora_progresada is None:
                return jsonify({"error": "Error desconocido al calcular la fecha y hora progresada."}), 500
        except ValueError:
            return jsonify({"error": "El parámetro 'edad_progresada' debe ser un número."}), 400
    else:
        fecha_hora_progresada, edad_actual, error = obtener_fecha_hora_progresada_por_coordenadas(
            fecha_nacimiento_str, hora_nacimiento_str, lat_nacimiento, lon_nacimiento, fecha_hoy_str
        )
        if error:
            return jsonify({"error": f"Error al calcular la fecha y hora progresada: {error}"}), 400
        if fecha_hora_progresada is None:
            return jsonify({"error": "Error desconocido al calcular la fecha y hora progresada."}), 500

    jd_progresado = swe.julday(
        fecha_hora_progresada.year,
        fecha_hora_progresada.month,
        fecha_hora_progresada.day,
        fecha_hora_progresada.hour + fecha_hora_progresada.minute / 60.0
    )

    planet_names_es = {
        "Sol": swe.SUN,
        "Luna": swe.MOON,
        "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS,
        "Marte": swe.MARS,
        "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN,
        "Urano": swe.URANUS,
        "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO,
        "Lilith": 13,
        "Quirón": swe.CHIRON,
        "Nodo Norte": 11,
    }

    planet_names_en = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
        "Lilith": 13,
        "Chiron": swe.CHIRON,
        "North Node": 11,
    }

    planet_names = planet_names_es if lang == 'es' else planet_names_en

    planet_positions = {}
    previous_positions = {}

    for planet, swe_code in planet_names.items():
        signo, degree, minutes, longitude, speed,seconds, retrograde, estacionario = get_planet_position(jd_progresado, swe_code, lang)

        if planet in previous_positions:
            prev_speed = previous_positions[planet]['speed']
            if abs(speed) < 0.001:
                estacionario = True
            else:
                estacionario = False

            if prev_speed > 0 and speed < 0:
                estacionario = True

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "longitud": longitude,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }

        previous_positions[planet] = {'speed': speed}

    return jsonify({
        "fecha_progresada": fecha_hora_progresada.isoformat(),
        "planetas": planet_positions,
        "edad_actual": edad_actual, # Devolver la edad ingresada o calculada
    })

@app.route('/astros_hoy', methods=['GET'])
def calcular_astros():
    fecha_param = request.args.get('fecha', default=None)
    lang = request.args.get('lang', default='es')  # Paramentro de idioma con valor predeterminado 'es'
    lat = request.args.get('lat', type=float, default=None)
    lon = request.args.get('lon', type=float, default=None)

    if fecha_param:
        try:
            now = datetime.fromisoformat(fecha_param)
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400
    else:
        now = datetime.now()

    jd = swe.julday(
        now.year,
        now.month,
        now.day,
        now.hour + now.minute / 60.0 
    )
    luna_pos = swe.calc_ut(jd, swe.MOON)[0][0]
    sol_pos = swe.calc_ut(jd, swe.SUN)[0][0]

    fase_lunar_grados = (luna_pos - sol_pos) % 360

    # Traducción de la fase lunar
    if lang == 'es':
        if 0 <= fase_lunar_grados < 45:
            fase_lunar = "Luna Nueva"
        elif 45 <= fase_lunar_grados < 90:
            fase_lunar = "Luna Creciente"
        elif 90 <= fase_lunar_grados < 135:
            fase_lunar = "Cuarto Creciente"
        elif 135 <= fase_lunar_grados < 180:
            fase_lunar = "Gibosa Creciente"
        elif 180 <= fase_lunar_grados < 225:
            fase_lunar = "Luna Llena"
        elif 225 <= fase_lunar_grados < 270:
            fase_lunar = "Gibosa Menguante"
        elif 270 <= fase_lunar_grados < 315:
            fase_lunar = "Cuarto Menguante"
        elif 315 <= fase_lunar_grados < 360:
            fase_lunar = "Luna Menguante"
        else:
            fase_lunar = "Luna Nueva" # Por si acaso
    else: # Default to English
        if 0 <= fase_lunar_grados < 45:
            fase_lunar = "New Moon"
        elif 45 <= fase_lunar_grados < 90:
            fase_lunar = "Waxing Crescent"
        elif 90 <= fase_lunar_grados < 135:
            fase_lunar = "First Quarter"
        elif 135 <= fase_lunar_grados < 180:
            fase_lunar = "Waxing Gibbous"
        elif 180 <= fase_lunar_grados < 225:
            fase_lunar = "Full Moon"
        elif 225 <= fase_lunar_grados < 270:
            fase_lunar = "Waning Gibbous"
        elif 270 <= fase_lunar_grados < 315:
            fase_lunar = "Last Quarter"
        elif 315 <= fase_lunar_grados < 360:
            fase_lunar = "Waning Crescent"
        else:
            fase_lunar = "New Moon"
    planet_names_es = {
        "Sol": swe.SUN,
        "Luna": swe.MOON,
        "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS,
        "Marte": swe.MARS,
        "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN,
        "Urano": swe.URANUS,
        "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO,
        "Lilith": 13,
        "Quirón": swe.CHIRON,
        "Nodo Norte": 11,
    }

    planet_names_en = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
        "Lilith": 13,
        "Chiron": swe.CHIRON,
        "North Node": 11,
    }

    planet_names = planet_names_es if lang == 'es' else planet_names_en

    planet_positions = {}

    for planet_name_str, swe_code in planet_names.items():

        signo, degree, minutes, seconds, longitude, speed, retrograde, estacionario = get_planet_position(jd, swe_code, lang)

        planet_positions[planet_name_str] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "longitud": longitude,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }
        

    return jsonify({
        "fase_lunar": fase_lunar,
        "planetas": planet_positions,
    })

@app.route('/mi_carta', methods=['POST'])
def mi_carta():
    data = request.json

    fecha_param = data.get('fecha')
    lat = data.get('lat')
    lon = data.get('lon')
    lang = data.get('lang', 'es')
    sistema_casas = data.get('sistema_casas', 'T')

    if not lat or not lon:
        return jsonify({"error": "Se requiere latitud y longitud."}), 400

    if fecha_param:
        try:
            user_datetime = datetime.fromisoformat(fecha_param)
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400
    else:
        user_datetime = datetime.now()

    timezone = get_timezone(lat, lon)
    user_datetime_utc = timezone.localize(user_datetime).astimezone(pytz.utc)

    jd = swe.julday(user_datetime_utc.year, user_datetime_utc.month, user_datetime_utc.day,
                    user_datetime_utc.hour + user_datetime_utc.minute / 60.0 + user_datetime_utc.second / 3600.0)
    
    luna_pos = swe.calc_ut(jd, swe.MOON)[0][0]
    sol_pos = swe.calc_ut(jd, swe.SUN)[0][0]

    fase_lunar_grados = (luna_pos - sol_pos) % 360

    if 0 <= fase_lunar_grados < 45:
        fase_lunar = "Luna Nueva"
    elif 45 <= fase_lunar_grados < 90:
        fase_lunar = "Luna Creciente"
    elif 90 <= fase_lunar_grados < 135:
        fase_lunar = "Cuarto Creciente"
    elif 135 <= fase_lunar_grados < 180:
        fase_lunar = "Gibosa Creciente"
    elif 180 <= fase_lunar_grados < 225:
        fase_lunar = "Luna Llena"
    elif 225 <= fase_lunar_grados < 270:
        fase_lunar = "Gibosa Menguante"
    elif 270 <= fase_lunar_grados < 315:
        fase_lunar = "Cuarto Menguante"
    elif 315 <= fase_lunar_grados < 360:
        fase_lunar = "Luna Menguante"
    else:
        fase_lunar = "Luna Nueva"

    planet_names_es = {
        "Sol": swe.SUN,
        "Luna": swe.MOON,
        "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS,
        "Marte": swe.MARS,
        "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN,
        "Urano": swe.URANUS,
        "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO,
        "Lilith": 13,
        "Quirón": swe.CHIRON,
        "Nodo Norte": 11,
    }

    planet_names_en = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
        "Lilith": 13,
        "Chiron": swe.CHIRON,
        "North Node": 11,
    }

    planet_names = planet_names_es if lang == 'es' else planet_names_en

    sistemas_casas = {
        "P": b'P', 
        "K": b'K', 
        "P": b'P', 
        "R": b'R', 
        "C": b'C', 
        "E": b'E',
        "W": b'W', 
        "T": b'T'  
    }

    house_system = sistemas_casas.get(sistema_casas, b'T')  

    planet_positions = {}
    previous_positions = {}
    
    for planet, swe_code in planet_names.items():
            signo, degree, minutes,seconds, longitude, speed, retrograde, estacionario = get_planet_position(jd, swe_code, lang)

            if planet in previous_positions:
                prev_speed = previous_positions[planet]['speed']
                if abs(speed) < 0.001: 
                    estacionario = True
                else:
                    estacionario = False

                if prev_speed > 0 and speed < 0:
                    estacionario = True 
            result, err = swe.calc(jd, swe_code)
    
    if err != 0:
        print(f"Error al calcular la posición del planeta: {err}")
    else:
        signo, degree, minutes, longitude, seconds = get_planet_position(jd, swe_code)
        print(f"{planet}: {signo} {degree}° {minutes}'")
        

    planet_positions = {}
    house_positions = get_houses(jd, lat, lon, house_system, lang)

    for planet, code in planet_names.items():
        signo, degree, minutes,seconds, longitude, speed,retrograde, estacionario = get_planet_position(jd, code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "casa": house,
            "longitud": longitude,
            "segundos": seconds,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }

    ascendente_longitude = house_positions[0][5]
    casa_2_longitude = house_positions[1][5]
    casa_3_longitude = house_positions[2][5]
    casa_4_longitude = house_positions[3][5]
    casa_5_longitude = house_positions[4][5]
    casa_6_longitude = house_positions[5][5]

    distancia_ascendente_casa2 = ((casa_2_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa3 = ((casa_3_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa4 = ((casa_4_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa5 = ((casa_5_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa6 = ((casa_6_longitude - ascendente_longitude) % 360)
    
    houses = {}
    for house_num, signo, degree, minutes, seconds, house_longitude in house_positions: # Incluimos segundos
        houses[house_num] = {"signo": signo, "grado": degree, "minutos": minutes, "segundos": seconds} # Incluimos segundos

    return jsonify({
        "fase_lunar": fase_lunar,
        "planetas": planet_positions,
        "casas": houses,
        "ascendente": ascendente_longitude,
        "distancia_ascendente_casa2": distancia_ascendente_casa2,
        "distancia_ascendente_casa3": distancia_ascendente_casa3,
        "distancia_ascendente_casa4": distancia_ascendente_casa4,
        "distancia_ascendente_casa5": distancia_ascendente_casa5,
        "distancia_ascendente_casa6": distancia_ascendente_casa6
        
    })

@app.route('/calcular_carta', methods=['POST'])
def calcular_carta():
    data = request.json

    fecha_param = data.get('fecha')
    lat = data.get('lat')
    lon = data.get('lon')
    lang = data.get('lang', 'es')
    sistema_casas = data.get('sistema_casas', 'T')

    if not lat or not lon:
        return jsonify({"error": "Se requiere latitud y longitud."}), 400

    if fecha_param:
        try:
            user_datetime = datetime.fromisoformat(fecha_param)
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400
    else:
        user_datetime = datetime.now()

    timezone = get_timezone(lat, lon)
    user_datetime_utc = timezone.localize(user_datetime).astimezone(pytz.utc)

    jd = swe.julday(user_datetime_utc.year, user_datetime_utc.month, user_datetime_utc.day,
                    user_datetime_utc.hour + user_datetime_utc.minute / 60.0 + user_datetime_utc.second / 3600.0)
    
    luna_pos = swe.calc_ut(jd, swe.MOON)[0][0]
    sol_pos = swe.calc_ut(jd, swe.SUN)[0][0]

    fase_lunar_grados = (luna_pos - sol_pos) % 360

    # Lunar phase translation (consider adding a dictionary for different languages if needed)
    if lang == 'es':
        if 0 <= fase_lunar_grados < 45:
            fase_lunar = "Luna Nueva"
        elif 45 <= fase_lunar_grados < 90:
            fase_lunar = "Luna Creciente"
        elif 90 <= fase_lunar_grados < 135:
            fase_lunar = "Cuarto Creciente"
        elif 135 <= fase_lunar_grados < 180:
            fase_lunar = "Gibosa Creciente"
        elif 180 <= fase_lunar_grados < 225:
            fase_lunar = "Luna Llena"
        elif 225 <= fase_lunar_grados < 270:
            fase_lunar = "Gibosa Menguante"
        elif 270 <= fase_lunar_grados < 315:
            fase_lunar = "Cuarto Menguante"
        elif 315 <= fase_lunar_grados < 360:
            fase_lunar = "Luna Menguante"
        else:
            fase_lunar = "Luna Nueva"
    else: # Default to English
        if 0 <= fase_lunar_grados < 45:
            fase_lunar = "New Moon"
        elif 45 <= fase_lunar_grados < 90:
            fase_lunar = "Waxing Crescent"
        elif 90 <= fase_lunar_grados < 135:
            fase_lunar = "First Quarter"
        elif 135 <= fase_lunar_grados < 180:
            fase_lunar = "Waxing Gibbous"
        elif 180 <= fase_lunar_grados < 225:
            fase_lunar = "Full Moon"
        elif 225 <= fase_lunar_grados < 270:
            fase_lunar = "Waning Gibbous"
        elif 270 <= fase_lunar_grados < 315:
            fase_lunar = "Last Quarter"
        elif 315 <= fase_lunar_grados < 360:
            fase_lunar = "Waning Crescent"
        else:
            fase_lunar = "New Moon"

    planet_names_es = {
        "Sol": swe.SUN, "Luna": swe.MOON, "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS, "Marte": swe.MARS, "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN, "Urano": swe.URANUS, "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO, "Lilith": 13, "Quirón": swe.CHIRON, "Nodo Norte": 11,
    }

    planet_names_en = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
        "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO, "Lilith": 13, "Chiron": swe.CHIRON, "North Node": 11,
    }

    planet_names = planet_names_es if lang == 'es' else planet_names_en

    sistemas_casas = {
        "P": b'P', "K": b'K', "R": b'R', "C": b'C', "E": b'E',
        "W": b'W', "T": b'T'
    }

    house_system = sistemas_casas.get(sistema_casas, b'T')

    planet_positions = {}
    house_positions = get_houses(jd, lat, lon, house_system, lang)
    
    ascendente_signo = house_positions[0][1] 
    regente_ascendente = regencias_signo_a_planeta.get(ascendente_signo)

    # Inicialización para el balance elemental
    balance_elemental_puntos = {
        "Fuego": 0.0,
        "Tierra": 0.0,
        "Aire": 0.0,
        "Agua": 0.0
    }
    if lang == 'en': # Adjust keys for English output if lang is 'en'
        balance_elemental_puntos = {
            "Fire": 0.0,
            "Earth": 0.0,
            "Air": 0.0,
            "Water": 0.0
        }

    balance_ritmico_puntos = {}
    if lang == 'es':
        balance_ritmico_puntos = {
            "Cardinal": 0.0,
            "Fijo": 0.0,
            "Mutable": 0.0,
        }
        current_sign_map_rhythm = signo_a_ritmo_es # Use the Spanish mapping
    else: # English
        balance_ritmico_puntos = {
            "Cardinal": 0.0,
            "Fixed": 0.0,
            "Mutable": 0.0,
        }
        current_sign_map_rhythm = signo_a_ritmo_en # Use the English mapping

    # NUEVO: Inicialización para el balance Yin/Yang
    balance_yin_yang_puntos = {
        "Yin": 0.0,
        "Yang": 0.0,
    }
    # No necesita traducción ya que "Yin" y "Yang" son universales.

    total_puntos_considerados = 0.0 # Este total se usará para todos los balances

    for planet_name_str, swe_code in planet_names.items():
        if planet_name_str not in puntos_planetas:
            puntos = 0.0
        else:
            puntos = puntos_planetas[planet_name_str]
            
        signo, degree, minutes, seconds, longitude, speed, retrograde, estacionario = get_planet_position(jd, swe_code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet_name_str] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "casa": house,
            "longitud": longitude,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }
        
        # Balance Elemental
        if lang == 'es':
            current_sign_map_element = signo_a_elemento
        else: # English
            current_sign_map_element = {
                "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
                "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
                "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
                "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
            }

        if signo in current_sign_map_element:
            elemento = current_sign_map_element[signo]
            balance_elemental_puntos[elemento] += puntos
            
        # Balance Rítmico
        if signo in current_sign_map_rhythm:
            ritmo = current_sign_map_rhythm[signo]
            balance_ritmico_puntos[ritmo] += puntos
            
        # NUEVO: Balance Yin/Yang
        # No necesita comprobación de idioma para el mapeo de signos, ya que signo_a_yin_yang tiene ambas versiones
        if signo in signo_a_yin_yang:
            yin_yang_type = signo_a_yin_yang[signo]
            balance_yin_yang_puntos[yin_yang_type] += puntos

        total_puntos_considerados += puntos # Se suma una sola vez por cada planeta

    # Puntos extra para Ascendente (Elemental)
    if lang == 'es':
        current_ascendant_sign_map_element = signo_a_elemento
    else: # English
        current_ascendant_sign_map_element = {
            "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
            "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
            "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
        }

    if ascendente_signo in current_ascendant_sign_map_element:
        elemento_ascendente = current_ascendant_sign_map_element[ascendente_signo]
        balance_elemental_puntos[elemento_ascendente] += PUNTOS_ASCENDENTE_EXTRA
        total_puntos_considerados += PUNTOS_ASCENDENTE_EXTRA # Suma estos puntos al total

    # Puntos extra para Ascendente (Rítmico)
    if lang == 'es':
        current_ascendant_sign_map_rhythm = signo_a_ritmo_es
    else: # English
        current_ascendant_sign_map_rhythm = signo_a_ritmo_en

    if ascendente_signo in current_ascendant_sign_map_rhythm:
        ritmo_ascendente = current_ascendant_sign_map_rhythm[ascendente_signo]
        balance_ritmico_puntos[ritmo_ascendente] += PUNTOS_ASCENDENTE_EXTRA
        # total_puntos_considerados ya fue incrementado por el ascendente_extra

    # NUEVO: Puntos extra para Ascendente (Yin/Yang)
    if ascendente_signo in signo_a_yin_yang:
        yin_yang_ascendente = signo_a_yin_yang[ascendente_signo]
        balance_yin_yang_puntos[yin_yang_ascendente] += PUNTOS_ASCENDENTE_EXTRA
        # total_puntos_considerados ya fue incrementado por el ascendente_extra


    # Puntos extra para el regente del Ascendente (Elemental)
    if regente_ascendente and regente_ascendente in planet_names:
        regente_ascendente_swe_code = planet_names[regente_ascendente]
        _, _, _, _, regente_ascendente_longitude, _, _, _ = get_planet_position(jd, regente_ascendente_swe_code, lang)
        
        regente_ascendente_signo_numero = int(regente_ascendente_longitude // 30)
        
        if lang == 'es':
            regente_ascendente_signo = signos_es[regente_ascendente_signo_numero]
            current_sign_map_for_regent_element = signo_a_elemento
        else:
            regente_ascendente_signo = signos_en[regente_ascendente_signo_numero] # Ensure English sign is used
            current_sign_map_for_regent_element = {
                "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
                "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
                "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
            }

        if regente_ascendente_signo in current_sign_map_for_regent_element:
            elemento_regente_ascendente = current_sign_map_for_regent_element[regente_ascendente_signo]
            balance_elemental_puntos[elemento_regente_ascendente] += PUNTOS_REGENTE_ASCENDENTE_EXTRA
            total_puntos_considerados += PUNTOS_REGENTE_ASCENDENTE_EXTRA # Suma estos puntos al total

        # Puntos extra para el regente del Ascendente (Rítmico)
    if lang == 'es':
        current_sign_map_for_regent_rhythm = signo_a_ritmo_es
    else:
        current_sign_map_for_regent_rhythm = signo_a_ritmo_en
        
        if regente_ascendente_signo in current_sign_map_for_regent_rhythm:
            ritmo_regente_ascendente = current_sign_map_for_regent_rhythm[regente_ascendente_signo]
            balance_ritmico_puntos[ritmo_regente_ascendente] += PUNTOS_REGENTE_ASCENDENTE_EXTRA
            # total_puntos_considerados ya fue incrementado

        # NUEVO: Puntos extra para el regente del Ascendente (Yin/Yang)
        if regente_ascendente_signo in signo_a_yin_yang:
            yin_yang_regente_ascendente = signo_a_yin_yang[regente_ascendente_signo]
            balance_yin_yang_puntos[yin_yang_regente_ascendente] += PUNTOS_REGENTE_ASCENDENTE_EXTRA
            # total_puntos_considerados ya fue incrementado

    # Puntos extra para el Medio Cielo (Elemental)
    mc_signo = None
    for house_num, signo, degree, minutes, house_longitude in house_positions:
        if house_num == 10: # Asumiendo que la Casa 10 es el MC
            mc_signo = signo
            break

    if mc_signo:
        if lang == 'es':
            current_mc_sign_map_element = signo_a_elemento
        else: # English
            current_mc_sign_map_element = {
                "Aries": "Fire", "Taurus": "Earth", "Gemini": "Air", "Cancer": "Water",
                "Leo": "Fire", "Virgo": "Earth", "Libra": "Air", "Scorpio": "Water",
                "Sagittarius": "Fire", "Capricorn": "Earth", "Aquarius": "Air", "Pisces": "Water",
            }
        
        if mc_signo in current_mc_sign_map_element:
            elemento_mc = current_mc_sign_map_element[mc_signo]
            balance_elemental_puntos[elemento_mc] += PUNTOS_MC_EXTRA
            total_puntos_considerados += PUNTOS_MC_EXTRA # Suma estos puntos al total

        # Puntos extra para el Medio Cielo (Rítmico)
    if lang == 'es':
        current_mc_sign_map_rhythm = signo_a_ritmo_es
    else:
        current_mc_sign_map_rhythm = signo_a_ritmo_en
        
        if mc_signo in current_mc_sign_map_rhythm:
            ritmo_mc = current_mc_sign_map_rhythm[mc_signo]
            balance_ritmico_puntos[ritmo_mc] += PUNTOS_MC_EXTRA
            # total_puntos_considerados ya fue incrementado

        # NUEVO: Puntos extra para el Medio Cielo (Yin/Yang)
        if mc_signo in signo_a_yin_yang:
            yin_yang_mc = signo_a_yin_yang[mc_signo]
            balance_yin_yang_puntos[yin_yang_mc] += PUNTOS_MC_EXTRA
            # total_puntos_considerados ya fue incrementado
            
    # Cálculo de porcentajes para balance elemental
    balance_elemental_porcentaje = {
        "Fuego": 0.0, "Tierra": 0.0, "Aire": 0.0, "Agua": 0.0
    }
    if lang == 'en':
        balance_elemental_porcentaje = {
            "Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0
        }

    if total_puntos_considerados > 0:
        for elemento, puntos_acumulados in balance_elemental_puntos.items():
            balance_elemental_porcentaje[elemento] = round((puntos_acumulados / total_puntos_considerados) * 100, 2)
            
    balance_elemental_porcentaje["Total_Puntos_Considerados"] = round(total_puntos_considerados, 2)

    balance_ritmico_porcentaje = {} # Initialize as empty
    if lang == 'es':
        balance_ritmico_porcentaje = {
            "Cardinal": 0.0, "Fijo": 0.0, "Mutable": 0.0
        }
    else: # English
        balance_ritmico_porcentaje = {
            "Cardinal": 0.0, "Fixed": 0.0, "Mutable": 0.0
        }

    if total_puntos_considerados > 0:
        for ritmo, puntos_acumulados in balance_ritmico_puntos.items():
            balance_ritmico_porcentaje[ritmo] = round((puntos_acumulados / total_puntos_considerados) * 100, 2)

    # NUEVO: Cálculo de porcentajes para balance Yin/Yang
    balance_yin_yang_porcentaje = {
        "Yin": 0.0, "Yang": 0.0
    }
    if total_puntos_considerados > 0:
        for tipo, puntos_acumulados in balance_yin_yang_puntos.items():
            balance_yin_yang_porcentaje[tipo] = round((puntos_acumulados / total_puntos_considerados) * 100, 2)

    # House longitudes from house_positions (Ascendant is house_positions[0])
    ascendente_longitude = house_positions[0][4]
    casa_2_longitude = house_positions[1][4]
    casa_3_longitude = house_positions[2][4]
    casa_4_longitude = house_positions[3][4]
    casa_5_longitude = house_positions[4][4]
    casa_6_longitude = house_positions[5][4]

    distancia_ascendente_casa2 = ((casa_2_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa3 = ((casa_3_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa4 = ((casa_4_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa5 = ((casa_5_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa6 = ((casa_6_longitude - ascendente_longitude) % 360)
    
    houses = {}
    for house_num, signo, degree, minutes, house_longitude in house_positions:
        houses[house_num] = {"signo": signo, "grado": degree, "minutos": minutes, "segundos": seconds}

    return jsonify({
        "fase_lunar": fase_lunar,
        "planetas": planet_positions,
        "casas": houses,
        "ascendente": ascendente_longitude,
        "distancia_ascendente_casa2": distancia_ascendente_casa2,
        "distancia_ascendente_casa3": distancia_ascendente_casa3,
        "distancia_ascendente_casa4": distancia_ascendente_casa4,
        "distancia_ascendente_casa5": distancia_ascendente_casa5,
        "distancia_ascendente_casa6": distancia_ascendente_casa6,
        "balance_elemental_porcentaje": balance_elemental_porcentaje,
        "balance_elemental_puntos": balance_elemental_puntos,
        "balance_ritmico_porcentaje": balance_ritmico_porcentaje,
        "balance_ritmico_puntos": balance_ritmico_puntos,
        "balance_yin_yang_porcentaje": balance_yin_yang_porcentaje, # NUEVO
        "balance_yin_yang_puntos": balance_yin_yang_puntos # NUEVO
    })

@app.route('/ver_carta', methods=['GET'])
def  ver_carta():
    fecha_param = request.args.get('fecha', default=None)
    lat = request.args.get('lat', type=float, default=None) 
    lon = request.args.get('lon', type=float, default=None)
    sistema_casas = request.args.get('sistema_casas', 'T') 
    lang = request.args.get('lang', default='es')

    if not lat or not lon:
        return jsonify({"error": "Se requiere latitud y longitud."}), 400

    if fecha_param:
        try:
            user_datetime = datetime.fromisoformat(fecha_param)
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use 'YYYY-MM-DDTHH:MM:SS'"}), 400
    else:
        user_datetime = datetime.now()

    timezone = get_timezone(lat, lon)

    user_datetime_utc = timezone.localize(user_datetime).astimezone(pytz.utc)

    jd = swe.julday(user_datetime_utc.year, user_datetime_utc.month, user_datetime_utc.day,
                    user_datetime_utc.hour + user_datetime_utc.minute / 60.0 + user_datetime_utc.second / 3600.0)
    
    luna_pos = swe.calc_ut(jd, swe.MOON)[0][0]
    sol_pos = swe.calc_ut(jd, swe.SUN)[0][0]

    fase_lunar_grados = (luna_pos - sol_pos) % 360

    if 0 <= fase_lunar_grados < 45:
        fase_lunar = "Luna Nueva"
    elif 45 <= fase_lunar_grados < 90:
        fase_lunar = "Luna Creciente"
    elif 90 <= fase_lunar_grados < 135:
        fase_lunar = "Cuarto Creciente"
    elif 135 <= fase_lunar_grados < 180:
        fase_lunar = "Gibosa Creciente"
    elif 180 <= fase_lunar_grados < 225:
        fase_lunar = "Luna Llena"
    elif 225 <= fase_lunar_grados < 270:
        fase_lunar = "Gibosa Menguante"
    elif 270 <= fase_lunar_grados < 315:
        fase_lunar = "Cuarto Menguante"
    elif 315 <= fase_lunar_grados < 360:
        fase_lunar = "Luna Menguante"
    else:
        fase_lunar = "Luna Nueva"

    planet_names_es = {
        "Sol": swe.SUN,
        "Luna": swe.MOON,
        "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS,
        "Marte": swe.MARS,
        "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN,
        "Urano": swe.URANUS,
        "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO,
        "Lilith": 13,
        "Quirón": swe.CHIRON,
        "Nodo Norte": 11,
    }

    planet_names_en = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
        "Lilith": 13,
        "Chiron": swe.CHIRON,
        "North Node": 11,
    }

    planet_names = planet_names_es if lang == 'es' else planet_names_en

    sistemas_casas = {
        "P": b'P', 
        "K": b'K', 
        "P": b'P', 
        "R": b'R', 
        "C": b'C', 
        "E": b'E',
        "W": b'W', 
        "T": b'T'  
    }

    house_system = sistemas_casas.get(sistema_casas, b'T')  

    planet_positions = {}
    previous_positions = {}
    
    for planet, swe_code in planet_names.items():
            signo, degree, minutes, longitude, speed, retrograde, estacionario = get_planet_position(jd, swe_code, lang)

            if planet in previous_positions:
                prev_speed = previous_positions[planet]['speed']
                if abs(speed) < 0.001: 
                    estacionario = True
                else:
                    estacionario = False

                if prev_speed > 0 and speed < 0:
                    estacionario = True 
            result, err = swe.calc(jd, swe_code)
    if err != 0:
        print(f"Error al calcular la posición del planeta: {err}")
    else:
        signo, degree, minutes, longitude = get_planet_position(jd, swe_code)
        print(f"{planet}: {signo} {degree}° {minutes}'")
        

    planet_positions = {}
    house_positions = get_houses(jd, lat, lon, house_system, lang)

    for planet, code in planet_names.items():
        signo, degree, minutes, longitude, speed, retrograde, estacionario = get_planet_position(jd, code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "casa": house,
            "longitud": longitude,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }

    ascendente_longitude = house_positions[0][4]
    casa_2_longitude = house_positions[1][4]
    casa_3_longitude = house_positions[2][4]
    casa_4_longitude = house_positions[3][4]
    casa_5_longitude = house_positions[4][4]
    casa_6_longitude = house_positions[5][4]

    distancia_ascendente_casa2 = ((casa_2_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa3 = ((casa_3_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa4 = ((casa_4_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa5 = ((casa_5_longitude - ascendente_longitude) % 360)
    distancia_ascendente_casa6 = ((casa_6_longitude - ascendente_longitude) % 360)
    
    houses = {}
    for house_num, signo, degree, minutes, house_longitude in house_positions:
        houses[house_num] = {"signo": signo, "grado": degree, "minutos": minutes}

    return jsonify({
        "fase_lunar": fase_lunar,
        "planetas": planet_positions,
        "casas": houses,
        "ascendente": ascendente_longitude,
        "distancia_ascendente_casa2": distancia_ascendente_casa2,
        "distancia_ascendente_casa3": distancia_ascendente_casa3,
        "distancia_ascendente_casa4": distancia_ascendente_casa4,
        "distancia_ascendente_casa5": distancia_ascendente_casa5,
        "distancia_ascendente_casa6": distancia_ascendente_casa6
        
    })

PLANETAS = {
        "Sol": swe.SUN,
        "Luna": swe.MOON,
        "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS,
        "Marte": swe.MARS,
        "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN,
        "Urano": swe.URANUS,
        "Neptuno": swe.NEPTUNE,
        "Plutón": swe.PLUTO,
        "Lilith": 13,
        "Quirón": swe.CHIRON,
        "Nodo": 11,
}

SIGNOS = {
    "Aries": 0,
    "Tauro": 1,
    "Géminis": 2,
    "Cáncer": 3,
    "Leo": 4,
    "Virgo": 5,
    "Libra": 6,
    "Escorpio": 7,
    "Sagitario": 8,
    "Capricornio": 9,
    "Acuario": 10,
    "Piscis": 11
}


def julday_to_datetime(jd):
    jd = jd + 0.5
    Z = int(jd)
    F = jd - Z
    A = int((Z - 1867216.25) / 36524.25)
    B = Z + 1 + A - int(A / 4)
    C = B + 1524
    D = int((C - 122.1) / 365.25)
    E = int(365.25 * D)
    G = int((C - E) / 30.6001)

    day = C - E - int(30.6001 * G) + F
    month = G - 1 if G < 14 else G - 13
    year = D - 4716 if month > 2 else D - 4715

    day_int = int(day)
    fractional_day = day - day_int
    hours = fractional_day * 24
    hour = int(hours)
    minutes = int((hours - hour) * 60)
    seconds = int((((hours - hour) * 60) - minutes) * 60)

    return datetime(year, month, day_int, hour, minutes, seconds)

def calcular_longitud_planeta(jd, planeta):
    result, ret = swe.calc(jd, planeta)
    return result[0]

def calcular_velocidad_planeta(jd, planeta):
    result, ret = swe.calc(jd, planeta)
    return result[3] # La velocidad en longitud eclíptica está en el índice 3


def calcular_signo_y_grado(longitud):
    signos = ['Aries', 'Tauro', 'Géminis', 'Cáncer', 'Leo', 'Virgo',
              'Libra', 'Escorpio', 'Sagitario', 'Capricornio', 'Acuario', 'Piscis']
    grado_total = longitud % 360  # Asegurarse que la longitud esté entre 0 y 360
    grado_signo = int(grado_total / 30)
    grado_exacto = int(grado_total % 30)
    minutos = round((grado_total - int(grado_total)) * 60)
    signo = signos[grado_signo]
    return signo, grado_exacto, minutos

def refinar_transito(planeta, jd_low, jd_high, grado_objetivo_total, signo_objetivo_index, retrogrado_deseado, tolerancia=1e-6):
    while (jd_high - jd_low) > tolerancia:
        jd_mid = (jd_low + jd_high) / 2.0
        long_mid = calcular_longitud_planeta(jd_mid, planeta)
        vel_mid = calcular_velocidad_planeta(jd_mid, planeta)
        long_low = calcular_longitud_planeta(jd_low, planeta)

        condicion_retrogrado = (retrogrado_deseado is None) or (retrogrado_deseado and vel_mid < 0) or (not retrogrado_deseado and vel_mid >= 0)

        if (long_low - grado_objetivo_total) * (long_mid - grado_objetivo_total) > 0:
            jd_low = jd_mid
        elif condicion_retrogrado:
            jd_high = jd_mid
        else:
            jd_low = jd_mid # Si no cumple la condición de retrogradación, seguimos buscando en la otra mitad
    return jd_high

def encontrar_transito_grado(planeta, grado_objetivo_interno, signo_objetivo_index, fecha_inicio, fecha_fin, buscar_retrogrado):
    jd_inicio = swe.julday(
        fecha_inicio.year, fecha_inicio.month, fecha_inicio.day,
        fecha_inicio.hour + fecha_inicio.minute / 60.0 + fecha_inicio.second / 3600.0
    )
    jd_fin = swe.julday(
        fecha_fin.year, fecha_fin.month, fecha_fin.day,
        fecha_fin.hour + fecha_fin.minute / 60.0 + fecha_fin.second / 3600.0
    )

    paso = 1 / 24.0 # Búsqueda por hora inicialmente
    total_steps = int((jd_fin - jd_inicio) / paso)

    long_anterior = calcular_longitud_planeta(jd_inicio, planeta)
    vel_anterior = calcular_velocidad_planeta(jd_inicio, planeta)
    jd_prev = jd_inicio
    encontrados = []
    nombre_signo_objetivo = list(SIGNOS.keys())[signo_objetivo_index]
    grado_objetivo_total = signo_objetivo_index * 30 + grado_objetivo_interno

    for i in range(1, total_steps + 1):
        jd_actual = jd_inicio + i * paso
        long_actual = calcular_longitud_planeta(jd_actual, planeta)
        vel_actual = calcular_velocidad_planeta(jd_actual, planeta)

        condicion_retrogrado_actual = (buscar_retrogrado is None) or (buscar_retrogrado and vel_actual < 0) or (not buscar_retrogrado and vel_actual >= 0)
        cruce_detectado = False

        if grado_objetivo_interno == 0 and nombre_signo_objetivo == "Aries":
            if (long_anterior > 359 and long_actual <= 1) or (long_anterior <= 1 and long_actual > 359):
                cruce_detectado = True
        else:
            if (long_anterior < grado_objetivo_total and long_actual >= grado_objetivo_total) or \
               (long_anterior > grado_objetivo_total and long_actual <= grado_objetivo_total):
                cruce_detectado = True

        if cruce_detectado and condicion_retrogrado_actual:
            jd_exacto = refinar_transito(planeta, jd_prev, jd_actual, grado_objetivo_total, signo_objetivo_index, buscar_retrogrado)
            fecha_evento = julday_to_datetime(jd_exacto)
            signo_evento, grado_evento, minutos_evento = calcular_signo_y_grado(calcular_longitud_planeta(jd_exacto, planeta))
            vel_evento = calcular_velocidad_planeta(jd_exacto, planeta)
            es_retrogrado = vel_evento < 0

            if signo_evento == nombre_signo_objetivo and grado_evento == grado_objetivo_interno:
                retro_str = " (retrógrado)" if es_retrogrado else ""
                if buscar_retrogrado is None or buscar_retrogrado == es_retrogrado:
                    print(f"El planeta cruzó los {grado_objetivo_interno}° de {nombre_signo_objetivo} el {fecha_evento} UTC ({grado_evento}° {minutos_evento}'){retro_str}")
                    encontrados.append(fecha_evento)
                    jd_prev = jd_actual + paso * 4
                    long_anterior = long_actual
                    vel_anterior = vel_actual
                    continue

        long_anterior = long_actual
        vel_anterior = vel_actual
        jd_prev = jd_actual

    if not encontrados:
        retro_msg = " retrógrado" if buscar_retrogrado else (" no retrógrado" if buscar_retrogrado is not None else "")
        print(f"No se encontró el tránsito específico al grado {grado_objetivo_interno}° de {nombre_signo_objetivo}{retro_msg} en el rango de fechas.")

    return encontrados

def encontrar_planeta_en_signo(planeta, signo_objetivo_index, fecha_inicio, fecha_fin, buscar_retrogrado, resolucion_horas=24):
    jd_inicio = swe.julday(
        fecha_inicio.year, fecha_inicio.month, fecha_inicio.day,
        0
    )
    jd_fin = swe.julday(
        fecha_fin.year, fecha_fin.month, fecha_fin.day,
        23.9999
    )

    paso = resolucion_horas / 24.0
    total_steps = int((jd_fin - jd_inicio) / paso) + 1
    fechas_en_signo = []
    signo_objetivo_nombre = list(SIGNOS.keys())[signo_objetivo_index]

    for i in range(total_steps):
        jd_actual = jd_inicio + i * paso
        long_actual = calcular_longitud_planeta(jd_actual, planeta)
        vel_actual = calcular_velocidad_planeta(jd_actual, planeta)
        signo_actual_index = int((long_actual % 360) / 30)
        es_retrogrado = vel_actual < 0

        if signo_actual_index == signo_objetivo_index:
            if buscar_retrogrado is None or buscar_retrogrado == es_retrogrado:
                fecha_actual = julday_to_datetime(jd_actual).date()
                if fecha_actual not in fechas_en_signo:
                    fechas_en_signo.append(fecha_actual)

    if fechas_en_signo:
        nombre_planeta = list(PLANETAS.keys())[list(PLANETAS.values()).index(planeta)]
        retro_msg = " (retrógrado)" if buscar_retrogrado else (" (no retrógrado)" if buscar_retrogrado is not None else "")
        print(f"El planeta {nombre_planeta} estuvo en {signo_objetivo_nombre}{retro_msg} en las siguientes fechas:")
        for fecha in fechas_en_signo:
            print(fecha)
    else:
        nombre_planeta = list(PLANETAS.keys())[list(PLANETAS.values()).index(planeta)]
        retro_msg = " retrógrado" if buscar_retrogrado else (" no retrógrado" if buscar_retrogrado is not None else "")
        print(f"El planeta {nombre_planeta} no estuvo en {signo_objetivo_nombre}{retro_msg} durante el rango de fechas especificado.")

    return fechas_en_signo

def encontrar_aspecto(planeta1, planeta2, aspecto_str, fecha_inicio, fecha_fin, tolerancia=1.0):
    jd_inicio = swe.julday(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day, 0)
    jd_fin = swe.julday(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23.9999)
    paso = 1 / 24.0 # Búsqueda por hora inicialmente
    total_steps = int((jd_fin - jd_inicio) / paso) + 1
    encontrados = []
    angulo_objetivo = ASPECTOS.get(aspecto_str)
    if angulo_objetivo is None:
        print(f"Aspecto '{aspecto_str}' no reconocido.")
        return encontrados

    long_anterior_p1 = calcular_longitud_planeta(jd_inicio, planeta1)
    long_anterior_p2 = calcular_longitud_planeta(jd_inicio, planeta2)
    jd_prev = jd_inicio

    for i in range(1, total_steps + 1):
        jd_actual = jd_inicio + i * paso
        long_actual_p1 = calcular_longitud_planeta(jd_actual, planeta1)
        long_actual_p2 = calcular_longitud_planeta(jd_actual, planeta2)
        diferencia_anterior = abs(long_anterior_p1 - long_anterior_p2) % 360
        diferencia_anterior = min(diferencia_anterior, 360 - diferencia_anterior)
        diferencia_actual = abs(long_actual_p1 - long_actual_p2) % 360
        diferencia_actual = min(diferencia_actual, 360 - diferencia_actual)

        if (diferencia_anterior - angulo_objetivo) * (diferencia_actual - angulo_objetivo) < 0:
            # Se detectó un cruce, refinar la búsqueda
            jd_exacto = refinar_aspecto(planeta1, planeta2, angulo_objetivo, jd_prev, jd_actual)
            fecha_evento = julday_to_datetime(jd_exacto)
            long_exacto_p1 = calcular_longitud_planeta(jd_exacto, planeta1)
            long_exacto_p2 = calcular_longitud_planeta(jd_exacto, planeta2)
            diferencia_exacta = abs(long_exacto_p1 - long_exacto_p2) % 360
            diferencia_exacta = min(diferencia_exacta, 360 - diferencia_exacta)

            print(f"{list(PLANETAS.keys())[list(PLANETAS.values()).index(planeta1)]} en {calcular_signo_y_grado(long_exacto_p1)[0]} {calcular_signo_y_grado(long_exacto_p1)[1]}° aspecta en {aspecto_str} a {list(PLANETAS.keys())[list(PLANETAS.values()).index(planeta2)]} en {calcular_signo_y_grado(long_exacto_p2)[0]} {calcular_signo_y_grado(long_exacto_p2)[1]}° el {fecha_evento} UTC.")
            encontrados.append(fecha_evento)
            jd_prev = jd_actual + paso * 4
            long_anterior_p1 = long_actual_p1
            long_anterior_p2 = long_actual_p2
            continue

        long_anterior_p1 = long_actual_p1
        long_anterior_p2 = long_actual_p2
        jd_prev = jd_actual

    return encontrados

ASPECTOS = {
    "Conjuncion": 0.0,
    "Cuadratura": 90.0,
    "Trigono": 120.0,
    "Oposicion": 180.0,
}
def calcular_diferencia_angular(jd, planeta1, planeta2):
    long1 = calcular_longitud_planeta(jd, planeta1)
    long2 = calcular_longitud_planeta(jd, planeta2)
    diferencia = abs(long1 - long2) % 360
    return min(diferencia, 360 - diferencia)

def encontrar_aspecto(planeta1, planeta2, aspecto_str, fecha_inicio, fecha_fin, tolerancia=1.0):
    jd_inicio = swe.julday(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day, 0)
    jd_fin = swe.julday(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23.9999)
    paso = 1 / 24.0 # Búsqueda por hora inicialmente
    total_steps = int((jd_fin - jd_inicio) / paso) + 1
    encontrados = []
    angulo_objetivo = ASPECTOS.get(aspecto_str)
    if angulo_objetivo is None:
        print(f"Aspecto '{aspecto_str}' no reconocido.")
        return encontrados

    long_anterior_p1 = calcular_longitud_planeta(jd_inicio, planeta1)
    long_anterior_p2 = calcular_longitud_planeta(jd_inicio, planeta2)
    jd_prev = jd_inicio

    for i in range(1, total_steps + 1):
        jd_actual = jd_inicio + i * paso
        long_actual_p1 = calcular_longitud_planeta(jd_actual, planeta1)
        long_actual_p2 = calcular_longitud_planeta(jd_actual, planeta2)
        diferencia_anterior = abs(long_anterior_p1 - long_anterior_p2) % 360
        diferencia_anterior = min(diferencia_anterior, 360 - diferencia_anterior)
        diferencia_actual = abs(long_actual_p1 - long_actual_p2) % 360
        diferencia_actual = min(diferencia_actual, 360 - diferencia_actual)

        if (diferencia_anterior - angulo_objetivo) * (diferencia_actual - angulo_objetivo) < 0:
            # Se detectó un cruce, refinar la búsqueda
            jd_exacto = refinar_aspecto(planeta1, planeta2, angulo_objetivo, jd_prev, jd_actual)
            fecha_evento = julday_to_datetime(jd_exacto)
            long_exacto_p1 = calcular_longitud_planeta(jd_exacto, planeta1)
            long_exacto_p2 = calcular_longitud_planeta(jd_exacto, planeta2)
            diferencia_exacta = abs(long_exacto_p1 - long_exacto_p2) % 360
            diferencia_exacta = min(diferencia_exacta, 360 - diferencia_exacta)

            print(f"{list(PLANETAS.keys())[list(PLANETAS.values()).index(planeta1)]} en {calcular_signo_y_grado(long_exacto_p1)[0]} {calcular_signo_y_grado(long_exacto_p1)[1]}° aspecta en {aspecto_str} a {list(PLANETAS.keys())[list(PLANETAS.values()).index(planeta2)]} en {calcular_signo_y_grado(long_exacto_p2)[0]} {calcular_signo_y_grado(long_exacto_p2)[1]}° el {fecha_evento} UTC.")
            encontrados.append(fecha_evento)
            jd_prev = jd_actual + paso * 4
            long_anterior_p1 = long_actual_p1
            long_anterior_p2 = long_actual_p2
            continue

        long_anterior_p1 = long_actual_p1
        long_anterior_p2 = long_actual_p2
        jd_prev = jd_actual

    return encontrados

def refinar_aspecto(planeta1, planeta2, angulo_objetivo, jd_low, jd_high, tolerancia=1e-6):
    while (jd_high - jd_low) > tolerancia:
        jd_mid = (jd_low + jd_high) / 2.0
        long_mid_p1 = calcular_longitud_planeta(jd_mid, planeta1)
        long_mid_p2 = calcular_longitud_planeta(jd_mid, planeta2)
        diferencia_mid = abs(long_mid_p1 - long_mid_p2) % 360
        diferencia_mid = min(diferencia_mid, 360 - diferencia_mid)
        long_low_p1 = calcular_longitud_planeta(jd_low, planeta1)
        long_low_p2 = calcular_longitud_planeta(jd_low, planeta2)
        diferencia_low = abs(long_low_p1 - long_low_p2) % 360
        diferencia_low = min(diferencia_low, 360 - diferencia_low)

        if (diferencia_low - angulo_objetivo) * (diferencia_mid - angulo_objetivo) > 0:
            jd_low = jd_mid
        else:
            jd_high = jd_mid
    return jd_high


@app.route('/buscar_astrologia', methods=['POST'])
def buscar_astrologia():

    data = request.get_json()
    planeta_signo_data = data.get('planeta_signo')
    aspecto_data = data.get('aspecto')
    año_inicio = data.get('año_inicio')
    año_fin = data.get('año_fin')

    if año_inicio is None or año_fin is None:
        return jsonify({'error': 'Faltan los años de inicio o fin'}), 400

    fecha_inicio = datetime(año_inicio, 1, 1)
    fecha_fin = datetime(año_fin, 12, 31)

    resultados_transito = None
    resultados_aspecto = None

    if planeta_signo_data:
        planeta_str = planeta_signo_data.get('planeta')
        signo_str = planeta_signo_data.get('signo')
        grado_input = planeta_signo_data.get('grado')
        retrogrado = planeta_signo_data.get('retrogrado')

        if planeta_str and signo_str:
            planeta_str = planeta_str.strip().capitalize()
            signo_str = signo_str.strip().capitalize()

            if planeta_str not in PLANETAS or signo_str not in SIGNOS:
                return jsonify({'error': 'Planeta o signo no reconocido en la búsqueda de tránsito'}), 400

            planeta = PLANETAS[planeta_str]
            signo_objetivo_index = SIGNOS[signo_str]

            buscar_retrogrado = None
            if retrogrado is True:
                buscar_retrogrado = True
            elif retrogrado is False:
                buscar_retrogrado = False

            if grado_input is not None:
                try:
                    grado_deseado = int(grado_input)
                    if 0 <= grado_deseado <= 29:
                        resultados_transito = encontrar_transito_grado(planeta, grado_deseado, signo_objetivo_index, fecha_inicio, fecha_fin, buscar_retrogrado)
                    else:
                        return jsonify({'error': 'El grado debe estar entre 0 y 29 en la búsqueda de tránsito'}), 400
                except ValueError:
                    return jsonify({'error': 'El grado ingresado no es un número válido en la búsqueda de tránsito'}), 400
            else:
                resultados_transito = encontrar_planeta_en_signo(planeta, signo_objetivo_index, fecha_inicio, fecha_fin, buscar_retrogrado)

    if aspecto_data:
        planeta1_str = aspecto_data.get('planeta1')
        planeta2_str = aspecto_data.get('planeta2')
        aspecto_str = aspecto_data.get('tipo')

        if planeta1_str and planeta2_str and aspecto_str:
            planeta1_str = planeta1_str.strip().capitalize()
            planeta2_str = planeta2_str.strip().capitalize()
            aspecto_str = aspecto_str.strip().capitalize()

            if planeta1_str not in PLANETAS or planeta2_str not in PLANETAS or aspecto_str not in ASPECTOS:
                return jsonify({'error': 'Uno de los planetas o el aspecto no es reconocido'}), 400

            planeta1 = PLANETAS[planeta1_str]
            planeta2 = PLANETAS[planeta2_str]
            resultados_aspecto = encontrar_aspecto(planeta1, planeta2, aspecto_str, fecha_inicio, fecha_fin)

    resultados_finales = []
    if resultados_transito is not None and resultados_aspecto is not None:
        fechas_transito = set()
        for res in resultados_transito:
            if isinstance(res, datetime):
                fechas_transito.add(res.date())
            elif isinstance(res, date):
                fechas_transito.add(res)

        fechas_aspecto = set(res.date() for res in resultados_aspecto)
        fechas_comunes = list(fechas_transito.intersection(fechas_aspecto))
        resultados_finales = [str(datetime.fromisoformat(str(fecha) + 'T00:00:00')) + ' UTC' for fecha in fechas_comunes]
    elif resultados_transito is not None:
        resultados_finales = [str(res) for res in resultados_transito]
    elif resultados_aspecto is not None:
        resultados_finales = [str(res) for res in resultados_aspecto]
    else:
        resultados_finales = []

    return jsonify({'resultados': resultados_finales})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
