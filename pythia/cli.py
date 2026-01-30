import argparse
import datetime
import json
import logging
import os
import tempfile

import pythia.analytics
import pythia.config
import pythia.dssat
import pythia.io
import pythia.peerless
import pythia.plugin
from pythia.custom_raster_creator import main as raster_main


def _build_raster_cfg_from_cli(args) -> dict:
    if not args.raster_output:
        raise ValueError("Missing --raster-output when using --create-raster --raster-input cli.")

    # For now: .SOL-based CLI input
    if not args.raster_sol_path:
        raise ValueError(
            "Missing --raster-sol-path (provide one or more paths) when using --create-raster --raster-input cli."
        )

    recursive = bool(args.raster_recursive)

    cfg = {
        "output_raster": str(args.raster_output),
        "sol_inputs": {
            "paths": [str(p) for p in args.raster_sol_path],
            "recursive": recursive,
        },
    }

    # Optional: allow building updates on top of an existing raster
    if args.raster_base:
        cfg["base_raster"] = str(args.raster_base)

    return cfg


def main():
    parser = argparse.ArgumentParser(prog="pythia")

    # Positional arguments
    parser.add_argument("config", nargs="?", default=None, help="JSON configuration file to run")


    # General run flags
    parser.add_argument("--all", action="store_true", help="Run all the steps in pythia")
    parser.add_argument("--export-runlist", action="store_true", help="Export a list of all the directories to be run")
    parser.add_argument("--setup", action="store_true", help="Setup DSSAT run structure and files")
    parser.add_argument("--run-dssat", action="store_true", help="Run DSSAT over the run structure")
    parser.add_argument("--analyze", action="store_true", help="Run the analysis for the DSSAT runs")
    parser.add_argument("--clean-work-dir", action="store_true", help="Clean the work directory prior to run")
    parser.add_argument(
        "--logfile-prefix",
        default="pythia",
        help="Prefix the log file with this string. <prefix|pythia>-YYYYmmdd-hhMMSS.log",
    )
    parser.add_argument("--quiet", action="store_true", help="Enjoy the silence")


    # Raster creation mode
    parser.add_argument("--create-raster", action="store_true", help="Create or update a soil raster GeoTIFF")

    parser.add_argument(
        "--raster-input",
        choices=["json", "cli"],
        required=False,
        help="Required with --create-raster: choose how to provide raster inputs (json or cli).",
    )

    parser.add_argument(
        "--raster-config",
        help="Path to raster build JSON config (used when --create-raster --raster-input json).",
    )

    parser.add_argument("--raster-output", help="Output GeoTIFF path (used when --create-raster --raster-input cli).")
    parser.add_argument(
        "--raster-sol-path",
        action="append",
        default=[],
        help="Path to a .SOL file or a directory containing .SOL files. Repeatable.",
    )
    parser.add_argument("--raster-base", help="Optional base raster (.tif) to update instead of creating a new one.")

    rec_group = parser.add_mutually_exclusive_group()
    rec_group.add_argument("--raster-recursive", dest="raster_recursive", action="store_true")
    rec_group.add_argument("--raster-no-recursive", dest="raster_recursive", action="store_false")
    parser.set_defaults(raster_recursive=False)

    args = parser.parse_args()

    
    # Raster creation workflow
    if args.create_raster:
        if not args.raster_input:
            parser.error("--raster-input is required when using --create-raster (choose: json or cli).")

        if args.raster_input == "json":
            if not args.raster_config:
                parser.error("Missing --raster-config when using --create-raster --raster-input json.")
            raster_main(args.raster_config, None)
            return

        if args.raster_input == "cli":
            cfg = _build_raster_cfg_from_cli(args)

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                ) as tf:
                    json.dump(cfg, tf, ensure_ascii=False, indent=2)
                    tmp_path = tf.name

                raster_main(tmp_path, None)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
            return

        parser.error("Invalid --raster-input value.")
        return


    # Normal Pythia run workflow
    if not args.config:
        parser.print_help()
        return

    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    logging.getLogger("pythia_app")
    logging.basicConfig(
        level=logging.INFO,
        filename="{}-{}.log".format(args.logfile_prefix, now),
        filemode="w",
    )

    config = pythia.config.load_config(args.config)
    if args is None or not config:
        print("Invalid configuration file")
        return

    logging.info(
        "Pythia started: %s",
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    if args.clean_work_dir:
        print("Cleaning the work directory")
        if os.path.exists(config["workDir"]):
            import shutil
            shutil.rmtree(config["workDir"])

    config["exportRunlist"] = args.export_runlist
    plugins = pythia.plugin.load_plugins(config, {})
    config = pythia.plugin.run_plugin_functions(
        pythia.plugin.PluginHook.post_config, plugins, full_config=config
    ).get("full_config", config)

    config["silence"] = bool(args.quiet)

    if args.all or args.setup:
        print("Setting up points and directory structure")
        pythia.peerless.execute(config, plugins)

    if args.all or args.run_dssat:
        print("Running DSSAT over the directory structure")
        pythia.dssat.execute(config, plugins)

    if args.all or args.analyze:
        print("Running simple analytics over DSSAT directory structure")
        pythia.analytics.execute(config, plugins)

    logging.info(
        "Pythia completed: %s",
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    