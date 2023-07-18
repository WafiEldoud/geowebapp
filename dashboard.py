from flask import Flask
import folium
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go
from collections import Counter
from folium.plugins import MarkerCluster
import pymysql
import os
import base64
import yaml
from datetime import date

app = Flask(__name__)
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

with open('base.yaml') as file:
    base = yaml.safe_load(file)

mydb = pymysql.connect(
    host=base['host'],
    user=base['user'],
    password=base['password'],
    database=base['database'],
    autocommit=True,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

mycursor_1= mydb.cursor()


students_data = 'student_data'
query_1 = f"SELECT * FROM {students_data}"



mycursor_1.execute(query_1)



rows_data = mycursor_1.fetchall()


columns_data = [desc[0] for desc in mycursor_1.description]


df = pd.DataFrame(rows_data, columns=columns_data)





### map section
students_map = folium.Map(
    location=[36.015495, -11.712043],
    zoom_start= 2)
folium.TileLayer('cartodbdark_matter').add_to(students_map)
folium.TileLayer('stamenterrain').add_to(students_map)
mCluster = MarkerCluster(name='Markers').add_to(students_map)

for i,row in df.iterrows():
    lat = df.at[i,'latitude']
    lng = df.at[i, 'longitude']

    latitude_value = lat
    longitude_value = lng

    lat_value = abs(latitude_value)
    lng_value= abs (longitude_value)

    degree_lat = int(lat_value)
    minutes_lat = (lat_value - degree_lat) * 60
    minutes_lat_round = int(minutes_lat)
    seconds_lat = (minutes_lat - minutes_lat_round) * 60
    latitude_DMS = f"{degree_lat}° {minutes_lat_round}' {seconds_lat:.2f}"

    degree_lng = int(lng_value)
    minutes_lng = (lng_value - degree_lng) * 60
    minutes_lng_round = int(minutes_lng)
    seconds_lng = (minutes_lng - minutes_lng_round) * 60
    longitude_DMS = f"{degree_lng}° {minutes_lng_round}' {seconds_lng:.2f}"

    direction_N_S = ''
    direction_E_W = ''
    if latitude_value < 0 and longitude_value < 0:
        direction_N_S = "S"
        direction_E_W = 'W'
    if latitude_value > 0 and longitude_value > 0:
        direction_N_S = "N"
        direction_E_W = 'E'
    if latitude_value < 0 and longitude_value > 0:
        direction_N_S = "S"
        direction_E_W = 'E'
    if latitude_value > 0 and longitude_value < 0:
        direction_N_S = "N"
        direction_E_W = 'W'
    coordinate_lat = [latitude_DMS,direction_N_S]
    coordinate_lng = [longitude_DMS, direction_E_W]
    filename = f"{str(row['username'])}.jpg"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_path = file_path.replace("\\", "/")

    with open(file_path, 'rb') as f:
        image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
    popup_html = '''
        <div>
            <img src="data:image/png;base64,{}" alt="Student Image" style="max-width: 200px; margin-bottom: 5px;">
            <br>
            <strong>Student Name:</strong> {name}<br>
            <strong>Surname:</strong> {surname}<br>
            <strong>Gender:</strong> {gender}<br>
            <strong>City:</strong> {city}<br>
            <strong>Nationality:</strong> {nationality}<br>
            <strong>Bachelor's Degree:</strong> {under_grad}<br>
            <strong>University:</strong> {university}<br>
            <strong>Latitude:</strong> {lat_vis}<br>
            <strong>Longitude:</strong> {lng_vis}<br>
            
        </div>
    '''.format(
        image_base64,
        name=df.at[i, 'name'],
        surname=df.at[i, 'surname'],
        gender=df.at[i, 'gender'],
        city=df.at[i, 'city'],
        nationality=df.at[i, 'nationality'],
        under_grad=df.at[i, 'under_grad'],
        university=df.at[i, 'university'],
        lat_vis= coordinate_lat,
        lng_vis= coordinate_lng
    )

    folium.Marker(
        location=[lat, lng],
        popup=folium.Popup(popup_html, max_width=500),
        icon=folium.Icon(color='darkblue')
    ).add_to(mCluster)

folium.LayerControl().add_to(students_map)

if __name__ == "__main__":
    students_map.save('templates/output.html')

### graphs section

         

#data for genders
genders = df['gender']
gender_counter = Counter()
for g in genders:
    gender_counter.update(g.split(';'))
gender_types = []
frequancy = []

for item in gender_counter.most_common(1000):
    gender_types.append(item[0])
    frequancy.append(item[1])

#variables for pie chart
values = frequancy
labels = gender_types

#data for regions
regions = df['region']
region_counter = Counter()
for g in regions:
   region_counter.update(g.split(';'))
region_names= []
reps = []

for item in region_counter.most_common(1000):
    region_names.append(item[0])
    reps.append(item[1])

#data for nationalities
nationalities = df['nationality']
nat_counter = Counter()
for e in nationalities:
    nat_counter.update(e.split(';'))
nat_types = []
rep = []

for a in nat_counter.most_common(1000):
    nat_types.append(a[0])
    rep.append(a[1])

#variables for bar chart
x = nat_types
y = rep


#data for ages
def calculate_age(birth_date):
    today = date.today()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age

birth_dates = df['birth_date']
ages = [calculate_age(birth_date) for birth_date in birth_dates]

###

# pie chart creation
trace_1 = go.Pie(labels=labels, values=values, hole=.5, textposition='outside')
layout = go.Layout(
    title='Gender Distribution', 
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(family='Montserrat Thin Light, sans-serif', color='white', size=12),
    hoverlabel=dict(font=dict(family='Montserrat Thin Light, sans-serif',color='white', size=12)),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1,
        xanchor='right',
        x=1,
    ),
)

fig = go.Figure(data=[trace_1], layout=layout)
fig.update_layout(
    plot_bgcolor='#222831',
    paper_bgcolor='#222831',
)

colors = ['#6B9EDB', '#DE3163', '#4863A0']
fig.update_traces(marker=dict(colors=colors, line=dict(color='#222831', width=2)))

# fig.show()
if __name__ == "__main__":
    with open('templates/pie_chart.html', 'w', encoding='utf-8') as f:
        f.write(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))


###


#bar chart creation
trace_2 = go.Bar(x=y, y=x, orientation='h')
layout = go.Layout(
    title='Nationalities',
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=14),
    hoverlabel=dict(font=dict(family='Montserrat Thin Light, sans-serif',color='black', size=14)),
    xaxis=dict(title='Number of Students', tickfont=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12)),
    yaxis=dict(title='Student Nationality', tickfont=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12)),
)

fig = go.Figure(data=[trace_2], layout=layout)
fig.update_layout(
    plot_bgcolor='#222831',
    paper_bgcolor='#222831',
)
fig.update_traces(width=0.5)
fig.update_traces(marker=dict(color='#FFFF8F'))

# fig.show()
if __name__ == "__main__":
    with open('templates/bar_chart.html', 'w', encoding='utf-8') as f:
        f.write(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))

###


#histogram creation
trace_3 = go.Histogram(x=ages, nbinsx=5)
layout = go.Layout(
    title='Age Range',
    font=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12),
    hoverlabel=dict(font=dict(family='Montserrat Thin Light, sans-serif',color='black', size=12)),
    xaxis=dict(title='Ages', tickfont=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12)),
    yaxis=dict(title='Number of Students', tickfont=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12)),
    bargap=0.1,
    bargroupgap=0.1,
    margin=dict(l=50, r=50, t=50, b=50),
    plot_bgcolor='#222831',
    paper_bgcolor='#222831',
)

colors = ['#00FFFF', '#7FFFD4', '#088F8F', '#5F9EA0', '#AFE1AF', '#50C878', '#5F8575']
marker_colors = [colors[i % len(colors)] for i in range(len(trace_3.x))]

trace_3.marker.color = marker_colors
trace_3.marker.line.width = 0.1
trace_3.marker.line.color = '#FFFFFF'

# fig.show()
if __name__ == "__main__":
    fig = go.Figure(data=[trace_3], layout=layout)
    with open('templates/histogram.html', 'w', encoding='utf-8') as f:
        f.write(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))

# regions bar chart
trace_4 = go.Bar(x=region_names, y=reps, orientation='v')
layout = go.Layout(
    title='Students by Region',
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=14),
    hoverlabel=dict(font=dict(family='Montserrat Thin Light, sans-serif',color='black', size=14)),
    xaxis=dict(title='Global Region', tickfont=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12)),
    yaxis=dict(title='Number of Students', tickfont=dict(family='Montserrat Thin Light, sans-serif', color='#FFFFFF', size=12)),
)

fig = go.Figure(data=[trace_4], layout=layout)
fig.update_layout(
    plot_bgcolor='#222831',
    paper_bgcolor='#222831',
)
fig.update_traces(width=0.5)
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
             "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
               "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
                 "#ffd8b1", "#c7e9c0"]
fig.update_traces(marker=dict(color=colors))

# fig.show()
if __name__ == "__main__":
    with open('templates/regions_chart.html', 'w', encoding='utf-8') as f:
        f.write(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))


print(ages)