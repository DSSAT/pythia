import datetime
import logging
import os

import pythia.config
import pythia.dssat
import pythia.analytics
import pythia.io
import pythia.peerless
import pythia.plugin

logging.getLogger("pythia_app")
logging.basicConfig(level=logging.INFO, filename="pythia.log", filemode="w")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="JSON configuration file to run")
    parser.add_argument("--all", action="store_true", help="Run all the steps in pythia")
    parser.add_argument(
        "--export-runlist",
        action="store_true",
        help="Export a list of all the directories to be run",
    )
    parser.add_argument("--setup", action="store_true", help="Setup DSSAT run structure and files")
    parser.add_argument("--run-dssat", action="store_true", help="Run DSSAT over the run structure")
    parser.add_argument(
        "--analyze", action="store_true", help="Run the analysis for the DSSAT runs"
    )
    parser.add_argument(
        "--clean-work-dir", action="store_true", help="Clean the work directory prior to run"
    )
    args = parser.parse_args()

    if not args.config:
        parser.print_help()
    else:
        config = pythia.config.load_config(args.config)
        if args is None or not config:
            print("Invalid configuration file")
        else:
            logging.info("Pythia started: %s", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            if args.clean_work_dir:
                print("Cleaning the work directory")
                if os.path.exists(config["workDir"]):
                    import shutil

                    shutil.rmtree(config["workDir"])

            config["exportRunlist"] = args.export_runlist
            plugins = pythia.plugin.load_plugins(config, {})
            config = pythia.plugin.run_plugin_functions(
                pythia.plugin.PluginHook.post_config, plugins, full_config=config
            )
            if args.all or args.setup:
                print("Setting up points and directory structure")
                pythia.peerless.execute(config, plugins)
            if args.all or args.run_dssat:
                print("Running DSSAT over the directory structure")
                pythia.dssat.execute(config, plugins)
            if args.all or args.analyze:
                print("Running simple analytics over DSSAT directory structure")
                pythia.analytics.execute(config, plugins)
            logging.info("Pythia completed: %s", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
