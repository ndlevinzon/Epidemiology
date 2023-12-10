import folium
import os
import webbrowser
import censusdata
import pandas as pd
import requests

def load_county_names(filename):
    county_names_df = pd.read_csv(filename, sep='\t', dtype=str)
    county_names_df['StateFIPS'] = county_names_df['StateFIPS'].str.zfill(2)
    county_names_df['CountyFIPS_3'] = county_names_df['CountyFIPS_3'].str.zfill(3)
    return county_names_df

def replace_fips_with_names(county_data, county_names):
    merged_data = pd.merge(county_data, county_names, how='left', left_on=['State', 'County'],
                           right_on=['StateFIPS', 'CountyFIPS_3'])
    merged_data = merged_data.drop(['StateFIPS', 'CountyFIPS_3'], axis=1)
    return merged_data

def get_county_population():
    variables = [
        'B01003_001E',  # Total population
        'B05004_001E',  # Total population age 18 and over
        'B05004_010E',  # Total population age 18 and over who are smokers
        'B05004_013E',  # Total population age 18 and over who are obese
        'B06011_001E',  # Median household income (in the past 12 months)
    ]

    dataset = 'acs5'
    year = 2019

    counties = censusdata.geographies(censusdata.censusgeo([('state', '*'), ('county', '*')]), dataset, year)

    county_data = censusdata.download(dataset, year, censusdata.censusgeo([('state', '*'), ('county', '*')]), variables)

    county_data['Population'] = county_data['B01003_001E']
    county_data['Prevalence_Tobacco_Use'] = county_data['B05004_010E']
    county_data['Prevalence_Obesity'] = county_data['B05004_013E']
    county_data['Median_Income'] = county_data['B06011_001E']

    county_data_final_df = pd.DataFrame({
        'State': [code.params()[0][1] for code in county_data.index],
        'County': [code.params()[1][1] for code in county_data.index],
        'Population': county_data['Population'],
        'Prevalence_Tobacco': county_data['Prevalence_Tobacco_Use'],
        'Prevalence_Obesity': county_data['Prevalence_Obesity'],
        'Median_Income': county_data['Median_Income']
    })

    # county_names_df = load_county_names('C:/Users/Nate Levinzon/PycharmProjects/epidemiology/fips2county.tsv')
    # county_data_final_df = replace_fips_with_names(county_data_final_df, county_names_df)

    # Keep only the desired columns
    county_data_final_df = county_data_final_df[
        ['State', 'County', 'Population', 'Prevalence_Tobacco', 'Prevalence_Obesity', 'Median_Income']]

    return county_data_final_df

# Download the GeoJSON file for US counties
geojson_url = 'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json'

# Fetch the GeoJSON features using the requests library
response = requests.get(geojson_url)
geojson_data = response.json()

# Check the structure of GeoJSON data
if 'features' in geojson_data and isinstance(geojson_data['features'], list) and len(geojson_data['features']) > 0:
    sample_feature = geojson_data['features'][0]
    if 'properties' in sample_feature:
        sample_properties = sample_feature['properties']
        if isinstance(sample_properties, dict):
            property_keys = sample_properties.keys()
            print(f"Sample GeoJSON properties keys: {property_keys}")
        else:
            print("Sample GeoJSON properties are not a dictionary.")
    else:
        print("Sample GeoJSON feature does not have 'properties' key.")
else:
    print("GeoJSON data does not have 'features' key or is not a list.")

# Create a DataFrame with some sample data
county_data = get_county_population()

# Add new columns for state and county to the GeoJSON DataFrame
geojson_df = pd.DataFrame(geojson_data.get('features', []))
geojson_df[['STATE', 'COUNTY']] = pd.DataFrame([feature.get('properties', {}) for feature in geojson_data.get('features', [])]).fillna('NA')[['STATE', 'COUNTY']]

# Merge the GeoJSON data with the DataFrame using the new columns
merged_data = pd.merge(geojson_df, county_data, left_on=['STATE', 'COUNTY'], right_on=['State', 'County'], how='left')

# Uncomment the following code to replace FIPS codes with names
county_names_df = load_county_names('C:/Users/Nate Levinzon/PycharmProjects/epidemiology/fips2county.tsv')
merged_data = replace_fips_with_names(merged_data, county_names_df)

# Print the updated merged data
with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    print(merged_data)

# Uncomment the following code to replace FIPS codes with names in the 'properties' column
merged_data['properties'] = merged_data.apply(lambda row: {
     'State': row['StateName'],
     'County': row['CountyName'],
     'Population': row['Population'],
     'Prevalence_Tobacco': row['Prevalence_Tobacco'],
     'Prevalence_Obesity': row['Prevalence_Obesity'],
     'Median_Income': row['Median_Income']
 }, axis=1)

# Print the 'properties' column
print(merged_data['properties'])

# Create a new GeoJSON object using the updated features
updated_geojson = {'type': 'FeatureCollection', 'features': merged_data.to_dict(orient='records')}

# Create a Folium map centered on the United States
us_map = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

# Add the US counties GeoJSON layer to the map with the updated data
folium.GeoJson(
    updated_geojson,
    name='geojson',
    style_function=lambda feature: {
        'fillColor': 'lightblue',
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.7
    },
    highlight_function=lambda x: {'weight': 2, 'color': 'black'},
    tooltip=folium.GeoJsonTooltip(fields=['County', 'State', 'Population', 'Median_Income', 'Prevalence_Tobacco', 'Prevalence_Obesity'], labels=True, sticky=True),
    popup=folium.GeoJsonPopup(fields=['County', 'State', 'Population', 'Median_Income', 'Prevalence_Tobacco', 'Prevalence_Obesity'], labels=True, sticky=True)
).add_to(us_map)

# Save the map as an HTML file
html_file_path = 'us_counties_map.html'
us_map.save(html_file_path)

# Open the HTML file in the default web browser
webbrowser.open('file://' + os.path.realpath(html_file_path))
