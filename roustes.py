from flask import Blueprint, request, jsonify
import time
from .models import OAuth2Token

oauth_bp = Blueprint("oauth", __name__)

def register_oauth_routes(app, server, db_session):
    @oauth_bp.route('/oauth/authorize', methods=['GET', 'POST'])
    def authorize():
        user = {'id': 1}
        return server.create_authorization_response(grant_user=user)

    @oauth_bp.route('/oauth/token', methods=['POST'])
    def token():
        return server.create_token_response()

    @oauth_bp.route('/oauth/introspect', methods=['POST'])
    def introspect():
        token_str = request.form.get("token")
        token = db_session.query(OAuth2Token).filter_by(access_token=token_str).first()
        if token and token.expires_at > time.time():
            return jsonify({
                "active": True,
                "scope": token.scope,
                "client_id": token.client_id,
                "exp": token.expires_at
            })
        return jsonify({"active": False})

    app.register_blueprint(oauth_bp)
