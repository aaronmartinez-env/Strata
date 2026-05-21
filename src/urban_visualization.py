import pydeck as pdk



def create_pm10_towers(df):

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,

        get_position='[longitude, latitude]',
        get_elevation='pm10 * 100',

        elevation_scale=1,
        radius=150,

        get_fill_color='[pm10 * 5, 80, 150]',
        pickable=True,
        auto_highlight=True
    )

    view_state = pdk.ViewState(
        latitude=df["latitude"].mean(),
        longitude=df["longitude"].mean(),
        zoom=11,
        pitch=45
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "text": """
            Station: {station}
            PM10: {pm10}
            """
        }
    )

    return deck