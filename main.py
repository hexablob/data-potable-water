import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import glob
import plotly.express as px
import plotly.io as pio
from unidecode import unidecode
import geopandas as gpd
from dotenv import load_dotenv
import os 
import numpy as np

load_dotenv()
px.set_mapbox_access_token(os.getenv("MAPBOX_TOKEN"))

def remove_accents_and_uppercase(str_val):
    return unidecode(str_val).upper()

def process_dataframe(df):
    df['dateprel'] = pd.to_datetime(df['dateprel'])
    df['month'] = df['dateprel'].dt.month
    df['year'] = df['dateprel'].dt.year
    df['nomcommuneprinc'] = df['nomcommuneprinc'].str.upper()
    df_filtered = df[df['conclusionprel'].str.contains("Eau d'alimentation non-conforme|Eau d'alimentation non conforme", na=False)]
    return df_filtered.groupby(['year', 'month', 'nomcommuneprinc']).size().reset_index(name='count')

def load_and_process_data(year_range):
    df_combined = pd.DataFrame()
    for year in year_range:
        print(f'Processing year {year}')
        for file_path in glob.glob(f'./dataset/DIS_PLV_{year}_*.txt'):
            df = pd.read_csv(file_path, delimiter=',')
            df_yearly = process_dataframe(df)
            df_combined = pd.concat([df_combined, df_yearly])
    return df_combined

def create_heatmap(df):
    plt.figure(figsize=(12, 8))
    heatmap_df = df.groupby(['year', 'month']).agg({'count': 'sum'}).reset_index()
    heatmap_data = heatmap_df.pivot(index="month", columns="year", values="count")
    ax = sns.heatmap(heatmap_data, annot=True, cmap="coolwarm", fmt=".0f", linewidths=.5,
                     annot_kws={"size": 12}, cbar_kws={'label': 'Nombre d\'occurrences'})
    plt.title('Eau d\'alimentation non-conforme aux limites de qualité.')
    plt.xlabel('Année')
    plt.ylabel('Mois')
    plt.xticks(rotation=45)
    plt.yticks(ticks=range(0, 12), labels=['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'], rotation=0)
    plt.savefig('heatmap.png', dpi=300, bbox_inches='tight')

def create_barplot(df):
    plt.figure(figsize=(8, 45))
    commune_counts = df.groupby('nomcommuneprinc').agg({'count': 'sum'}).reset_index().sort_values('count', ascending=False)
    n_bars = len(commune_counts)
    palette = plt.cm.rainbow(np.linspace(1, 0, n_bars))

    # Utilisation de barplot de Matplotlib
    plt.barh(commune_counts['nomcommuneprinc'], commune_counts['count'], color=palette)
    ax2 = plt.gca()
    ax2.invert_yaxis()
    ax2.margins(y=0)
    for i, v in enumerate(commune_counts['count']):
        ax2.text(v + 3, i + .25, str(v), color='black', ha='center', va='center', fontsize=7)
    plt.title("Eau d\'alimentation non-conforme aux limites de qualité par commune depuis 2016.")
    plt.xlabel('Nombre d\'échantillons d\'eau non-conforme aux limites de qualité')
    plt.ylabel('Nom de la commune')
    plt.xticks(rotation=45)
    plt.yticks(fontsize=7)
    plt.savefig('barplot.png', dpi=300, bbox_inches='tight')
    return commune_counts

def create_choropleth(df, gdf):
    merged_df = gdf.merge(df, left_on='nom', right_on='nomcommuneprinc', how='left')
    merged_df['count'].fillna(0, inplace=True)
    top_tier_value = merged_df['count'].quantile(0.95)
    fig = px.choropleth_mapbox(merged_df,
                               geojson=merged_df.geometry,
                               locations=merged_df.index,
                               color='count',
                               color_continuous_scale=["white", "lightblue", "violet", "indigo", "red"],
                               range_color=(0, top_tier_value),
                               mapbox_style="carto-positron",
                               opacity=0.5,
                               hover_name="nom",
                               hover_data=["nomcommuneprinc", "count"],
                               labels={'count': 'Occurrences'},
                               title='Occurrences de non-conformité de l\'eau potable distribuée en Corse depuis 2016.',
                               center={"lat": 42.039604, "lon": 9.012893},
                               zoom=7.8,
                               width=1280,
                               height=1080)
    fig.update_traces(hovertemplate="<br>".join([
        "Commune: %{hovertext}",
        "Occurrences: %{z}"
    ]))

    fig.update_layout(
        mapbox_style='open-street-map',
        coloraxis_colorbar=dict(
            xanchor='left',
            titleside='right',
        )
    )

    fig.update_layout(title='Occurrences de non-conformité de l\'eau en Corse')
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Corsica Water Quality</title>
    </head>
    <body>

    <h1>Occurrences de non-conformité de l'eau en Corse (2016-2023)</h1>
   
    """

    plotly_html_str = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

    with open('index.html', 'w') as f:
        f.write(html_code)
        f.write("""<h2>Carte Choroplèthe</h2>""")
        f.write(plotly_html_str)
        f.write("""
                 <h2>Heatmap</h2>
                <img height="600" src="heatmap.png" alt="Heatmap">

                <h2>Barplot</h2>
                <img width="980" src="barplot.png" alt="Barplot">
                """)
        f.write("""
        </body>
        </html>
        """)

if __name__ == "__main__":
    df_plv_combined = load_and_process_data(range(2016, 2024))
    create_heatmap(df_plv_combined)
    commune_counts = create_barplot(df_plv_combined)
    
    gdf = gpd.read_file("communes-corse.geojson")
    gdf['nom'] = gdf['nom'].apply(remove_accents_and_uppercase)
    create_choropleth(commune_counts, gdf)