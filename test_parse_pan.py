import sys
from api.app.domain.equipment.pv_module.parse_pan.c_parse_pan import parse_pan

with open("FS-6430A CdTe Dec2017_v640.PAN", "rb") as f:
    content = f.read()

res = parse_pan(file_content=content)
print(res)
