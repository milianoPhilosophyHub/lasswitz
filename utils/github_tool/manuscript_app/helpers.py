import json
import logging
import subprocess
from pyramid.response import Response

def json_response(data, status=200):
    return Response(json.dumps(data), status=status, content_type='application/json', charset='UTF-8')

def run_command(command_list, cwd):
    """Ejecuta un comando de forma segura."""
    try:
        result = subprocess.run(
            command_list,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300
        )
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"Error al ejecutar '{' '.join(e.cmd)}': {e.stderr}")
        raise