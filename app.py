import streamlit as st
import folium
from streamlit_folium import st_folium
from gedcom.parser import Parser
from datetime import datetime
import tempfile

# Datei laden
gedcom_file = 'krendl-4Gen.ged'

# Parser vorbereiten
gedcom_parser = Parser()

uploaded_file = st.file_uploader("Upload GEDCOM file", type=["ged"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ged") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name

    gedcom_parser.parse_file(tmp_file_path)

#with open(gedcom_file, 'r', encoding='utf-8') as file:

# Ereignisse extrahieren
events = []
for element in gedcom_parser.get_element_list():
    if element.get_tag() == 'INDI':
        name = element.get_name()
        for child in element.get_child_elements():
            if child.get_tag() in ['BIRT', 'DEAT', 'MARR']:
                date = None
                lat, lon = None, None
                for sub in child.get_child_elements():
                    if sub.get_tag() == 'DATE':
                        try:
                            date = datetime.strptime(sub.get_value(), "%d %b %Y")
                        except:
                            continue
                    if sub.get_tag() == 'PLAC':
                        for m in sub.get_child_elements():
                            if m.get_tag() == 'MAP':
                                for coord in m.get_child_elements():
                                    if coord.get_tag() == 'LATI':
                                        lat = float(coord.get_value().replace('N','').replace('S','-'))
                                    if coord.get_tag() == 'LONG':
                                        lon = float(coord.get_value().replace('E','').replace('W','-'))
                if lat and lon and date:
                    events.append({
                        'name': name,
                        'event': child.get_tag(),
                        'date': date,
                        'lat': lat,
                        'lon': lon
                    })

# Zeitfilter
st.title("📍 Ahnenkarte nach Zeit")
start_year, end_year = st.slider("Zeitraum auswählen", 1700, 2025, (1800, 1900))

# Karte
m = folium.Map(location=[48.3, 14.3], zoom_start=5)

# Marker setzen
for e in events:
    if start_year <= e['date'].year <= end_year:
        folium.Marker(
            location=[e['lat'], e['lon']],
            popup=f"{e['name']} – {e['event']} am {e['date'].date()}",
            icon=folium.Icon(color='blue' if e['event'] == 'BIRT' else 'red')
        ).add_to(m)

# Karte anzeigen
st_folium(m, width=700, height=500)
