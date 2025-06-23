from authlib.oauth2.rfc6749 import grants


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def authenticate_user(self, code):
        user = self.request.user or {'id': 1}  # fallback
        # Optional: check a real user
        # z. B.: db_session.query(User).get(code.user_id)
        return user
