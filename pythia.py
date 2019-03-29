import pythia.config
import pythia.io
import pythia.runner
import pythia.template
import pprint
import logging

logging.getLogger("pythia_app")

config = pythia.config.load_config("sample.json")
single_run = config["runs"][0]
peerless = pythia.io.peer(single_run)
pythia.runner.run_peerless(single_run, peerless, config)
pprint.pprint(config)
