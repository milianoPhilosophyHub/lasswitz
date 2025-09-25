import os
import logging
import tempfile
import shutil
import subprocess
import json
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='add_references', request_method='POST', renderer='json')
def add_references(request):
    """
    Agrega una o mas referencias al archivo content/manual-references.json.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        data = request.json_body

        references_to_add = []
        if isinstance(data, list):
            references_to_add = data
        elif isinstance(data, dict):
            references_to_add = [data]
        else:
            return json_response({'error': 'La entrada debe ser un objeto JSON o una lista de objetos.'}, status=400)
        
        for ref in references_to_add:
            if 'id' not in ref:
                return json_response({'error': 'Cada referencia en la lista debe tener una clave "id".'}, status=400)
        
        commit_message = f"Add {len(references_to_add)} manual reference(s)"

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo_name)
            secure_url = f"https://{token}@github.com/{owner}/{repo_name}.git"
            run_command(['git', 'clone', secure_url, repo_name], cwd=temp_dir)
            
            references_path = os.path.join(repo_path, 'content', 'manual-references.json')

            existing_references = []
            if os.path.exists(references_path):
                try:
                    with open(references_path, 'r', encoding='utf-8') as f:
                        existing_references = json.load(f)
                    if not isinstance(existing_references, list):
                        logging.warning(f"El archivo {references_path} no contiene una lista valida.")
                        existing_references = []
                except json.JSONDecodeError:
                    logging.error(f"Error con el JSON en {references_path}.")
                    existing_references = []
            
            existing_references.extend(references_to_add)

            with open(references_path, 'w', encoding='utf-8') as f:
                json.dump(existing_references, f, indent=2, ensure_ascii=False)

            run_command(['git', 'add', references_path], cwd=repo_path)
            
            status_result = run_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout:
                return {'status': 'no_changes', 'message': 'No se detectaron cambios en el archivo.'}

            run_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            run_command(['git', 'push', secure_url, 'main'], cwd=repo_path)

            logging.info(f"{len(references_to_add)} referencia(s) agregada(s) a {repo_name}.")
            return {
                'status': 'success',
                'message': f"{len(references_to_add)} referencia(s) agregada(s) a {repo_name}.",
                'total_references': len(existing_references)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Verifica que el repositorio exista.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno al agregar referencias: {e}", exc_info=True)
        return json_response({'error': 'Error interno en el servidor.'}, status=500)