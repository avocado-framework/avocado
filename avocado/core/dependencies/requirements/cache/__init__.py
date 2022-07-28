# The sqlite based backend is the only implementation
from avocado.core.dependencies.requirements.cache.backends.sqlite import (
    delete_environment,
    delete_requirement,
    get_all_environments_with_requirement,
    is_environment_prepared,
    is_requirement_in_cache,
    set_requirement,
    update_environment,
    update_requirement_status,
)
