"""Import every model module so its classes register on Base.metadata.

A model module that's never imported never runs its class body, so its
table never gets added to Base.metadata — which breaks both Alembic
autogenerate and any ORM operation that needs to resolve a foreign key
into another model's table (e.g. Document.tenant_id -> tenants.id).
Anything that needs the full schema (Alembic's env.py, the app's
entrypoint) should import this one module, rather than each keeping its
own list of model imports that can silently drift out of sync as new
model modules are added.
"""

from ascent.documents import models as _documents_models  # noqa: F401
from ascent.shared import models as _shared_models  # noqa: F401