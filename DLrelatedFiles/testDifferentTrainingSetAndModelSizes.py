import matplotlib.pyplot as plt
import re
import os
import argparse
import pandas as pd

totNumberVideos = 18

def testDifferentTrainingSetAndModelSizes(folder_paths):
    plt.figure(figsize=(8, 5))
    all_data = {}  # Store data for Excel export
    
    for folder_path in folder_paths:
        x_values = []
        y_values = []
        folder_name = os.path.basename(os.path.normpath(folder_path))
        all_data[folder_name] = {}
        
        # Process each file in the folder
        for filename in os.listdir(folder_path):
            if filename.startswith("nbFilesRemoved") and filename.endswith(".txt"):
                match = re.search(r"nbFilesRemoved(\d+).txt", filename)
                if match:
                    nb_files_removed = int(match.group(1))
                    with open(os.path.join(folder_path, filename), "r") as f:
                        content = f.read()
                        fitness_match = re.search(r"fitness:\s*([\d.]+)", content)
                        if fitness_match:
                            fitness = float(fitness_match.group(1))
                            x_val = totNumberVideos - nb_files_removed
                            x_values.append(totNumberVideos - nb_files_removed)
                            y_values.append(fitness)
                            all_data[folder_name][x_val] = fitness
        
        # Sort values by x-axis
        sorted_indices = sorted(range(len(x_values)), key=lambda k: x_values[k])
        x_values = [x_values[i] for i in sorted_indices]
        y_values = [y_values[i] for i in sorted_indices]
        
        # Plot the graph for this folder
        plt.plot(x_values, y_values, marker='o', linestyle='-', label=folder_name)
    
    plt.xlabel("Nb training videos")
    plt.ylabel("Fitness")
    plt.ylim(0, 0.6)  # Set Y-axis range from 0 to 0.6
    plt.title("Fitness vs. Nb training videos")
    plt.legend()
    plt.grid()
    plt.show()
    
    # Convert data to DataFrame and export to Excel
    df = pd.DataFrame(all_data).sort_index()
    df.to_excel("fitness_values.xlsx")
    print("Data exported to fitness_values.xlsx")
    
    # Export data to Excel
    df = pd.DataFrame(all_data, columns=["Folder", "Nb training videos", "Fitness"])
    df.to_excel("fitness_values.xlsx", index=False)
    print("Data exported to fitness_values.xlsx")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot fitness values from multiple directories.")
    parser.add_argument("folder_paths", type=str, nargs='+', help="Paths to the folders containing the files.")
    args = parser.parse_args()
    
    testDifferentTrainingSetAndModelSizes(args.folder_paths)