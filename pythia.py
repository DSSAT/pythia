import logging
import pprint

import pythia.config
import pythia.dssat
import pythia.io
import pythia.peerless

logging.getLogger("pythia_app")
logging.basicConfig(level=logging.INFO)

config = pythia.config.load_config("sample.json")
single_run = config["runs"][0]
peerless = pythia.io.peer(single_run, config.get("sample", None))
pythia.peerless.execute(single_run, peerless, config)
pprint.pprint(config)
pythia.dssat.execute(config)
