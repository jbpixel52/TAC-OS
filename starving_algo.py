#%%           
boyish = {'messi':'bad',"bicho":'good'}

for insect in boyish.values():
    print(insect)

#%%

def get_starving_treshold(order):
    waiting_time = 0 #this must be the time of the order since entering queue
    order_in_queue = True
    while order_in_queue:  
        utis = 10 #example value
        order_is_split=True #determine if its a suborder
        wait_twice = 0
        wait_twice +=1 if order_is_split else 0
        starving_treshold = utis * wait_twice
        
        if waiting_time > starving_treshold:
            print('I WANT TO TALK TO THE MANAGER')

