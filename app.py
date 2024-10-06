import rasterio
import numpy as np
import geopandas as gpd
import dash
from dash import dcc, html
import plotly.graph_objs as go
import json
from dash.dependencies import Input, Output
from datetime import datetime, timedelta
import os

current_directory = os.path.dirname(os.path.abspath(__file__))

# 列出该目录下的所有文件和文件夹
all_files = os.listdir(current_directory)
print(current_directory)

# 过滤出所有文件
only_files = [f for f in all_files if os.path.isfile(os.path.join(current_directory, f))]

print("所有文件名：")
for file in only_files:
    print(file)

def read_tif_file(tif_file):
    with rasterio.open(tif_file) as src:
        bounds = src.bounds
        tif_data = src.read(1)
        lon_min, lat_min = bounds.left, bounds.bottom
        lon_max, lat_max = bounds.right, bounds.top
        return (lon_min, lat_min, lon_max, lat_max), tif_data

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(
    style={'display': 'flex', 'height': '100vh', 'margin': 0, 'padding': 0},
    children=[
        # 左侧时间选择器
        html.Div(
            style={
                'width': '25%',
                'padding': '20px',
                'backgroundColor': '#f9f9f9'
            },
            children=[
                html.H1('Select a Date Range'),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    min_date_allowed='2022-08-10',
                    max_date_allowed='2024-09-02',
                    initial_visible_month='2022-08-010',
                    start_date='2022-08-10',
                    end_date='2022-08-31'
                ),
                html.Div(id='output-date-range', style={'fontSize': '20px', 'marginTop': '20px'})
            ]
        ),

        # 右侧地图区域
        html.Div(
            style={
                'width': '75%',
                'padding': '0px'
            },
            children=[
                dcc.Graph(
                    id='geo-map',
                    style={'height': '100%', 'width': '100%'},
                    figure={}
                )
            ]
        )
    ]
)

@app.callback(
    Output('geo-map', 'figure'),
    Output('output-date-range', 'children'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_output(start_date, end_date):
    as_date = start_date.replace('-', '')
    ae_date = end_date.replace('-', '')
    s_date = datetime.strptime(as_date, "%Y%m%d")
    e_date = datetime.strptime(ae_date, "%Y%m%d")

    # 初始化日期列表
    date_list = []
    current_date = s_date
    while current_date <= e_date:
        date_list.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)

    # 过滤文件
    filtered_files = []
    for file in only_files:
        parts = file.split('_')
        if len(parts) > 4:
            date_part = parts[4][:8]
            if date_part in date_list:
                filtered_files.append(file)

    json_files = [f for f in filtered_files if f.endswith('.json')]
    tif_files = [f for f in filtered_files if f.endswith('.tif')]

    lons, lats, concentrations, hover_texts = [], [], [], []
    
    # 处理每个 JSON 文件
    for j_file in json_files:
        with open(j_file, 'r') as f:
            data = json.load(f)

        for feature in data['features']:
            properties = feature['properties']
            geometry = feature['geometry']
            max_concentration = properties.get('Max Plume Concentration (ppm m)', None)
            coordinates = geometry.get('coordinates', [])

            for polygon in coordinates:
                for coord in polygon:
                    lon, lat = coord
                    lons.append(lon)
                    lats.append(lat)
                    concentrations.append(max_concentration)

                    hover_text = f"Max Plume Concentration: {max_concentration} ppm m"
                    hover_texts.append(hover_text)

    # 生成图形
    figure = {
        'data': [
            go.Scattergeo(
                lon=lons,
                lat=lats,
                mode='markers',
                marker=dict(
                    size=10,
                    color=concentrations,
                    colorbar=dict(title="Concentration"),
                    colorscale='Viridis',
                ),
                hoverinfo='text',
                hovertext=hover_texts,
                name='Plume Points'
            )
        ],
        'layout': go.Layout(
            title='Filtered Data on World Map',
            geo=dict(
                scope='world',
                projection=dict(type='natural earth'),
                showland=True,
                landcolor='rgb(217, 217, 217)',
                showcountries=True,
                countrycolor='rgb(204, 204, 204)',
            ),
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            autosize=True
        )
    }

    # 返回一个元组，包含图形数据和日期范围信息
    return figure, f'Selected Date Range: {start_date} to {end_date}'

if __name__ == '__main__':
    app.run_server(debug=True)

