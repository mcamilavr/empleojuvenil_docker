import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta

# Intentar importar geopandas, pero manejar el error si no está disponible
try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

# =============================================
# CONFIGURACIÓN INICIAL Y CARGA DE DATOS
# =============================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Análisis Empleo Juvenil Colombia"
server = app.server  # Esta línea es crítica para Render

# Definir rutas relativas para los archivos
base_dir = os.path.dirname(os.path.abspath(__file__))
shapefile_path = os.path.join(base_dir, "MGN_DPTO_POLITICO", "MGN_DPTO_POLITICO.shp")
data_path = os.path.join(base_dir, "empleo_juvenil.csv")

# Variables globales para los datos
gdf = None
geojson = None

# Cargar datos geoespaciales si geopandas está disponible
if GEOPANDAS_AVAILABLE:
    try:
        gdf = gpd.read_file(shapefile_path)
        gdf['DPTO_CNMBR'] = gdf['DPTO_CNMBR'].str.upper().str.strip()
        
        # Simplificar geometría para reducir tamaño
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.01, preserve_topology=True)
        
        # Crear GeoJSON en memoria (sin guardar archivo)
        geojson = json.loads(gdf.to_json())
    except Exception as e:
        print(f"Error al cargar datos geoespaciales: {e}")
        # Fallback si el shapefile no está disponible
        gdf = None
        geojson = None

# Cargar datos transaccionales
try:
    df = pd.read_csv(data_path)
    # Limpieza de datos - quitar tildes y convertir a minúsculas
    df['departamento'] = df['Departamento'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.lower()
    df['ocupacion'] = df['Ocupación'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.lower()
except Exception as e:
    print(f"Error al cargar datos: {e}")
    # Crear un DataFrame vacío con estructura similar si hay error
    df = pd.DataFrame(columns=['ID', 'Departamento', 'Latitud', 'Longitud', 'Edad', 'Ocupación', 'Ingreso', 'departamento', 'ocupacion'])
    # Añadir algunos datos de ejemplo para que la aplicación no falle
    df = pd.DataFrame({
        'ID': [1, 2, 3],
        'Departamento': ['Santander', 'Cundinamarca', 'Bogotá D.C.'],
        'departamento': ['santander', 'cundinamarca', 'bogota d.c.'],
        'Latitud': [7.1254, 4.6814, 4.7110],
        'Longitud': [-73.1198, -74.1371, -74.0721],
        'Edad': [20, 24, 25],
        'Ocupación': ['Estudiante', 'Desempleado', 'Trabajador'],
        'ocupacion': ['estudiante', 'desempleado', 'trabajador'],
        'Ingreso': [868997, 586245, 415614]
    })

# =============================================
# PROCESAMIENTO DE DATOS
# =============================================

# Correcciones para nombres de departamentos (para match con shapefiles)
correcciones = {
    "bogota d.c.": "bogota, d.c.",
    "valle del cauca": "valle",
    "cordoba": "cordoba"  # Asegurarse que coincida con el shapefile
}

df['departamento'] = df['departamento'].replace(correcciones)

# Calcular estadísticas básicas
edad_promedio = df['Edad'].mean()
ingreso_promedio = df['Ingreso'].mean()
total_jovenes = len(df)

# Calcular distribución por ocupación
ocupacion_counts = df['ocupacion'].value_counts().reset_index()
ocupacion_counts.columns = ['Ocupación', 'Cantidad']

# Calcular ingreso promedio por departamento
ingreso_por_departamento = df.groupby('departamento')['Ingreso'].mean().reset_index()
ingreso_por_departamento.columns = ['departamento', 'ingreso_promedio']

# Calcular ingreso promedio por ocupación
ingreso_por_ocupacion = df.groupby('ocupacion')['Ingreso'].mean().reset_index()
ingreso_por_ocupacion.columns = ['ocupacion', 'ingreso_promedio']

# Calcular edad promedio por departamento
edad_por_departamento = df.groupby('departamento')['Edad'].mean().reset_index()
edad_por_departamento.columns = ['departamento', 'edad_promedio']

# Unir datos geoespaciales con datos de ingreso por departamento
if gdf is not None:
    try:
        # Transformar nombres de departamentos para coincidir
        # Asegurarse que los nombres de departamentos coincidan (ambos en mayúsculas)
        ingreso_por_departamento['departamento_upper'] = ingreso_por_departamento['departamento'].str.upper()
        gdf['DPTO_CNMBR_NORM'] = gdf['DPTO_CNMBR'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8').str.upper()
        
        # Realizar el merge
        gdf_merged = gdf.merge(
            ingreso_por_departamento,
            left_on='DPTO_CNMBR_NORM',
            right_on='departamento_upper',
            how='left'
        ).fillna(0)
    except Exception as e:
        print(f"Error al unir datos geoespaciales: {e}")
        gdf_merged = None
else:
    gdf_merged = None

# =============================================
# COMPONENTES VISUALES
# =============================================

# Navbar
navbar = dbc.NavbarSimple(
    brand="Análisis de Empleo Juvenil en Colombia",
    brand_href="#",
    color="primary",
    dark=True,
)

# Tarjetas informativas
def create_card(title, value, color, is_currency=False, is_percent=False):
    if is_currency:
        formatted_value = f"${value:,.0f}"
    elif is_percent:
        formatted_value = f"{value:.1f}%"
    else:
        formatted_value = f"{value:,.1f}"
        
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className="card-title"),
            html.H2(formatted_value, className="card-text")
        ]),
        color=color,
        inverse=True,
        className="mb-3"
    )

# Crear tarjetas de resumen
cards = dbc.Row([
    dbc.Col(create_card("Edad Promedio", edad_promedio, "info")),
    dbc.Col(create_card("Ingreso Promedio", ingreso_promedio, "success", is_currency=True)),
    dbc.Col(create_card("Total de Jóvenes Analizados", total_jovenes, "warning"))
])

# Pestaña de contextualización
contexto_tab = dbc.Tab(
    label="Contexto",
    children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Img(
                        src="/assets/empleo_juvenil.png",
                        className="img-fluid",
                        style={'maxHeight': '400px'}
                    )
                ], md=4),
                dbc.Col([
                    html.H2("Contextualización del Dataset", className="mb-4"),
                    dcc.Markdown(''' 
                    **Registros:** 200  
                    **Cobertura:** Nacional

                    #### Variables Clave:
                    - `Departamento`: Ubicación geográfica del joven
                    - `Edad`: Edad del joven (entre 18 y 27 años)
                    - `Ocupación`: Situación laboral del joven (Estudiante, Trabajador, Desempleado)
                    - `Ingreso`: Ingresos mensuales en pesos colombianos (COP)
                    - `Latitud` y `Longitud`: Coordenadas geográficas

                    #### Objetivos Analíticos:
                    1. Analizar la distribución geográfica del empleo juvenil en Colombia
                    2. Identificar diferencias en ingresos por departamento y ocupación
                    3. Evaluar la situación socioeconómica de los jóvenes por región
                    4. Visualizar patrones espaciales de empleabilidad juvenil
                    ''')
                ], md=8)
            ], className="mb-5"),
            html.Hr(),
            cards
        ], fluid=True)
    ]
)

# Pestaña del mapa
def create_mapa_figure():
    if gdf_merged is not None and geojson is not None:
        try:
            fig = px.choropleth(
                gdf_merged,
                geojson=geojson,
                locations=gdf_merged.index,
                color='ingreso_promedio',
                hover_name='DPTO_CNMBR',
                color_continuous_scale="viridis",
                labels={'ingreso_promedio': 'Ingreso Promedio (COP)'},
                range_color=(ingreso_por_departamento['ingreso_promedio'].min(), 
                            ingreso_por_departamento['ingreso_promedio'].max())
            ).update_geos(
                fitbounds="locations",
                visible=False,
                projection_type="mercator"
            ).update_layout(
                margin={"r":0,"t":30,"l":0,"b":0},
                paper_bgcolor='#f8f9fa',
                plot_bgcolor='#f8f9fa',
                coloraxis_colorbar={
                    'title': {'text': 'COP', 'font': {'color': '#333'}},
                    'tickfont': {'color': '#333'}
                }
            )
            return fig
        except Exception as e:
            print(f"Error al crear mapa: {e}")
            return create_alternative_map()
    else:
        return create_alternative_map()

def create_alternative_map():
    # Si no tenemos acceso a los shapefiles, crear un mapa alternativo con los departamentos
    # como marcadores en un mapa basado en las coordenadas de cada departamento
    try:
        # Calcular coordenadas centrales para cada departamento
        dept_coords = df.groupby('departamento').agg({
            'Latitud': 'mean',
            'Longitud': 'mean',
            'Ingreso': 'mean'
        }).reset_index()
        
        fig = px.scatter_mapbox(
            dept_coords, 
            lat="Latitud", 
            lon="Longitud", 
            color="Ingreso",
            size=[15] * len(dept_coords),  # Tamaño fijo para todos
            hover_name="departamento",
            color_continuous_scale="viridis",
            zoom=5,
            height=600,
            labels={'Ingreso': 'Ingreso Promedio (COP)'}
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":30,"l":0,"b":0},
            title="Mapa Alternativo: Ingresos Promedio por Departamento",
            coloraxis_colorbar={
                'title': {'text': 'COP', 'font': {'color': '#333'}},
                'tickfont': {'color': '#333'}
            }
        )
        
        return fig
    except Exception as e:
        print(f"Error al crear mapa alternativo: {e}")
        return px.scatter().update_layout(
            title="Datos geoespaciales no disponibles para mostrar el mapa."
        )

# Función para crear mapa de puntos
def create_mapa_puntos():
    try:
        fig = px.scatter_mapbox(
            df, 
            lat="Latitud", 
            lon="Longitud", 
            color="ocupacion",
            size="Ingreso",
            size_max=15,
            hover_name="Departamento",
            hover_data=["Edad", "Ingreso", "Ocupación"],
            color_discrete_map={
                "estudiante": "#1E88E5",
                "trabajador": "#4CAF50",
                "desempleado": "#E53935"
            },
            zoom=5,
            height=600
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":0,"l":0,"b":0},
            legend_title_text="Ocupación"
        )
        
        return fig
    except Exception as e:
        print(f"Error al crear mapa de puntos: {e}")
        return px.scatter().update_layout(
            title="Error al crear el mapa de puntos."
        )

mapa_tab = dbc.Tab(
    label="Mapa Interactivo",
    children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("Mapa de Ingresos Promedio por Departamento", className="mb-3 mt-4"),
                    dcc.Graph(
                        id='mapa-principal',
                        figure=create_mapa_figure()
                    )
                ], md=12, className="mb-4")
            ]),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Distribución Geográfica de Jóvenes por Ocupación", className="mb-3"),
                    dcc.Graph(
                        id='mapa-puntos',
                        figure=create_mapa_puntos()
                    )
                ], md=12)
            ])
        ], fluid=True)
    ]
)

# Pestaña de análisis por ocupación
analisis_ocupacion_tab = dbc.Tab(
    label="Análisis por Ocupación",
    children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("Distribución por Ocupación", className="mb-4 mt-4"),
                    dcc.Graph(
                        id='grafico-ocupacion',
                        figure=px.pie(
                            ocupacion_counts, 
                            values='Cantidad', 
                            names='Ocupación',
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            hole=0.4
                        ).update_layout(
                            template='plotly_white'
                        )
                    )
                ], md=6),
                
                dbc.Col([
                    html.H3("Ingreso Promedio por Ocupación", className="mb-4 mt-4"),
                    dcc.Graph(
                        id='grafico-ingreso-ocupacion',
                        figure=px.bar(
                            ingreso_por_ocupacion,
                            x='ocupacion',
                            y='ingreso_promedio',
                            color='ocupacion',
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={
                                'ocupacion': 'Ocupación', 
                                'ingreso_promedio': 'Ingreso Promedio (COP)'
                            }
                        ).update_layout(
                            template='plotly_white',
                            showlegend=False,
                            xaxis_title="Ocupación",
                            yaxis_title="Ingreso Promedio (COP)"
                        )
                    )
                ], md=6)
            ], className="mb-4"),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Edad Promedio por Ocupación", className="mb-4"),
                    dcc.Graph(
                        id='grafico-edad-ocupacion',
                        figure=px.box(
                            df, 
                            x='ocupacion', 
                            y='Edad',
                            color='ocupacion',
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={
                                'ocupacion': 'Ocupación', 
                                'Edad': 'Edad (años)'
                            }
                        ).update_layout(
                            template='plotly_white',
                            showlegend=False,
                            xaxis_title="Ocupación",
                            yaxis_title="Edad (años)"
                        )
                    )
                ], md=12)
            ]),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Relación entre Edad e Ingreso por Ocupación", className="mb-4"),
                    dcc.Graph(
                        id='grafico-scatter-edad-ingreso',
                        figure=px.scatter(
                            df, 
                            x='Edad', 
                            y='Ingreso',
                            color='ocupacion',
                            size='Ingreso',
                            size_max=15,
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={
                                'ocupacion': 'Ocupación', 
                                'Edad': 'Edad (años)',
                                'Ingreso': 'Ingreso (COP)'
                            }
                        ).update_layout(
                            template='plotly_white',
                            xaxis_title="Edad (años)",
                            yaxis_title="Ingreso (COP)",
                            legend_title="Ocupación"
                        )
                    )
                ], md=12)
            ])
        ], fluid=True)
    ]
)

# Pestaña de comparativas por departamento
comparativas_tab = dbc.Tab(
    label="Comparativas por Departamento",
    children=[
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("Departamentos con Mayores y Menores Ingresos", className="mb-4 mt-4"),
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(
                                id='grafico-top-ingresos',
                                figure=px.bar(
                                    ingreso_por_departamento.sort_values('ingreso_promedio', ascending=False).head(5),
                                    y='departamento',
                                    x='ingreso_promedio',
                                    orientation='h',
                                    title="Top 5 Departamentos con Mayores Ingresos",
                                    labels={'departamento': 'Departamento', 'ingreso_promedio': 'Ingreso Promedio (COP)'},
                                    color='ingreso_promedio',
                                    color_continuous_scale="Greens"
                                ).update_layout(
                                    yaxis={'categoryorder': 'total ascending'},
                                    template='plotly_white'
                                )
                            )
                        ], md=6),
                        dbc.Col([
                            dcc.Graph(
                                id='grafico-bottom-ingresos',
                                figure=px.bar(
                                    ingreso_por_departamento.sort_values('ingreso_promedio').head(5),
                                    y='departamento',
                                    x='ingreso_promedio',
                                    orientation='h',
                                    title="Top 5 Departamentos con Menores Ingresos",
                                    labels={'departamento': 'Departamento', 'ingreso_promedio': 'Ingreso Promedio (COP)'},
                                    color='ingreso_promedio',
                                    color_continuous_scale="Reds_r"
                                ).update_layout(
                                    yaxis={'categoryorder': 'total descending'},
                                    template='plotly_white'
                                )
                            )
                        ], md=6)
                    ])
                ], md=12, className="mb-4")
            ]),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Edad Promedio por Departamento", className="mb-4"),
                    dcc.Graph(
                        id='grafico-edad-departamento',
                        figure=px.bar(
                            edad_por_departamento.sort_values('edad_promedio', ascending=False),
                            x='departamento',
                            y='edad_promedio',
                            title="Edad Promedio por Departamento",
                            labels={'departamento': 'Departamento', 'edad_promedio': 'Edad Promedio (años)'},
                            color='edad_promedio',
                            color_continuous_scale="Blues"
                        ).update_layout(
                            template='plotly_white',
                            xaxis_tickangle=-45
                        )
                    )
                ], md=12, className="mb-4")
            ]),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H3("Comparativa por Departamento", className="mb-4"),
                    html.P("Seleccione departamentos para comparar:"),
                    dcc.Dropdown(
                        id='dropdown-comparar',
                        options=[{'label': dep.capitalize(), 'value': dep} for dep in sorted(df['departamento'].unique())],
                        value=[df['departamento'].iloc[0], df['departamento'].iloc[1]] if len(df) > 1 else [],
                        multi=True,
                        className="mb-3"
                    ),
                    html.Div(id='tabla-comparativa')
                ], md=12)
            ])
        ], fluid=True)
    ]
)

# Layout principal
app.layout = dbc.Container([
    navbar,
    dbc.Tabs([
        contexto_tab,
        mapa_tab,
        analisis_ocupacion_tab,
        comparativas_tab,
        dbc.Tab(
            label="Resumen Analítico",
            children=[
                dbc.Container([
                    dbc.Row([
                        dbc.Col([
                            html.Img(
                                src="/assets/empleo_juvenil_analisis.png",
                                className="img-fluid",
                                style={'maxHeight': '500px'}
                            )
                        ], md=4),
                        dbc.Col([
                            html.H3("Interpretación General del Estudio", className="mb-4"),
                            dcc.Markdown('''
                            Tras el análisis de los datos de empleo juvenil en Colombia, se han identificado las siguientes interpretaciones:
                            
                            ### Distribución Ocupacional
                            - La población juvenil estudiada presenta una distribución relativamente equilibrada entre trabajadores (36%), desempleados (32.5%) y estudiantes (31.5%).
                            - Este equilibrio refleja la diversidad de situaciones que experimentan los jóvenes colombianos en su inserción al mercado laboral.
                            
                            ### Disparidades de Ingresos
                            - Se observa una variación significativa en los ingresos promedios entre departamentos.
                            - Atlántico y Nariño lideran con los ingresos más altos, mientras que Cundinamarca y Santander presentan los valores más bajos.
                            - Esta brecha regional supera los 400,000 COP, evidenciando desigualdades económicas territoriales.
                            
                            ### Patrones Geográficos
                            - La distribución espacial muestra mayor concentración de jóvenes trabajadores en la región Caribe y centro del país.
                            - Las zonas costeras presentan indicadores económicos más favorables para la población juvenil que las zonas interiores.
                            
                            ### Relación Edad-Ingreso
                            - No existe una correlación directa clara entre la edad y el nivel de ingresos en el rango estudiado (18-27 años).
                            - Los ingresos más elevados se distribuyen a lo largo de todo el espectro de edad, sin tendencias marcadas hacia los extremos.
                            
                            ### Características Demográficas
                            - Bogotá D.C. concentra la población juvenil de mayor edad promedio (superior a 24 años).
                            - Los departamentos periféricos como Magdalena y Nariño tienen poblaciones juveniles más jóvenes.
                            - Estas diferencias pueden indicar patrones de migración interna por motivos educativos o laborales.
                            
                            ### Economía Informal
                            - Los niveles de ingreso reportados por jóvenes clasificados como "desempleados" sugieren una significativa participación en la economía informal.
                            - Esta economía paralela podría estar funcionando como mecanismo de subsistencia ante la limitada oferta de empleo formal para jóvenes.
                            ''')
                        ], md=8)
                    ], className="mb-5"),
                ], fluid=True)
            ]
        )
    ])
], fluid=True)

# =============================================
# CALLBACKS Y EJECUCIÓN
# =============================================

# Callback para la tabla comparativa
@app.callback(
    Output('tabla-comparativa', 'children'),
    [Input('dropdown-comparar', 'value')]
)
def update_tabla_comparativa(departamentos):
    if not departamentos or len(df) == 0:
        return html.P("Por favor, seleccione al menos un departamento para comparar.")
    
    # Crear un DataFrame con métricas por departamento
    resultados = []
    
    for dep in departamentos:
        dep_data = df[df['departamento'] == dep]
        
        if not dep_data.empty:
            # Calcular métricas para cada ocupación
            estudiantes = dep_data[dep_data['ocupacion'] == 'estudiante']
            trabajadores = dep_data[dep_data['ocupacion'] == 'trabajador']
            desempleados = dep_data[dep_data['ocupacion'] == 'desempleado']
            
            resultados.append({
                'Departamento': dep.capitalize(),
                'Edad Promedio': dep_data['Edad'].mean(),
                'Ingreso Promedio': dep_data['Ingreso'].mean(),
                'Total Jóvenes': len(dep_data),
                '% Estudiantes': len(estudiantes) / len(dep_data) * 100 if len(dep_data) > 0 else 0,
                '% Trabajadores': len(trabajadores) / len(dep_data) * 100 if len(dep_data) > 0 else 0,
                '% Desempleados': len(desempleados) / len(dep_data) * 100 if len(dep_data) > 0 else 0,
                'Ingreso Estudiantes': estudiantes['Ingreso'].mean() if not estudiantes.empty else 0,
                'Ingreso Trabajadores': trabajadores['Ingreso'].mean() if not trabajadores.empty else 0,
                'Ingreso Desempleados': desempleados['Ingreso'].mean() if not desempleados.empty else 0
            })
    
    df_resultados = pd.DataFrame(resultados)
    
    # Crear la tabla
    tabla = dash_table.DataTable(
        data=df_resultados.to_dict('records'),
        columns=[
            {"name": "Departamento", "id": "Departamento"},
            {"name": "Edad Promedio", "id": "Edad Promedio", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": "Ingreso Promedio (COP)", "id": "Ingreso Promedio", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": "Total Jóvenes", "id": "Total Jóvenes", "type": "numeric"},
            {"name": "% Estudiantes", "id": "% Estudiantes", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": "% Trabajadores", "id": "% Trabajadores", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": "% Desempleados", "id": "% Desempleados", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": "Ingreso Estudiantes (COP)", "id": "Ingreso Estudiantes", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": "Ingreso Trabajadores (COP)", "id": "Ingreso Trabajadores", "type": "numeric", "format": {"specifier": ",.0f"}},
            {"name": "Ingreso Desempleados (COP)", "id": "Ingreso Desempleados", "type": "numeric", "format": {"specifier": ",.0f"}}
        ],
        style_cell={'textAlign': 'center', 'padding': '10px'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
    )
    
    return tabla

if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_hot_reload=False)