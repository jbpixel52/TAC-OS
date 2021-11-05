#%%
while True:
    clients = [0,1,2,3,4,5,6,7,8,9,9,9,9]

    index_starved = int(input('indice:'))
    index_unlucky = 0

    def get_unlucky_index(index_starved):
        return int((len(clients)-index_starved)/2)
    index_unlucky =get_unlucky_index(index_starved=index_starved)
    starved = clients[index_starved]
    close_enough = clients[index_unlucky]

    clients[close_enough]=starved
    clients[starved] = close_enough

    print(clients)