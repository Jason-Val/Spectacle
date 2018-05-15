import time

start_time = time.time()

minutes = 60

while time.time() < start_time + minutes*60:
    print(time.time() - start_time)    
    time.sleep(1)

print("========== Finished counting!!!! ===========")