from fastapi import FastAPI

from monitor_comunitario.api.main import add_security_headers, lifespan
from monitor_comunitario.api.routes_email_internal import router as email_internal_router
from monitor_comunitario.api.routes_hermes_internal import router as hermes_internal_router
from monitor_comunitario.api.routes_monitor_bot import router as monitor_bot_router
from monitor_comunitario.api.routes_users import hermes_callback_router

app = FastAPI(title="Monitor Comunitario internal API", lifespan=lifespan)
app.middleware("http")(add_security_headers)
app.include_router(hermes_callback_router)
app.include_router(hermes_internal_router)
app.include_router(monitor_bot_router)
app.include_router(email_internal_router)
