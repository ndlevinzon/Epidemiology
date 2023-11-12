import folium
import webbrowser
import os
import requests

# Function to fetch state populations from the US Census API
def get_state_populations():
    base_url = "https://api.census.gov/data/2019/pep/population"
    state_url = f"{base_url}?get=POP,NAME&for=state:*"
    response = requests.get(state_url)
    data = response.json()

    # Mapping state FIPS codes to populations
    state_populations = {state[1]: int(state[0]) for state in data[1:]}

    return state_populations

# Load GeoJSON data for US state boundaries
us_states_geojson_path = 'C:/Users/Nate Levinzon/PycharmProjects/epidemiology/gadm41_USA_1.json'
us_states_geojson = folium.GeoJson(us_states_geojson_path, name='geojson')

# Fetch state populations
state_populations = get_state_populations()

# Manually add population data to GeoJSON
for feature in us_states_geojson.data['features']:
    state_name = feature['properties']['NAME_1']
    population = state_populations.get(state_name, 0)
    feature['properties']['Population'] = population

# Create a map centered on the United States
us_map = folium.Map()

# Add GeoJSON data to the map
us_states_geojson.add_to(us_map)

# Add a popup with state names and populations on hover
popup = folium.features.GeoJsonPopup(fields=['NAME_1', 'Population'], aliases=['State: ', 'Population: '], labels=True,
                                     style="background-color: yellow;")
us_states_geojson.add_child(popup)

# Add a text box at the top right with a title and subtitles
title_html = """
    <h3 align="center" style="font-size:16px"><b>Title</b></h3>
    <h4 align="center" style="font-size:12px">Subtitle 1</h4>
    <h4 align="center" style="font-size:12px">Subtitle 2</h4>
"""

title_box = folium.Html(title_html, script=True)
title_popup = folium.Popup(title_box, max_width=300)
title_popup.add_to(us_map)

# Save the map to a temporary HTML file
temp_html_path = 'temp_us_map.html'
us_map.save(temp_html_path)

# Open the HTML file in the default web browser
webbrowser.open('file://' + os.path.realpath(temp_html_path))

# Optionally, remove the temporary HTML file after viewing
# os.remove(temp_html_path)
