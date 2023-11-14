import folium
import webbrowser
import os
import requests
import csv
import pandas as pd
from sklearn.linear_model import LinearRegression

def spatial_interpolation(csv_path):
    # Load the CSV data into a DataFrame
    county_data = pd.read_csv(csv_path)

    # Sample data for Ukrainian immigrants in a subset of counties
    ukrainian_immigrants_data = {
        'County': ['Sacramento County, California', 'Roseville County, California', 'Folsom County, California',
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
    merged_data = pd.merge(county_data, ukrainian_immigrants_df, on='County', how='left')

    # Fill missing values with 0 for counties with no Ukrainian immigrants data
    merged_data['Ukrainian_Immigrants'].fillna(0, inplace=True)

    # Perform linear regression
    X = merged_data[['Population']]
    y = merged_data['Ukrainian_Immigrants']

    model = LinearRegression()
    model.fit(X, y)

    # Predict Ukrainian immigrants for all counties based on the population
    county_data['Predicted_Ukrainian_Immigrants'] = model.predict(county_data[['Population']])

    # Replace negative values with 0
    county_data['Predicted_Ukrainian_Immigrants'] = county_data['Predicted_Ukrainian_Immigrants'].apply(
        lambda x: max(0, round(x)))

    # Display the DataFrame with predicted values
    print(county_data)

    # Append the source CSV with the predicted Ukrainian immigrants data
    county_data.to_csv(csv_path, mode='a', header=False, index=False)

    return county_data


def get_state_and_county_populations():
    # Fetch state populations
    state_base_url = "https://api.census.gov/data/2019/pep/population"
    state_url = f"{state_base_url}?get=POP,NAME&for=state:*"
    state_response = requests.get(state_url)
    state_data = state_response.json()

    # Mapping state FIPS codes to populations
    state_populations = {state[1]: int(state[0]) for state in state_data[1:]}

    # Fetch county populations
    county_base_url = "https://api.census.gov/data/2019/pep/population"
    county_url = f"{county_base_url}?get=POP,NAME&for=county:*"
    county_response = requests.get(county_url)
    county_data = county_response.json()

    # Mapping county FIPS codes to populations
    county_populations = {county[1]: int(county[0]) for county in county_data[1:]}

    return state_populations, county_populations

state_populations, county_populations = get_state_and_county_populations()

us_states_geojson_path = 'gadm41_USA_2.json'
us_states_geojson = folium.GeoJson(us_states_geojson_path, name='geojson')

interpolation_csv_data = []

# Manually add population data to GeoJSON
for feature in us_states_geojson.data['features']:
    state_name = feature['properties']['NAME_1']
    county_name = feature['properties']['NAME_2']
    formatted_county_name = f"{county_name} County, {state_name}"

    state_population = state_populations.get(state_name, 0)
    county_population = county_populations.get(formatted_county_name, 0)

    feature['properties']['State_Population'] = state_population
    feature['properties']['County_Population'] = county_population

    interpolation_csv_data.append([formatted_county_name, county_population])

csv_file_path = 'county_population_data.csv'
with open(csv_file_path, 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['County', 'Population'])
    print(['County', 'Population'])
    csv_writer.writerows(interpolation_csv_data)

# Perform spatial interpolation
predicted_data = spatial_interpolation(csv_path='county_population_data.csv')

# Add a new GeoJSON field for predicted Ukrainian immigrants
for feature in us_states_geojson.data['features']:
    county_name = feature['properties']['NAME_2']
    # Check if there is a match in the predicted_data DataFrame
    match = predicted_data[predicted_data['County'] == county_name]
    if not match.empty:
        predicted_value = match['Predicted_Ukrainian_Immigrants'].values[0]
        feature['properties']['Predicted_Ukrainian_Immigrants'] = predicted_value
    else:
        # If there is no match, set the field to 0 or any other default value
        feature['properties']['Predicted_Ukrainian_Immigrants'] = 0

# Create a map centered on the United States
us_map = folium.Map()

# Add GeoJSON data to the map
us_states_geojson.add_to(us_map)

# Add a popup with state names, populations, and predicted Ukrainian immigrants on hover
popup = folium.features.GeoJsonPopup(
    fields=['NAME_1', 'State_Population', 'NAME_2', 'County_Population', 'Predicted_Ukrainian_Immigrants'],
    aliases=['State: ', 'State Population: ', 'County: ', 'County Population: ', 'Predicted Ukrainian Immigrants: '],
    labels=True, style="background-color: yellow;",
    parse_html=False  # Set parse_html to False to handle formatting manually
)

# Convert predicted values to integers before displaying in the popup
for feature in us_states_geojson.data['features']:
    feature['properties']['Predicted_Ukrainian_Immigrants'] = int(feature['properties']['Predicted_Ukrainian_Immigrants'])

# Add the popup to the GeoJSON layer
us_states_geojson.add_child(popup)

# Save the map to a temporary HTML file
temp_html_path = 'temp_us_map.html'
us_map.save(temp_html_path)

# Open the HTML file in the default web browser
webbrowser.open('file://' + os.path.realpath(temp_html_path))
