import os, requests, logging
from pyramid.view import view_config
from ..helpers import json_response, run_command

@view_config(route_name='repo_resource', request_method='DELETE', renderer='json')
def delete_manuscript(request):
    """Maneja la ELIMINACION de un repositorio."""
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        repo_name = request.matchdict['repo_name']
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
        headers = {"Authorization": f"token {token}"}
        
        delete_response = requests.delete(api_url, headers=headers)
        
        if delete_response.status_code == 204:
            logging.info(f"Eliminando repositorio...")
            return {'status': 'success', 'message': f'Repositorio {repo_name} eliminado.'}
        elif delete_response.status_code == 404:
            return json_response({'error': 'El repositorio no fue encontrado.'}, status=404)
        else:
            return json_response({'error': 'No se pudo eliminar el repositorio.'}, status=delete_response.status_code)
    except Exception as e:
        logging.error(f"Error interno en DELETE: {e}", exc_info=True)
        return json_response({'error': 'Error interno.'}, status=500)