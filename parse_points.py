import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_style("whitegrid")  # Set the plot style
sns.set_palette("Set1")     # Set the color palette    
sns.set_context("talk")   # Set the plot context
colormap = plt.colormaps['tab20'] # Set the colormap

NAME_RE = re.compile(r'quad(\d+)_lad(\d+)_si(\d+)_(\d+)')
X_RE = re.compile(r'X=\s*([-\d.]+)')
Y_RE = re.compile(r'Y=\s*([-\d.]+)')
Z_RE = re.compile(r'Z=\s*([-\d.]+)')

NAME_HEF_RE = re.compile(r'quad(\d+)_hef(\d+)_(\d+)')

def parse_file(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    rows = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith('Point'):
            x_match = X_RE.search(line)
            name_match = None
            y_match = None
            z_match = None

            # next line: name + Y=
            if i + 1 < n:
                name_match = NAME_RE.search(lines[i+1])
                hef_match = NAME_HEF_RE.search(lines[i+1])
                y_match = Y_RE.search(lines[i+1])
            # next next line: (n) + Z=
            if i + 2 < n:
                z_match = Z_RE.search(lines[i+2])

            if x_match and name_match and y_match and z_match:
                quad, lad, si, point = name_match.groups()
                rows.append({
                    'QUADDER': int(quad),
                    'LADDER': int(lad),
                    'SI': int(si),
                    'POINT': int(point),
                    'X': float(x_match.group(1)),
                    'Y': float(y_match.group(1)),
                    'Z': float(z_match.group(1)),
                })
            elif x_match and hef_match and y_match and z_match:
                quad, hef, point = hef_match.groups()
                rows.append({
                    'QUADDER': int(quad),
                    'LADDER': int(hef),
                    'SI': -1, # Hef points are artificially assigned to silicon -1
                    'POINT': int(point),
                    'X': float(x_match.group(1)),
                    'Y': float(y_match.group(1)),
                    'Z': float(z_match.group(1)),
                })
            i += 3
        else:
            i += 1

    return pd.DataFrame(rows, columns=['QUADDER', 'LADDER', 'SI', 'POINT', 'X', 'Y', 'Z'])

def get_point(df, quad, lad, si, point):
    match = df[(df['QUADDER'] == quad) & (df['LADDER'] == lad) &
               (df['SI'] == si) & (df['POINT'] == point)]
    if len(match) != 1:
        raise Exception(
            f"Expected exactly 1 match for QUADDER={quad}, LADDER={lad}, "
            f"SI={si}, POINT={point}, found {len(match)}"
        )
    return match.iloc[0][['X', 'Y', 'Z']]

def compute_2D_distance_between(df, quad1, lad1, si1, point1, quad2, lad2, si2, point2, coordinate):
    p1 = get_point(df, quad1, lad1, si1, point1)
    p2 = get_point(df, quad2, lad2, si2, point2)
    if coordinate == 'X':
        dist = abs(p2['X'] - p1['X'])
    elif coordinate == 'Y':
        dist = abs(p2['Y'] - p1['Y'])
    else:
        raise Exception(f"Invalid coordinate {coordinate}")
    
    return dist

def compute_3D_distance_between(df, quad1, lad1, si1, point1, quad2, lad2, si2, point2):
    p1 = get_point(df, quad1, lad1, si1, point1)
    p2 = get_point(df, quad2, lad2, si2, point2)
    dist = ((p2['X'] - p1['X'])**2 + (p2['Y'] - p1['Y'])**2 + (p2['Z'] - p1['Z'])**2) ** 0.5
    return dist

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python parse_points.py <input_file1> [input_file2 ...]")
        sys.exit(1)

    infiles = sys.argv[1:]
    # Check that all files exist
    for f in infiles:
        if not os.path.exists(f):
            print(f"File {f} does not exist")
            sys.exit(1)
    df = pd.concat([parse_file(f) for f in infiles], ignore_index=True)

    outfile = 'points_parsed.csv'
    df.to_csv(outfile, index=False)
    print(df)
    print(f"Saved points to {outfile}\n")
    
    insilicon_df_rows = []
    NOMINAL_INSILICON_DISTANCE = 97.5
    # Compute distances between points 0-1 of each silicon
    dist_outfile = 'distances_01.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER,SI,DISTANCE, DELTA WITH NOMINAL\n')
        for quad in range(1, 9):
            for lad in range(0, 2):
                for si in range(0, 2):
                    try:
                        dist = compute_3D_distance_between(df, quad, lad, si, 0, quad, lad, si, 1)
                        f.write(f'{quad},{lad},{si},{dist}, {dist - NOMINAL_INSILICON_DISTANCE}\n')
                        insilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER': lad,
                            'SI': si,
                            'POINT PAIR': '0-1',
                            'DISTANCE': dist,
                            'DELTA WITH NOMINAL': dist - NOMINAL_INSILICON_DISTANCE,
                        })
                    except:
                        pass
                    
    # Compute distances between points 1-2 of each silicon
    dist_outfile = 'insilicon_distances12.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER,SI,DISTANCE, DELTA WITH NOMINAL\n')
        for quad in range(1, 9):
            for lad in range(0, 2):
                for si in range(0, 2):
                    try:
                        dist = compute_3D_distance_between(df, quad, lad, si, 1, quad, lad, si, 2)
                        f.write(f'{quad},{lad},{si},{dist}, {dist - NOMINAL_INSILICON_DISTANCE}\n')
                        insilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER': lad,
                            'SI': si,
                            'POINT PAIR': '1-2',
                            'DISTANCE': dist,
                            'DELTA WITH NOMINAL': dist - NOMINAL_INSILICON_DISTANCE,
                        })
                    except:
                        pass
                    
    # Compute distances between points 2-3 of each silicon
    dist_outfile = 'insilicon_distances23.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER,SI,DISTANCE, DELTA WITH NOMINAL\n')
        for quad in range(1, 9):
            for lad in range(0, 2):
                for si in range(0, 2):
                    try:
                        dist = compute_3D_distance_between(df, quad, lad, si, 2, quad, lad, si, 3)
                        f.write(f'{quad},{lad},{si},{dist}, {dist - NOMINAL_INSILICON_DISTANCE}\n')
                        insilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER': lad,
                            'SI': si,
                            'POINT PAIR': '2-3',
                            'DISTANCE': dist,
                            'DELTA WITH NOMINAL': dist - NOMINAL_INSILICON_DISTANCE,
                        })
                    except:
                        pass
    
    # Compute distances between points 0-3 of each silicon
    dist_outfile = 'insilicon_distances03.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER,SI,DISTANCE, DELTA WITH NOMINAL\n')
        for quad in range(1, 9):
            for lad in range(0, 2):
                for si in range(0, 2):
                    try:
                        dist = compute_3D_distance_between(df, quad, lad, si, 0, quad, lad, si, 3)
                        f.write(f'{quad},{lad},{si},{dist}, {dist - NOMINAL_INSILICON_DISTANCE}\n')
                        insilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER': lad,
                            'SI': si,
                            'POINT PAIR': '0-3',
                            'DISTANCE': dist,
                            'DELTA WITH NOMINAL': dist - NOMINAL_INSILICON_DISTANCE,
                        })
                    except:
                        pass
                    
    insilicon_df = pd.DataFrame(insilicon_df_rows, columns=['QUADDER', 'LADDER', 'SI', 'POINT PAIR', 'DISTANCE', 'DELTA WITH NOMINAL'])
    print(insilicon_df)
    insilicon_df.to_csv('insilicon_distances.csv', index=False)
    
    
        
    intersilicon_df_rows = []
    
    # Compute distances between points 3 of silicon (0 or 1) of one ladder and points 0 of silicon (0 or 1) of the other ladder
    dist_outfile = 'intersilicon_distances_03.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER1,LADDER2,SI,POINT PAIR,DISTANCE\n')
        for quad in range(1, 9):
                for si in range(0, 2):
                    try:
                        dist = compute_2D_distance_between(df, quad, 0, si, 3, quad, 1, si, 0, 'X')
                        dist -= 0.5 # Account for distance of silicon crosses wrt the edge
                        f.write(f'{quad},0,1,{si},3-0,{dist}\n')
                        intersilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER1': 0,
                            "LADDER2": 1,
                            'SI1': si,
                            'SI2': si,
                            'POINT PAIR': '3-0',
                            'DISTANCE': dist,
                        })
                    except:
                        pass
                    
    # Compute distances between points 2 of silicon (0 or 1) of one ladder and points 1 of silicon (0 or 1) of the other ladder
    dist_outfile = 'intersilicon_distances_02.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER1,LADDER2,SI,POINT PAIR,DISTANCE\n')
        for quad in range(1, 9):
                for si in range(0, 2):
                    try:
                        dist = compute_2D_distance_between(df, quad, 0, si, 2, quad, 1, si, 1, 'X')
                        dist -= 0.5 # Account for distance of silicon crosses wrt the edge
                        f.write(f'{quad},{lad},{si},{dist}\n')
                        intersilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER1': 0,
                            "LADDER2": 1,
                            'SI1': si,
                            'SI2': si,
                            'POINT PAIR': '2-1',
                            'DISTANCE': dist,
                        })
                    except:
                        pass
                    
    # Compute distances between points 1 of silicon 0 and points 0 of silicon 1 for each ladder
    dist_outfile = 'intersilicon_distances_01.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER1,LADDER2,SI,POINT PAIR,DISTANCE\n')
        for quad in range(1, 9):
                for lad in range(0, 2):
                    try:
                        dist = compute_2D_distance_between(df, quad, lad, 0, 1, quad, lad, 1, 0, 'Y')
                        dist -= 0.5 # Account for distance of silicon crosses wrt the edge
                        f.write(f'{quad},{lad},{si},{dist}\n')
                        intersilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER1': lad,
                            'LADDER2': lad,
                            'SI1': 0,
                            'SI2': 1,
                            'POINT PAIR': '1-0',
                            'DISTANCE': dist,
                        })
                    except:
                        pass
                    
    # Compute distances between points 2 of silicon 0 and points 3 of silicon 1 for each ladder
    dist_outfile = 'intersilicon_distances_23.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER1,LADDER2,SI,POINT PAIR,DISTANCE\n')
        for quad in range(1, 9):
                for lad in range(0, 2):
                    try:
                        dist = compute_2D_distance_between(df, quad, lad, 0, 2, quad, lad, 1, 3, 'Y')
                        dist -= 0.5 # Account for distance of silicon crosses wrt the edge
                        f.write(f'{quad},{lad},{si},{dist}\n')
                        intersilicon_df_rows.append({
                            'QUADDER': quad,
                            'LADDER1': lad,
                            'LADDER2': lad,
                            'SI1': 0,
                            'SI2': 1,
                            'POINT PAIR': '2-3',
                            'DISTANCE': dist,
                        })
                    except:
                        pass
    
    intersilicon_df = pd.DataFrame(intersilicon_df_rows, columns=['QUADDER', 'LADDER1', 'LADDER2', 'SI1', 'SI2', 'POINT PAIR', 'DISTANCE'])
    print(intersilicon_df)
    intersilicon_df.to_csv('intersilicon_distances.csv', index=False)
    
    
    hef_to_si_df_rows = []
    
    # Compute distances between points 0(1) of each hef and points 0(3) of silicon 0 in the same ladder
    dist_outfile = 'hef_to_si_distances_00.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER,HEF,POINT PAIR,DISTANCE\n')
        for quad in range(1, 9):
                for hef in range(0, 2):
                    try:
                        dist = compute_3D_distance_between(df, quad, hef, -1, 0, quad, hef, 0, 0)
                        dist -= 55.6 # Account for distance of point from HEF border
                        f.write(f'{quad},{hef},{si},{dist}\n')
                        hef_to_si_df_rows.append({
                            'QUADDER': quad,
                            'LADDER': hef,
                            'HEF': hef,
                            'POINT PAIR': '0-0',
                            'DISTANCE': dist,
                        })
                    except:
                        pass
                    
    dist_outfile = 'hef_to_si_distances_13.csv'
    with open(dist_outfile, 'w') as f:
        f.write('QUADDER,LADDER,HEF,POINT PAIR,DISTANCE\n')
        for quad in range(1, 9):
                for hef in range(0, 2):
                    try:
                        dist = compute_3D_distance_between(df, quad, hef, -1, 1, quad, hef, 0, 3)
                        dist -= 55.6 # Account for distance of point from HEF border
                        f.write(f'{quad},{hef},{si},{dist}\n')
                        hef_to_si_df_rows.append({
                            'QUADDER': quad,
                            'LADDER': hef,
                            'HEF': hef,
                            'POINT PAIR': '1-3',
                            'DISTANCE': dist,
                        })
                    except: 
                        pass
                    
    hef_to_si_df = pd.DataFrame(hef_to_si_df_rows, columns=['QUADDER', 'LADDER', 'HEF', 'POINT PAIR', 'DISTANCE'])
    print(hef_to_si_df)
    hef_to_si_df.to_csv('hef_to_si_distances.csv', index=False)
    
    
    # Histogram of the distances of insilicon points
    plt.figure(figsize=(16/2, 9/2))
    sns.histplot(data=insilicon_df['DISTANCE'], bins=50, kde=False, color='blue')
    plt.xlabel('Distance (mm)')
    plt.ylabel('Entries')
    plt.title('Insilicon Distances')
    plt.minorticks_on()
    plt.ticklabel_format(axis='x', useOffset=False, style='plain')
    plt.grid(which='major', linestyle='-', linewidth='0.2', color='black')
    plt.grid(which='minor', linestyle=':', linewidth='0.2', color='black')
    plt.grid(True)
    plt.tight_layout()

    # Add stats text to the plot
    stats_str = (f"Entries: {len(insilicon_df)}\n"
                 f"Mean: {insilicon_df["DISTANCE"].mean():.3f}\n"
                 f"Median: {insilicon_df["DISTANCE"].median():.3f}\n"
                 f"Min: {insilicon_df["DISTANCE"].min():.3f}\n" 
                 f"Max: {insilicon_df["DISTANCE"].max():.3f}" 
                 )
    
    plt.text(0.05, 0.95, stats_str, transform=plt.gca().transAxes, fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))
    plt.show()

    # Histogram of the distance of intersilicon points (3-0 and 2-1)
    plt.figure(figsize=(16/2, 9/2))
    filtered_df = intersilicon_df[(intersilicon_df['POINT PAIR'] == '3-0') | (intersilicon_df['POINT PAIR'] == '2-1')]
    sns.histplot(data=filtered_df['DISTANCE'], bins=50, kde=False, color='blue')
    plt.xlabel('Distance (mm)')
    plt.ylabel('Entries')
    plt.title('Intersilicon Distances (between ladders)')
    plt.minorticks_on()
    plt.ticklabel_format(axis='x', useOffset=False, style='plain')
    plt.grid(which='major', linestyle='-', linewidth='0.2', color='black')
    plt.grid(which='minor', linestyle=':', linewidth='0.2', color='black')
    plt.grid(True)
    plt.tight_layout()

    # Add stats text to the plot
    stats_str = (f"Entries: {len(filtered_df)}\n"
                 f"Mean: {filtered_df["DISTANCE"].mean():.3f}\n"
                 f"Median: {filtered_df["DISTANCE"].median():.3f}\n"
                 f"Min: {filtered_df["DISTANCE"].min():.3f}\n"
                 f"Max: {filtered_df["DISTANCE"].max():.3f}"
                 )
    
    plt.text(0.05, 0.95, stats_str, transform=plt.gca().transAxes, fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))
    plt.show()
    
    # Histogram of the distance of intersilicon points (1-0 and 2-3)
    plt.figure(figsize=(16/2, 9/2))
    filtered_df = intersilicon_df[(intersilicon_df['POINT PAIR'] == '1-0') | (intersilicon_df['POINT PAIR'] == '2-3')]
    sns.histplot(data=filtered_df['DISTANCE'], bins=50, kde=False, color='blue')
    plt.xlabel('Distance (mm)')
    plt.ylabel('Entries')
    plt.title('Intersilicon Distances (between silicons of the same ladder)')
    plt.minorticks_on()
    plt.ticklabel_format(axis='x', useOffset=False, style='plain')
    plt.grid(which='major', linestyle='-', linewidth='0.2', color='black')
    plt.grid(which='minor', linestyle=':', linewidth='0.2', color='black')
    plt.grid(True)
    plt.tight_layout()

    # Add stats text to the plot
    stats_str = (f"Entries: {len(filtered_df)}\n"
                 f"Mean: {filtered_df["DISTANCE"].mean():.3f}\n"
                 f"Median: {filtered_df["DISTANCE"].median():.3f}\n"
                 f"Min: {filtered_df["DISTANCE"].min():.3f}\n"
                 f"Max: {filtered_df["DISTANCE"].max():.3f}"    
                 )
    
    plt.text(0.05, 0.95, stats_str, transform=plt.gca().transAxes, fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))
    plt.show()
    
    # Histogram of the distance of hef to silicon points (0-0 and 1-3)
    plt.figure(figsize=(16/2, 9/2))
    sns.histplot(data=hef_to_si_df[(hef_to_si_df['POINT PAIR'] == '0-0') | (hef_to_si_df['POINT PAIR'] == '1-3')]['DISTANCE'], bins=50, kde=False, color='blue')
    plt.xlabel('Distance (mm)')
    plt.ylabel('Entries')
    plt.title('Hef to Silicon Distances (between silicons of the same ladder)')
    plt.minorticks_on()
    plt.ticklabel_format(axis='x', useOffset=False, style='plain')
    plt.grid(which='major', linestyle='-', linewidth='0.2', color='black')
    plt.grid(which='minor', linestyle=':', linewidth='0.2', color='black')
    plt.grid(True)
    plt.tight_layout()

    # Add stats text to the plot
    stats_str = (f"Entries: {len(hef_to_si_df)}\n"
                 f"Mean: {hef_to_si_df["DISTANCE"].mean():.3f}\n"
                 f"Median: {hef_to_si_df["DISTANCE"].median():.3f}\n"
                 f"Min: {hef_to_si_df["DISTANCE"].min():.3f}\n" 
                 f"Max: {hef_to_si_df["DISTANCE"].max():.3f}" 
                 )
    
    plt.text(0.05, 0.95, stats_str, transform=plt.gca().transAxes, fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))
    plt.show()