from app.db.supabase import get_supabase_client
import json

c = get_supabase_client()
res = c.table('classes').select('*').execute()
print(json.dumps(res.data or [], indent=2))
