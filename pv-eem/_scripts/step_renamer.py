from pathlib import Path

# --- CONFIGURATION ---
# Set the starting number after which all numbers should be incremented
START_NUMBER = 2  # This will increment all files numbered X and above

# --- MAIN ---

# Ask for confirmation
confirmation = input(
    "This will rename files in the specified directory. "
    "Are you sure you want to continue? (y/n): "
)
if confirmation.lower() != "y":
    print("Operation cancelled.")
    exit()
# Get the directory of the script
directory = Path("src/p02_simulation/p3_epoai")

# Get all files that match the pattern s##_*.py
files = sorted([f for f in directory.glob("s[0-9][0-9]_*.py")], reverse=True)

# Process files in reverse order to avoid naming conflicts
for file_path in files:
    # Extract the number from the filename
    filename = file_path.name
    current_number = int(filename[1:3])

    # Only process files with numbers greater than START_NUMBER
    if current_number > START_NUMBER:
        # Create new filename with incremented number
        new_number = str(current_number + 1).zfill(2)
        new_filename = f"s{new_number}{filename[3:]}"

        # Construct new path
        new_path = file_path.parent / new_filename

        # Rename the file
        file_path.rename(new_path)
        print(f"Renamed {filename} to {new_filename}")
