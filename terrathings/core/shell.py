import subprocess, os, logging


def exec(command, cwd, env):
    """
    Executes a command in a subprocess.

    :param str command: The command to execute.
    :param str cwd: The working directory to execute the command in.
    :param dict env: A dictionary of environment variables to pass to the command.
    """
    p = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ.copy(), **env} if env else os.environ.copy(),
    )
    for line in p.stdout:
        logging.debug(f"Compiling: {line.decode('utf-8').strip()}")
