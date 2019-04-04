import logging

import pythia.config
import pythia.dssat
import pythia.io
import pythia.peerless

logging.getLogger("pythia_app")
logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="JSON configuration file to run")
    parser.add_argument("--all", action='store_true')
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--run-dssat", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if not args.config:
        parser.print_help()
    else:
        config = pythia.config.load_config(args.config)
        for run in config.get("runs", []):
            if args.all or args.setup:
                peerless = pythia.io.peer(run, config.get("sample", None))
                pythia.peerless.execute(run, peerless, config)
            if args.all or args.run_dssat:
                pythia.dssat.execute(config)
            if args.analyze:
                print("Analysis module is still being hooked up")
