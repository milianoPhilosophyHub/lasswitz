# manuscript_tool/views/deployment_status.py

import os
import logging
import requests
from pyramid.view import view_config
from ..helpers import json_response

@view_config(route_name='repo_deployment', request_method='POST', renderer='json')
def check_deployment(request):
    """
    Asegura la configuracion de GitHub Pages y luego verifica el estado del despliegue.
    """
    try:
        owner, token = os.getenv('OWNER'), os.getenv('TOKEN')
        if not owner or not token:
            return json_response({'error': 'Configuracion del servidor incompleta'}, status=500)

        repo_name = request.matchdict['repo_name']
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        config_payload = {
            "source": {
                "branch": "gh-pages",
                "path": "/"
            }
        }
        logging.info(f"Asegurando la configuracion de Pages para {repo_name}...")
        config_response = requests.post(api_url, headers=headers, json=config_payload)
        
        if config_response.status_code not in [201, 204]:
             return json_response({
                'error': 'No se pudo configurar GitHub Pages.',
                'details': config_response.json()
            }, status=config_response.status_code)

        logging.info(f"Consultando estado de GitHub Pages para {repo_name}...")
        status_response = requests.get(api_url, headers=headers)

        if status_response.status_code == 200:
            data = status_response.json()
            html_url = data.get('html_url')
            site_status = data.get('status')

            if html_url:
                base_url = html_url.rstrip('/')
                pdf_url = f"{base_url}/manuscript.pdf"
                return {
                    'status': 'success',
                    'deployment_status': site_status,
                    'html_url': html_url,
                    'pdf_url': pdf_url,
                    'message': f'Sitio y PDF para {repo_name} disponibles.'
                }

        elif status_response.status_code == 404:
            logging.warning(f"Aun no se encuentra el despliegue para {repo_name}.")
            return json_response({
                'status': 'pending',
                'message': 'Despliegue en proceso.'
            }, status=202)
        
        else:
             return json_response({
                'error': 'No se pudo obtener el estado del despliegue desde GitHub.',
                'details': status_response.json()
            }, status=status_response.status_code)

    except Exception as e:
        logging.error(f"Error interno en DEPLOY: {e}", exc_info=True)
        return json_response({'error': 'Error interno.'}, status=500)