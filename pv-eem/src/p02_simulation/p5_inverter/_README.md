# Inverter Model

## Stage 1:  Determine the Operating Point
1. Check to see if the maximum power point fits within the inverter normal operations window.
2. If MPP voltage < Vmin, change voltage to Vmin and check window.
3. If MPP power > Pmax, change voltage to V at Pmax.
4. If MPP voltage > Vmpp,max change voltage to Vmpp, max and check window.


### SolarFarmer
- Minimum DC Power
- Minimum MPPT DC Voltage
- Maximum MPPT DC Voltage
- Maximum AC Power
  - Requires that we calculate the maximum AC power given the ambient temperature by linear interpolation.
- Maximum DC Current

### Database
CREATE TABLE inverters (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    temperature_points NUMERIC[],
    power_points NUMERIC[]
);

## Stage 2:  Determine the Efficiency at the Operating Point

## Resources
[1] **SolarFarmer:**

https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/CalcRef/Inverter/Inverter.html

[2] **PlantPredict:**

https://terabase.atlassian.net/servicedesk/customer/portal/3/article/1292009483

[3] **"Control of Power Inverters in Renewable Energy and Smart Grid Integration"** by Qing-Chang Zhong and Tomas Hornik
