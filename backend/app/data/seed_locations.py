"""Ciudades semilla para el pipeline de siembra masiva (ver seed_queue.py).

Cada directorio (instalación de MyDirectoryTool) se centra en un país
concreto, elegido al configurarlo -- ver `DIRECTORY_COUNTRY_CODE` en
`init_db()` (database.py). Este fichero es una librería de datos
compartida entre TODOS los directorios que puedan desplegarse con este
mismo código (uno por país cuando toque), no una lista que se inserte
entera en cada instalación: `init_db()` solo inserta, vía `INSERT OR
IGNORE`, las ciudades del país configurado para *esa* instalación
concreta. Un directorio de restaurantes en España no debe arrastrar 50
ciudades de EEUU sin usar solo porque el código las conoce.

Las ciudades añadidas después a mano (ej. Manacor) usan `tier='manual'` y
no viven aquí, se crean vía `POST /seed/locations`.

SPAIN_CAPITALS: las 50 capitales de provincia + Ceuta y Melilla. Lista fija
y estable (división provincial oficial), no requiere verificación externa.

USA_MAIN_CITIES: la ciudad más poblada de cada uno de los 50 estados --
NO necesariamente la capital política (p.ej. Nueva York, no Albany; Los
Ángeles, no Sacramento), tal y como se pidió ("principales ciudades de
cada estado"). Verificado contra estimaciones de población recientes del
Census Bureau vía Wikipedia
(https://en.wikipedia.org/wiki/List_of_largest_cities_of_U.S._states_and_territories_by_population,
consultado 30 de julio de 2026) en vez de completarse de memoria -- p.ej.
Alabama ya no es Birmingham sino Huntsville, que la superó recientemente.
Antes de dar la lista por definitiva conviene recontrastarla si pasa mucho
tiempo desde esa fecha, porque el ranking de población de ciudades cambia.
"""

# (country_code, name, region)
SPAIN_CAPITALS: list[tuple[str, str, str]] = [
    ("ES", "Vitoria-Gasteiz", "País Vasco"),
    ("ES", "Albacete", "Castilla-La Mancha"),
    ("ES", "Alicante", "Comunidad Valenciana"),
    ("ES", "Almería", "Andalucía"),
    ("ES", "Oviedo", "Asturias"),
    ("ES", "Ávila", "Castilla y León"),
    ("ES", "Badajoz", "Extremadura"),
    ("ES", "Palma", "Illes Balears"),
    ("ES", "Barcelona", "Cataluña"),
    ("ES", "Burgos", "Castilla y León"),
    ("ES", "Cáceres", "Extremadura"),
    ("ES", "Cádiz", "Andalucía"),
    ("ES", "Santander", "Cantabria"),
    ("ES", "Castellón de la Plana", "Comunidad Valenciana"),
    ("ES", "Ciudad Real", "Castilla-La Mancha"),
    ("ES", "Córdoba", "Andalucía"),
    ("ES", "Cuenca", "Castilla-La Mancha"),
    ("ES", "A Coruña", "Galicia"),
    ("ES", "Girona", "Cataluña"),
    ("ES", "Granada", "Andalucía"),
    ("ES", "Guadalajara", "Castilla-La Mancha"),
    ("ES", "San Sebastián", "País Vasco"),
    ("ES", "Huelva", "Andalucía"),
    ("ES", "Huesca", "Aragón"),
    ("ES", "Jaén", "Andalucía"),
    ("ES", "Logroño", "La Rioja"),
    ("ES", "Las Palmas de Gran Canaria", "Canarias"),
    ("ES", "León", "Castilla y León"),
    ("ES", "Lleida", "Cataluña"),
    ("ES", "Lugo", "Galicia"),
    ("ES", "Madrid", "Comunidad de Madrid"),
    ("ES", "Málaga", "Andalucía"),
    ("ES", "Murcia", "Región de Murcia"),
    ("ES", "Pamplona", "Comunidad Foral de Navarra"),
    ("ES", "Ourense", "Galicia"),
    ("ES", "Palencia", "Castilla y León"),
    ("ES", "Pontevedra", "Galicia"),
    ("ES", "Salamanca", "Castilla y León"),
    ("ES", "Santa Cruz de Tenerife", "Canarias"),
    ("ES", "Segovia", "Castilla y León"),
    ("ES", "Sevilla", "Andalucía"),
    ("ES", "Soria", "Castilla y León"),
    ("ES", "Tarragona", "Cataluña"),
    ("ES", "Teruel", "Aragón"),
    ("ES", "Toledo", "Castilla-La Mancha"),
    ("ES", "Valencia", "Comunidad Valenciana"),
    ("ES", "Valladolid", "Castilla y León"),
    ("ES", "Bilbao", "País Vasco"),
    ("ES", "Zamora", "Castilla y León"),
    ("ES", "Zaragoza", "Aragón"),
    ("ES", "Ceuta", "Ceuta"),
    ("ES", "Melilla", "Melilla"),
]

# (country_code, name, region)
USA_MAIN_CITIES: list[tuple[str, str, str]] = [
    ("US", "Huntsville", "Alabama"),
    ("US", "Anchorage", "Alaska"),
    ("US", "Phoenix", "Arizona"),
    ("US", "Little Rock", "Arkansas"),
    ("US", "Los Angeles", "California"),
    ("US", "Denver", "Colorado"),
    ("US", "Bridgeport", "Connecticut"),
    ("US", "Wilmington", "Delaware"),
    ("US", "Jacksonville", "Florida"),
    ("US", "Atlanta", "Georgia"),
    ("US", "Honolulu", "Hawaii"),
    ("US", "Boise", "Idaho"),
    ("US", "Chicago", "Illinois"),
    ("US", "Indianapolis", "Indiana"),
    ("US", "Des Moines", "Iowa"),
    ("US", "Wichita", "Kansas"),
    ("US", "Louisville", "Kentucky"),
    ("US", "New Orleans", "Louisiana"),
    ("US", "Portland", "Maine"),
    ("US", "Baltimore", "Maryland"),
    ("US", "Boston", "Massachusetts"),
    ("US", "Detroit", "Michigan"),
    ("US", "Minneapolis", "Minnesota"),
    ("US", "Jackson", "Mississippi"),
    ("US", "Kansas City", "Missouri"),
    ("US", "Billings", "Montana"),
    ("US", "Omaha", "Nebraska"),
    ("US", "Las Vegas", "Nevada"),
    ("US", "Manchester", "New Hampshire"),
    ("US", "Newark", "New Jersey"),
    ("US", "Albuquerque", "New Mexico"),
    ("US", "New York", "New York"),
    ("US", "Charlotte", "North Carolina"),
    ("US", "Fargo", "North Dakota"),
    ("US", "Columbus", "Ohio"),
    ("US", "Oklahoma City", "Oklahoma"),
    ("US", "Portland", "Oregon"),
    ("US", "Philadelphia", "Pennsylvania"),
    ("US", "Providence", "Rhode Island"),
    ("US", "Charleston", "South Carolina"),
    ("US", "Sioux Falls", "South Dakota"),
    ("US", "Nashville", "Tennessee"),
    ("US", "Houston", "Texas"),
    ("US", "Salt Lake City", "Utah"),
    ("US", "Burlington", "Vermont"),
    ("US", "Virginia Beach", "Virginia"),
    ("US", "Seattle", "Washington"),
    ("US", "Charleston", "West Virginia"),
    ("US", "Milwaukee", "Wisconsin"),
    ("US", "Cheyenne", "Wyoming"),
]

# Un directorio nuevo en un país sin lista todavía (Corea del Sur, etc.)
# simplemente añade su propia lista aquí y una entrada en este dict --
# init_db() la recoge sola en cuanto DIRECTORY_COUNTRY_CODE la referencia.
SEED_CITIES_BY_COUNTRY: dict[str, list[tuple[str, str, str]]] = {
    "ES": SPAIN_CAPITALS,
    "US": USA_MAIN_CITIES,
}


def seed_locations_for(country_codes: list[str]) -> list[tuple[str, str, str, str]]:
    """Filas (country_code, name, region, tier) listas para insertar en
    `seed_location`, limitadas a los países pedidos."""
    rows = []
    for requested_code in country_codes:
        for country_code, name, region in SEED_CITIES_BY_COUNTRY.get(requested_code, []):
            rows.append((country_code, name, region, "capital"))
    return rows
