from pyaml_env import parse_config
from dotenv import load_dotenv

load_dotenv()


def init():
    cli_args = read_cli_arguments()
    return (
        cli_args.action,
        cli_args.devices,
        _read_yaml(cli_args.config),
        cli_args.deployment,
    )


def read_cli_arguments():
    """
    Reads the command line arguments and returns a dictionary with the config values.
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to the config file", required=True)
    parser.add_argument("--deployment", help="ID of the deployment", required=False)
    parser.add_argument(
        "action", help="Action to perform", choices=["build", "init", "update", "apply"]
    )
    parser.add_argument(
        "devices", nargs=argparse.REMAINDER, help="Devices to apply the action to"
    )
    # args = parser.parse_args()
    # if args.action == "init" and len(args.devices) == 0:
    #     parser.error("init requires a device ID")
    return parser.parse_args()


def _read_yaml(file_path):
    """
    Reads the yaml file and returns a dictionary with the config values.
    """
    return parse_config(file_path)
