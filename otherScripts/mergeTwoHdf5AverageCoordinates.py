import numpy as np
import h5py
import copy

filename1 = "../zebrazoom/ZZoutput/recording_2024-01-16_10-03-55_2024_02_12-09_18_47.h5"
f1 = h5py.File(filename1, "r")

filename2 = "../zebrazoom/ZZoutput/recording_2024-01-16_10-03-55_2024_02_12-09_24_19.h5"
f2 = h5py.File(filename2, "r")

TailPosX1 = f1["dataForWell0/dataForAnimal0/dataPerFrame/TailPosX"][:]
TailPosY1 = f1["dataForWell0/dataForAnimal0/dataPerFrame/TailPosY"][:]
HeadPos1  = f1["dataForWell0/dataForAnimal0/dataPerFrame/HeadPos"][:]

TailPosX2 = f2["dataForWell0/dataForAnimal0/dataPerFrame/TailPosX"][:]
TailPosY2 = f2["dataForWell0/dataForAnimal0/dataPerFrame/TailPosY"][:]
HeadPos2  = f2["dataForWell0/dataForAnimal0/dataPerFrame/HeadPos"][:]

# Inverting if necessary
TailPosX1np = np.array([np.array([i for i in TailPosX1[j]]) for j in range(len(TailPosX1))])
TailPosY1np = np.array([np.array([i for i in TailPosY1[j]]) for j in range(len(TailPosY1))])
invert1 = (TailPosX1np[:, 0]**2 + TailPosY1np[:, 0]**2) > (TailPosX1np[:, len(TailPosX1np[0])-1]**2 + TailPosY1np[:, len(TailPosY1np[0])-1]**2)
mirror_indices = np.arange(len(TailPosX1[0]))[::-1]
for i, invert_value in enumerate(invert1):
  if invert_value:
    TailPosX1[i] = tuple(reversed(TailPosX1[i]))
    TailPosY1[i] = tuple(reversed(TailPosY1[i]))

TailPosX2np = np.array([np.array([i for i in TailPosX2[j]]) for j in range(len(TailPosX2))])
TailPosY2np = np.array([np.array([i for i in TailPosY2[j]]) for j in range(len(TailPosY2))])
invert2 = (TailPosX2np[:, 0]**2 + TailPosY2np[:, 0]**2) > (TailPosX2np[:, len(TailPosX2np[0])-1]**2 + TailPosY2np[:, len(TailPosY2np[0])-1]**2)
mirror_indices = np.arange(len(TailPosX2[0]))[::-1]
for i, invert_value in enumerate(invert2):
  if invert_value:
    TailPosX2[i] = tuple(reversed(TailPosX2[i]))
    TailPosY2[i] = tuple(reversed(TailPosY2[i]))

# Calculate the average for TailX
TailPosXAvg = (np.array([tuple(x) for x in TailPosX1.tolist()]) + np.array([tuple(x) for x in TailPosX2.tolist()])) / 2
TailPosXAvgOrgFormat = np.empty_like(TailPosX1)
for i, field in enumerate(TailPosXAvgOrgFormat.dtype.fields.keys()):
  TailPosXAvgOrgFormat[field] = TailPosXAvg[:, i]

# Calculate the average for TailY
TailPosYAvg = (np.array([tuple(x) for x in TailPosY1.tolist()]) + np.array([tuple(x) for x in TailPosY2.tolist()])) / 2
TailPosYAvgOrgFormat = np.empty_like(TailPosY1)
for i, field in enumerate(TailPosYAvgOrgFormat.dtype.fields.keys()):
  TailPosYAvgOrgFormat[field] = TailPosYAvg[:, i]

# Calculate the average for TailY
HeadPosAvg = (np.array([tuple(x) for x in HeadPos1.tolist()]) + np.array([tuple(x) for x in HeadPos2.tolist()])) / 2
HeadPosAvgOrgFormat = np.empty_like(HeadPos1)
for i, field in enumerate(HeadPosAvgOrgFormat.dtype.fields.keys()):
  HeadPosAvgOrgFormat[field] = HeadPosAvg[:, i]

# Create a new file for copying the contents
merge_filename = "../zebrazoom/ZZoutput/recording_2024-01-16_10-03-55_merged.h5"
f_merge = h5py.File(merge_filename, "w")

def copy_groups_and_datasets(source_group, dest_group):
  """Recursively copy groups and datasets along with their attributes."""
  for name, obj in source_group.items():
    if isinstance(obj, h5py.Group):
      # Recursively copy groups
      subgroup = dest_group.create_group(name)
      # Copy group attributes
      for attr_name, attr_value in obj.attrs.items():
        subgroup.attrs[attr_name] = attr_value
      copy_groups_and_datasets(obj, subgroup)
    elif isinstance(obj, h5py.Dataset):
      # Copy datasets
      dest_group[name] = obj[()]
      # Copy dataset attributes
      for attr_name, attr_value in obj.attrs.items():
        dest_group[name].attrs[attr_name] = attr_value

# Copy root-level attributes
for attr_name, attr_value in f1.attrs.items():
  f_merge.attrs[attr_name] = attr_value
 
# Copy the contents of the original file to the new file
copy_groups_and_datasets(f1, f_merge)

f_merge["dataForWell0/dataForAnimal0/dataPerFrame/TailPosX"][:] = TailPosXAvgOrgFormat
f_merge["dataForWell0/dataForAnimal0/dataPerFrame/TailPosY"][:] = TailPosYAvgOrgFormat
f_merge["dataForWell0/dataForAnimal0/dataPerFrame/HeadPos"][:]  = HeadPosAvgOrgFormat

f_merge.close()
