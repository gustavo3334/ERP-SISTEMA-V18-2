from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from gateway.main import Base, CATALOG_DATABASE_URL

config=context.config
config.set_main_option("sqlalchemy.url", CATALOG_DATABASE_URL.replace("%", "%%"))
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata=Base.metadata

def only_commercial(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name.startswith("commercial_")
    return True

def run_migrations_offline():
    context.configure(url=CATALOG_DATABASE_URL, target_metadata=target_metadata, version_table="alembic_version_commercial", include_object=only_commercial, literal_binds=True, dialect_opts={"paramstyle":"named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable=engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, version_table="alembic_version_commercial", include_object=only_commercial, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
