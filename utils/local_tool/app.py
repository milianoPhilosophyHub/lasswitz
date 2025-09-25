import os
import re
import shutil
import logging
import yaml
import json
import subprocess

from waitress import serve
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.response import Response, FileResponse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MANUSCRIPTS_BASE_DIR = os.path.join(SCRIPT_DIR, 'manuscripts')
ROOTSTOCK_TEMPLATE_DIR = os.path.join(SCRIPT_DIR, 'rootstock_template')
PORT = 6543

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def json_response(data, status=200):
    """Crea una respuesta HTTP en formato JSON."""
    return Response(json.dumps(data), status=status, content_type='application/json', charset='UTF-8')

def run_command(command_list, cwd, env_vars=None):
    """Ejecuta un comando de terminal de forma segura."""
    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        result = subprocess.run(
            command_list,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
            env=env
        )
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"Error al ejecutar '{' '.join(e.cmd)}':\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        raise

@view_config(route_name='manuscript_collection', request_method='GET', renderer='json')
def show_manuscripts(request):
    """Muestra todos los manuscritos disponibles."""
    try:
        manuscripts = [d for d in os.listdir(MANUSCRIPTS_BASE_DIR) if os.path.isdir(os.path.join(MANUSCRIPTS_BASE_DIR, d))]
        return {'manuscripts': manuscripts}
    except FileNotFoundError:
        return json_response({'error': 'La carpeta base de manuscritos no existe.'}, status=500)

@view_config(route_name='manuscript_collection', request_method='POST', renderer='json')
def create_manuscript(request):
    """Crea un nuevo manuscrito localmente desde la plantilla."""
    repo_name = request.json_body.get('name')
    if not repo_name or not re.match(r'^[a-zA-Z0-9_.-]+$', repo_name):
        return json_response({'error': 'Parámetro "name" faltante o con formato inválido.'}, status=400)

    target_path = os.path.join(MANUSCRIPTS_BASE_DIR, repo_name)
    if os.path.exists(target_path):
        return json_response({'error': f'El manuscrito "{repo_name}" ya existe.'}, status=409)

    logging.info(f"Creando nuevo manuscrito '{repo_name}' en {target_path}")
    try:
        shutil.copytree(ROOTSTOCK_TEMPLATE_DIR, target_path, symlinks=True)

        run_command(['git', 'init'], cwd=target_path)
        run_command(['git', 'add', '.'], cwd=target_path)
        run_command(['git', 'commit', '-m', f'Creación inicial del manuscrito {repo_name}'], cwd=target_path)

        return {'status': 'success', 'message': f'Manuscrito {repo_name} creado exitosamente.'}
    except Exception as e:
        logging.error(f"Error creando manuscrito {repo_name}: {e}", exc_info=True)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        return json_response({'error': 'Error interno del servidor al crear el manuscrito.'}, status=500)

@view_config(route_name='manuscript_build', request_method='POST', renderer='json')
def build_manuscript(request):
    """Ejecuta el script de compilacion para un manuscrito."""
    repo_name = request.matchdict['name']
    target_path = os.path.join(MANUSCRIPTS_BASE_DIR, repo_name)
    if not os.path.isdir(target_path):
        return json_response({'error': f'Manuscrito "{repo_name}" no encontrado.'}, status=404)

    build_options = request.json_body if request.body else {}
    env_vars = {
        'BUILD_PDF': str(build_options.get('build_pdf', True)).lower(),
        'BUILD_DOCX': str(build_options.get('build_docx', False)).lower(),
    }
    
    logging.info(f"Iniciando build para '{repo_name}' con opciones: {env_vars}")
    try:
        run_command(['bash', 'build/build.sh'], cwd=target_path, env_vars=env_vars)
        output_dir = os.path.join(target_path, 'output')
        generated_files = os.listdir(output_dir) if os.path.isdir(output_dir) else []
        return {'status': 'success', 'message': f'Build de {repo_name} completado.', 'outputs': generated_files}
    except Exception as e:
        return json_response({'error': f'Erro en el build de {repo_name}.', 'details': str(e)}, status=500)

@view_config(route_name='manuscript_output')
def download_output(request):
    """Permite descargar un archivo de la carpeta de salida."""
    repo_name = request.matchdict['name']
    filename = request.matchdict['filename']

    if '..' in filename or '/' in filename:
        return json_response({'error': 'Acceso no permitido.'}, status=403)

    file_path = os.path.join(MANUSCRIPTS_BASE_DIR, repo_name, 'output', filename)
    if not os.path.exists(file_path):
        return json_response({'error': 'Archivo no encontrado.'}, status=404)
        
    return FileResponse(file_path, request=request)

if __name__ == '__main__':
    os.makedirs(MANUSCRIPTS_BASE_DIR, exist_ok=True)
    if not os.path.isdir(ROOTSTOCK_TEMPLATE_DIR):
        logging.error(f"Error Critico! La carpeta de la plantilla no se encuentra en: {ROOTSTOCK_TEMPLATE_DIR}")
        logging.error("Asegurate de clonar 'manubot/rootstock' en esa carpeta.")
    else:
        with Configurator() as config:
            config.add_route('manuscript_collection', '/manuscripts')
            config.add_route('manuscript_build', '/manuscripts/{name}/build')
            config.add_route('manuscript_output', '/manuscripts/{name}/output/{filename}')
            config.scan('.')
            
            app = config.make_wsgi_app()

        logging.info(f"Los manuscritos se guardaran en: {MANUSCRIPTS_BASE_DIR}")
        serve(app, host='0.0.0.0', port=PORT)