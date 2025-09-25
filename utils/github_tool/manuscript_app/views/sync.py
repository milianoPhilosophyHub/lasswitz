import os
import logging
import tempfile
import shutil
import subprocess
import glob
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='repo_content', request_method='PUT', renderer='json')
def sync_manuscript(request):
    """
    Sincroniza todo el contenido .md de la carpeta /content con la solicitud.
    Esta operacion reemplaza todos los archivos .md existentes,
    protegiendo archivos de plantilla como 00.front-matter.md.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        data = request.json_body
        files_to_write = data.get('files')
        commit_message = data.get('commit_message', 'Sync manuscript content via API')

        if not isinstance(files_to_write, dict):
            return json_response({'error': 'El cuerpo debe contener un objeto "files".'}, status=400)

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo_name)
            secure_url = f"https://{token}@github.com/{owner}/{repo_name}.git"

            run_command(['git', 'clone', secure_url, repo_name], cwd=temp_dir)

            content_dir = os.path.join(repo_path, 'content')
            if not os.path.isdir(content_dir):
                os.makedirs(content_dir)

            logging.info("Limpiando archivos .md existentes, excepto plantillas...")
            for md_file in glob.glob(os.path.join(content_dir, '*.md')):
                # Condicion para saltar y proteger el archivo de plantilla
                if os.path.basename(md_file) == '00.front-matter.md':
                    logging.info(f"Protegiendo el archivo de plantilla: {md_file}")
                    continue
                os.remove(md_file)

            # Escribe los nuevos archivos desde la solicitud    
            for filename, content in files_to_write.items():
                if '..' in filename or not filename.endswith('.md'):
                    continue
                file_path = os.path.join(content_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            run_command(['git', 'add', 'content/'], cwd=repo_path)
            
            status_result = run_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout:
                return {'status': 'no_changes', 'message': 'El contenido es identico al existente.'}

            run_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            run_command(['git', 'push', secure_url, 'main'], cwd=repo_path)

            logging.info(f"Contenido sincronizado.")
            return {'status': 'success', 'message': f'Contenido de {repo_name} sincronizado.'}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Verifica que el repositorio exista.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno en SYNC: {e}", exc_info=True)
        return json_response({'error': 'Error interno.'}, status=500)