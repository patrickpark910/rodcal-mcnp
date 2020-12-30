'''
ROD CALIBRATION (MCNP)

Written by Patrick Park (RO, Physics '22)
ppark@reed.edu
Last updated Dec. 30, 2020

'''

import os, sys, multiprocessing
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from 'mcnp-funcs' import *

# Variables
filepath = "C:/MCNP6/facilities/reed/rodcal-mcnp" # do NOT include / at the end
rods = ["Safe", "Shim", "Reg"]
heights = [10,20,30,40,50,60,70,80,90,100]

# Main function to be executed
def main(argv):
    os.chdir(f'{filepath}')
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
        run_mcnp(f"{filepath}/{inputs_folder_name}",f"{filepath}/{outputs_folder_name}",file,tasks)

    # Deletes MCNP runtape and scriptape files.
    delete_files(f"{filepath}/{outputs_folder_name}")

#
# HELPER FUNCTIONS
#

# Finds the desired set of parameters to change for a given rod
def find_height(rod, height, base_input_name, inputs_folder_name):
    base_input_deck = open(base_input_name, 'r')
    
    if height != 100:
        new_input_name = './'+ inputs_folder_name + '/' + 'rc-'+rod.lower()+ '-0' + str(height) +'.i'
    else:
        new_input_name = './'+ inputs_folder_name + '/' + 'rc-'+rod.lower()+ '-' + str(height) +'.i'
    
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
    start_marker = rod + " Rod (0% Withdrawn)"
    end_marker = "End of " + rod
    
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
                new_input_deck.write("c "+ rod + " Rod ("+ str(height) + "0% withdrawn)\n")
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
             
            if 'pz' in line:
                new_input_deck.write(change_height('pz', line, height) + '\n')
                continue
            if 'k/z' in line:
                new_input_deck.write(change_height('k/z', line, height) + '\n')
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
def math(n, x):
    CONST = 4.81488
    n += x*CONST
    # This returns 'n' rounded to 5 places of decimals
    return str(round(n, 5))

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

    
if __name__ == "__main__":
    main(sys.argv[1:])
        
