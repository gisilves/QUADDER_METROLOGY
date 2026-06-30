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
            i += 3
        else:
            i += 1

    return pd.DataFrame(rows, columns=['QUADDER', 'LADDER', 'SI', 'POINT', 'X', 'Y', 'Z'])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python plot_points.py <input_file1> [input_file2 ...]")
        sys.exit(1)

    infiles = sys.argv[1:]
    
    # Check that all files exist
    for f in infiles:
        if not os.path.exists(f):
            print(f"File {f} does not exist")
            sys.exit(1)
            
    df = pd.concat([parse_file(f) for f in infiles], ignore_index=True)
    print(df)
    
    df['UNIQUE_SI'] = 2*df['LADDER'] + df['SI']
    
    fig, ax = plt.subplots(figsize=(8,6))
    colors = {0:'tab:blue',1:'tab:orange',2:'tab:green',3:'tab:red'}
    for g, sub in df.groupby('UNIQUE_SI'):
        sub = sub.sort_values('POINT')
        ax.fill(sub['X'], sub['Y'], color=colors[g], alpha=0.3)
        ax.plot(sub['X'].tolist() + [sub['X'].iloc[0]],
                sub['Y'].tolist() + [sub['Y'].iloc[0]],
                color=colors[g])
        ax.scatter(sub['X'], sub['Y'], label=f'UNIQUE_SI={g}', color=colors[g], s=60)
        
        # Add point labels
        for i, row in sub.iterrows():
            # Label is LADDER_SI_POINT
            label = f'{int(row["LADDER"])}_{int(row["SI"])}_{int(row["POINT"])}'
            ax.text(row['X'], row['Y'], label, fontsize=8, color='black')
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title('Measured silicon positions')
    # fix aspect ratio to 1:1
    ax.set_aspect(1/ax.get_data_ratio())
    plt.tight_layout()
    plt.show()
    
