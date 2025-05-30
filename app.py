import streamlit as st
import folium
from streamlit_folium import st_folium
from gedcom.parser import Parser
from datetime import datetime
import tempfile
from gedcom.element.individual import IndividualElement
import pdb

local_file = False
# Datei laden
#gedcom_file = 'familie_krendl_2025.ged'
gedcom_file_path = r"C:/Users/katsc/OneDrive/Documents/0 aktuell/andreas/genealogie/krendl-4Gen.ged"

# Parser vorbereiten
gedcom_parser = Parser()

if local_file == False:
    try:
        gedcom_parser.parse_file(gedcom_file_path)
        #print("GEDCOM-Datei erfolgreich geladen.")
        local_file = True
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {gedcom_file_path}")
    except Exception as e:
        print(f"Fehler beim Einlesen der GEDCOM-Datei: {e}")

# Parser vorbereiten
#gedcom_parser = Parser()

uploaded_file = st.file_uploader("Upload GEDCOM file")
#uploaded_file = st.file_uploader("Upload GEDCOM file", type=["ged", "*"])

if not gedcom_parser or local_file == False:
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
    #with tempfile.NamedTemporaryFile(delete=False, suffix=".ged") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        gedcom_parser.parse_file(tmp_file_path)

#with open(gedcom_file, 'r', encoding='utf-8') as file:

def finde_eltern(proband):
    #st.write("eltern-proband", proband)
    if not proband:
        return []
    eltern = []
    for child in proband.get_child_elements():
        if child.get_tag() == 'FAMS':
            fam = child.get_pointer()
            if not fam:
                continue
            for e in fam.get_child_elements():
                if e.get_tag() in ['HUSB', 'WIFE']:
                    eltern.append(e.get_pointer())
    return eltern

def finde_kinder(proband):
    if not proband:
        return []
    kinder = []
    for child in proband.get_child_elements():
        if child.get_tag() == 'FAMC':  # Familieneintrag, in der Person Elternteil ist
            fam = child.get_pointer()
            if not fam:
                continue
            for e in fam.get_child_elements():
                if e.get_tag() == 'CHIL':
                    kinder.append(e.get_pointer())
    return kinder

def finde_partner(proband):
    if not proband:
        return []    
    partner = []
    for child in proband.get_child_elements():
        if child.get_tag() == 'FAMS':
            fam = child.get_pointer()
            if not fam:
                continue
            for e in fam.get_child_elements():
                if e.get_tag() in ['HUSB', 'WIFE']:
                    person = e.get_pointer()
                    if person != proband:
                        partner.append(person)
    return partner

# Ereignisse extrahieren
events = []
personen_liste = []
# Parsing
for element in gedcom_parser.get_element_list():
    if element.get_tag() == 'INDI':
        #pdb.set_trace() #Debug
        name_tuple = element.get_name()
        #name_tuple = ('Josef', 'Kalcher')
        nachname = name_tuple[1] #" ".join(name_tuple)
        vorname = name_tuple[0]
        name = name_tuple[1], name_tuple[0]
        #st.write("Debug: ", name)
        #st.text(f"Aktuelle Position: {position}")
        geburtsdatum = "Unbekannt"

        for child in element.get_child_elements():
            if child.get_tag() == 'BIRT':
                for sub in child.get_child_elements():
                    if sub.get_tag() == 'DATE':
                        try:
                            geburtsdatum = datetime.strptime(sub.get_value(), "%d %b %Y").strftime("%d.%m.%Y")
                            #st.write("Datum: ", geburtsdatum)
                        except:
                            geburtsdatum = sub.get_value()

            # Optional: weitere Events mit Koordinaten erfassen
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
                if lat and lon:
                    events.append({
                        'name': name,
                        'event': child.get_tag(),
                        'date': date,
                        'lat': lat,
                        'lon': lon
                    })

        # Liste für Sidebar
        personen_liste.append((nachname, vorname, geburtsdatum, element))

# Streamlit Sidebar: Auswahl des Probanden
st.sidebar.title("Proband auswählen")
#anzeige_name = f"{vorname} {nachname} ({geburtsdatum})"
optionen = [f"{nachname} {vorname} {geburtsdatum}" for nachname, vorname, geburtsdatum, _ in personen_liste]
#pdb.set_trace() #Debug
#st.write("nachname: ", nachname)
auswahl = st.sidebar.selectbox("Wähle den Probanden:", optionen)

# Ausgewählte Person extrahieren
proband = None
proband_name = None
for nachname, vorname, geburtsdatum, person in personen_liste:
    if f"{nachname} {vorname} {geburtsdatum}" == auswahl:
        proband = person
        proband_name = nachname, vorname  # Merken für spätere Markierung
        #st.write("proband_name: ", proband_name)
        break

# Initiale Kartenposition auf Proband setzen, falls Koordinaten vorhanden
proband_coords = [48.3, 14.3]  # fallback
for e in events:
    #st.write("e-name", e['name'])
    if e['name'] == proband_name:
        proband_coords = [e['lat'], e['lon']]
        break


# Ausgabe Hauptbereich
if proband:
    st.write(f"**Proband ausgewählt:** {proband.get_name()[1]} {proband.get_name()[0]}")

# Zeitfilter
st.title("📍 Ahnenkarte nach Zeit")
start_year, end_year = st.slider("Zeitraum auswählen", 1600, 2025, (1800, 2025))

# if proband: 
#     event = next((e for e in events if e['name'] == auswahl and e['lat'] and e['lon']), None)
#     if event:
#         m = folium.Map(location=[event['lat'], events['lon']], zoom_start=5)

#     # #m = folium.Map(location=[48.3, 14.3], zoom_start=5)
#     # for e in events:
#     #     #pdb.Pdb # set_trace() #Debug
#     #     st.write("proband: ", proband)
#     #     if proband == e['name']:
#     #         m = folium.Map(location=[e['lat'], e['lon']], zoom_start=5)
#     #         folium.Marker(
#     #             location=[e['lat'], e['lon']],
#     #             popup=f"{e['name']} – {e['event']} am {e['date'].date()}",
#     #             icon=folium.Icon(color='blue' if e['event'] == 'BIRT' else 'red')
#     #         ).add_to(m)
#else:
# Karte

if proband:
    st.write("proband: ", proband)
    # Koordinaten des Probanden-Events finden (z. B. Geburt)
    proband_coords = None
    for e in events:
        st.write("name: ", e['name'])
        if e['name'] == (proband.get_name()[1], proband.get_name()[0]):            
            proband_coords = (e['lat'], e['lon'])
            break

    # Zentriere auf Proband oder Standard
    if proband_coords:
        m = folium.Map(location=proband_coords, zoom_start=6)
    else:
        m = folium.Map(location=[48.3, 14.3], zoom_start=5)
else:
    m = folium.Map(location=[48.3, 14.3], zoom_start=5)

#m = folium.Map(location=proband_coords, zoom_start=6)
#m = folium.Map(location=[48.3, 14.3], zoom_start=5)

if proband_coords:
    verwandte = finde_eltern(proband) + finde_kinder(proband) + finde_partner(proband)

    for verwandter in verwandte:
        for e in events:
            if e['name'] == (verwandter.get_name()[1], verwandter.get_name()[0]):
                folium.PolyLine(
                    locations=[proband_coords, (e['lat'], e['lon'])],
                    color='purple',
                    weight=2,
                    dash_array='5,5'
                ).add_to(m)
                break

# Marker setzen
for e in events:
    if start_year <= e['date'].year <= end_year:
        # Ist es der gewählte Proband?
        if e['name'] == proband_name:
            farbe = 'green'
        else:
            farbe = 'blue' if e['event'] == 'BIRT' else 'red'
        folium.Marker(
            location=[e['lat'], e['lon']],
            popup=f"{e['name']} – {e['event']} am {e['date'].date()}",
            icon=folium.Icon(color=farbe) #'blue' if e['event'] == 'BIRT' else 'red')
        ).add_to(m)

# Karte anzeigen
st_folium(m, width=700, height=500)
