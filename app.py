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
        house_positions.append((i + 1, signo, degree, minutes,seconds, house))
    return house_positions


def determine_house(longitude, house_positions):
    for i, (_, _, _, _, _, house_longitude) in enumerate(house_positions):
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
    signo = signos_es[signo_numero]
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
    house_positions = get_houses(jd, lat, lon, house_system)

    for planet, code in planet_names.items():
        signo, degree, minutes,seconds, longitude, speed,retrograde, estacionario = get_planet_position(jd, code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "casa": house,
            "longitud": longitude,
            "retrógrado": speed < 0,
            "estacionario": estacionario
        }

    # Obtener las posiciones de las casas
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

    # Respuesta final con la carta astral y la fecha y hora de la repetición solar
    return jsonify({
        "planetas": planet_positions,
        "casas": houses,
        "ascendente": ascendente_longitude,
        "distancia_ascendente_casa2": distancia_ascendente_casa2,
        "distancia_ascendente_casa3": distancia_ascendente_casa3,
        "distancia_ascendente_casa4": distancia_ascendente_casa4,
        "distancia_ascendente_casa5": distancia_ascendente_casa5,
        "distancia_ascendente_casa6": distancia_ascendente_casa6,
        "fecha_repeticion": solar_return_iso  # Fecha y hora de la repetición solar
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
        signo, degree, minutes, longitude, speed, seconds, retrograde, estacionario = get_planet_position(jd, swe_code, lang)

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
        "planetas": planet_positions,
    })
    

@app.route('/mi_carta', methods=['GET'])
def  mi_carta():
    fecha_param = request.args.get('fecha', default=None)
    lat = request.args.get('lat', type=float, default=None) 
    lang = request.args.get('lang', default='es')
    lon = request.args.get('lon', type=float, default=None)
    sistema_casas = request.args.get('sistema_casas', 'T') 

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

    signos = signos_es if lang == "es" else signos_en

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
        "P": b'P',  # Placidus
        "K": b'K',  # Koch
        "P": b'P',  # Porfirio
        "R": b'R',  # Regiomontanus
        "C": b'C',  # Campanus
        "E": b'E',  # Equatorial
        "W": b'W',  # Whole sign
        "T": b'T'   # Polich-Page
    }

    house_system = sistemas_casas.get(sistema_casas, b'T')  

    for planet, swe_code in planet_names.items():
        result, err = swe.calc(jd, swe_code)
    
    if err != 0:
        print(f"Error al calcular la posición del planeta: {err}")
    else:
        signo, degree, minutes, seconds, longitude, = get_planet_position(jd, swe_code)
        print(f"{planet}: {signo} {degree}° {minutes}'")
        

    planet_positions = {}
    house_positions = get_houses(jd, lat, lon, house_system, lang)

   

    for planet, code in planet_names.items():
        signo, degree, minutes, longitude, speed, seconds, retrograde, estacionario = get_planet_position(jd, code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "casa": house,
            "retrógrado": speed < 0
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
            signo, degree, minutes, seconds, longitude, speed, retrograde, estacionario = get_planet_position(jd, swe_code, lang)

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
        signo, degree, minutes, longitude, speed, seconds, retrograde, estacionario = get_planet_position(jd, code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "casa": house,
            "longitud": longitude,
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
    for house_num, signo, degree, minutes, seconds, house_longitude in house_positions:
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
        "distancia_ascendente_casa6": distancia_ascendente_casa6
        
    })


@app.route('/ver_carta', methods=['GET'])
def  ver_carta():
    fecha_param = request.args.get('fecha', default=None)
    lat = request.args.get('lat', type=float, default=None) 
    lang = request.args.get('lang', default='es')
    lon = request.args.get('lon', type=float, default=None)
    sistema_casas = request.args.get('sistema_casas', 'T') 

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

    signos = signos_es if lang == "es" else signos_en

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
        "P": b'P',  # Placidus
        "K": b'K',  # Koch
        "P": b'P',  # Porfirio
        "R": b'R',  # Regiomontanus
        "C": b'C',  # Campanus
        "E": b'E',  # Equatorial
        "W": b'W',  # Whole sign
        "T": b'T'   # Polich-Page
    }

    house_system = sistemas_casas.get(sistema_casas, b'T')  

    for planet, swe_code in planet_names.items():
        result, err = swe.calc(jd, swe_code)
    
    if err != 0:
        print(f"Error al calcular la posición del planeta: {err}")
    else:
        signo, degree, minutes, seconds, longitude, = get_planet_position(jd, swe_code)
        print(f"{planet}: {signo} {degree}° {minutes}'")
        

    planet_positions = {}
    house_positions = get_houses(jd, lat, lon, house_system, lang)

   

    for planet, code in planet_names.items():
        signo, degree, minutes, longitude, speed, seconds, retrograde, estacionario = get_planet_position(jd, code, lang)
        house = determine_house(longitude, house_positions)

        planet_positions[planet] = {
            "signo": signo,
            "grado": degree,
            "minutos": minutes,
            "segundos": seconds,
            "casa": house,
            "retrógrado": speed < 0
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
