import os
import logging
import tempfile
import shutil
import subprocess
import yaml
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='update_metadata', request_method='PATCH', renderer='json')
def update_metadata(request):
    """
    Actualiza campos especificos en el archivo content/metadata.yaml.
    Acepta un objeto JSON con las claves a modificar.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        patch_data = request.json_body

        if not isinstance(patch_data, dict):
            return json_response({'error': 'El cuerpo debe ser un objeto JSON.'}, status=400)

        commit_message = "Update metadata via API"
        if 'title' in patch_data:
            commit_message = f"Update title: {patch_data['title'][:50]}"

        temp_dir = tempfile.mkdtemp()
        try:
            repo_path = os.path.join(temp_dir, repo_name)
            secure_url = f"https://{token}@github.com/{owner}/{repo_name}.git"
            run_command(['git', 'clone', secure_url, repo_name], cwd=temp_dir)
            
            metadata_path = os.path.join(repo_path, 'content', 'metadata.yaml')

            if not os.path.exists(metadata_path):
                return json_response({'error': 'El archivo content/metadata.yaml no fue encontrado.'}, status=404)

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f)

            metadata.update(patch_data)

            with open(metadata_path, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, sort_keys=False, allow_unicode=True)

            run_command(['git', 'add', metadata_path], cwd=repo_path)
            
            status_result = run_command(['git', 'status', '--porcelain'], cwd=repo_path)
            if not status_result.stdout:
                return {'status': 'no_changes', 'message': 'No se detectaron cambios en el archivo.'}

            run_command(['git', 'commit', '-m', commit_message], cwd=repo_path)
            run_command(['git', 'push', secure_url, 'main'], cwd=repo_path)

            logging.info(f"Metadatos actualizados en {repo_name}.")
            return {
                'status': 'success',
                'message': f'Metadatos de {repo_name} actualizados.',
                'updated_metadata': metadata
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return json_response({'error': 'Verifica que el repositorio exista.'}, status=500)
    except Exception as e:
        logging.error(f"Error interno al actualizar metadatos: {e}", exc_info=True)
        return json_response({'error': 'Error interno en el servidor.'}, status=500)