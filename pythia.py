import logging

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
    parser.add_argument("--all", action='store_true', help="Run all the steps in pythia")
    parser.add_argument("--setup", action="store_true", help="Setup DSSAT run structure and files")
    parser.add_argument("--run-dssat", action="store_true", help="Run DSSAT over the run structure")
    parser.add_argument("--analyze", action="store_true", help="Run the analysis for the DSSAT runs")
    parser.add_argument("--clean-work-dir", action="store_true", help="Clean the work directory prior to run")
    args = parser.parse_args()

    if not args.config:
        parser.print_help()
    else:
        config = pythia.config.load_config(args.config)
        if args.clean_work_dir:
            print("Cleaning work directory")
            import shutil
            shutil.rmtree(config["workDir"])
        for run in config.get("runs", []):
            if args.all or args.setup:
                peerless = pythia.io.peer(run, config.get("sample", None))
                pythia.peerless.execute(run, peerless, config)
            if args.all or args.run_dssat:
                pythia.dssat.execute(config)
            if args.analyze:
                print("Analysis module is still being hooked up")
