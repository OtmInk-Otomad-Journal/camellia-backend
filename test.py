import yaml

with open("./config/data.yaml","r") as conf_file:
    conf = yaml.safe_load(conf_file)

print(conf)