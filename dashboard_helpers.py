
import json
import os

import pandas as pd
from dash import dash_table, html




def read_log(filepath=None):
    """[summary]

    Args:
        filepath ([type], optional): [description]. Defaults to None.

    Returns:
        [list]: [description]
    """
    HTMLparagraphs = []
    with open(filepath, mode='r') as file:
        for line in file:
            HTMLparagraphs.append(html.P(line))
        file.close()
    return HTMLparagraphs


def json_to_dataframe(filepath, normal_column=None):
    """[summary]

    Args:
        filepath ([type]): [description]
        normal_column ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]
    """
    if normal_column is None:
        return pd.read_json(filepath)
    elif normal_column is not None:
        with open(filepath, mode='r') as file:
            data = json.loads(file.read())
            df_nested = pd.json_normalize(
                data, record_path=[str(normal_column)])
            file.close()
        return df_nested


def taqueroToDataFrame(filepath=None, column=None):
    with open(filepath, mode='r') as file:
        data = json.load(file)
        file.close()
    df = pd.DataFrame(data.get(column)).transpose()
    return df


def readjson(filepath):
    """[summary]

    Args:
        filepath ([type]): [description]

    Returns:
        [type]: [description]
    """
    data = dict()
    with open(filepath, mode='r') as file:
        data = json.load(file)
        # print(data)
        file.close()
    return dict(data)


def get_status(filepath, key):
    """[summary]

    Args:
        filepath ([string]): [description]
        key ([string]): [description]

    Returns:
        [type]: [description]
    """
    metadata = readjson(filepath)
    if key in metadata:
        if metadata.get(key) is True:
            if key == 'cooking' or 'isFanActive':
                return 'YES'
            else:
                return metada.get(key)
        elif metadata.get(key) is False:
            if key == 'cooking' or 'isFanActive':
                return 'NO'
            else:
                return metada.get(key)
        else:
            # ESTO ES PARA LOS CASOS COMO NOMBRES O NON BINARY VALUES
            return metadata.get(key)
    else:
        return 'key doesn\'t exist in given metadata dictionary.'


def Tables(directory='logs/staff/taqueros'):
    elements_list = []
    df = json_to_dataframe('jsons.json',normal_column='orden')
    """elements_list.append(dash_table.DataTable(
        columns=[
            {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
        ],
        id='global-orders',
        data=json_to_dataframe(
            filepath='jsons.json', normal_column='orden').to_dict('records'),
        sort_action="native",
        page_action="native",
        page_current=0,
        page_size=5))"""
    filepaths = []
    for subdir, dirs, files in os.walk(directory):
        for file in files:
            filepaths.append(os.path.join(subdir, file))

    for file in filepaths:
        DataFrame = taqueroToDataFrame(file)
        elements_list.append(
            dash_table.DataTable(
                columns=[
                    {"name": str(i), "id": str(i)} for i in DataFrame.columns
                ],
                data=DataFrame,
                editable=False,
                sort_action="native",
                page_action="native",
                page_current=0,
                page_size=5,
            )
        )
    return elements_list


def staff_metadata_html(directory='logs/staff/taqueros'):
    """[summary]

    Args:
        directory (str, optional): [description]. Defaults to 'logs/staff/taqueros'.

    Returns:
        [list]: [created html wrapped elements for DASH]
    """
    elements_list = []
    filepaths = []
    for subdir, dirs, files in os.walk(directory):
        for file in files:
            filepaths.append(os.path.join(subdir, file))

    for file in filepaths:
        metadata = readjson(file)
        taquero_div = []
        taquero_div.append(
            html.H3(f"metadata for {metadata.get('name')}"))
        for key, value in metadata.items():
            if key != 'ordenes':
                taquero_div.append(html.P(f" {key} = {value}"))
        elements_list.append(html.Div(children=taquero_div))

    return elements_list


def taqueroOrderTable(filepath, dataframe=None):

    dash_table.DataTable(
        columns=[
            {"name": str(i), "id": str(i)} for i in dataframe.columns
        ],
        id='datatable_taquero',
        data=nested_dict_to_dataframe(filepath, 'ordenes').to_dict('records'),
        editable=False,
        sort_action="native",
        page_action="native",
        page_current=0,
        page_size=10,
    )


if __name__ == "__main__":
    staffhtml = staff_metadata_html()
