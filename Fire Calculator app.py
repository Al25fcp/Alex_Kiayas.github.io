
import numpy as np
import matplotlib.pyplot as plt
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox
import pandas as pd
from tkinter import filedialog

# ==============================================================================
# --- CORE LOGIC FUNCTIONS ---
# ==============================================================================

def run_zone_model_simulation(
    room_height, room_width, room_length, 
    fire_growth_rate, 
    temp_tenability, height_tenability,
    max_sim_time, resolution
):
    """Runs the two-zone model simulation based on user inputs."""
    print("Running Zone Model Simulation...")
    #Constants
    air_density = 1.2; specific_hc = 1.0; T_amb = 292; gravity = 9.81; K = 0.2; z_0 = 0.0
    
    #Calculations
    A_room = room_width * room_length
    time_points = np.linspace(0, max_sim_time, resolution)
    dt = time_points[1] - time_points[0]
    HRR = fire_growth_rate * (time_points**2)
    Q_conv = 0.7 * HRR
    
    #Initialize arrays
    z = np.zeros(resolution); T_upper = np.zeros(resolution); rho_upper = np.zeros(resolution)
    m_upper = np.zeros(resolution); T_smoke = np.zeros(resolution)
    
    #Initial conditions
    z[0] = room_height; T_upper[0] = T_amb; rho_upper[0] = air_density; m_upper[0] = 0.0; T_smoke[0] = T_amb
    
    con = K * ((gravity * (air_density**2)) / (specific_hc * T_amb))**(1/3)
    
    #Main simulation loop
    for i in range(1, resolution):
        z_previous = z[i-1]; m_upper_previous = m_upper[i-1]; T_upper_previous = T_upper[i-1]
        Q_conv_previous = Q_conv[i-1]
        
        if Q_conv_previous <= 0:
            m_plume = 0.0
        else:
            plume_height = max(0, z_previous - z_0)
            m_plume = con * (Q_conv_previous**(1/3)) * (plume_height**(5/3))
      
        mass_added = m_plume * dt
        m_upper[i] = m_upper_previous + mass_added
        
        if m_plume <= 0:
            T_smoke[i] = T_amb
        else:
            T_smoke[i] = (Q_conv_previous / (m_plume * specific_hc)) + T_amb 

        numerator = (m_upper_previous * T_upper_previous) + (mass_added * T_smoke[i])
        denominator = m_upper[i]
        
        if denominator <= 0:
            T_upper[i] = T_amb
        else:
            T_upper[i] = numerator / denominator

        rho_upper[i] = air_density * (T_amb / T_upper[i])
        
        if m_upper[i] <= 0:
            z[i] = room_height
        else:
            z[i] = room_height - (m_upper[i] / rho_upper[i] / A_room)
    
    print("Zone Model Simulation Finished!")
    return time_points, HRR, Q_conv, T_upper, z, temp_tenability, height_tenability

def calculate_external_fire_spread(inputs):
    """Calculates fire spread and returns a dictionary of RAW data, including allowable area."""
    # Unpack inputs
    width = inputs["Width (m)"]
    height = inputs["Height (m)"]
    bound_dist = inputs["Boundary Dist. (m)"]
    i_crit = inputs["I_crit (W/m²)"]
    source_emissive_power = inputs["Radiation Intensity (W/m²)"]
    sprinklers_active = inputs["Sprinklered"]

    # Calculate view factor
    X = width / (4 * bound_dist) if bound_dist > 0 else 0
    Y = height / (4 * bound_dist) if bound_dist > 0 else 0
    if X > 0 and Y > 0:
        term1 = (X / np.sqrt(1 + X**2)) * np.arctan(Y / np.sqrt(1 + X**2))
        term2 = (Y / np.sqrt(1 + Y**2)) * np.arctan(X / np.sqrt(1 + Y**2))
        view_factor = (2 / np.pi) * (term1 + term2)
    else: view_factor = 0.0

    # Calculate radiation and apply sprinkler reduction
    initial_radiation_received = source_emissive_power * view_factor
    sprinkler_reduction_factor = 0.5 if sprinklers_active == 1 else 1.0
    final_radiation_received = initial_radiation_received * sprinkler_reduction_factor
    
    # Calculate unprotected area ratio
    unprotected_area_ratio = i_crit / final_radiation_received if final_radiation_received > 0 else 1.0
    max_unprotected_area_ratio = min(1.0, unprotected_area_ratio)

    # --- NEW CALCULATION: Convert ratio to physical area ---
    total_radiator_area = width * height
    max_allowable_area_m2 = max_unprotected_area_ratio * total_radiator_area

    # --- Create results dictionary with RAW NUMBERS ---
    result_data = inputs.copy()
    result_data.update({
        "View Factor": view_factor,
        "Initial Radiation (W/m²)": initial_radiation_received,
        "Sprinkler Reduction Factor": sprinkler_reduction_factor,
        "Final Radiation Received (W/m²)": final_radiation_received,
        "Max Unprotected Area (Ratio)": max_unprotected_area_ratio,
        # ADDED: The new value
        "Max Allowable Area (m²)": max_allowable_area_m2
    })
    
    return result_data
# ==============================================================================
# --- GLOBAL VARIABLES & GUI HELPER FUNCTIONS ---
# ==============================================================================
plot_canvas = None
results_history = []

def plot_results(parent_frame, results):
    """Takes zone model results, calculates breach times, and plots them."""
    global plot_canvas
    if plot_canvas: plot_canvas.get_tk_widget().destroy()
    time_points, HRR, Q_conv, T_upper, z, upper_temp_ten, plume_ten = results
    time_to_temp_breach, time_to_height_breach, break_time = None, None, None
    for i in range(len(time_points)):
        if T_upper[i] >= upper_temp_ten and time_to_temp_breach is None: time_to_temp_breach = time_points[i]
        if z[i] <= plume_ten and time_to_height_breach is None: time_to_height_breach = time_points[i]
        if z[i] <= 0.0 and break_time is None: break_time = time_points[i]
        if time_to_temp_breach and time_to_height_breach and break_time: break
    temp_result_label.configure(text=f"{time_to_temp_breach:.1f} s" if time_to_temp_breach is not None else "Not Met")
    height_result_label.configure(text=f"{time_to_height_breach:.1f} s" if time_to_height_breach is not None else "Not Met")
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    fig.suptitle('Zone Model Simulation Results', fontsize=16)
    
    ax1.plot(time_points, HRR, label='Total HRR (kW)', color='red'); ax1.plot(time_points, Q_conv, label='Convective HRR (kW)', color='orange', linestyle='--'); ax1.set_ylabel('Heat Release Rate (kW)'); ax1.grid(True); ax1.legend()
    ax2.plot(time_points, T_upper, label='Upper Layer Temp.', color='blue'); ax2.axhline(y=upper_temp_ten, color='r', linestyle=':', label=f'Tenability Limit ({upper_temp_ten} K)'); ax2.set_ylabel('Temperature (K)'); ax2.grid(True); ax2.legend()
    ax3.plot(time_points, z, label='Interface Height', color='green'); ax3.axhline(y=plume_ten, color='r', linestyle=':', label=f'Tenability Limit ({plume_ten} m)'); ax3.set_xlabel('Time (s)'); ax3.set_ylabel('Interface Height (m)'); ax3.grid(True); ax3.legend()
    
    if break_time is not None:
        shade_properties = {'color': 'grey', 'alpha': 0.4}; text_properties = {'color': 'white', 'fontsize': 14, 'rotation': 90, 'ha': 'center', 'va': 'center'}
        end_time = time_points[-1]
        for ax in [ax1, ax2, ax3]:
            ax.axvspan(break_time, end_time, **shade_properties)
            ax.text(break_time + (end_time - break_time) / 2, sum(ax.get_ylim()) / 2, 'Model Breaks', **text_properties)
    
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    plot_canvas = FigureCanvasTkAgg(fig, master=parent_frame); plot_canvas.draw(); plot_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

def on_run_simulation_button_click():
    """Button command for the Zone Model tab."""
    try:
        results = run_zone_model_simulation(
            room_height=float(entry_height.get()), room_width=float(entry_width.get()), room_length=float(entry_length.get()),
            fire_growth_rate=float(entry_fire_growth.get()), temp_tenability=float(entry_temp_ten.get()),
            height_tenability=float(entry_height_ten.get()), max_sim_time=float(entry_sim_time.get()),
            resolution=int(entry_resolution.get()))
        plot_results(plot_frame, results)
    except ValueError as e: messagebox.showerror("Input Error", f"Invalid input for Zone Model. Please check all fields.\nDetails: {e}")

def update_results_display():
    """Clears and redraws the fire spread results history, formatting for display."""
    results_textbox.configure(state="normal")
    results_textbox.delete("1.0", "end")
    
    if not results_history:
        results_textbox.insert("end", "No results yet. Run a calculation to add one.")
    else:
        for i, result in enumerate(results_history):
            results_textbox.insert("end", f"--- Run #{i+1} ---\n", "header")
            
            for key, value in result.items():
                if key == "Max Unprotected Area (Ratio)":
                    line = f"{key}: {value:.2%}\n"
                elif key == "Max Allowable Area (m²)":
                    line = f"{key}: {value:.2f}\n"
                elif isinstance(value, float):
                    line = f"{key}: {value:.4f}\n"
                else:
                    line = f"{key}: {value}\n"
                results_textbox.insert("end", line)
            results_textbox.insert("end", "\n")
            
    results_textbox.configure(state="disabled")


def on_add_fire_spread_result():
    """Gathers inputs for fire spread, runs calculation, and updates display."""
    try:
        # Create the dictionary of inputs from the GUI widgets
        inputs = {
            "Description": fs_entry_description.get(),
            "Block": fs_entry_block.get(),
            "Floor": fs_entry_floor.get(),
            "Facade": fs_option_facade.get(),
            # Get the value from the new dropdown and convert to a number
            "Radiation Intensity (W/m²)": float(fs_option_intensity.get()),
            "Width (m)": float(fs_entry_width.get()),
            "Height (m)": float(fs_entry_height.get()),
            "Boundary Dist. (m)": float(fs_entry_distance.get()),
            "I_crit (W/m²)": float(fs_entry_icrit.get()),
            # Get the value from the checkbox (1 if checked, 0 if not)
            "Sprinklered": sprinkler_var.get()
        }
        
        # Run the calculation with the gathered inputs
        new_result = calculate_external_fire_spread(inputs)
        
        # Add the full results dictionary to our history and update the display
        results_history.append(new_result)
        update_results_display()
        
    except ValueError:
        messagebox.showerror("Input Error", "Please ensure all numeric fields (Width, Height, etc.) are filled with valid numbers.")


def export_to_excel():
    """Exports the results history to a well-formatted Excel file."""
    if not results_history:
        messagebox.showinfo("Export Info", "There are no results to export.")
        return
        
    try:
        df = pd.DataFrame(results_history)
        
        df.insert(0, 'Run #', range(1, len(df) + 1))
        
        desired_column_order = [
            'Run #', 'Description', 'Block', 'Floor', 'Facade',
            'Width (m)', 'Height (m)', 'Boundary Dist. (m)',
            'Radiation Intensity (W/m²)', 'I_crit (W/m²)', 'Sprinklered',
            'View Factor', 'Initial Radiation (W/m²)', 'Sprinkler Reduction Factor',
            'Final Radiation Received (W/m²)', 
            'Max Unprotected Area (Ratio)', 
            'Max Allowable Area (m²)' 
        ]
        
        final_columns = [col for col in desired_column_order if col in df.columns]
        df = df[final_columns]
        
        # Open a "Save As" dialog window
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            title="Save Fire Spread Results As..."
        )
        
        if not file_path:
            print("Export cancelled by user.")
            return

        # Save to the file path the user selected
        df.to_excel(file_path, index=False)
        
        messagebox.showinfo("Export Success", f"Results successfully exported to\n{file_path}")
        
    except Exception as e:
        messagebox.showerror("Export Error", f"An error occurred while exporting:\n{e}")
# ==============================================================================
# --- MAIN GUI APPLICATION ---
# ==============================================================================
app = ctk.CTk()
app.title("Fire Engineering Calculator")
app.geometry("1400x900")

tab_view = ctk.CTkTabview(app)
tab_view.pack(padx=10, pady=10, fill="both", expand=True)

# --- TAB 1: ZONE MODEL SETUP (This entire section is unchanged) ---
zone_model_tab = tab_view.add("Zone Model")
zm_main_frame = ctk.CTkFrame(zone_model_tab, fg_color="transparent")
zm_main_frame.pack(fill="both", expand=True)
input_frame = ctk.CTkFrame(zm_main_frame)
input_frame.pack(side="left", fill="y", padx=(0, 10), pady=0)
plot_frame = ctk.CTkFrame(zm_main_frame)
plot_frame.pack(side="left", fill="both", expand=True, pady=0)
input_frame.grid_columnconfigure(1, weight=1)
row_index = 0
ctk.CTkLabel(input_frame, text="Room Dimensions", font=ctk.CTkFont(weight="bold")).grid(row=row_index, column=0, columnspan=2, pady=(5, 10), sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Height (m):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_height = ctk.CTkEntry(input_frame); entry_height.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Width (m):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_width = ctk.CTkEntry(input_frame); entry_width.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Length (m):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_length = ctk.CTkEntry(input_frame); entry_length.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Fire Properties", font=ctk.CTkFont(weight="bold")).grid(row=row_index, column=0, columnspan=2, pady=(15, 10), sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Growth Rate (kW/s²):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_fire_growth = ctk.CTkEntry(input_frame); entry_fire_growth.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Simulation Parameters", font=ctk.CTkFont(weight="bold")).grid(row=row_index, column=0, columnspan=2, pady=(15, 10), sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Simulation Time (s):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_sim_time = ctk.CTkEntry(input_frame); entry_sim_time.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Resolution (steps):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_resolution = ctk.CTkEntry(input_frame); entry_resolution.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Tenability Limits", font=ctk.CTkFont(weight="bold")).grid(row=row_index, column=0, columnspan=2, pady=(15, 10), sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Temperature (K):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_temp_ten = ctk.CTkEntry(input_frame); entry_temp_ten.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Interface Height (m):").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); entry_height_ten = ctk.CTkEntry(input_frame); entry_height_ten.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="ew"); row_index += 1
run_button = ctk.CTkButton(input_frame, text="Run Simulation", command=on_run_simulation_button_click); run_button.grid(row=row_index, column=0, columnspan=2, pady=20, padx=10, sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Results", font=ctk.CTkFont(weight="bold")).grid(row=row_index, column=0, columnspan=2, pady=(15, 10), sticky="ew"); row_index += 1
ctk.CTkLabel(input_frame, text="Temp. Limit Met:").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); temp_result_label = ctk.CTkLabel(input_frame, text="---", font=ctk.CTkFont(weight="bold")); temp_result_label.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="w"); row_index += 1
ctk.CTkLabel(input_frame, text="Height Limit Met:").grid(row=row_index, column=0, padx=(10,5), pady=5, sticky="e"); height_result_label = ctk.CTkLabel(input_frame, text="---", font=ctk.CTkFont(weight="bold")); height_result_label.grid(row=row_index, column=1, padx=(0,10), pady=5, sticky="w"); row_index += 1
entry_height.insert(0, "3.0"); entry_width.insert(0, "10.0"); entry_length.insert(0, "20.0"); entry_fire_growth.insert(0, "0.012"); entry_sim_time.insert(0, "500"); entry_resolution.insert(0, "1000"); entry_temp_ten.insert(0, "363"); entry_height_ten.insert(0, "2.5")

# --- TAB 2: EXTERNAL FIRE SPREAD SETUP (This is the complete and corrected version) ---
fire_spread_tab = tab_view.add("External Fire Spread")

# Main layout frames for the tab
fs_main_frame = ctk.CTkFrame(fire_spread_tab, fg_color="transparent")
fs_main_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Input Panel on the Left
fs_input_frame = ctk.CTkFrame(fs_main_frame)
fs_input_frame.pack(side="left", fill="y", padx=(0, 10))
fs_input_frame.grid_columnconfigure(1, weight=1)

# Output Panel on the Right
fs_output_frame = ctk.CTkFrame(fs_main_frame)
fs_output_frame.pack(side="left", fill="both", expand=True)

# --- Widgets for the Input Panel ---
row = 0
ctk.CTkLabel(fs_input_frame, text="Location Identifiers", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, columnspan=2, pady=10); row+=1
ctk.CTkLabel(fs_input_frame, text="Description:").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_description = ctk.CTkEntry(fs_input_frame, placeholder_text="e.g., Living Room Window"); fs_entry_description.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1
ctk.CTkLabel(fs_input_frame, text="Block:").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_block = ctk.CTkEntry(fs_input_frame, placeholder_text="e.g., A"); fs_entry_block.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1
ctk.CTkLabel(fs_input_frame, text="Floor:").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_floor = ctk.CTkEntry(fs_input_frame, placeholder_text="e.g., 05"); fs_entry_floor.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1
facade_options = ["North", "South", "East", "West", "NW", "NE", "SW", "SE"]
ctk.CTkLabel(fs_input_frame, text="Facade:").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_option_facade = ctk.CTkOptionMenu(fs_input_frame, values=facade_options); fs_option_facade.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1

ctk.CTkLabel(fs_input_frame, text="Radiator (Fire Opening)", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, columnspan=2, pady=10); row+=1
intensity_options = ["84000", "168000"]
ctk.CTkLabel(fs_input_frame, text="Radiation (W/m²):").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_option_intensity = ctk.CTkOptionMenu(fs_input_frame, values=intensity_options); fs_option_intensity.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1
ctk.CTkLabel(fs_input_frame, text="Width (m):").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_width = ctk.CTkEntry(fs_input_frame, placeholder_text="5.0"); fs_entry_width.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1
ctk.CTkLabel(fs_input_frame, text="Height (m):").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_height = ctk.CTkEntry(fs_input_frame, placeholder_text="5.0"); fs_entry_height.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1

ctk.CTkLabel(fs_input_frame, text="Receiver & Conditions", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, columnspan=2, pady=10); row+=1
ctk.CTkLabel(fs_input_frame, text="Boundary Dist. (m):").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_distance = ctk.CTkEntry(fs_input_frame, placeholder_text="5.0"); fs_entry_distance.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1
ctk.CTkLabel(fs_input_frame, text="Critical Flux (W/m²):").grid(row=row, column=0, padx=5, pady=5, sticky="e"); fs_entry_icrit = ctk.CTkEntry(fs_input_frame, placeholder_text="12600"); fs_entry_icrit.grid(row=row, column=1, padx=5, pady=5, sticky="ew"); row+=1

sprinkler_var = ctk.IntVar(value=0)
ctk.CTkCheckBox(fs_input_frame, text="Apply 50% Sprinkler Reduction", variable=sprinkler_var).grid(row=row, column=0, columnspan=2, pady=10); row+=1

# --- BUTTONS ---
ctk.CTkButton(fs_input_frame, text="Add to Results", command=on_add_fire_spread_result).grid(row=row, column=0, columnspan=2, pady=10, sticky="ew"); row+=1

# --- Widgets for the Output Panel ---
ctk.CTkButton(fs_output_frame, text="Export All to Excel", command=export_to_excel).pack(pady=5, padx=5, fill="x")
results_textbox = ctk.CTkTextbox(fs_output_frame, wrap="none", font=ctk.CTkFont(family="monospace")); results_textbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
results_textbox.tag_config("header", foreground="cyan", underline=True)
update_results_display()


# --- Start the main application loop ---
app.mainloop()
