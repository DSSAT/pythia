import logging

import pythia.analytics
import pythia.config
import pythia.dssat
import pythia.io
import pythia.peerless

logging.getLogger("pythia_app")
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="JSON configuration file to run")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--run-dssat", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--clean-work-dir", action="store_true")
    args = parser.parse_args()

    if not args.config:
        parser.print_help()
    else:
        config = pythia.config.load_config(args.config)
        if args.clean_work_dir:
            import os
            import shutil

            print("Cleaning work directory")
            if(os.path.isdir(config["workDir"])):
                shutil.rmtree(config["workDir"])
        for run in config.get("runs", []):
            peerless = []
            if args.all or args.setup or args.analyze:
                peerless = pythia.io.peer(run, config.get("sample", None))
            if args.all or args.setup:
                print("Setting up DSSAT runs...", end=" ")
                pythia.peerless.execute(run, peerless, config)
                print("DONE")
            if args.all or args.run_dssat:
                print("Running gridded DSSAT", end=" ")
                pythia.dssat.execute(config)
                print("DONE")
            if args.all or args.analyze:
                # pythia.analytics.execute(run, peerless, config)
                print("Analytics are not yet supported")
