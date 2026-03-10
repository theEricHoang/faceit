from supabase import create_client, Client

from app.core.config import get_settings


def get_supabase_client() -> Client:
    """Create a Supabase client using the service role key.

    Returns a fresh client each time to prevent auth state mutations
    (e.g. from sign_in_with_password) from leaking between requests
    and breaking RLS-protected table operations.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)
