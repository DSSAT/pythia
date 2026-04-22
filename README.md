# DSSAT-Pythia Installation Guide

## Software Requirements
To install and run DSSAT-Pythia on your PC, you will need the following software:

1. **DSSAT**:  
   Download and install DSSAT from [DSSAT website](https://get.dssat.net/request/?sft=4).

2. **Python 3.8**:  
   Download the Python 3.8 installer for Windows or macOS from [Python 3.8 release page](https://www.python.org/downloads/release/python-389/).  
   - During installation, select “Customize installation.”
   - Select all options under “Optional Features” and “Advanced Options.”
   - Note: DSSAT-Pythia only works with Python 3.8. If you have another version, uninstall it and download Python 3.8 from the above link.

3. **Git**:  
   Download and install Git from [Git download page](https://git-scm.com/download/win).

4. **Community Version of Visual Studio**:  
   Download and install Visual Studio from [Visual Studio website](https://visualstudio.microsoft.com/downloads/).  
   Select the **Desktop development with C++** workload during installation.

5. **RStudio**:  
   To use RStudio on your PC, install both R and RStudio:
   - Download and install R from [CRAN website](https://cran.rstudio.com/).
   - Download and install RStudio from [RStudio website](https://posit.co/download/rstudio-desktop/).

---


## Steps to Install DSSAT-Pythia on PC

1. Enable **Developer Mode**:
   - Open Windows Settings > Update & Security > For Developers.
   - Switch on Developer Mode and restart the computer.

2. Open the **Command Prompt** in the C Drive:
   - Open the C drive and type `cmd` in the address bar and press Enter.

3. Clone the DSSAT-Pythia repository:
   ```bash
   git clone https://github.com/dssat/pythia.git pythia
   ```

4. Navigate to the cloned directory:
   ```bash
   cd pythia
   ```

5. Delete the `poetry.lock` file:
   ```bash
   del poetry.lock
   ```

6. Install Poetry:
   ```bash
   pip install poetry
   ```

7. Install DSSAT-Pythia:
   ```bash
   <full path to poetry>\poetry install
   <full path to poetry>\poetry build
   ```
   - On Windows, poetry will be found in "C:\Users\username\AppData\Local\Programs\Python\Python38\Scripts"
     
8. Install the Pythia wheel file:
   - Navigate to the `dist` folder and install the `.whl` file:
     ```bash
     cd dist
     pip install pythia-2.3.0-py3-none-any.whl
     ```
   - **Note**: Check the version in the `dist` folder and adjust the command if necessary.

9. Add the path to `pythia.exe` to your environment variables.

10. Close the command prompt.

---

## Troubleshooting

- If you encounter any issues during installation, delete the folder `C:\pythia` and repeat the installation steps.

---

## Input Files Setup

1. Download the `InputFiles.zip` folder from [Google Drive link](https://drive.google.com/file/d/1vlBeWEavNggcuhRMgmO79aHTYZ7aq_Im/view?usp=sharing), unzip it, and save the `Simulation_Data` folder in `C:\pythia\`.

2. Open the folder `C:\pythia\Simulation_Data\OUTPUT\Sri_Lanka` and remove all folders (if any).

   **Note**: Remove the contents from the `OUTPUT` folder every time you run the model.

---

## Running the Model

1. Open the command prompt at `C:\pythia\Simulation_Data\Sri_Lanka` by typing `cmd` in the folder address bar.

2. Run the following commands to simulate maize and rice:
   ```bash
   pythia --all C:/pythia/Simulation_Data/Sri_Lanka/SL_Maize.json
   pythia --all C:/pythia/Simulation_Data/Sri_Lanka/SL_Rice.json
   ```

3. To view the output:
   - Open the `.json` file in `C:\pythia\Simulation_Data\Sri_Lanka\`.
   - Find the working directory in `"workDir": "C:/pythia/Simulation_Data/OUTPUT/Sri_Lanka/…"` and navigate to that folder.
   - The output will be available in `.csv` format.

---

## Plotting Output in RStudio

1. Open the R code file: `C:\pythia\Simulation_Data\OUTPUT\ACASA_Sri_Lanka_maize.R`.

2. Install all required packages and modify the file location on line 22 to match the output `.csv` file.

3. Run the R script to generate the yield plot.

4. The plot will be saved at the location specified in line 62.

   **Note**: If you encounter errors reading the `.csv` file, open the file and delete all columns except `LATITUDE`, `LONGITUDE`, and `HWAH`.
