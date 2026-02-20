# Style Guide
## Design Patterns to Follow
- **Functional Core Imperative Shell (FCIS)**:  All functions in the simulation folder are purely functional for easy testing and reasoning.  All "side-effects" like database reads and writes are located in the pre-processing and post-processing steps"

## Keywords
- Filenames
  - **c**: Controller for a set of step numbers
  - **p**: Phase of the simulation
  - **sxx**:  The step number to keep files in order of their operation
  - **get**:  The function in this file only does a read operation
  - **calc**:  The function in this file only does a calculation
- Versions
  - **vX.Y.Z**:  Semantic versioning of the simulation
    - X:  Major version -> Breaking changes for the API of the simulation
    - Y:  Minor version -> There has been a change to the energy model results
    - Z:  Patch version -> There has been a change to the simulation code that does not change the results
