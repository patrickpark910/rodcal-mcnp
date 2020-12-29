'''
ROD CALIBRATION (MCNP)

Written by Patrick Park (RO, Physics '22)
ppark@reed.edu
Last updated Dec. 29, 2020

'''

import os, sys, multiprocessing
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# Variables
filepath = "C:/MCNP6/facilities/reed/critloadexp" # do NOT include / at the end
categories = ["Safe", "Shim", "Reg"]

# 
def main(argv):
    for category in categories:
        for i in range(1,11):
            edit(category, i)

#This function returns the value of the line in the form of a list with the various elements as its items
# Eg: ['812301', 'pz', '54.19344', '$', 'top', 'of', 'control']
def req_format(s):
    output = []
    s = ' ' + s
    wrd = ''
    for i in range(0, len(s)):
        if s[i] != ' ':
            wrd += s[i]
        else:
            if s[i-1] != ' ':
                output.append(wrd)
                wrd = ''
    output.append(wrd[:-1])
    return output[1:]

# This function performs the mathematical operations on the exact value
def maths(n, x):
    CONST = 4.81488
    n += x*CONST
    # This returns 'n' rounded to 5 places of decimals
    return str(round(n, 5))


# This function performs the necessary changes on the values
def change(value, line, x):

    line_formatted = req_format(line)
    
    if value == 'pz':
        line_formatted[2] = maths(float(line_formatted[2]), x)
        s = '   '.join(line_formatted[0:4]) + ' '
        s += ' '.join(line_formatted[4:])

    if value == 'k/z':
        line_formatted[4] = maths(float(line_formatted[4]), x)
        s = '   '.join(line_formatted[0:7]) + ' '
        s += ' '.join(line_formatted[7:])

    return s




def edit(category, x):
    
    f = open('rc-test.i', 'r')
    
    # Folder name you want files saved to
    folder_name = "files"

    if x in range(1,10):
        new_file_name = './'+ folder_name + '/' + 'rc-test-'+category.lower()+ '-0' + str(x) +'0.i'
    else:
        new_file_name = './'+ folder_name + '/' + 'rc-test-'+category.lower()+ '-' + str(x) +'0.i'
    
    # If the folder doesn't exist, create it
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)

    # If the file exists, print "File exists"
    if os.path.isfile(new_file_name):
        print("File exists")
        return

    w = open(new_file_name, 'w+')

    # 'search_value' is what you're searching for in each line of the whole document. Thus it needs to be unique,
    # like "Safe Rod (0% Withdrawn)"
    search_value = category + " Rod (0% Withdrawn)"
    end_value = "End of " + category

    # Using 'inside_block' to indicate whether the current line is inbetween "Safe Rod (0% Withdrawn)" and
    # "End of Safe Rod", i.e lines (4778,4807), (4812, 4841), (4846, 4875)
    inside_block = False
    
    for line in f:

        # If we're not inside the block, just write the line to the new file
        if inside_block == False:
            # If this is the line with the 'search_value', rewrite it to the new file with required changes
            # This would signify, that we are inside the block
            if search_value in line and "90%" not in line:
                inside_block = True
                w.write("c "+ category + " Rod ("+ str(x) + "0% withdrawn)\n")
                continue
            w.write(line)
            continue

        # Logic for what to do when we're inside the block
        if inside_block == True:
            
            # If the line starts with a 'c'
            if line[0] == 'c':
                # If this is the line with the 'search_value', it means we're outside the block now
                if end_value in line:
                    inside_block = False
                    continue
                # If not, just write the line to new file
                else:
                    w.write(line)
                    continue
             
            if 'pz' in line:
                w.write(change('pz', line, x) + '\n')
                continue
            if 'k/z' in line:
                w.write(change('k/z', line, x) + '\n')
                continue
            # If not, just write the line to the new file
            else:
                w.write(line)
                continue



    f.close()
    w.close()


    

    
    
if __name__ == "__main__":
    main(sys.argv[1:])
        
