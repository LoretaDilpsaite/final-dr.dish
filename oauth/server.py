import time
from authlib.integrations.flask_oauth2 import AuthorizationServer
from .models import OAuth2Token
from .grants import AuthorizationCodeGrant

def create_authorization_server(app, db_session, query_client):
    def save_token(token_data, request):
        expires_at = int(time.time()) + token_data['expires_in']
        token = OAuth2Token(
            client_id=request.client.client_id,
            user_id=request.user.get('id'),
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            scope=token_data.get('scope'),
            expires_at=expires_at
        )
        db_session.add(token)
        db_session.commit()

    server = AuthorizationServer(app, query_client=query_client, save_token=save_token)
    server.register_grant(AuthorizationCodeGrant)
    return server
