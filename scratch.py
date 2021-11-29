import pandas as pd
import json

def test(a=None, b=None):
    if a is None or b is None:
        print(f'{a=} and {b=}')
    else:
        print('None were None...')

                            

def json_to_dataframe(filepath, normal_column=None):
    if normal_column is None:
        return pd.read_json(filepath)
    elif normal_column is not None:
        with open(filepath, mode='r') as file:
            data = json.loads(file.read())
            df_nested = pd.json_normalize(
                data, record_path=[str(normal_column)])
            file.close()
        return df_nested

with open('logs/staff/taqueros/Omar.json', mode='r') as file:
    data = json.load(file)
    file.close()
df = pd.DataFrame(data.get('ordenes')).transpose()
#df_new=pd.DataFrame(df['ordenes'],index = list(df['ordenes'].keys()))

