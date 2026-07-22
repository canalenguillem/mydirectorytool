import requests
from decouple import config

API_KEY = config("GOOGLE_API_KEY")  # Assegura't que és la variable correcta
PLACE_ID = "ChIJneQLS5_AlxIRMd7egwbdcyE"  # Substitueix pel teu place_id de prova

url = (
    "https://maps.googleapis.com/maps/api/place/details/json"
    f"?place_id={PLACE_ID}&fields=photos&key={API_KEY}"
)


response = requests.get(url)
data = response.json()

print("Status:", data.get("status"))
print("Photos:", data.get("result", {}).get("photos"))
print("Error message:", data.get("error_message"))

print(f"the url: {url}")