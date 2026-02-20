from pdf_reader.class_project_name import ProjectName
from pdf_reader.s01_parse_tables import parse_tables
from pdf_reader.s02_parse_combiner_names import parse_combiner_names

project_name = ProjectName.SUN_STREAMS_4


df = parse_tables(project_name)
df = parse_combiner_names(df)
# print(df.head())

df.to_csv("./pdf_reader/output.csv")
