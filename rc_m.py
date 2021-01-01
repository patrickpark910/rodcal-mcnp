'''
ROD CALIBRATION (MCNP)

Written by Patrick Park (RO, Physics '22)
ppark@reed.edu
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

'''

import os, sys, multiprocessing
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from mcnp_funcs import *

# Variables
filepath = "C:/MCNP6/facilities/reed/rodcal-mcnp" # do NOT include / at the end
rods = ["safe", "shim", "reg"]
heights = [0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100] # for use in name strings, use str(height).zfill(3) to pad 0s until it is 3 characters long

# Main function to be executed
def main(argv):
    os.chdir(f'{filepath}')
    # '''
    base_input_name = find_base_file(filepath)
    check_kcode(filepath,base_input_name)

    inputs_folder_name = "inputs" # Folder name you want files saved to
    outputs_folder_name = "outputs"
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
    
    print(keff_df)
    keff_df.to_csv("keff.csv")

    convert_keff_to_rho("keff.csv","rho.csv")
    # '''
    plot_rodcal_data("rho.csv")
    
def plot_rodcal_data(rho_csv_name):
    rho_df = pd.read_csv(rho_csv_name,index_col=0)
    rods = [c for c in rho_df.columns.values.tolist() if "unc" not in c]
    heights = rho_df.index.values.tolist()
    
    my_dpi = 96
    
    fig,axs = plt.subplots(2,1, figsize=(1636/my_dpi, 2*673/my_dpi), dpi=my_dpi,facecolor='w',edgecolor='k')
    ax_int, ax_dif = axs[0], axs[1] # integral, differential worth on top, bottom, resp.
    color = {rods[0]:"tab:red",rods[1]:"tab:green",rods[2]:"tab:blue"}
    
    for rod in rods: # We want to sort our curves by rods
        int_y = rho_df[f"{rod}"].tolist()
        int_y_unc = rho_df[f"{rod} unc"].tolist()

        int_eq = np.polyfit(heights,int_y,3) # integral worth curve equation
        fit_x = np.linspace(heights[0],heights[-1],heights[-1]-heights[0]+1)
        int_fit_y = np.polyval(int_eq,fit_x)
        
        ax_int.errorbar(heights, int_y, yerr=int_y_unc,
                            marker="o",ls="none",
                            label=f'{rod.capitalize()}',
                            color=color[rod],elinewidth=2,capsize=3,capthick=2)
        
        ax_int.plot(fit_x,int_fit_y,color=color[rod])
        

        dif_eq = -1*np.polyder(int_eq) # differential worth curve equation
        
        
        dif_fit_y = np.polyval(dif_eq,fit_x)
        
        ax_dif.errorbar(fit_x, dif_fit_y,
                            label=f'{rod.capitalize()}',
                            color=color[rod],linewidth=2,capsize=3,capthick=2)
    
    x_label = "Axial height withdrawn (%)"
    y_label_int = r"Integral worth $(\%\Delta\rho)$"
    y_label_dif = r"Differential worth ($\%\Delta\rho$/cm)"
    label_fontsize = 16
    
    # INTEGRAL WORTH PLOT SETTINGS
    
    #df_int.plot(ax=ax_int, linewidth='0.75') 
    
    #plt.title('Relative integral worths for varied control blade thickness')
    ax_int.set_xlim([0,100])
    ax_int.set_ylim([-.5,3.5])

    ax_int.xaxis.set_major_locator(MultipleLocator(10))
    ax_int.yaxis.set_major_locator(MultipleLocator(0.5))
    
    ax_int.minorticks_on()
    ax_int.xaxis.set_minor_locator(MultipleLocator(2.5))
    ax_int.yaxis.set_minor_locator(MultipleLocator(0.125))
    
    ax_int.tick_params(axis='both', which='major', labelsize=16)
    
    ax_int.grid(b=True, which='major', color='#999999', linestyle='-', linewidth='1')
    ax_int.grid(which='minor', linestyle=':', linewidth='1', color='gray')
    
    ax_int.set_xlabel(x_label,fontsize=label_fontsize)
    ax_int.set_ylabel(y_label_int,fontsize=label_fontsize)
    ax_int.legend(title=f'Key', title_fontsize='x-large', ncol=4, fontsize='x-large',loc='upper right')
    # fontsize: int or {'xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'}
    
    #
    # DIFFERENTIAL WORTH PLOT SETTINGS
    ax_dif.set_xlim([0,100])
    ax_dif.set_ylim([0,0.06])
    
    ax_dif.minorticks_on()
    ax_dif.xaxis.set_minor_locator(MultipleLocator(2.5))
    ax_dif.yaxis.set_minor_locator(MultipleLocator(0.0025))
    
    ax_dif.grid(b=True, which='major', color='#999999', linestyle='-', linewidth='1')
    ax_dif.grid(which='minor', linestyle=':', linewidth='1', color='gray')

    ax_dif.tick_params(axis='both', which='major', labelsize=16)
    
    ax_dif.set_xlabel(x_label,fontsize=label_fontsize)
    ax_dif.set_ylabel(y_label_dif,fontsize=label_fontsize)
    #plt.title(f'Fuel Assembly B-1, {cycle_state}',fontsize=fs1)
    ax_dif.legend(title=f'Key', title_fontsize='x-large', ncol=4, fontsize='x-large', loc='lower center')
    
    plt.savefig(f'results.png', bbox_inches = 'tight', pad_inches = 0.1, dpi=320)
    print(f'Figure saved!')

    print(f"************ PROGRAM COMPLETE ************")
    
    
    
    






#
# HELPER FUNCTIONS
#

# Finds the desired set of parameters to change for a given rod
def find_height(rod, height, base_input_name, inputs_folder_name):
    base_input_deck = open(base_input_name, 'r')
    
    new_input_name = './'+ inputs_folder_name + '/' + 'rc-'+rod.lower()+ '-' + str(height).zfill(3) +'.i'

    # If the folder doesn't exist, create it
    if not os.path.isdir(inputs_folder_name):
        os.mkdir(inputs_folder_name)

    # If the file exists, print message
    if os.path.isfile(new_input_name):
        print(f"--The input deck '{new_input_name}' will be skipped because it already exists.")
        return False

    new_input_deck = open(new_input_name, 'w+')

    # 'start_marker' is what you're searching for in each line of the whole document. Thus it needs to be unique,
    # like "Safe Rod (0% Withdrawn)"
    start_marker = rod.capitalize() + " Rod (0% Withdrawn)"
    end_marker = f"End of {rod.capitalize()} Rod"
    
    # Using 'inside_block' to indicate whether the current line is inbetween "Safe Rod (0% Withdrawn)" and
    # "End of Safe Rod", i.e lines (4778,4807), (4812, 4841), (4846, 4875)
    inside_block = False
    
    for line in base_input_deck:
        # If we're not inside the block, just write the line to the new file
        if inside_block == False:
            # If this is the line with the 'start_marker', rewrite it to the new file with required changes
            # This would signify, that we are inside the block
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

# Returns the value of the line in the form of a list with the various elements as its items
# e.g.: ['812301', 'pz', '54.19344', '$', 'top', 'of', 'control']
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

# Performs the mathematical operations on the exact value
def math(z_coordinate, height):
    # z_coordinate: a decimal value 
    # height: a value ranging from 0 to 100 for % rod withdrawn
    # +/- 4.81488 to z_coordinate for a 10 % rod change
    # bottom of rod is 5.120640 at 0 % and 53.2694 at 100 %
    z_coordinate += height*0.481488
    return str(round(z_coordinate, 5)) # Round to at least 5 or 6 digits

# Performs the necessary changes on the values
def change_height(value, line, x):
    line_formatted = sep_entries(line)
    
    # For loop not recommended here. Leads to errors and bugs.
    if value == 'pz':
        line_formatted[2] = math(float(line_formatted[2]), x)
        s = '   '.join(line_formatted[0:4]) + ' '
        s += ' '.join(line_formatted[4:])

    if value == 'k/z':
        line_formatted[4] = math(float(line_formatted[4]), x)
        s = '   '.join(line_formatted[0:7]) + ' '
        s += ' '.join(line_formatted[7:])

    return s

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

    print(rho_df)
    rho_df.to_csv(f"{rho_csv_name}")
    
if __name__ == "__main__":
    main(sys.argv[1:])
        
