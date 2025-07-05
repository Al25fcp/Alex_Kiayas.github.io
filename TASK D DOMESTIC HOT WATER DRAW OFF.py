import numpy as np
import matplotlib.pyplot as plt

#Three different events are considered to have the biggest effect on hot water demand: showers, dishwashing, and laundry.
#Educated guesses were made to estimate the probability of each event occurring either at peak or off-peak times.

#Shower parameters
shower_vol = 50  #Average volume of water used in L for a 5 minute shower
shower_peak_prob = 0.7  #Probability during peak hours
shower_off_peak_prob = 0.02  #Probability during off-peak hours

#Dishwashing parameters
dishwashing_vol = 10  #Average volume of water used in L
dishwashing_peak_prob = 0.5  #Probability during peak hours
dishwashing_off_peak_prob = 0.1  #Probability during off-peak hours

#Laundry parameters
laundry_vol = 60  #Average volume of water used in L
laundry_peak_prob = 0.3  #Probability during peak hours
laundry_off_peak_prob = 0.05  #Probability during off-peak hours

#Peak hours are assumed to be 6-8 am and 5-7 pm every day
peak_hours = list(range(6, 8)) + list(range(17, 19))

#Daily usage limits
#Set the variables to 0 for each 24h period
daily_laundry_count = 0
daily_dishwasher_count = 0
daily_shower_count = 0

MAX_LAUNDRY_USAGE = (3/7) #Laundry happens on average 3 times a week so the probability of it happening over a single time period is 3/7
MAX_DISHWASHER_USAGE = (215/365) #Average dishwasher usage in the UK is 215 times over the year per household
MAX_SHOWER_USAGE = 3

#Hot water demand simulation for a 24-hour time period
def water_demand():
    global daily_laundry_count, daily_dishwasher_count, daily_shower_count
    #Reset counters at the start of each simulation
    daily_laundry_count = 0
    daily_dishwasher_count = 0
    daily_shower_count = 0

    shower_demand = [0] * 24
    dishwashing_demand = [0] * 24
    laundry_demand = [0] * 24
    
    #List to store hot water demand for each hour
    demand = [0] * 24 

    #Loop through each hour of the day
    for hour in range(24):
        #Assume no events occur between midnight and 6am
        if hour < 5:
            continue

        #Starting demand for each hour is assumed to be 0
        hourly_demand = 0 
        #Check if this hour is in the peak hours list
        hour_cond = hour in peak_hours  

        #Check if shower event happens
        prob = shower_peak_prob if hour_cond else shower_off_peak_prob
        if np.random.rand() < prob and daily_shower_count < MAX_SHOWER_USAGE:
            hourly_demand += shower_vol
            shower_demand[hour] += shower_vol  #Track shower demand separately
            daily_shower_count += 1  #Increment daily shower count

        #Check if dishwashing event happens
        prob = dishwashing_peak_prob if hour_cond else dishwashing_off_peak_prob
        if np.random.rand() < prob and daily_dishwasher_count < MAX_DISHWASHER_USAGE:
            hourly_demand += dishwashing_vol
            dishwashing_demand[hour] += dishwashing_vol  #Track dishwashing demand separately
            daily_dishwasher_count += 1  #Increment daily dishwasher count

        #Check if laundry event happens
        prob = laundry_peak_prob if hour_cond else laundry_off_peak_prob
        if np.random.rand() < prob and daily_laundry_count < MAX_LAUNDRY_USAGE:
            hourly_demand += laundry_vol
            laundry_demand[hour] += laundry_vol  #Track laundry demand separately
            daily_laundry_count += 1  #Increment daily laundry count

        #Store demand in the demand list
        demand[hour] = hourly_demand  

    #Calculate cumulative demand for smoothing
    cumulative_demand = np.cumsum(demand)
    
    total_demand = sum(demand)
    return shower_demand, dishwashing_demand, laundry_demand, cumulative_demand, total_demand

#Run simulation
shower_demand, dishwashing_demand, laundry_demand, cumulative_demand, total_demand = water_demand()



#Results over 24-hour period
plt.figure(figsize=(10, 5))  
plt.plot(range(24), shower_demand,color='dodgerblue',  marker='o', label="Shower Demand")
plt.plot(range(24), dishwashing_demand,color ='red', marker='o', label="Dishwashing Demand")
plt.plot(range(24), laundry_demand,color='green', marker='o', label="Laundry Demand")
plt.plot(range(24), cumulative_demand, color="blueviolet", linestyle="--", linewidth=2, label="Cumulative Demand (Smooth)")

plt.xlabel("Hour of Day T (h)")           
plt.ylabel("Hot Water Demand DWH (L)")  
plt.title("Simulated Hot Water Demand Over 24 Hours by Event with Cumulative Demand")  
plt.xticks(range(0, 25, 5))        
plt.legend()                        
plt.grid(True)           

#Regions to highlight peak hours        
plt.axvspan(6, 8, color='gray',alpha=0.3)
plt.axvspan(17, 19, color='gray',alpha=0.3)

#Labeling figures
plt.figtext(0.15, -0.03, f"Total Daily Water Consumption: {total_demand} liters", 
            style='italic', bbox={'facecolor': 'gray', 'alpha': 0.5, 'pad': 10}, 
            fontsize=12, color="blue")
plt.figtext(.55, -0.03, "Gray regions indicate peak hours", 
            style='italic', bbox={'facecolor': 'gray', 'alpha': 0.5, 'pad': 10}, 
            fontsize=12, color="black")

plt.show()

print("Total hot water demand is", total_demand)
