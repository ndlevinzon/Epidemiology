import folium
import webbrowser
import os
import requests
import pandas as pd
from requests.exceptions import RequestException
from sklearn.linear_model import LinearRegression

def get_state_and_county_populations():
    # Fetch state populations
    state_url = "https://api.census.gov/data/2019/pep/population?get=POP,NAME&for=state:*"
    try:
        state_response = requests.get(state_url)
        state_response.raise_for_status()
        state_data = state_response.json()[1:]
        state_populations = pd.DataFrame(state_data, columns=['Population', 'State_Name', 'State_FIPS'])
        state_populations['Population'] = state_populations['Population'].astype(int)
    except RequestException as e:
        print(f"Error fetching state data: {e}")
        return None

    # Fetch county populations
    county_url = "https://api.census.gov/data/2019/pep/population?get=POP,NAME&for=county:*"
    try:
        county_response = requests.get(county_url)
        county_response.raise_for_status()
        county_data = county_response.json()[1:]

        # Print the first few rows of county_data
        print("County Data Sample:", county_data[:5])

        # Adjust columns based on the actual structure of county_data
        county_populations = pd.DataFrame(county_data, columns=['Population', 'County_Name', 'State_FIPS', 'County_FIPS'])
        county_populations['Population'] = county_populations['Population'].astype(int)
    except RequestException as e:
        print(f"Error fetching county data: {e}")
        return state_populations

    return state_populations, county_populations

# Fetch populations
populations_result = get_state_and_county_populations()

# Unpack the result into state_populations and county_populations
state_populations, county_populations = populations_result

print(state_populations)
print(county_populations)

def spatial_interpolation(county_populations):
    # Sample data for Ukrainian immigrants in a subset of counties
    ukrainian_immigrants_data = {
        'County_Name': ['Sacramento County, California', 'Roseville County, California', 'Folsom County, California',
                   'San Francisco County, California', 'Oakland County, California', 'Berkeley, California',
                   'San Jose County, California', 'Sunnyvale County, California', 'Santa Clara County, California',
                   'Los Angeles County, California', 'Long Beach County, California', 'Anaheim County, California',
                   'Portland County, Oregon', 'Vancouver County, Washington', 'Hillsboro County, Oregon',
                   'Seattle County, Washington', 'Tacoma County, Washington', 'Bellevue County, Washington',
                   'Spokane County, Washington', 'Spokane Valley County, Washington',
                   'Denver County, Colorado', 'Aurora County, Colorado', 'Lakewood County, Colorado',
                   'Dallas County, Texas', 'Fort Worth County, Texas', 'Arlington County, Texas',
                   'Minneapolis County, Minnesota', 'St. Paul County, Minnesota', 'Bloomington County, Wisconsin',
                   'Chicago County, Illinois', 'Naperville County, Indiana', 'Elgin County, Wisconsin',
                   'Detroit County, Michigan', 'Warren County, Michigan', 'Dearborn County, Michigan',
                   'Atlanta County, Georgia', 'Sandy Springs County, Georgia', 'Alpharetta County, Georgia',
                   'Cleveland County, Ohio', 'Elyria County, Ohio',
                   'Charlotte County, North Carolina', 'Concord County, North Carolina', 'Gastonia County, North Carolina',
                   'Arlington County, Virginia', 'Alexandria County, Virginia',
                   'Baltimore County, Maryland', 'Columbia County, Maryland', 'Towson County, Maryland',
                   'Tampa County, Florida', 'St. Petersburg County, Florida', 'Clearwater County, Florida',
                   'Miami County, Florida', 'Fort Lauderdale County, Florida', 'Pompano Beach County, Florida',
                   'Philadelphia County, Pennsylvania', 'Camden County, New Jersey', 'Wilmington County, Delaware',
                   'New York County, New York', 'Newark County, New Jersey', 'Jersey City, New Jersey',
                   'Bridgeport County, Connecticut', 'Stamford County, Connecticut', 'Norwalk County, Connecticut',
                   'Springfield County, Massachusetts',
                   'Boston County, Massachusetts', 'Cambridge County, Massachusetts', 'Newton County, New Hampshire'],
        'Ukrainian_Immigrants': [6000, 6000, 6000,
                                 3667, 3667, 3667,
                                 1667, 1667, 1667,
                                 5667, 5667, 5667,
                                 4667, 4667, 4667,
                                 8333, 8333, 8333,
                                 1000, 1000,
                                 667, 667, 667,
                                 1000, 1000, 1000,
                                 1333, 1333, 1333,
                                 9333, 9333, 9333,
                                 1667, 1667, 1667,
                                 1000, 1000, 1000,
                                 3000, 3000,
                                 1000, 1000, 1000,
                                 3000, 3000,
                                 1000, 1000, 1000,
                                 1000, 1000, 1000,
                                 2667, 2667, 2667,
                                 4000, 4000, 4000,
                                 29333, 29333, 29333,
                                 667, 667, 667,
                                 2000,
                                 2333, 2333, 2333]
    }

    ukrainian_immigrants_df = pd.DataFrame(ukrainian_immigrants_data)

    # Merge county population data with Ukrainian immigrants data
    merged_data = pd.merge(county_populations, ukrainian_immigrants_df, on='County_Name', how='left')

    # Fill missing values with 0 for counties with no Ukrainian immigrants data
    merged_data['Ukrainian_Immigrants'].fillna(0, inplace=True)

    # Perform linear regression
    X = merged_data[['Population']]
    y = merged_data['Ukrainian_Immigrants']

    model = LinearRegression()
    model.fit(X, y)

    # Predict Ukrainian immigrants for all counties based on the population
    merged_data['Predicted_Ukrainian_Immigrants'] = model.predict(merged_data[['Population']])

    # Replace negative values with 0
    merged_data['Predicted_Ukrainian_Immigrants'] = merged_data['Predicted_Ukrainian_Immigrants'].clip(lower=0).round().astype(int)

    return merged_data[['County_Name', 'County_FIPS', 'Population', 'Predicted_Ukrainian_Immigrants']]

# Perform spatial interpolation
predicted_data = spatial_interpolation(county_populations)

# Create GeoJSON map
us_states_geojson_path = 'gadm41_USA_2.json'
us_states_geojson = folium.GeoJson(us_states_geojson_path, name='geojson')

# Manually add population data to GeoJSON
for feature in us_states_geojson.data['features']:
    state_name, county_name = feature['properties']['NAME_1'], feature['properties']['NAME_2']
    formatted_county_name = f"{county_name} County, {state_name}"

    # Find the corresponding row in state_populations DataFrame
    state_row = state_populations[state_populations['State_Name'] == state_name]
    state_population = int(state_row['Population'].values[0]) if not state_row.empty else 0

    # Find the corresponding row in county_populations DataFrame
    county_row = county_populations[county_populations['County_Name'] == formatted_county_name]
    county_population = int(county_row['Population'].values[0]) if not county_row.empty else 0

    feature['properties']['State_Population'] = state_population
    feature['properties']['County_Population'] = county_population

# Add a new GeoJSON field for predicted Ukrainian immigrants
for feature in us_states_geojson.data['features']:
    county_name = feature['properties']['NAME_2']
    match = predicted_data[predicted_data['County_Name'] == county_name]
    feature['properties']['Predicted_Ukrainian_Immigrants'] = int(match['Predicted_Ukrainian_Immigrants'].values[0]) if not match.empty else 0

# Create a map centered on the United States
us_map = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

# Add GeoJSON data to the map
us_states_geojson.add_to(us_map)

# Add a popup with state names, populations, and predicted Ukrainian immigrants on hover
popup = folium.features.GeoJsonPopup(
    fields=['NAME_1', 'State_Population', 'NAME_2', 'County_Population', 'Predicted_Ukrainian_Immigrants'],
    aliases=['State: ', 'State Population: ', 'County: ', 'County Population: ', 'Predicted Ukrainian Immigrants: '],
    labels=True, style="background-color: yellow;",
    parse_html=False
)


# Add the popup to the GeoJSON layer
us_states_geojson.add_child(popup)

# Save the map to a temporary HTML file
temp_html_path = 'temp_us_map.html'
us_map.save(temp_html_path, minify_html=True)

# Open the HTML file in the default web browser
webbrowser.open('file://' + os.path.realpath(temp_html_path))
