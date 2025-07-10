import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import scipy as sp
from tkcalendar import Calendar
from sys import platform
import datetime as dt
import meteostat as meteo
import yaml
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import os


#Preset values for different types of buildings.
presets = {
    "Default": {
        "Indoor Temperature Set Point (K)": "293.15",
        "Roof U-value (W/m²K)": "0.18",
        "Roof Area (m²)": "120",
        "Wall U-value (W/m²K)": "0.51",
        "Wall Area (m²)": "132",
        "Mass of Water in Tank (kg)": "200",
        "Initial Tank Temperature (K)": "318.15",
        "Heat Pump ON Threshold (K)": "313.15",
        "Heat Pump OFF Threshold (K)": "333.15",
        "Heat Loss Coefficient": "5",
        "Transfer Coefficient": "300"
    },
    "Factory": {
        "Indoor Temperature Set Point (K)": "289.15",
        "Roof U-value (W/m²K)": "0.25",
        "Roof Area (m²)": "1500",
        "Wall U-value (W/m²K)": "0.35",
        "Wall Area (m²)": "2500",
        "Mass of Water in Tank (kg)": "950",
        "Initial Tank Temperature (K)": "318.15",
        "Heat Pump ON Threshold (K)": "294.25",
        "Heat Pump OFF Threshold (K)": "304.25",
        "Heat Loss Coefficient": "5",
        "Transfer Coefficient": "300"
    },
    "Multi-Story Building": {
        "Indoor Temperature Set Point (K)": "289.15",
        "Roof U-value (W/m²K)": "0.2",
        "Roof Area (m²)": "700",
        "Wall U-value (W/m²K)": "0.2",
        "Wall Area (m²)": "3000",
        "Mass of Water in Tank (kg)": "700",
        "Initial Tank Temperature (K)": "318.15",
        "Heat Pump ON Threshold (K)": "308.15",
        "Heat Pump OFF Threshold (K)": "317.15",
        "Heat Loss Coefficient": "5",
        "Transfer Coefficient": "300"
    },
    "Edinburgh Tenement": {
        "Indoor Temperature Set Point (K)": "291.15",
        "Roof U-value (W/m²K)": "0.16",
        "Roof Area (m²)": "300",
        "Wall U-value (W/m²K)": "0.20",
        "Wall Area (m²)": "2000",
        "Mass of Water in Tank (kg)": "700",
        "Initial Tank Temperature (K)": "318.15",
        "Heat Pump ON Threshold (K)": "311.95",
        "Heat Pump OFF Threshold (K)": "321.95",
        "Heat Loss Coefficient": "5",
        "Transfer Coefficient": "300"
    }
}

def add_text_options(parent_frame, start_row=2):
    """
    Adds all the text options to the parent frame
    """
    options = [(k, v) for k, v in presets["Default"].items()]
    
    #Dictionary to store entry widgets
    entries = {}
    
    #Configure columns to expand properly
    parent_frame.grid_columnconfigure(1, weight=1)
    
    #Create label and entry for each option
    for idx, (label_text, default_value) in enumerate(options):
        label = tk.Label(parent_frame, text=label_text, anchor="w")
        label.grid(row=start_row + idx, column=0, padx=(5,10), pady=5, sticky="w")
        
        entry = tk.Entry(parent_frame)
        entry.grid(row=start_row + idx, column=1, padx=5, pady=5, sticky="ew")
        entry.insert(0, default_value)
        
        entries[label_text] = entry
    
    return entries


def create_preset_button(frame, text, preset_values, entries, row, column, color):
    #Helper function to create a preset button with consistent styling
    def update_values():
        if messagebox.askyesno("Confirm Preset", f"Load {text} preset values?"):
            for label, value in preset_values.items():
                if label in entries:
                    entry = entries[label]
                    entry.delete(0, tk.END)
                    entry.insert(0, value)

    button = tk.Button(
        frame,
        text=text,
        command=update_values,
        fg=color,
        #Make all buttons the same width
        width=15  
    )
    print(column)
    button.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")
    return button

def create_date_button(parent_frame, row, column):
    """
    Creates a date selection button and label showing the selected date.
    
    Args:
        parent_frame: The frame to place the button and label in
        row: Grid row position
        column: Grid column position
    
    Returns:
        date_reference: List containing the selected datetime
    """
    #Create reference for the selected date
    date_ref = {
        'start_date': None,
        'end_date': None
    }
    
    #Create and configure the status label
    start_label = tk.Label(
        parent_frame,
        text="",
    )
    end_label = tk.Label(
        parent_frame,
        text="",
    )
    
    def select_date():
        top = tk.Toplevel(parent_frame)
        top.title("Select Date")
        
        #Create calendar widget
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='ew')
        
        def get_date():
            selected_date = cal.get_date()
            start_datetime = dt.datetime.strptime(selected_date, '%Y-%m-%d')
            today = dt.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            
            #Validate date is not in future
            if start_datetime >= today:
                messagebox.showerror("Invalid Date", "Please select a date before current date.")
                return
            
            #Update the reference and label
            date_ref['start_date'] = start_datetime
            date_ref['end_date'] = start_datetime + dt.timedelta(days=1)
            start_label.config(text=f"Selected start date: {start_datetime.strftime('%Y-%m-%d')}")
            end_label.config(text=f"Selected end date: {(start_datetime + dt.timedelta(days=1)).strftime('%Y-%m-%d')}")
            top.destroy()
        
        #Add select button
        select_btn = tk.Button(
            top, 
            text="Select Date",
            command=get_date,
        )
        select_btn.grid(row=1, column=0, columnspan=2, pady=10)
        
        #Center the window
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f'+{x}+{y}')

     #Create the date selection button
    button = tk.Button(
        parent_frame,
        text="Select Date",
        command=select_date,
        width=15
    )
    
    #Layout button and label using grid
    button.grid(row=row, column=column, padx=5, pady=5)
    start_label.grid(row=row, column=column+1, padx=5, pady=5, sticky='w')
    end_label.grid(row=row+1, column=column+1, padx=5, pady=5, sticky='w')
    
    return date_ref

def calculate_tank_area(water_mass, tank_height):
    #Calculate tank surface area based on water mass and height
    radius = np.sqrt((water_mass / 1000) / (np.pi * tank_height))
    return (2 * np.pi * radius) * (radius + tank_height)

def calculate_temperature_change(T_tank, t, heat_pump_on, time_points, total_time, T_amb,
                               water_mass, heatloss_coff, U_cond, A_cond, Cond_out,
                               A_w, U_w, A_r, U_r, T_sp, Tot_thermal_cap):
    """
    Calculate rate of change of tank temperature.
    
    Args:
        T_tank: Current tank temperature (K)
        t: Current time (s)
        heat_pump_on: Boolean for heat pump status
        time_points: Array of simulation time points
        total_time: Total simulation time (s)
        T_amb: Array of ambient temperatures
        water_mass: Mass of water in tank (kg)
        heatloss_coff: Heat loss coefficient
        U_cond: Heat transfer coefficient
        A_cond: Condenser area (m²)
        Cond_out: Condenser output temperature (K)
        A_w: Wall area (m²)
        U_w: Wall U-value (W/m²K)
        A_r: Roof area (m²)
        U_r: Roof U-value (W/m²K)
        T_sp: Indoor temperature setpoint (K)
        Tot_thermal_cap: Total thermal capacity (J/K)
    """
    #Get current outdoor temperature
    time_index = min(min(int(t // (total_time / len(time_points))), 
                    len(time_points) - 1), 24)
    outdoor_temp = T_amb[time_index]
    
    #Calculate tank  surface area
    A_tank = calculate_tank_area(water_mass, 2.0)  #Assumes a fixed height of 2m
    
    #Calculate heat flows
    Q_loss = heatloss_coff * A_tank * (T_tank - outdoor_temp)
    Q_load = abs((A_w * U_w + A_r * U_r) * (outdoor_temp - T_sp))
    Q_trans = U_cond * A_cond * (Cond_out - T_tank) if heat_pump_on else 0
    
    return (Q_trans - Q_loss - Q_load) / Tot_thermal_cap

def calculate_cop(outdoor_temp, Cond_out, a, b):
    #Calculate Coefficient of Performance
    return a + (b / (Cond_out - outdoor_temp))

def simulate_heat_pump(time_points, T_tank_initial, Tank_ON, Tank_OFF, temp_amb,
                      water_mass, heatloss_coff, U_cond, A_cond, Cond_out,
                      A_w, U_w, A_r, U_r, T_sp, Tot_thermal_cap, a, b):
    """
    Run heat pump simulation with direct parameters.
    
    Args:
        time_points: Array of simulation time points
        T_tank_initial: Initial tank temperature (K)
        Tank_ON: Temperature to turn on heat pump (K)
        Tank_OFF: Temperature to turn off heat pump (K)
        T_amb: Array of ambient temperatures (C)
        water_mass: Mass of water in tank (kg)
        heatloss_coff: Heat loss coefficient
        U_cond: Heat transfer coefficient
        A_cond: Condenser area (m²)
        Cond_out: Condenser output temperature (K)
        A_w: Wall area (m²)
        U_w: Wall U-value (W/m²K)
        A_r: Roof area (m²)
        U_r: Roof U-value (W/m²K)
        T_sp: Indoor temperature setpoint (K)
        Tot_thermal_cap: Total thermal capacity (J/K)
        a, b: COP calculation coefficients
    """
    T_amb = (temp_amb + 273.15)
    n_points = len(time_points)
    total_time = time_points[-1] - time_points[0]
    
    #Initialize arrays
    T_tank = np.zeros(n_points)
    heat_pump_status = np.zeros(n_points)
    COP_timed = np.zeros(n_points)
    t_amb_timed = np.zeros(n_points)
    Q_trans_values = np.zeros(n_points)
    COP_values = []
    T_for_COP = []
    
    #Set initial values
    T_tank[0] = T_tank_initial
    heat_pump_on = False
    
    #Run simulation
    for i in range(1, n_points):
        #Update heat pump status
        prev_temp = T_tank[i - 1]
        heat_pump_on = (not heat_pump_on and prev_temp <= Tank_ON or 
                       heat_pump_on and prev_temp < Tank_OFF)
        
        #Calculate COP if heat pump is on
        if heat_pump_on:
            outdoor_temp = T_amb[min(int((i-1)/3.6), 24)]
            cop = calculate_cop(outdoor_temp, Cond_out, a, b)
            COP_values.append(cop)
            T_for_COP.append(prev_temp)
            COP_timed[i] = cop
            t_amb_timed[i] = outdoor_temp
        
        #Calculate next temperature
        temp_range = [time_points[i-1], time_points[i]]
        next_temp = odeint(calculate_temperature_change, prev_temp, temp_range, 
                          args=(heat_pump_on, time_points, total_time, T_amb,
                                water_mass, heatloss_coff, U_cond, A_cond, Cond_out,
                                A_w, U_w, A_r, U_r, T_sp, Tot_thermal_cap))
        T_tank[i] = next_temp[-1]
        
        #Store results
        heat_pump_status[i] = float(heat_pump_on)
        if heat_pump_on:
            Q_trans_values[i] = U_cond * A_cond * (Cond_out - T_tank[i])
    
    return (T_tank, heat_pump_status, COP_values, T_for_COP, 
            COP_timed, t_amb_timed, Q_trans_values)

def heat_load_time(temp_amb, T_sp, U_r, A_r, U_w, A_w):
    T_amb = (temp_amb + 273.15) #In K

    #Equation for calculating Heat load
    Q_load = (A_w * U_w * (T_amb - T_sp)) + (A_r * U_r * (T_amb - T_sp))

    dT_ambient = T_amb - T_sp

    #Storing the heat load values in a NumPy array for efficiency
    Q_load = np.array(Q_load)

    return dT_ambient, Q_load



def simulate():
    if date_reference['start_date'] is None or date_reference['end_date'] is None:
        messagebox.showerror("Invalid Date", "Please select a date before running the simulation.")
        return
    
    #Get values from UI inputs
    T_sp = float(entries["Indoor Temperature Set Point (K)"].get())
    U_r =  float(entries["Roof U-value (W/m²K)"].get())
    A_r =  float(entries["Roof Area (m²)"].get())
    U_w =  float(entries["Wall U-value (W/m²K)"].get())
    A_w =  float(entries["Wall Area (m²)"].get())
    water_mass = float(entries["Mass of Water in Tank (kg)"].get())
    T_tank_initial = float(entries["Initial Tank Temperature (K)"].get())
    Tank_ON = float(entries["Heat Pump ON Threshold (K)"].get())
    Tank_OFF = float(entries["Heat Pump OFF Threshold (K)"].get())
    heat_loss_coeff = float(entries["Heat Loss Coefficient"].get())
    transfer_coeff = float(entries["Transfer Coefficient"].get())

    start = date_reference['start_date']
    end = date_reference['end_date']

    #Define the location (Edinburgh: 55.9533° N, 3.1883° W)
    location = meteo.Point(55.9533, -3.1883)
    #Fetch hourly temperature data
    data = meteo.Hourly(location, start, end)

    data = data.fetch()

    #Extract temperatures from data aand store in numpy array
    temp_amb = np.array(data['temp'])   
    
    #Get directory where the sinput file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    #Path to the heat pump COP data 
    file_path = os.path.join(current_dir, "heat_pump_cop_synthetic_full.yaml")

    #Import the heat pump COP data YAML file
    with open(file_path, 'r') as file:
        #Import all the data under heat_pump_cop_data  
        input_data = yaml.safe_load(file)['heat_pump_cop_data']

    #Convert the data lists into arrays for more efficient access
    outdoor_temp = np.array([entry['outdoor_temp_C'] for entry in input_data])
    COP_noisy = np.array([entry['COP_noisy'] for entry in input_data])

    #Calculate difference in temperature DT = Condenser Temp (60°C) - Outdoor Temp
    #Also converting to kelvin by adding 273.15
    dT = (60 + 273.15) - (outdoor_temp + 273.15)

    # #Define fucntion of emperical relationship of COP: COP = a + (b / DT)
    def empirical_cop(DT, a, b):
        return a + (b / DT)

    #Using scipy fit line and obtain coefficients
    popt, _ = sp.optimize.curve_fit(empirical_cop, dT, COP_noisy, p0=[1, 1])

    #Extract and print the coefficients a and b
    a, b = popt
    print(f"Fitted coefficients: a = {a:.4f}, b = {b:.4f}")

    #Graph to show fit line for obtaining coefficients a and b
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(1/dT, COP_noisy, label='Data')
    ax.plot(1/dT, empirical_cop(dT, *popt), color='red', label='Fitted curve')
    ax.set_xlabel('Temperature difference 1/ΔT (K)')
    ax.set_ylabel('Coefficient Of Performance COP [-]')
    ax.set_title("COP against 1/ΔT")
    #Set distance between x ticks
    ax.set_xticks(np.arange(0.015, 0.035, 0.003))  
    ax.text(0.0205, 3.6, 'a = 2.19 , b= 30.94', style='italic', bbox={'facecolor': 'red', 'alpha': 0.5, 'pad': 10})
    ax.legend(loc='lower right')
    ax.grid(True)
    fig.tight_layout()
    #Location of gaprh in UI display
    plt_canvas = FigureCanvasTkAgg(fig, master=content_frame)
    plt_canvas.draw()
    plt_canvas.get_tk_widget().grid(row=0, column=4, rowspan=5, sticky="ns", pady=5, padx=5)
    
    dT_ambient, Q_load = heat_load_time(temp_amb, T_sp, U_r, A_r, U_w, A_w)

    #Plot heat load over temperature difference showing how heat demand of building changes with outdoor temperature
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(dT_ambient, Q_load)
    ax.set_xlabel('Temperature Difference ΔT (K)')
    ax.set_ylabel('Heat Load Q_load (W)')
    ax.set_title("Heat Load vs ΔT")
    ax.grid(True)
    fig.tight_layout()
    #Location of plot in UI
    plt_canvas = FigureCanvasTkAgg(fig, master=content_frame)
    plt_canvas.draw()
    plt_canvas.get_tk_widget().grid(row=0, column=6, rowspan=5, sticky="ns", pady=5, padx=5)

    #Simulation parameters
    total_time = 86400 #24hrs in seconds
    time_points = np.linspace(0, total_time, 1000)  # Creating 10000 time points during the 24h period
    #Converting outdoor teemperature to Kelvin
    outdoor_temp = outdoor_temp + 273.15

    Cond_out = (67+273.15) #Conderseer output temperature in (K)
    A_cond = 1.11 #Heat transfer area in (m^2)
    T_cond = 333.15 #Fixed condenser temperature in K (60degC)
    Tot_thermal_cap = 837200

    T_tank_solution, heat_pump_status_odeint, _, _, COP_Timed, amb_timed, Q_trans_values = simulate_heat_pump(time_points, T_tank_initial, Tank_ON, Tank_OFF, temp_amb,
                      water_mass, heat_loss_coeff, transfer_coeff, A_cond, Cond_out,
                      A_w, U_w, A_r, U_r, T_sp, Tot_thermal_cap, a, b)

    #Plot of tank temperature over time
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(time_points / 3600, T_tank_solution, label="Tank Temperature (K)")
    #Set lines to visualize upper and lower limits
    ax.axhline(Tank_ON, color='green', linestyle='--', label="ON Threshold (40°C)")
    ax.axhline(Tank_OFF, color='red', linestyle='--', label="OFF Threshold (60°C)")
    ax.set_xlabel("Time t (hours)")
    ax.set_ylabel("Tank Temperature T_tank (K)")
    ax.set_title("Tank Temperature Over 24 Hours \n (odeint with Pump Control)")
    on_text = ax.text(time_points[-1] / 3600, Tank_ON - 0.3, 'ON Threshold (40°C)', color='green', verticalalignment='top', horizontalalignment='right')
    on_text.set_path_effects([path_effects.Stroke(linewidth=0.3, foreground='black'), path_effects.Normal()])
    off_text = ax.text(time_points[-1] / 3600, Tank_OFF + 0.8, 'OFF Threshold (60°C)', color='red', verticalalignment='top', horizontalalignment='right')
    off_text.set_path_effects([path_effects.Stroke(linewidth=0.3, foreground='black'), path_effects.Normal()])
    fig.tight_layout()
    #Loaction in UI
    plt_canvas = FigureCanvasTkAgg(fig, master=content_frame)
    plt_canvas.draw()
    plt_canvas.get_tk_widget().grid(row=5, column=4, rowspan=5, sticky="ns", pady=5, padx=5)


    #Plot heat pump status as step funtion. 1 is ON 0 is OFF. shows and demonstrates correct system operation
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(time_points / 3600, heat_pump_status_odeint, label="Heat Pump Status On/Off [-]")
    ax.set_xlabel("Time t (hours)")
    ax.set_ylabel("Heat Pump Status")
    ax.set_title("Heat Pump Status Over 24 Hours")
    ax.grid(True)
    fig.tight_layout()
    #Location of plot in the UI
    plt_canvas = FigureCanvasTkAgg(fig, master=content_frame)
    plt_canvas.draw()
    plt_canvas.get_tk_widget().grid(row=5, column=6, rowspan=5, sticky="ns", pady=5, padx=5)

    #COP against ambient temp
    fig, ax = plt.subplots(figsize=(5, 4))
    amb_timed = np.delete(amb_timed, np.where(amb_timed==0))
    COP_Timed = np.delete(COP_Timed, np.where(COP_Timed==0))
    ax.scatter( amb_timed , COP_Timed, label="COP vs Ambient temp")
    ax.set_xlabel("Ambient Temperature T (K)")
    ax.set_ylabel("COP Coefficient Of Performance [-]")
    ax.set_title("COP vs Ambient Temperature")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    #Location in the UI
    plt_canvas = FigureCanvasTkAgg(fig, master=content_frame)
    plt_canvas.draw()
    plt_canvas.get_tk_widget().grid(row=10, column=4, rowspan=5, sticky="ns", pady=5, padx=5)

    #System relative efficiency calculation
    lowest_temp = min(amb_timed)
    #COP carnot is maximum achievable efficicency
    COP_carnot = T_sp/(T_sp - lowest_temp)
    Efficinecy=(COP_Timed/COP_carnot)*100

    #Efficicncy vs temperature plot
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(amb_timed,Efficinecy)
    ax.set_title("Heat pump Efficiency Relative to Outdoor \n Temperature")
    ax.set_ylabel("Efficiency E (%)")
    ax.set_xlabel("Ambient Temperature T (K)")
    ax.grid(True)
    fig.tight_layout()
    #UI location
    plt_canvas = FigureCanvasTkAgg(fig, master=content_frame)
    plt_canvas.draw()
    plt_canvas.get_tk_widget().grid(row=10, column=6, rowspan=5, sticky="ns", pady=5, padx=5)


    T_amb = (temp_amb + 273.15)

    #Performance metrics
    #Calculating efficiency usig COP carnot
    lowest_temp = min(amb_timed)
    COP_carnot = T_sp/(T_sp-lowest_temp)
    Efficiency_out=(COP_Timed/COP_carnot)*100

    global Eff
    Eff = np.mean(Efficiency_out)
    
    #Energy Coverage ratio
    average_Q_trans = np.mean(Q_trans_values)
    average_Q_load = np.mean(np.abs(A_w * U_w * (T_amb - T_sp) + A_r * U_r * (T_amb - T_sp)))

    global ECR
    ECR = average_Q_trans/average_Q_load
    
    
    #Calculate the maximum thermal output of the heat pump based on the lowest tank temperature
    lowest_tank_temp = np.min(T_tank_solution)
    global Q_max
    Q_max = transfer_coeff * A_cond * (T_cond - lowest_tank_temp)
    #Assuming Q_trans_values and COP_Timed have been calculated

    #Total energy expenditure
    #Generate corresponding arrays for interpolation
    time_points_qtrans = np.linspace(0, 1, len(Q_trans_values))
    time_points_cop = np.linspace(0, 1, len(COP_Timed))

    #Interpolate COP_Timed to match the length of Q_trans_values (1000 points)
    COP_new = np.interp(time_points_qtrans, time_points_cop, COP_Timed)

    power_consumption_instantaneous = Q_trans_values / COP_new
    time_step_duration = total_time / len(Q_trans_values) 

    total_energy_consumption = np.sum(power_consumption_instantaneous * time_step_duration)
    global total_energy_consumption_kwh
    total_energy_consumption_kwh = total_energy_consumption / 3_600_000  #In kWh

    update_performance_metrics()

    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d+0+0" % (w, h))

def update_performance_metrics():
    """Update the performance metrics labels with current values"""
    global performance_labels

    #If labels don't exist yet, create them
    if not hasattr(update_performance_metrics, 'labels'):
        update_performance_metrics.labels = {
            'ecr': tk.Label(additional_options_frame, font=('Arial', 16)),
            'efficiency': tk.Label(additional_options_frame, font=('Arial', 16)),
            'max_output': tk.Label(additional_options_frame, font=('Arial', 16)),
            'energy': tk.Label(additional_options_frame, font=('Arial', 16)),
            'status': tk.Label(additional_options_frame, font=('Arial', 24))
        }
        
        #Grid the labels
        update_performance_metrics.labels['ecr'].grid(row=19, column=0, columnspan=2)
        update_performance_metrics.labels['efficiency'].grid(row=20, column=0, columnspan=2)
        update_performance_metrics.labels['max_output'].grid(row=21, column=0, columnspan=2)
        update_performance_metrics.labels['energy'].grid(row=22, column=0, columnspan=2)
        update_performance_metrics.labels['status'].grid(row=18, column=0, columnspan=2)
    
    #Update the text of each label
    if ECR:
        update_performance_metrics.labels['ecr'].config(text=f'ECR is: {ECR:.2f}')
    if Eff:
        update_performance_metrics.labels['efficiency'].config(text=f'Efficiency relative to outdoor temperature is {Eff:.2f}%')
    if Q_max:
        update_performance_metrics.labels['max_output'].config(text=f'Max heat pump output is: {Q_max:.2f}W')
    if total_energy_consumption_kwh:
        update_performance_metrics.labels['energy'].config(text=f'Total energy expenditure is: {total_energy_consumption_kwh:.2f}kWh')
    
    #Update system status
    if ECR == "":
        return
    
    if ECR < 1:
        system_status = "Inefficient"
        status_color = "red"
    else:
        system_status = "Efficient"
        status_color = "green"
    
    update_performance_metrics.labels['status'].config(
        text=f"System status: {system_status}",
        fg=status_color
    )


if __name__ == "__main__":
    #Step 2: Create the Tkinter Window
    root = tk.Tk()
    root.title("Heat Pump Simulation")
    root.geometry("1080x720")

    #Step 3: Create a Frame for Grid Layout
    frame = ttk.Frame(root)
    frame.grid(row=0, column=0, sticky="nsew")

    #Step 4: Create a Canvas and Scrollbar
    canvas = tk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    #Step 5: Create a Frame for Scrollable Content
    content_frame = ttk.Frame(canvas)

    #Step 6: Configure the Canvas and Scrollable Content Frame
    content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    
    #Add a header frame for the title and button
    header_frame = ttk.Frame(content_frame)
    header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    tk.Label(header_frame, text="Simulation Parameters", font=("Arial", 32, "bold")).grid(row=0, column=0, padx=10, pady=10)
    header_frame.columnconfigure(0, weight=1)

    tk.Label(header_frame, text="Select a preset or configure custom values:", font=("Arial", 16)).grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")

    additional_options_frame = ttk.Frame(content_frame)
    additional_options_frame.grid(row=2, column=0, rowspan=11, columnspan=2, padx=10, pady=10, sticky="nsew")
    entries = add_text_options(additional_options_frame, start_row=2)

    button_frame = ttk.Frame(content_frame)
    button_frame.grid(row=1, column=0, columnspan=10, sticky="ew")
    create_preset_button(button_frame, "Default", presets["Default"], entries, 1, 0, "#4CAF50")
    create_preset_button(button_frame, "Factory", presets["Factory"], entries, 1, 1, "#2196F3")
    create_preset_button(button_frame, "Multi-Story Building", presets["Multi-Story Building"], entries, 2, 0, "#FF9800")
    create_preset_button(button_frame, "Edinburgh Tenement", presets["Edinburgh Tenement"], entries, 2, 1, "#F44336")

    #Create the button
    date_reference = create_date_button(additional_options_frame, row=14, column=0)

    button = tk.Button(
        additional_options_frame,
        text="Run Simulation",
        command=simulate,
        width=15
    )
    button.grid(row=15, column=0, padx=5, pady=5)

    tk.Label(additional_options_frame, text="Performance Metrics", font=("Arial", 32, "bold")).grid(row=16, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    ECR = ""
    Eff = ""
    Q_max = ""
    total_energy_consumption_kwh = ""
    update_performance_metrics()

    #Step 8: Create Window Resizing Configuration
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    #Step 9: Pack Widgets onto the Window
    canvas.create_window((0, 0), window=content_frame, anchor="nw")
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    #Step 10: Bind the Canvas to Mousewheel Events
    def _on_mousewheel(event):
        if platform == "darwin":
            canvas.yview_scroll(int(-1 * event.delta), "units")
        elif platform == "win32":
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    #Step 11: Run the Tkinter Event Loop
    root.mainloop()
