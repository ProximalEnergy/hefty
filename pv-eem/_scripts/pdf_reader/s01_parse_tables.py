import pandas as pd
import pymupdf as pdf
from pdf_reader.class_project_name import ProjectName


def parse_tables(
    project_name: ProjectName,
) -> pd.DataFrame:
    match project_name:
        case ProjectName.SUN_STREAMS_4:
            file = "pdf_reader/_pdf/SS4.pdf"
            page_start = 215
            page_end = 999

            cols = [
                "Combiner Box Schedule",
                "Parallel Source Circuit Detail",
                "# of PV Modules Per PV Source Circuit",
                "# Of PV Source Circuits Per Parallel Source Circuit",
                "1500 VDC Fuse Rating Per PV Source Circuit (A)",
                "# Of Parallel Source Circuits Per Combiner Box",
                "1500 VDC Fuse Rating Per Parallel Source Circuit Harness (A)",
                "# Of PV Source Circuits Per Combiner Box",
                "Average PV Module Power (W)",
                "# Of PV Modules Per Combiner Box",
                "Combiner Box Power (kW)",
                "DC/AC Ratio (Based on 3600kW Nominal)",
                "1500 VDC Fuse Rating Per PV Combiner Output (A)",
                "DC Combiner Box Rating (A)",
                "PV Combiner Output Conductor Size and Type",
                "Maximum Voltage (V)",
                "Operating Voltage (V)",
                "Max. Short Circuit Current (A)",
                "Operating Current (A)",
                "CB Length (ft)",
                "Power Loss From Combiner To Inverter",
                "Power Loss Percentage From Average Harness To Combiner",
                "Power Loss Percentage From Average Harness To Combiner",
                "Total",
            ]
        case ProjectName.SERRANO:
            file = "pdf_reader/_pdf/Serrano.pdf"
            page_start = 136
            page_end = 163

            cols = [
                "Combiner Box Schedule",
                "Parallel Source Circuit Detail",
                "# of PV Modules Per PV Source Circuit",
                "# Of PV Source Circuits Per Parallel Source Circuit",
                "1500 VDC Fuse Rating Per PV Source Circuit (A)",
                "# Of Parallel Source Circuits Per Combiner Box",
                "1500 VDC Fuse Rating Per Parallel Source Circuit Harness (A)",
                "# Of PV Source Circuits Per Combiner Box",
                "Average PV Module Power (W)",
                "# Of PV Modules Per Combiner Box",
                "Combiner Box Power (kW)",
                "DC/AC Ratio (Based on 3600kW Nominal)",
                "1500 VDC Fuse Rating Per PV Combiner Output (A)",
                "DC Combiner Box Rating (A)",
                "PV Combiner Output Conductor Size and Type",
                "Maximum Voltage (V)",
                "Operating Voltage (V)",
                "Max. Short Circuit Current (A)",
                "Operating Current (A)",
                "CB Length (ft)",
                "Power Loss From Combiner To Inverter",
                "Power Loss Percentage From Combiner To Inverter",
                "Total",
            ]

    doc = pdf.open(file)
    dfs = []
    for page_number in range(page_start - 1, page_end):
        page = doc.load_page(page_number)
        tables = page.find_tables()
        for i, table in enumerate(tables):
            df = table.to_pandas()
            if df.shape[0] == 0:
                continue

            # remove header and footer rows
            match project_name:
                case ProjectName.SUN_STREAMS_4:
                    df = df.iloc[1:-1:]
                case ProjectName.SERRANO:
                    df = df.iloc[0:-1:]

            # Function to split newlines and expand into new rows
            def split_newlines(df):
                new_rows = []
                for _, row in df.iterrows():
                    split_data = [str(cell).split("\n") for cell in row]
                    max_len = max(len(lst) for lst in split_data)
                    for i in range(max_len):
                        new_row = [lst[i] if i < len(lst) else "" for lst in split_data]
                        new_rows.append(new_row)
                return pd.DataFrame(new_rows)

            # Apply the function
            df = split_newlines(df)

            # Replace empty strings with NaN
            df = df.replace("", pd.NA)
            df = df.replace("None", pd.NA)

            # Forward fill NaN values
            df = df.ffill()

            try:
                df.columns = cols
                # print(f"Success: {page_number}")
                dfs.append(df)
            except:
                print(df.head())
                # print(f"Failure: {page_number}")

    df = pd.concat(dfs)
    return df
