import matplotlib.pyplot as plt
import re
import os
import argparse
import pandas as pd
import numpy as np

# Total number of videos
TOT_NUMBER_VIDEOS = 18

def extract_base_name(folder_name):
    # Extract base model name (e.g., 'nano' from 'nano', 'nano2', 'nano3', etc.)
    return re.sub(r'\d+$', '', folder_name)

def test_different_training_set_and_model_sizes(folder_paths):
    plt.figure(figsize=(8, 5))
    all_data = {}  # Store data for Excel export
    grouped_data = {}  # Store data grouped by base model name
    
    for folder_path in folder_paths:
        folder_name = os.path.basename(os.path.normpath(folder_path))
        base_name = extract_base_name(folder_name)
        
        if base_name not in grouped_data:
            grouped_data[base_name] = {}
        
        for filename in os.listdir(folder_path):
            if filename.startswith("nbFilesRemoved") and filename.endswith(".txt"):
                match = re.search(r"nbFilesRemoved(\d+).txt", filename)
                if match:
                    nb_files_removed = int(match.group(1))
                    x_val = TOT_NUMBER_VIDEOS - nb_files_removed
                    
                    with open(os.path.join(folder_path, filename), "r") as f:
                        content = f.read()
                        fitness_match = re.search(r"fitness:\s*([\d.]+)", content)
                        if fitness_match:
                            fitness = float(fitness_match.group(1))
                            
                            if x_val not in grouped_data[base_name]:
                                grouped_data[base_name][x_val] = []
                            
                            grouped_data[base_name][x_val].append(fitness)
    
    # Plot grouped data
    for base_name, values in grouped_data.items():
        x_values = sorted(values.keys())
        y_means = [np.mean(values[x]) for x in x_values]
        y_errors = [np.std(values[x]) for x in x_values]  # Standard deviation as error bars
        
        plt.errorbar(x_values, y_means, yerr=y_errors, marker='o', linestyle='-', label=base_name)
        
        # Store for Excel export
        all_data[base_name] = {x: {'mean': np.mean(values[x]), 'std': np.std(values[x])} for x in x_values}
    
    plt.xlabel("Nb training videos")
    plt.ylabel("Fitness")
    plt.ylim(0, 0.6)  # Set Y-axis range from 0 to 0.6
    plt.title("Fitness vs. Nb training videos")
    plt.legend()
    plt.grid()
    plt.show()
    
    # Convert to DataFrame and export to Excel
    df = pd.DataFrame({(key, stat): [all_data[key][x][stat] for x in sorted(all_data[key].keys())] 
                       for key in all_data for stat in ['mean', 'std']},
                      index=sorted(next(iter(all_data.values())).keys()))
    df.index.name = "Nb training videos"
    df.to_excel("fitness_values.xlsx")
    print("Data exported to fitness_values.xlsx")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot fitness values from multiple directories.")
    parser.add_argument("folder_paths", type=str, nargs='+', help="Paths to the folders containing the files.")
    args = parser.parse_args()
    
    test_different_training_set_and_model_sizes(args.folder_paths)