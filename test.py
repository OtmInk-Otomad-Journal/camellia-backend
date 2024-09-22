import yaml
from dateutil.parser import isoparse
import datetime
import pytz

with open("./config/data.yaml","r") as conf_file:
    conf = yaml.safe_load(conf_file)

o_time = isoparse(conf["time_range"][1])
print(o_time)
t_time = o_time.astimezone(pytz.timezone("Asia/Shanghai"))
print(t_time)