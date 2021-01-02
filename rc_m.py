'''
ROD CALIBRATION (MCNP)

Written by Patrick Park (RO, Physics '22)
ppark@reed.edu

This proejct should be available at 
https://github.com/patrickpark910/rodcal-mcnp/

Last updated Dec. 30, 2020

__________________
Default MCNP units

Length: cm
Mass: g
Energy & Temp.: MeV
Positive density (+x): atoms/barn-cm
Negative density (-x): g/cm3
Time: shakes
(1 barn = 10e-24 cm2, 1 sh = 10e-8 sec)

_______________
Technical Notes

Go to GitHub link for a complete instructions.

NB: You can use this without MCNP. This repository should have the 
appropriate decks in ./inputs/ and ./outputs/ for this python program
to recognize and skip all the MCNP portions.

NB: You can also use this program plot your own worth curves (and skip all MCNP), 
if you have your own CSV of keff and uncertainty results. Change 'keff_csv_name'
to your file name and comment out the code between [START] and [END].

NB: To use this at another facility, you will have to edit find_height()
to match your MCNP deck. Namely, you will need to change (or add) a 
start marker, end marker, and adjust what surface number your rods start with. 
Reed's control rod cells start with '8', so I have hardcoded in
'line[0].startswith("8")' in the function. You will also need to edit math() to
add the right z-height that fits your core geometry.

'''

import os, sys, multiprocessing
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from mcnp_funcs import *

# Variables
cm_per_percent_height = 0.38 # Control rods have 38 cm of travel, so 0.38 cm/%
rods = ["safe", "shim", "reg"]
heights = [0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100] # % heights, 
# for use in strings, use str(height).zfill(3) to pad 0s until it is 3 characters long,
# e.g. 'rc-reg-010.i'

filepath = "C:/MCNP6/facilities/reed/rodcal-mcnp" # do NOT include / at the end
inputs_folder_name = "inputs" # Folder for newly-generated MCNP input decks
outputs_folder_name = "outputs" # Folder for all MCNP output decks
keff_csv_name = "keff.csv" # File for keff and uncertainty values.
# NB: If you choose to load your own keff csv, 
# make sure to comment out the MCNP portions ("TO PLOT YOUR OWN KEFF") below, 
# or YOUR FILE WILL BE OVERWRITTEN.
rho_csv_name = "rho.csv" # File for rho and uncertainty values.
params_csv_name = "rod_parameters.csv"

# Normal rod motion speed is about 11 inches (27.9 cm) per minute for the Shim rod, 19 inches (48.3 cm) per minute for the Safe rod, and 24 inches (61 cm) per minute for the Reg rod.

'''
Main function to be executed.

Use this 'def main(argv)' and 'if __name__ == "__main__": main(sys.argv[1:])' 
method to avoid functions from being inadvertently run if you try to
import this into another py file, e.g. 'from mcnp_funcs import *'.
'''
def main(argv):
    os.chdir(f'{filepath}')
    
    # ''' # [START] TO PLOT YOUR OWN KEFF: Remove first # to just plot rodcal data using a CSV of keff values.
    
    base_input_name = find_base_file(filepath)
    check_kcode(filepath,base_input_name)

    num_inputs_created = 0

    for rod in rods:
        for height in heights:
            input_created = find_height(rod, height, base_input_name, inputs_folder_name)
            # find_height returns False if the input already exists.
            # Otherwise, it finds and changes the heights and returns True.
            if input_created: num_inputs_created +=1
    
    print(f"Created {num_inputs_created} new input decks.")

    # Check if you want to run MCNP right now. 
    # check_run_mcnp() returns True or False. If False, quit program.
    if not check_run_mcnp(): sys.exit()

    # Run MCNP for all .i files in f".\{inputs_folder_name}".
    tasks = get_tasks()
    for file in os.listdir(f"{filepath}/{inputs_folder_name}"):
        run_mcnp(filepath,inputs_folder_name,outputs_folder_name,file,tasks)

    # Deletes MCNP runtape and source dist files.
    delete_files(f"{filepath}/{outputs_folder_name}",r=True,s=True)

    # Setup a dataframe to collect keff values
    keff_df = pd.DataFrame(columns=["height","safe", "safe unc", "shim", "shim unc", "reg", "reg unc"]) # use lower cases to match 'rods' def above
    keff_df["height"] = heights
    keff_df.set_index("height",inplace=True)

    # Add keff values to dataframe
    # NB: Use keff_df.iloc[row, column] to select by range integers, .loc[row, column] to select by row/column labels
    for rod in rods:
        for height in heights:
            keff, keff_unc = extract_keff(f"{filepath}/{outputs_folder_name}/o_rc-{rod}-{str(height).zfill(3)}.o")
            keff_df.loc[height,rod] = keff 
            keff_df.loc[height,f'{rod} unc'] = keff_unc    
    
    print(f"\nDataframe of keff values and their uncertainties:\n{keff_df}")
    keff_df.to_csv(keff_csv_name)

    # ''' # [END] TO PLOT YOUR OWN KEFF: Remove first # to just plot rodcal data using a CSV of keff values.
    
    convert_keff_to_rho(keff_csv_name,rho_csv_name)
    
    plot_rodcal_data(rho_csv_name)

    calc_params(rho_csv_name,params_csv_name)

    print(f"************ PROGRAM COMPLETE ************")
    




'''
HELPER FUNCTIONS
'''



'''
Finds the desired set of parameters to change for a given rod.

rod: str, name of rod, e.g. "shim"
height: float, percent rod height, e.g. 10
base_input_name: str, name of base deck with extension, e.g. "rc.i"
inputs_folder_name: str, name of input folder, e.g. "inputs"

Returns 'True' when new input deck is completed, or 'False' if the input deck already exists.

NB: This is the function you will change the most for use with a different facility's MCNP deck.
'''
def find_height(rod, height, base_input_name, inputs_folder_name):
    base_input_deck = open(base_input_name, 'r')
    new_input_name = './'+ inputs_folder_name + '/' + 'rc-'+rod.lower()+ '-' + str(height).zfill(3) +'.i'

    # If the inputs folder doesn't exist, create it
    if not os.path.isdir(inputs_folder_name):
        os.mkdir(inputs_folder_name)

    # If the input deck exists, skip
    if os.path.isfile(new_input_name):
        print(f"--The input deck '{new_input_name}' will be skipped because it already exists.")
        return False

    new_input_deck = open(new_input_name, 'w+')

    '''
    'start_marker' and 'end_marker' are what you're searching for in each 
    line of the whole input deck to indicate start and end of rod parameters. 
    Thus it needs to be unique, like "Safe Rod (0% Withdrawn)" and "End of Safe Rod".
    Make sure the input deck contains these markers EXACTLY as they are defined here,
    e.g. watch for capitalizations or extra spaces between words.
    '''
    start_marker = rod.capitalize() + " Rod (0% Withdrawn)"
    end_marker = f"End of {rod.capitalize()} Rod"
    
    # Indicates if we are between 'start_marker' and 'end_marker'
    inside_block = False
    
    # Now, we're reading the base input deck ('rc.i') line-by-line.
    for line in base_input_deck:
        # If we're not inside the block, just copy the line to a new file
        if inside_block == False:
            # If this is the line with the 'start_marker', rewrite it to the new file with required changes
            if start_marker in line and "90%" not in line:
                inside_block = True
                new_input_deck.write(f"c {rod.capitalize()} Rod ({height}% withdrawn)\n")
                print(f'{new_input_name} block check')
                continue
            new_input_deck.write(line)
            continue

        # Logic for what to do when we're inside the block
        if inside_block == True:
            
            # If the line starts with a 'c'
            if line[0] == 'c':
                # If this is the line with the 'start_marker', it means we're outside the block now
                if end_marker in line:
                    inside_block = False
                    continue
                # If not, just write the line to new file
                else:
                    new_input_deck.write(line)
                    continue
            
            # We're now making the actual changes to the rod geometry 
            if 'pz' in line and line[0].startswith('8'):
                new_input_deck.write(change_height('pz', line, height) + '\n')
                # print(f'{new_input_name} pz change')
                continue
            if 'k/z' in line and line[0].startswith('8'):
                new_input_deck.write(change_height('k/z', line, height) + '\n')
                # print(f'{new_input_name} k/z change')
                continue
            # If not, just write the line to the new file
            else:
                new_input_deck.write(line)
                continue

    base_input_deck.close()
    new_input_deck.close()
    return True




'''
Performs the necessary changes on the values

value: str, MCNP geometry mnemonic, e.g. "pz"
line: str, line read from input deck
height: float, desired rod height, e.g. 10
'''
def change_height(value, line, height):
    line_formatted = sep_entries(line)
    
    # For loop not recommended here. Leads to errors and bugs.
    if value == 'pz':
        line_formatted[2] = math(float(line_formatted[2]), height)
        s = '   '.join(line_formatted[0:4]) + ' '
        s += ' '.join(line_formatted[4:])

    if value == 'k/z':
        line_formatted[4] = math(float(line_formatted[4]), height)
        s = '   '.join(line_formatted[0:7]) + ' '
        s += ' '.join(line_formatted[7:])

    return s



'''
Returns the value of the line in the form of a list with the various elements as its items

s: str, a line of a file read as a string, e.g. "812301 pz 54.19344 $ top of rod"

Returns list, e.g. ['812301', 'pz', '54.19344', '$', 'top', 'of', 'rod']

NB: This method is more robust than just using s.sep(' ') by avoiding instances of multiple spaces.
'''
def sep_entries(s):
    output = []
    s = ' ' + s
    wrd = ''
    for i in range(0, len(s)):
        if s[i] != ' ': wrd += s[i]
        else:
            if s[i-1] != ' ':
                output.append(wrd)
                wrd = ''
    output.append(wrd[:-1])
    return output[1:]



'''
Performs the mathematical operations on the exact value

z_coordinate: float, a MCNP geomtery parameter, e.g. 54.19344
height: float, desired rod height, e.g. 10

Returns a new str for the 'z_coordinate' adjusted to the desired 'height'

NB: Bottom of rod is 5.120640 at 0% and 53.2694 at 100%. 
Use +/- 4.81488 to 'z_coordinate' for a 1% height change. 
'''
def math(z_coordinate, height):
    z_coordinate += height*cm_per_percent_height
    return str(round(z_coordinate, 5)) # Round to at least 5 or 6 digits



'''
Converts a CSV of keff and uncertainty values to a CSV of rho and uncertainty values.

keff_csv_name: str, name of CSV of keff values, including extension, "keff.csv"
rho_csv_name: str, desired name of CSV of rho values, including extension, "rho.csv"

Does not return anything. Only makes the actual file changes.
'''
def convert_keff_to_rho(keff_csv_name,rho_csv_name):
    # Assumes the keff.csv has columns labeled "rod" and "rod unc" for keff and keff uncertainty values for a given rod
    keff_df = pd.read_csv(keff_csv_name,index_col=0)
    rods = [c for c in keff_df.columns.values.tolist() if "unc" not in c]
    heights = keff_df.index.values.tolist()

    # Setup a dataframe to collect rho values
    rho_df = pd.DataFrame(columns=keff_df.columns.values.tolist()) # use lower cases to match 'rods' def above
    rho_df["height"] = heights
    rho_df.set_index("height",inplace=True)

    '''
    ERROR PROPAGATION FORMULAE
    % Delta rho = 100* frac{k2-k1}{k2*k1}
    numerator = k2-k1
    delta num = sqrt{(delta k2)^2 + (delta k1)^2}
    denominator = k2*k1
    delta denom = k2*k1*sqrt{(frac{delta k2}{k2})^2 + (frac{delta k1}{k1})^2}
    delta % Delta rho = 100*sqrt{(frac{delta num}{num})^2 + (frac{delta denom}{denom})^2}
    '''   
    for rod in rods: 
        for height in heights: 
            k1 = keff_df.loc[height,rod]
            k2 = keff_df.loc[heights[-1],rod]
            dk1 = keff_df.loc[height,f"{rod} unc"] 
            dk2 = keff_df.loc[heights[-1],f"{rod} unc"] 
            k2_minus_k1 = k2-k1
            k2_times_k1 = k2*k1
            d_k2_minus_k1 = np.sqrt(dk2**2+dk1**2)
            d_k2_times_k1 = k2*k1*np.sqrt((dk2/k2)**2+(dk1/k1)**2)
            rho = (k2-k1)/(k2*k1)*100

            rho_df.loc[height,rod] = rho
            if k2_minus_k1 != 0: 
                d_rho = rho*np.sqrt((d_k2_minus_k1/k2_minus_k1)**2+(d_k2_times_k1/k2_times_k1)**2)
                rho_df.loc[height,f"{rod} unc"] = d_rho
            else: rho_df.loc[height,f"{rod} unc"] = 0

    print(f"\nDataframe of rho values and their uncertainties:\n{rho_df}")
    rho_df.to_csv(f"{rho_csv_name}")



'''
Plots integral and differential worths given a CSV of rho and uncertainties.

rho_csv_name: str, name of CSV of rho and uncertainties, e.g. "rho.csv"

Does not return anything. Only produces a figure.

NB: Major plot settings have been organized into variables for your personal convenience.
'''
def plot_rodcal_data(rho_csv_name):
    rho_df = pd.read_csv(rho_csv_name,index_col=0)
    rods = [c for c in rho_df.columns.values.tolist() if "unc" not in c]
    heights = rho_df.index.values.tolist()
    
    # Personal parameters, to be used in plot settings below.
    my_dpi = 96
    x_label = "Axial height withdrawn (%)"
    y_label_int = r"Integral worth $(\%\Delta\rho)$"
    y_label_dif = r"Differential worth ($\%\Delta\rho$/%)"
    label_fontsize = 16
    legend_fontsize = "x-large"
    # fontsize: int or {'xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'}
    figure_name = "results.png"

    fig,axs = plt.subplots(2,1, figsize=(1636/my_dpi, 2*673/my_dpi), dpi=my_dpi,facecolor='w',edgecolor='k')
    ax_int, ax_dif = axs[0], axs[1] # integral, differential worth on top, bottom, resp.
    color = {rods[0]:"tab:red",rods[1]:"tab:green",rods[2]:"tab:blue"}
    
    for rod in rods: # We want to sort our curves by rods
        int_y = rho_df[f"{rod}"].tolist()
        int_y_unc = rho_df[f"{rod} unc"].tolist()

        int_eq = np.polyfit(heights,int_y,3) # coefs of integral worth curve equation
        fit_x = np.linspace(heights[0],heights[-1],heights[-1]-heights[0]+1)
        int_fit_y = np.polyval(int_eq,fit_x)
        
        # Data points with error bars
        ax_int.errorbar(heights, int_y, yerr=int_y_unc,
                            marker="o",ls="none",
                            color=color[rod],elinewidth=2,capsize=3,capthick=2)
        
        # The standard least squaures fit curve
        ax_int.plot(fit_x,int_fit_y,color=color[rod],label=f'{rod.capitalize()}')
        

        dif_eq = -1*np.polyder(int_eq) # coefs of differential worth curve equation
        dif_fit_y = np.polyval(dif_eq,fit_x)
        
        # The differentiated curve.
        # The errorbar method allows you to add errors to the differential plot too.
        ax_dif.errorbar(fit_x, dif_fit_y,
                            label=f'{rod.capitalize()}',
                            color=color[rod],linewidth=2,capsize=3,capthick=2)
    
    # Integral worth plot settings
    ax_int.set_xlim([0,100])
    ax_int.set_ylim([-.5,3.5])

    ax_int.xaxis.set_major_locator(MultipleLocator(10))
    ax_int.yaxis.set_major_locator(MultipleLocator(0.5))
    
    ax_int.minorticks_on()
    ax_int.xaxis.set_minor_locator(MultipleLocator(2.5))
    ax_int.yaxis.set_minor_locator(MultipleLocator(0.125))
    
    ax_int.tick_params(axis='both', which='major', labelsize=label_fontsize)
    
    ax_int.grid(b=True, which='major', color='#999999', linestyle='-', linewidth='1')
    ax_int.grid(which='minor', linestyle=':', linewidth='1', color='gray')
    
    ax_int.set_xlabel(x_label,fontsize=label_fontsize)
    ax_int.set_ylabel(y_label_int,fontsize=label_fontsize)
    ax_int.legend(title=f'Key', title_fontsize=legend_fontsize, ncol=4, fontsize=legend_fontsize,loc='upper right')
    
    # Differential worth plot settings
    ax_dif.set_xlim([0,100])
    ax_dif.set_ylim([0,0.06])

    ax_dif.xaxis.set_major_locator(MultipleLocator(10))
    ax_dif.yaxis.set_major_locator(MultipleLocator(0.01))
    
    ax_dif.minorticks_on()
    ax_dif.xaxis.set_minor_locator(MultipleLocator(2.5))
    ax_dif.yaxis.set_minor_locator(MultipleLocator(0.0025))
    
    ax_dif.grid(b=True, which='major', color='#999999', linestyle='-', linewidth='1')
    ax_dif.grid(which='minor', linestyle=':', linewidth='1', color='gray')

    ax_dif.tick_params(axis='both', which='major', labelsize=label_fontsize)
    
    ax_dif.set_xlabel(x_label,fontsize=label_fontsize)
    ax_dif.set_ylabel(y_label_dif,fontsize=label_fontsize)
    #plt.title(f'Fuel Assembly B-1, {cycle_state}',fontsize=fs1)
    ax_dif.legend(title=f'Key', title_fontsize=legend_fontsize, ncol=4, fontsize=legend_fontsize, loc='lower center')
    
    plt.savefig(f'{figure_name}', bbox_inches = 'tight', pad_inches = 0.1, dpi=320)
    print(f'\nFigure saved!\n') # no space near \ 
    

'''
Calculates a few other rod parameters.

rho_csv_name: str, name of CSV of rho values to read from, e.g. "rho.csv"
params_csv_name: str, desired name of CSV of rod parameters, e.g. "rod_parameters.csv"

Does not return anything. Only performs file creation.
'''
def calc_params(rho_csv_name,params_csv_name):
    rho_df = pd.read_csv(rho_csv_name,index_col=0)
    rods = [c for c in rho_df.columns.values.tolist() if "unc" not in c]
    heights = rho_df.index.values.tolist()
    
    beta_eff = 0.0075
    react_add_rate_limit = 0.16
    motor_speed = {"safe":19,"shim":11,"reg":24} # inches/min
    
    parameters = ["worth ($)","max worth added per % height ($/%)", "max worth added per height ($/in)", "reactivity addition rate ($/sec)","max motor speed (in/min)"]
    
    # Setup a dataframe to collect rho values
    params_df = pd.DataFrame(columns=parameters) # use lower cases to match 'rods' def above
    params_df["rod"] = rods
    params_df.set_index("rod",inplace=True)
   
    for rod in rods: # We want to sort our curves by rods
        rho = rho_df[f"{rod}"].tolist()
        # worth ($) = rho / beta_eff, rho values are in % rho per NIST standard
        worth = 0.01*float(max(rho)) / float(beta_eff) 
        params_df.loc[rod,parameters[0]] = worth
        
        int_eq = np.polyfit(heights,rho,3) # coefs of integral worth curve equation
        dif_eq = -1*np.polyder(int_eq)
        max_worth_rate_per = 0.01*max(np.polyval(dif_eq,heights)) / float(beta_eff) 
        params_df.loc[rod,parameters[1]] = max_worth_rate_per
        
        max_worth_rate_inch = float(max_worth_rate_per)/float(cm_per_percent_height)*2.54
        params_df.loc[rod,parameters[2]] = max_worth_rate_inch
        
        # Normal rod motion speed is about: 
        # 19 inches (48.3 cm) per minute for the Safe rod,
        # 11 inches (27.9 cm) per minute for the Shim rod, 
        # 24 inches (61.0 cm) per minute for the Reg rod.
        
        react_add_rate = motor_speed[rod]*max_worth_rate_inch/60
        params_df.loc[rod,parameters[3]] = react_add_rate
        
        max_motor_speed = 1/max_worth_rate_inch*react_add_rate_limit*60
        params_df.loc[rod,parameters[4]] = max_motor_speed

    print(f"\nVarious rod parameters:\n{params_df}")
    params_df.to_csv(params_csv_name)



if __name__ == "__main__":
    main(sys.argv[1:])
        
