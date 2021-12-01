#%%
 
A = {'a':'112','b':'22','c':'52'} #test dict



print(A)
keys = [] #key list
values = [] #value list

for key, value in A.items():
    keys.append(key)
    values.append(int(value)) #CLAVE AQUI QUE LO CASTEO A INT, si no no se hace sort
    
print(f"KEYS: {keys}")
print(f"VALUES PRE SORT {values}")
values = sorted(values)
print(f"ValUES POST SORT {values}")
zip_iterator = zip(keys, values)
FINAL = dict(zip_iterator)
print(f"FINAL DICT {FINAL}")
# %%
