import pythia.config
import pprint
import logging

logging.getLogger("pythia_app")

config = pythia.config.load_config("sample.json")
pprint.pprint(config)
